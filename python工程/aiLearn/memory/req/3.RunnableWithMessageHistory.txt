#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
3. 会话记忆：checkpointer（最新 API）+ 已废弃写法对照
====================================================

【Python 语法看不懂？】闭包、lambda、** 解包、推导式等见 ../PYTHON_SYNTAX.md


    新写法一句话：
        agent = create_agent(model=llm, checkpointer=InMemorySaver())
        agent.invoke({"messages": [...]}, config={"configurable": {"thread_id": "xxx"}})

    读历史、拼上下文、写回历史 —— 全由 checkpointer 负责，一行代码都不用写。

【session_id → thread_id：】
    新方式：config={"configurable": {"thread_id":  "xxx"}}
    都是「这段会话的唯一标识」，照着改个 key 名就行。

【本文件实测结论（DeepSeek + langchain-core 1.7.0）】
    · 不传 thread_id：ValueError: Checkpointer requires one or more of the
      following 'configurable' keys: thread_id, checkpoint_ns, checkpoint_id
    · stream() 同样会自动写历史（实测：stream 后再问能答出名字，消息共 4 条）
    · 两维度（用户 + 会话）用 thread_id 拼接 "u_001:s_001" 即可，隔离有效
    · agent.checkpointer.list(None) 可以枚举出所有 thread

【运行】
    ./yzy/Scripts/python.exe "aiLearn/memory/3.RunnableWithMessageHistory.py"
