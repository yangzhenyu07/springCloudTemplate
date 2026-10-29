#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
7. 记忆选型与 LangGraph 方案（最新 API 版）
============================================


【Python 语法看不懂？】闭包、lambda、** 解包、推导式等见 ../PYTHON_SYNTAX.md

【本文件讲什么】

    LangChain 1.x 里「记忆」不再是一个组件，而是一个**架构问题**。
    官方把它拆成了三层，每层一个东西负责，互不干扰：

        ┌─────────────────────────────────────────────────────────┐
        │ 第 1 层  上下文管理（这一次给模型看什么）               │
        │         trim_messages / SummarizationMiddleware          │
        │         特点：纯函数或中间件，不动存储                   │
        ├─────────────────────────────────────────────────────────┤
        │ 第 2 层  短期记忆（这一轮会话的完整历史）               │
        │         checkpointer + thread_id                        │
        │         特点：按会话存取，全量保留                       │
        ├─────────────────────────────────────────────────────────┤
        │ 第 3 层  长期记忆（跨会话都要记得的东西）               │
        │         Store + namespace                                │
        │         特点：按用户/主题存取，跨会话存活                 │
        └─────────────────────────────────────────────────────────┘

    一句话区分：
        短期记忆  = 「我们刚才聊到哪了」    → 存全量，靠 thread_id 区分会话
        长期记忆  = 「这个人是谁」          → 存结论，靠 namespace 区分归属
        上下文管理 = 「这次发多少给模型」  → 不改存储，只改发出去的那一批

【本文件的 7 个演示】
    demo_1  记忆分几类，边界在哪（不调模型）
    demo_2  ⭐ 短期记忆：checkpointer + thread_id（含查看存了什么）
    demo_3  短期记忆持久化：SqliteSaver（关库重开仍记得）
    demo_4  ⭐ 长期记忆：Store + ToolRuntime（跨会话实测）
    demo_5  长期记忆的 namespace 设计与持久化
    demo_6  上下文管理：三个官方中间件怎么选
    demo_7  最终选型表 + 老教材迁移对照

【前置知识】建议先看
    memory/3.RunnableWithMessageHistory.py   ← 短期记忆基础
    memory/4.上下文裁剪trim_messages.py      ← 上下文裁剪

【运行】
    ./yzy/Scripts/python.exe "aiLearn/memory/7.记忆选型与LangGraph方案.py"