"""

import os
import warnings
from pathlib import Path

import dotenv
from langchain.agents import create_agent
from langchain_core.messages import AIMessage, HumanMessage
from langchain_openai import ChatOpenAI
from langchain_core._api.deprecation import LangChainDeprecationWarning
from langgraph.checkpoint.memory import InMemorySaver


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
    """构造 DeepSeek 模型。

    DeepSeek 是 OpenAI 兼容协议，所以用 ChatOpenAI + 改 base_url 就能接。
    """
    return ChatOpenAI(
        model="deepseek-flash",
        api_key=os.getenv("DEEPSEEK_API_KEY"),
        base_url=os.getenv("DEEPSEEK_API_BASE"),
        temperature=0.3,      # 记忆类演示要稳定一点，别太飘
    )


def section(title: str) -> None:
    """打印分节标题，纯排版用。"""
    print("\n" + "=" * 62)
    print(title)
    print("=" * 62)


def build_memory_agent(system_prompt: str):
    """建一个带记忆的 agent —— 就多一个 checkpointer 参数。"""
    return create_agent(
        model=build_llm(),
        system_prompt=system_prompt,
        checkpointer=InMemorySaver(),     # ← 加这一行，记忆就有了
    )


# ===========================================================================
# 1. 不带记忆 vs 带记忆
# ===========================================================================
def demo_1_with_and_without() -> None:
    section("1. 先看对比：不带记忆 vs 带记忆")

    # ---------- ① 不带记忆 ----------
    llm = build_llm()
    print("【不带记忆】连续问两句：\n")
    q1 = "我叫yangzhenyu，请记住这个名字"
    q2 = "我叫什么名字？"
    print("  Q1:", str(llm.invoke(q1).content)[:60])
    print("  Q2:", str(llm.invoke(q2).content)[:60])
    print("\n  → 第二次压根不知道，因为每次 invoke 都是全新的请求，")
    print("     模型是无状态的，它不会「记得」上一次聊了什么。")

    # ---------- ② 带记忆 ----------
    print("\n【带记忆】同样的两句：\n")
    agent = build_memory_agent("你是一个贴心的助手，回答用中文，尽量简短。")
    config = {"configurable": {"thread_id": "demo1"}}   # thread_id 就是会话 ID

    r1 = agent.invoke({"messages": [{"role": "user", "content": q1}]}, config)
    r2 = agent.invoke({"messages": [{"role": "user", "content": q2}]}, config)
    print("  Q1:", str(r1["messages"][-1].content)[:60])
    print("  Q2:", str(r2["messages"][-1].content)[:60])

    print("\n  → 第二次答出来了。中间发生的事：")
    print("     读历史 → 拼进消息列表 → 调模型 → 把本轮问答写回历史")
    print("     这四步 checkpointer 全自动，我们一行都没写。")

    print(f"\n  状态里现在有 {len(r2['messages'])} 条消息：")
    for m in r2["messages"]:
        print(f"    [{type(m).__name__}] {str(m.content)[:50]}")

    print("\n  >> 注意：第二次 invoke 时我们只传了「我叫什么名字？」这一句，")
    print("     但模型看到了完整 4 条 —— 历史是 checkpointer 自动拼上去的。")


# ===========================================================================
# 2. 多会话隔离
# ===========================================================================
def demo_2_session_isolation() -> None:
    section("2. 多会话隔离：一份代码服务多个用户")

    agent = build_memory_agent("你是助手，回答用中文，尽量简短。")

    print("  thread_id 决定「这是哪段会话」，不同的 id 天然隔离。\n")

    cfg_a = {"configurable": {"thread_id": "user_a"}}
    cfg_b = {"configurable": {"thread_id": "user_b"}}

    r_a1 = agent.invoke({"messages": [{"role": "user", "content": "我喜欢打篮球"}]}, cfg_a)
    r_b1 = agent.invoke({"messages": [{"role": "user", "content": "我喜欢游泳"}]}, cfg_b)

    r_a2 = agent.invoke({"messages": [{"role": "user", "content": "我喜欢什么运动？"}]}, cfg_a)
    r_b2 = agent.invoke({"messages": [{"role": "user", "content": "我喜欢什么运动？"}]}, cfg_b)

    print("  问 user_a「我喜欢什么运动」：")
    print("    ", str(r_a2["messages"][-1].content)[:50])
    print("  问 user_b 同样的问题：")
    print("    ", str(r_b2["messages"][-1].content)[:50])

    print(f"\n  各自的历史条数：")
    print(f"    user_a: {len(r_a2['messages'])} 条")
    print(f"    user_b: {len(r_b2['messages'])} 条")

    print("\n  >> 这就是 SaaS 里「一个应用服务所有客户」的做法：")
    print("     agent 是**无状态**的，状态全在 thread_id 对应的 checkpoint 里。")
    print("     生产上把 InMemorySaver 换成 Redis / Postgres 版即可（见第 7 个文件）。")


# ===========================================================================
# 3. 坑一：它自动写历史，别自己再写一遍
# ===========================================================================
def demo_3_pitfall_duplicate() -> None:
    section("3. ⚠️ 坑一：它会自动写历史，别自己再写一遍")

    agent = build_memory_agent("你是助手，回答中文，尽量简短。")
    config = {"configurable": {"thread_id": "dupe"}}

    r = agent.invoke({"messages": [{"role": "user", "content": "用一句话介绍 Redis"}]}, config)
    print(f"  调一次之后，状态里有 {len(r['messages'])} 条（应该是 2：一问一答）")
    for m in r["messages"]:
        print(f"    [{type(m).__name__}] {str(m.content)[:50]}")

    print("\n  【错误示范】自己手动把历史再拼一遍传进去：")
    # 手动把上一轮的历史 + 新问题一起传 —— 这就是重复的根因
    manual = list(r["messages"]) + [HumanMessage("用一句话介绍 Redis")]
    r2 = agent.invoke({"messages": manual}, config)
    print(f"    结果变成 {len(r2['messages'])} 条")
    print("    ↑ checkpointer 已经存过一遍了，你又传一遍，直接翻倍\n")

    print("  >> 正确做法：**只传本轮的新消息**，历史交给 checkpointer。")
    print("     agent.invoke({'messages': [{'role':'user','content': 本轮一句}]}, config)")
    print("\n     消息重复会让模型看到两遍同样的问题，")
    print("     轻则浪费 token，重则答非所问。")


# ===========================================================================
# 4. 坑二：忘了传 thread_id
# ===========================================================================
def demo_4_pitfall_no_thread() -> None:
    section("4. ⚠️ 坑二：忘了传 thread_id 会怎样")

    agent = build_memory_agent("你是助手，回答中文，尽量简短。")

    print("  不传 config 直接 invoke，看报什么错：\n")
    try:
        agent.invoke({"messages": [{"role": "user", "content": "你好"}]})
        print("  没报错（说明这个版本放宽了限制）")
    except Exception as e:
        print(f"  异常类型: {type(e).__name__}")
        print(f"  异常信息: {str(e)[:180]}")

    print("\n  >> thread_id 是**必传**的，checkpointer 靠它定位会话。")
    print("     和老 API 的 session_id 完全一个性质，只是换了个 key 名。")
    print("     生产上建议封装一层：thread_id 缺失时用默认会话或直接拒绝。")


# ===========================================================================
# 5. 进阶：user_id + session_id 两个维度
# ===========================================================================
def demo_5_two_dimensions() -> None:
    section("5. 进阶：用 user_id + session_id 两个维度定位会话")

    print("  checkpointer 只有一个 thread_id，怎么表达「某用户的某会话」？\n")
    print("  最实用的做法：**拼成一个字符串**\n")
    print("    thread_id = f'{user_id}:{session_id}'   # 例如 u_001:s_001\n")

    agent = build_memory_agent("你是助手，回答中文，尽量简短。")

    def cfg_for(user_id: str, session_id: str) -> dict:
        """把两个维度拼成 thread_id（生产上常用这招）。"""
        return {"configurable": {"thread_id": f"{user_id}:{session_id}"}}

    r = agent.invoke({"messages": [{"role": "user", "content": "我在做一个 Java 项目"}]},
                     cfg_for("u_001", "s_001"))
    print(f"  用 (u_001, s_001) 存了 {len(r['messages'])} 条")

    r2 = agent.invoke({"messages": [{"role": "user", "content": "我在做什么项目"}]},
                      cfg_for("u_001", "s_001"))
    print(f"  同一会话再问 →  {str(r2['messages'][-1].content)[:45]}")

    r3 = agent.invoke({"messages": [{"role": "user", "content": "我在做什么项目"}]},
                      cfg_for("u_001", "s_002"))
    print(f"  换个会话问   →  {str(r3['messages'][-1].content)[:45]}")
    print("     （答不出来才是对的，这是新会话）")

    print("\n  【怎么列出某用户的所有会话】checkpointer 能枚举出全部 thread：")
    try:
        threads = sorted({
            c.config["configurable"]["thread_id"]
            for c in agent.checkpointer.list(None)
        })
        print(f"    已有 thread: {threads}")
        mine = [t for t in threads if t.startswith("u_001:")]
        print(f"    u_001 的会话: {mine}")
        print("    → 按前缀过滤就能做出「会话列表」这种功能")
    except Exception as e:
        print(f"    枚举失败: {type(e).__name__}: {str(e)[:120]}")


# ===========================================================================
# 6. 流式输出 + 记忆
# ===========================================================================
def demo_6_stream() -> None:
    section("6. 流式输出 + 记忆（做打字机效果）")

    agent = build_memory_agent("你是助手，回答中文，尽量简短。")
    config = {"configurable": {"thread_id": "stream_demo"}}

    print("  先用 stream 说一个事实：")
    print("  ", end="", flush=True)
    for chunk in agent.stream(
        {"messages": [{"role": "user", "content": "我的幸运数字是 7，记住它"}]},
        config,
        stream_mode="messages",
    ):
        # chunk 是 (token, metadata) 二元组；只要 AIMessage 的正文
        token = chunk[0] if isinstance(chunk, tuple) else chunk
        if isinstance(token, AIMessage) and token.content:
            print(str(token.content), end="", flush=True)
    print("\n")

    print("  再用 invoke 问，看历史有没有存下来：")
    r = agent.invoke({"messages": [{"role": "user", "content": "我的幸运数字是多少"}]}, config)
    print("  ", str(r["messages"][-1].content)[:60])
    print(f"\n  状态里累计 {len(r['messages'])} 条消息（含刚才 stream 的两条）")

    print("\n  >> stream() 同样会自动写历史，和 invoke() 行为一致。")
    print("     注意 DeepSeek 思考阶段会先吐一些空 chunk（见 model/3 的实测）。")


# ===========================================================================
# 7. 持久化：服务重启后历史还在吗？（生产必看）
# ===========================================================================
def demo_7_persistence() -> None:
    section("7. 持久化：服务重启后历史还在吗？")

    try:
        from langgraph.checkpoint.sqlite import SqliteSaver
    except ImportError:
        print("  未装 langgraph-checkpoint-sqlite，跳过本节。")
        print("  安装：pip install langgraph-checkpoint-sqlite")
        return

    print("  前面用的全是 InMemorySaver —— 数据在**内存**里，")
    print("  **进程一重启就全没了**，只适合 demo 和单测。\n")
    print("  生产要换成落盘版本：\n")
    print("    import sqlite3")
    print("    from langgraph.checkpoint.sqlite import SqliteSaver")
    print("")
    print("    conn = sqlite3.connect('checkpoints.db', check_same_thread=False)")
    print("    checkpointer = SqliteSaver(conn)")
    print("    agent = create_agent(model=llm, checkpointer=checkpointer)")

    print("\n  ⚠️ 实测踩坑：网上最常见的这行在 3.x 会直接报错\n")
    print("    checkpointer = SqliteSaver.from_conn_string('checkpoints.db')   ❌")
    print("    → TypeError: Invalid checkpointer provided.")
    print("       Expected an instance of BaseCheckpointSaver...")
    print("       Received _GeneratorContextManager")
    print()
    print("    原因：3.x 起 from_conn_string 被改成了 @contextmanager，")
    print("    直接赋值拿到的是**上下文管理器**，不是 saver 实例。")
    print("    两种正确写法：")
    print("      ① with SqliteSaver.from_conn_string('x.db') as cp:  # 用完自动关连接")
    print("      ② SqliteSaver(sqlite3.connect('x.db', check_same_thread=False))")
    print("         ↑ 长期运行的服务用这种，连接自己管")
    print("    ⚠️ check_same_thread=False 必须写，否则多线程服务会报错。")

    import sqlite3
    import subprocess
    import sys

    root = Path(__file__).resolve().parents[2]        # 项目根
    db_path = root / "tmp" / "checkpoints_demo.db"
    db_path.parent.mkdir(exist_ok=True)
    if db_path.exists():
        db_path.unlink()                               # 每次 demo 从干净状态开始

    def make_agent():
        """用同一个 db 建一个带持久化记忆的 agent。"""
        conn = sqlite3.connect(str(db_path), check_same_thread=False)
        return conn, create_agent(
            model=build_llm(),
            system_prompt="你是助手，回答中文，尽量简短。",
            checkpointer=SqliteSaver(conn),
        )

    cfg = {"configurable": {"thread_id": "persist_demo"}}

    print(f"\n  【实测 1】写入 sqlite（{db_path.name}）")
    conn, agent = make_agent()
    r1 = agent.invoke({"messages": [{"role": "user", "content": "我叫老王，记住这个名字"}]}, cfg)
    print(f"    存进去: {str(r1['messages'][-1].content)[:40]}")
    conn.close()                                       # 关连接 = 服务停了

    print("\n  【实测 2】模拟重启：重新开连接，问它我叫什么")
    conn2, agent2 = make_agent()
    r2 = agent2.invoke({"messages": [{"role": "user", "content": "我叫什么名字"}]}, cfg)
    print(f"    答: {str(r2['messages'][-1].content)[:50]}")
    print(f"    状态里累计 {len(r2['messages'])} 条消息 → 历史确实还在")
    conn2.close()

    print("\n  【实测 3】直接看 sqlite 里存了什么")
    try:
        c = sqlite3.connect(str(db_path))
        for (name,) in c.execute("select name from sqlite_master where type='table'"):
            n = c.execute(f'select count(*) from "{name}"').fetchone()[0]
            print(f"    表 {name}: {n} 行")
        print("    checkpoints 列:", [d[1] for d in c.execute("PRAGMA table_info(checkpoints)")])
        print("    → 对话是**序列化**后存在 checkpoint 字段里，不是明文消息表")
        c.close()
    except Exception as e:
        print(f"    查询失败: {e}")

    print("\n  【实测 4】起一个**全新的 python 进程**读同一个库（真·重启）")
    probe = db_path.parent / "_probe_persist.py"
    probe.write_text(
        "# -*- coding: utf-8 -*-\n"
        "import os, sqlite3, dotenv\n"
        "from pathlib import Path\n"
        "dotenv.load_dotenv(r'{env}')\n"
        "from langchain.agents import create_agent\n"
        "from langchain_openai import ChatOpenAI\n"
        "from langgraph.checkpoint.sqlite import SqliteSaver\n"
        "llm = ChatOpenAI(model='deepseek-flash', api_key=os.getenv('DEEPSEEK_API_KEY'),\n"
        "                 base_url=os.getenv('DEEPSEEK_API_BASE'), temperature=0.3)\n"
        "conn = sqlite3.connect(r'{db}', check_same_thread=False)\n"
        "agent = create_agent(model=llm, system_prompt='回答中文，20字内',\n"
        "                     checkpointer=SqliteSaver(conn))\n"
        "r = agent.invoke({{'messages': [{{'role': 'user', 'content': '我叫什么名字'}}]}},\n"
        "                 {{'configurable': {{'thread_id': 'persist_demo'}}}})\n"
        "print('  子进程答:', str(r['messages'][-1].content)[:50])\n"
        "print('  子进程看到', len(r['messages']), '条历史消息')\n"
        "conn.close()\n".format(env=str(_ENV_PATH).replace("\\", "/"), db=str(db_path).replace("\\", "/")),
        encoding="utf-8",
    )
    try:
        p = subprocess.run(
            [sys.executable, str(probe)],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
            env=dict(os.environ, PYTHONIOENCODING="utf-8"), cwd=str(root), timeout=300,
        )
        for line in (p.stdout or "").strip().splitlines():
            print("    " + line)
        if p.returncode != 0:
            print(f"    （子进程退出码 {p.returncode}: {(p.stderr or '')[:200]}）")
    except Exception as e:
        print(f"    子进程跑失败: {type(e).__name__}: {str(e)[:150]}")
    finally:
        probe.unlink(missing_ok=True)

    print("\n  >> 选型：")
    print("     demo / 单测        → InMemorySaver（内存，重启即丢）")
    print("     单机 / 中小规模    → langgraph-checkpoint-sqlite（本节的写法）")
    print("     多实例 / 分布式    → langgraph-checkpoint-postgres")
    print("  ⚠️ 生产别用 InMemorySaver —— 重启一次用户历史全没。")


def main() -> None:
    print("3. 会话记忆：checkpointer（最新 API）")

    if not os.getenv("DEEPSEEK_API_KEY"):
        print("\n❌ 没读到 DEEPSEEK_API_KEY，请检查 .env：", _ENV_PATH)
        return

    demo_1_with_and_without()
    demo_2_session_isolation()
    demo_3_pitfall_duplicate()
    demo_4_pitfall_no_thread()
    demo_5_two_dimensions()
    demo_6_stream()
    demo_7_persistence()

    print("\n" + "=" * 62)
    print("全部示例执行完毕。下一个：4.上下文裁剪trim_messages.py")
    print()
    print("💡 主线已全部换成 LangGraph checkpointer（官方推荐）。")
    print("   checkpointer 选型/持久化详见 7.记忆选型与LangGraph方案.py")


if __name__ == "__main__":
    main()