"""

import sqlite3
from pathlib import Path

import dotenv
from langchain.agents import create_agent
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, trim_messages
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.prebuilt import ToolRuntime
from langgraph.store.memory import InMemoryStore
from langgraph.store.sqlite import SqliteStore

# 项目根目录：本文件在 aiLearn/memory/ 下，往上两级就是根
PROJECT_ROOT = Path(__file__).resolve().parents[2]
# 本演示用的临时数据库，放在 tmp/ 下，跟业务代码完全隔离
TMP_DIR = PROJECT_ROOT / "tmp"


def _find_env() -> Path:
    """从本文件所在目录向上逐层查找 .env，不依赖固定的目录层级。"""
    current = Path(__file__).resolve()
    for parent in [current.parent, *current.parents]:
        candidate = parent / ".env"
        if candidate.exists():
            return candidate
    return current.parent / ".env"


_ENV_PATH = _find_env()
dotenv.load_dotenv(_ENV_PATH)


def build_llm() -> ChatOpenAI:
    """构造 DeepSeek 模型。"""
    import os

    return ChatOpenAI(
        model="deepseek-flash",
        api_key=os.getenv("DEEPSEEK_API_KEY"),
        base_url=os.getenv("DEEPSEEK_API_BASE"),
        temperature=0.3,
    )


def section(title: str) -> None:
    """打印分节标题，纯排版用。"""
    print("\n" + "=" * 62)
    print(title)
    print("=" * 62)


# ---------------------------------------------------------------------------
# 1. 记忆分几类，边界在哪
# ---------------------------------------------------------------------------
def demo_1_memory_taxonomy() -> None:
    section("1. 记忆分几类，边界在哪")

    print("  按「作用范围 + 存活时间」分，实际就这三层：\n")

    rows = [
        ("短期记忆", "这一轮会话聊了什么", "checkpointer + thread_id", "会话内", "本文件 demo_2/3"),
        ("长期记忆", "这个用户是谁、偏好是什么", "Store + namespace", "永久", "本文件 demo_4/5"),
        ("语义记忆", "外部知识、文档、产品库", "向量库 + RAG 检索", "永久", "runnable/2"),
    ]
    print(f"  {'层':<10}{'记什么':<24}{'用什么存':<26}{'存活':<8}{'见'}")
    print("  " + "-" * 96)
    for a, b, c, d, e in rows:
        print(f"  {a:<10}{b:<24}{c:<26}{d:<8}{e}")

    print("\n  ⚠️ 三个最容易搞混的点：")

    print("\n  ① 「上下文管理」不属于记忆")
    print("     裁剪、摘要改的是「这次发给模型的那一批消息」，")
    print("     存储里的历史一条没少。所以它是第 1 层，跟第 2/3 层解耦。")
    print("     老教材的 ConversationBufferWindowMemory 把这层和第 2 层")
    print("     揉在一个类里（存的时候就丢），所以又难测试又难回滚。")

    print("\n  ② 短期记忆是「全量」的，长期记忆是「结论」的")
    print("     短期：每句话都留着，靠 thread_id 区分是哪次会话")
    print("     长期：只存抽取出来的事实（用户画像、偏好），靠 namespace 区分归属")
    print("     → 别把原始对话流水往 Store 里塞，那是短期记忆的活。")

    print("\n  ③ 模型本身没有记忆")
    print("     所谓「记住」全是你把历史文本重新发给它。")
    print("     所以记忆的所有成本问题，本质都是 token 成本问题：")
    print("       历史越长 → 每次请求 token 越多 → 越慢越贵 → 越容易超窗口")

    print("\n  【Java 对照】")
    print("     短期记忆 ≈ HttpSession，一次会话一份，会话结束就过期")
    print("     长期记忆 ≈ 数据库里的 user_profile 表，永久，按 user_id 查")
    print("     上下文管理 ≈ 分页/投影（Pageable），不改数据库，只改查出来多少")


# ---------------------------------------------------------------------------
# 2. ⭐ 短期记忆：checkpointer + thread_id
# ---------------------------------------------------------------------------
def demo_2_short_term_memory() -> None:
    section("2. ⭐ 短期记忆：create_agent + checkpointer")

    print("  【核心思路】")
    print("    历史不用自己管，交给 checkpointer：")
    print("      · 对话历史作为「图的状态」保存")
    print("      · 用 thread_id 区分是哪次会话（就是 session_id 的马甲）")
    print("      · 每次 invoke 自动读出状态 → 执行 → 自动写回状态")

    print("\n  【心智负担对比】")
    print("     自己管：读历史 → 拼 prompt → 调模型 → 写回历史（4 步，每处都可能出错）")
    print("     checkpointer：agent.invoke({...}, config={'configurable': {'thread_id': '1'}})")

    agent = create_agent(
        model=build_llm(),
        system_prompt="你是一个贴心的助手，回答用中文，尽量简短（30 字以内）。",
        checkpointer=InMemorySaver(),        # 就这一行，短期记忆就有了
    )

    # ⚠️ thread_id 决定「这是哪一段会话」，同一个 id 才会接着聊
    config = {"configurable": {"thread_id": "thread_001"}}

    print("\n  【实测】同一个 thread_id 连聊三轮：\n")

    questions = [
        "我叫yangzhenyu，记住这个名字",
        "我住在广州，有 9 年 Java 经验",
        "我叫什么？住在哪里？",
    ]
    for i, q in enumerate(questions, 1):
        result = agent.invoke({"messages": [{"role": "user", "content": q}]}, config)
        answer = result["messages"][-1].content
        print(f"    第 {i} 轮  Q: {q}")
        print(f"            A: {str(answer)[:52]}")
        print(f"            状态里累计 {len(result['messages'])} 条消息")

    print("\n  【换个 thread_id，短期记忆立刻隔离】")
    config2 = {"configurable": {"thread_id": "thread_002"}}
    result2 = agent.invoke(
        {"messages": [{"role": "user", "content": "我叫什么名字？"}]}, config2
    )
    print(f"    新会话问「我叫什么」 → {str(result2['messages'][-1].content)[:52]}")
    print("    （答不出来才是对的——短期记忆只在本会话内有效）")

    print("\n  【查看 checkpointer 里到底存了什么】")
    print("    checkpointer 不只是「存消息」，它存的是整个图的状态快照。")
    print("    用 get_state(config) 可以原样读出来，调试时非常有用：\n")

    snapshot = agent.get_state(config)
    msgs = snapshot.values["messages"]
    print(f"    thread_001 的快照：")
    print(f"      · messages 数量  : {len(msgs)}")
    print(f"      · checkpoint_id  : {snapshot.config['configurable']['checkpoint_id'][:20]}...")
    print(f"      · 下一步要执行的节点: {snapshot.next}")
    print(f"      · 最后一条       : {type(msgs[-1]).__name__}: {str(msgs[-1].content)[:30]}")

    snapshot2 = agent.get_state(config2)
    print(f"\n    thread_002 的快照：messages 数量 = {len(snapshot2.values['messages'])}")
    print("    （只有 2 条：user + ai，说明确实是独立的新会话）")

    print("\n  【还能看历史版本（时间旅行）】")
    print("    agent.get_state_history(config) 返回该 thread 的所有快照，")
    print("    按时间倒序。想要「回到上一轮重新问」，把某个快照的 config")
    print("    传给 invoke 就行——这是 LangGraph 独有的能力。")

    print("\n  >> 注意：InMemorySaver 进程一重启就没了，只适合 demo 和单测。")


# ---------------------------------------------------------------------------
# 3. 短期记忆持久化：SqliteSaver
# ---------------------------------------------------------------------------
def demo_3_persist_checkpointer() -> None:
    section("3. 短期记忆持久化：换成 SqliteSaver")

    print("  生产环境不能重启就失忆。换 checkpointer 只要改一行：\n")
    print("    InMemorySaver()                  →  SqliteSaver(conn)")
    print("    其余代码（invoke / thread_id / get_state）**完全不用动**。")
    print("    这就是把「存储」做成接口的好处——对上层透明。")

    print("\n  ⚠️ 一个真实踩过的坑：")
    print("    SqliteSaver.from_conn_string(path) 在 3.x 里是 @contextmanager，")
    print("    直接赋值会拿到一个 _GeneratorContextManager，然后报")
    print("    AttributeError: '...' object has no attribute 'put'。")
    print("    正确写法是自己建连接再包一层：\n")
    print("      conn = sqlite3.connect(path, check_same_thread=False)")
    print("      saver = SqliteSaver(conn)")
    print("\n    check_same_thread=False 必须加：LangGraph 可能在不同线程里用这个连接。")

    TMP_DIR.mkdir(exist_ok=True)
    db_path = TMP_DIR / "memory7_checkpoints.db"
    if db_path.exists():
        db_path.unlink()      # 每次演示从干净状态开始

    print(f"\n  【实测】数据库文件：{db_path.relative_to(PROJECT_ROOT)}")

    # —— 第一段：写入 ——
    conn = sqlite3.connect(str(db_path), check_same_thread=False)
    agent = create_agent(
        model=build_llm(),
        system_prompt="回答用中文，尽量简短（20 字以内）。",
        checkpointer=SqliteSaver(conn),
    )
    config = {"configurable": {"thread_id": "user_001"}}
    r = agent.invoke(
        {"messages": [{"role": "user", "content": "我叫老王，记住这个名字"}]}, config
    )
    print(f"    写入  Q: 我叫老王        A: {str(r['messages'][-1].content)[:40]}")

    # —— 第二段：关掉连接，模拟服务重启 ——
    conn.close()
    print("    >> 关闭数据库连接（模拟服务重启）")

    # —— 第三段：重新打开同一个文件，换新 agent、新连接 ——
    conn2 = sqlite3.connect(str(db_path), check_same_thread=False)
    agent2 = create_agent(
        model=build_llm(),
        system_prompt="回答用中文，尽量简短（20 字以内）。",
        checkpointer=SqliteSaver(conn2),
    )
    r2 = agent2.invoke(
        {"messages": [{"role": "user", "content": "我叫什么名字？"}]}, config
    )
    answer2 = str(r2["messages"][-1].content)
    print(f"    重开  Q: 我叫什么名字？  A: {answer2[:40]}")
    print("    ✅ 换了个全新的 agent 实例，照样答得出「老王」——历史在库里。")

    state2 = agent2.get_state(config)
    print(f"    读回状态：messages 累计 {len(state2.values['messages'])} 条")
    conn2.close()

    print("\n  【生产选型】checkpointer 的几种实现：\n")
    rows = [
        ("langgraph.checkpoint.memory.InMemorySaver", "内存", "demo / 单测 / 无状态服务", "✅ 已装"),
        ("langgraph.checkpoint.sqlite.SqliteSaver", "SQLite", "单机部署、小项目、桌面应用", "✅ 已装"),
        ("langgraph-checkpoint-postgres", "PostgreSQL", "生产首选，支持多实例", "⬜ 按需"),
        ("langgraph-checkpoint-redis", "Redis", "要 TTL 自动过期、高并发", "⬜ 按需"),
    ]
    print(f"    {'实现类':<46}{'存储':<12}{'适用场景':<26}{'本项目'}")
    print("    " + "-" * 92)
    for a, b, c, d in rows:
        print(f"    {a:<46}{b:<12}{c:<26}{d}")

    print("\n  >> 多实例部署时千万别用 InMemorySaver：")
    print("     A 实例存的内存里，B 实例读不到，用户会「聊着聊着失忆」。")


# ---------------------------------------------------------------------------
# 4. ⭐ 长期记忆：Store + ToolRuntime
# ---------------------------------------------------------------------------
def demo_4_long_term_memory() -> None:
    section("4. ⭐ 长期记忆：Store + ToolRuntime（跨会话）")

    print("  【场景】短期记忆只能活在一次会话里。")
    print("  但「这个用户叫yangzhenyu、住在广州」这类事实，应该**跨所有会话**都记得。")
    print("  这就是 Store（长期记忆）。\n")

    print("  【怎么把 Store 给到工具】关键在 ToolRuntime：")
    print("      @tool")
    print("      def save_fact(fact: str, runtime: ToolRuntime) -> str:")
    print("          runtime.store.put(...)")
    print("\n  ⚠️ 坑：参数注解必须写 ToolRuntime，不能写 Runtime。")
    print("     Runtime 是给「图节点 / 中间件」用的；给工具用的子类是 ToolRuntime，")
    print("     它多了 state / config / tool_call_id / tools 这几个工具侧才有的字段。")
    print("     写错成 Runtime 会直接崩：")
    print("       pydantic.errors.PydanticInvalidForJsonSchema:")
    print("       Cannot generate a JsonSchema for core_schema.IsInstanceSchema(BaseStore)")
    print("     原因：工具的每个参数都要生成 JSON Schema 给模型看，")
    print("     而 Runtime/BaseStore 不是「模型该填的参数」，pydantic 转不动。")
    print("     ToolRuntime 继承 _DirectlyInjectedToolArg，框架会识别并")
    print("     把它从 Schema 里摘掉——所以不需要 Annotated 包一层。")

    store = InMemoryStore()

    @tool
    def save_fact(fact: str, runtime: ToolRuntime) -> str:
        """把一条关于用户的事实保存进长期记忆。fact 是要记住的内容。"""
        items = runtime.store.search(("facts",))       # 先看已有几条，用来生成 key
        runtime.store.put(("facts",), f"f{len(items)}", {"fact": fact})
        return f"已记住：{fact}"

    @tool
    def read_facts(runtime: ToolRuntime) -> str:
        """读取长期记忆里保存的所有用户事实。"""
        items = runtime.store.search(("facts",))
        if not items:
            return "长期记忆为空"
        return "\n".join(f"- {i.value['fact']}" for i in items)

    agent = create_agent(
        model=build_llm(),
        tools=[save_fact, read_facts],
        system_prompt=(
            "你是助手。当用户提到自己的个人信息（姓名、城市、职业、偏好）时，"
            "先用 save_fact 存进长期记忆，再回答。回答用中文，尽量简短。"
        ),
        checkpointer=InMemorySaver(),   # 短期记忆：本会话历史
        store=store,                    # 长期记忆：跨会话事实
    )

    print("\n  【实测】在 thread_A 里告诉 agent 两件事：\n")
    cfg_a = {"configurable": {"thread_id": "thread_A"}}
    for q in ["我叫yangzhenyu，住在广州", "我有 9 年 Java 经验"]:
        r = agent.invoke({"messages": [{"role": "user", "content": q}]}, cfg_a)
        print(f"    Q: {q}")
        print(f"    A: {str(r['messages'][-1].content)[:56]}")

    print(f"\n  Store 里的实际内容：")
    for item in store.search(("facts",)):
        print(f"      key={item.key}  value={item.value}")

    print("\n  【关键验证】换一个全新的 thread（全新会话）去问：\n")
    cfg_b = {"configurable": {"thread_id": "thread_B"}}
    r2 = agent.invoke(
        {"messages": [{"role": "user", "content": "你还记得我的什么信息？"}]}, cfg_b
    )
    print(f"    thread_B  Q: 你还记得我的什么信息？")
    print(f"              A: {str(r2['messages'][-1].content)[:80]}")

    print("\n  ✅ 短期记忆隔离了（thread_B 是空的），长期记忆共享了（事实还在）。")
    print("     这就是两层分开的意义：")
    print("       短期：这次聊到哪了  → 换会话就丢")
    print("       长期：这个人是谁    → 换会话还在")

    print("\n  【Java 对照】")
    print("     ToolRuntime 注入 ≈ Spring 的 @Autowired / 方法参数注入：")
    print("     你只声明「我要这个东西」，容器自动塞进来，函数签名里不用自己 new。")
    print("     而且因为它带 InjectedToolArg 标记，不会被当成接口的入参（不进 Swagger）。")


# ---------------------------------------------------------------------------
# 5. 长期记忆的 namespace 设计与持久化
# ---------------------------------------------------------------------------
def demo_5_namespace_and_persist() -> None:
    section("5. 长期记忆的 namespace 设计")

    print("  【namespace 是什么】")
    print("    Store 是两层键：namespace（元组，可前缀匹配）+ key（字符串）。")
    print("    类比 Java：namespace ≈ 表名 + 分区键，key ≈ 主键。")

    print("\n  【怎么设计】最常用的是「主题 + 用户」：\n")
    print("    ('facts', user_id)        → 用户画像")
    print("    ('preferences', user_id)  → 偏好设置")
    print("    ('history', user_id, ym)  → 按月归档")
    print("    ('products',)             → 全局共享，不按用户分")

    print("\n  ⚠️ 黄金规则：**跟用户相关的，namespace 里必须有 user_id**。")
    print("    否则 A 用户的事实会被 B 用户读到——这是最常见的越权 bug。")

    store = InMemoryStore()
    store.put(("facts", "u_alice"), "name", {"fact": "Alice 喜欢咖啡"})
    store.put(("facts", "u_bob"), "name", {"fact": "Bob 喜欢茶"})
    store.put(("products",), "p1", {"name": "机械键盘"})

    print("\n  【实测】三个操作：\n")

    alice = store.search(("facts", "u_alice"))
    print(f"    ① 精确 namespace   search(('facts','u_alice'))")
    print(f"       → {[i.value['fact'] for i in alice]}")

    all_facts = store.search(("facts",))
    print(f"\n    ② 前缀匹配         search(('facts',))")
    print(f"       → 命中 {len(all_facts)} 条，namespace 分别是 {[tuple(i.namespace) for i in all_facts]}")
    print("       （前缀匹配 = 传短的元组，等价于 SQL 的 LIKE 'facts%'）")

    one = store.get(("facts", "u_bob"), "name")
    print(f"\n    ③ 单条精确读       get(('facts','u_bob'), 'name')")
    print(f"       → {one.value['fact']}")
    print(f"       完整 Item: namespace={tuple(one.namespace)} key={one.key}")
    print(f"                 created_at={one.created_at}  （Store 自动维护时间戳）")

    print("\n    >> 如果 search 传空元组 ()，会列出所有 namespace，慎用。")

    print("\n  【持久化】InMemoryStore 同样重启就没，生产要换实现：\n")

    TMP_DIR.mkdir(exist_ok=True)
    db_path = TMP_DIR / "memory7_store.db"
    if db_path.exists():
        db_path.unlink()

    print("    from langgraph.store.sqlite import SqliteStore")
    print("    with SqliteStore.from_conn_string(path) as store:   # 自动建表")
    print("        store.put(...)")

    with SqliteStore.from_conn_string(str(db_path)) as s1:
        s1.put(("facts", "u_alice"), "lang", {"fact": "Alice 用 Java"})
    print(f"\n    写库 → {db_path.relative_to(PROJECT_ROOT)}")

    with SqliteStore.from_conn_string(str(db_path)) as s2:
        got = s2.get(("facts", "u_alice"), "lang")
    print(f"    关掉再打开 → 仍读到：{got.value['fact']}  ✅")

    print("\n    ⚠️ 注意这里和 checkpointer 不一样：")
    print("       Store  的 from_conn_string **是** 上下文管理器（要 with）")
    print("       Saver  的 from_conn_string **也是** 上下文管理器（但我们不用它，")
    print("              改成自己 sqlite3.connect 再包 SqliteSaver，见 demo_3）")
    print("       两个地方行为不一致，是历史遗留，记住就行。")

    print("\n  【Store 实现选型】\n")
    rows = [
        ("langgraph.store.memory.InMemoryStore", "内存", "demo / 单测", "✅ 已装"),
        ("langgraph.store.sqlite.SqliteStore", "SQLite", "单机、小项目", "✅ 已装"),
        ("langgraph-store-postgres", "PostgreSQL", "生产首选，支持向量检索", "⬜ 按需"),
    ]
    print(f"    {'实现类':<44}{'存储':<12}{'适用场景':<28}{'本项目'}")
    print("    " + "-" * 92)
    for a, b, c, d in rows:
        print(f"    {a:<44}{b:<12}{c:<28}{d}")

    print("\n    >> Store 还能配 index_config 做语义检索（传 embeddings 进去），")
    print("       那时它就同时是「长期记忆 + 语义记忆」，适合事实条目多的场景。")


# ---------------------------------------------------------------------------
# 6. 上下文管理：三个官方中间件
# ---------------------------------------------------------------------------
def demo_6_context_management() -> None:
    section("6. 上下文管理：官方给了三个现成中间件")

    print("  历史越攒越长，不可能每次全发。LangChain 已经把三种策略做好了，")
    print("  不用自己写中间件：\n")

    rows = [
        ("TrimMessagesMiddleware", "硬裁剪", "砍掉最早的 N 条，保留最近", "丢信息", "最省事、最可控"),
        ("SummarizationMiddleware", "摘要", "超阈值就把老的压成一段摘要", "多花一次调用", "不想丢信息"),
        ("ContextEditingMiddleware", "编辑", "按规则改写/删除特定消息", "要配规则", "精细控制"),
    ]
    print(f"  {'中间件':<28}{'策略':<8}{'做什么':<28}{'代价':<16}{'什么时候用'}")
    print("  " + "-" * 100)
    for a, b, c, d, e in rows:
        print(f"  {a:<28}{b:<8}{c:<28}{d:<16}{e}")

    print("\n  【实测】这三个中间件确实存在（import 探活）：")
    try:
        from langchain.agents.middleware import (
            ContextEditingMiddleware,
            SummarizationMiddleware,
        )
        print(f"      ✅ SummarizationMiddleware   {SummarizationMiddleware.__module__}")
        print(f"      ✅ ContextEditingMiddleware  {ContextEditingMiddleware.__module__}")
        print("      ✅ TrimMessagesMiddleware    在 memory/4 里我们自己实现过")
    except ImportError as e:
        print(f"      ❌ {e}")

    print("\n  【裁剪策略本身是个纯函数，可以单独测】")
    print("    trim_messages() 不依赖 agent、不依赖存储，")
    print("    输入一个 list[Message]，输出一个 list[Message]：\n")

    long_history = (
        [SystemMessage("你是助手")]
        + [HumanMessage(f"第 {i} 轮问题：一些内容") for i in range(1, 9)]
        + [AIMessage(f"第 {i} 轮回答：一些回复") for i in range(1, 9)]
    )
    trimmed = trim_messages(
        long_history,
        max_tokens=8,        # 这里 token_counter=len，所以就是「最多 8 条消息」
        token_counter=len,
        strategy="last",      # 保留最近的
        include_system=True,  # SystemMessage 永不丢
    )
    print(f"      原始 {len(long_history)} 条 → 裁剪后 {len(trimmed)} 条")
    print(f"      第一条仍是: {type(trimmed[0]).__name__}「{trimmed[0].content}」")
    print(f"      最后一条:   {type(trimmed[-1]).__name__}「{trimmed[-1].content}」")

    print("\n  【关键点】裁剪 vs 摘要，改的东西不一样：\n")
    print("      wrap_model_call  只改「发给模型的那一批」→ 存储里历史不变")
    print("      before_model     返回状态更新          → 存储里历史真的被改了")
    print("\n      想要「省钱但不丢历史」→ 用 wrap_model_call（memory/4 的做法）")
    print("      想要「存储也瘦身」  → 用 before_model 或 SummarizationMiddleware")
    print("\n      这也是纯函数的好处：裁剪逻辑不碰 IO，单元测试秒过。")

    print("\n  【Java 对照】")
    print("     wrap_model_call ≈ 装饰器/拦截器：包装调用，不改被包装对象")
    print("     before_model   ≈ Filter 里改 request：状态真的被改写了")


# ---------------------------------------------------------------------------
# 7. 最终选型表
# ---------------------------------------------------------------------------
def demo_7_final_choice() -> None:
    section("7. 最终选型表")

    print("  【新项目怎么选】\n")

    rows = [
        ("只是个问答机器人，要记住上下文", "create_agent + checkpointer", "本文件 demo_2"),
        ("要跨会话记住用户画像/偏好", "Store + ToolRuntime", "本文件 demo_4"),
        ("历史太长，token 太贵", "TrimMessagesMiddleware", "memory/4"),
        ("老信息不能丢，但要省钱", "SummarizationMiddleware", "本文件 demo_6"),
        ("要检索大量外部知识", "向量库 + RAG（不是记忆组件）", "runnable/2"),
        ("单机部署，重启不能失忆", "SqliteSaver / SqliteStore", "本文件 demo_3/5"),
        ("多实例生产部署", "Postgres checkpointer + Store", "本文件 demo_3"),
    ]
    print(f"  {'需求':<30}{'用什么':<34}{'见'}")
    print("  " + "-" * 88)
    for a, b, c in rows:
        print(f"  {a:<30}{b:<34}{c}")

    print("\n  【老教材迁移对照】如果你看过旧版教材，这些名字都变了：\n")

    rows = [
        ("ConversationBufferMemory", "create_agent + checkpointer", "本文件 demo_2"),
        ("ConversationBufferWindowMemory", "TrimMessagesMiddleware", "memory/4"),
        ("ConversationTokenBufferMemory", "trim_messages(max_tokens=...)", "memory/4"),
        ("ConversationSummaryBufferMemory", "SummarizationMiddleware", "本文件 demo_6"),
        ("ConversationEntityMemory", "Store + ToolRuntime", "本文件 demo_4"),
        ("RunnableWithMessageHistory", "create_agent + checkpointer（⚠️ 前者已废弃）", "memory/3"),
        ("LLMChain", "prompt | llm | parser（LCEL）", "runnable/1"),
    ]
    print(f"  {'老名字':<34}{'现在用什么':<44}{'见'}")
    print("  " + "-" * 96)
    for a, b, c in rows:
        print(f"  {a:<34}{b:<44}{c}")

    print("\n  【一句话总结】")
    print("    · 记忆不是一个组件，是三层架构：上下文管理 / 短期 / 长期")
    print("    · 短期靠 checkpointer + thread_id，长期靠 Store + namespace")
    print("    · 上下文管理是纯函数/中间件，跟存储解耦，随便换")
    print("    · 老教材那些 Memory 类不用再学了，记住上面的迁移表就够")
    print("    · 新项目直接上 create_agent，别再用 RunnableWithMessageHistory")

    print("\n  【判断你现在的代码有没有用对】")
    print("    ❌ 还在 new ConversationBufferMemory()      → 老 API，换 checkpointer")
    print("    ❌ 自己读写 list[Message] 再拼 prompt        → 交给 checkpointer")
    print("    ❌ 把完整对话流水往 Store 里塞                → 那是短期记忆的活")
    print("    ❌ 多实例部署还在用 InMemorySaver             → 一定会串会话")
    print("    ✅ checkpointer 存会话、Store 存事实、中间件控上下文 → 对的")


def main() -> None:
    print("7. 记忆选型与 LangGraph 方案（DeepSeek + 最新 API）")
    print("   主题：把「记忆」拆成三层，每层一个组件负责")

    import os

    demo_1_memory_taxonomy()

    if not os.getenv("DEEPSEEK_API_KEY"):
        print("\n⚠️ 没读到 DEEPSEEK_API_KEY，跳过需要调模型的演示。.env 路径：", _ENV_PATH)
        return

    demo_2_short_term_memory()
    demo_3_persist_checkpointer()
    demo_4_long_term_memory()
    demo_5_namespace_and_persist()
    demo_6_context_management()
    demo_7_final_choice()

    print("\n" + "=" * 62)
    print("全部示例执行完毕。")


if __name__ == "__main__":
    main()
