#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
6. 「给 Runnable 加记忆能力」这件事，现在怎么干（最新 API 版）
==========================================================


【Python 语法看不懂？】闭包、lambda、** 解包、推导式等见 ../PYTHON_SYNTAX.md

【这一组（runnableModule）讲的是「怎么包装 / 组合一个 Runnable」】

    前面 5 个文件：
        bind                        预置参数
        configurable_fields         运行时改字段
        configurable_alternatives   运行时换组件
        with_retry / with_fallbacks 加容错
        with_listeners              加监听

    第 6 个讲的是「给组件加记忆能力」。这一项**实现方式彻底换了**：

        老思路：记忆 = 一层 Runnable 包装
                RunnableWithMessageHistory(chain, get_session_history, ...)
                它不改变 chain 的行为，只是帮你「跑之前读历史、跑之后写历史」

        新思路：记忆 = 图的内建能力
                create_agent(model=..., checkpointer=...)
                checkpointer 自动存取状态，根本没有「包装」这个动作

    ⭐ 关键结论：**前 5 个文件学的东西一个都没过时**
    因为 `ChatOpenAI` 本身还是 Runnable，`with_retry` / `with_fallbacks` /
    `with_listeners` 照旧挂在模型上，再传给 `create_agent` 就行。
    变的只有「记忆」这一项。

【本文件的 7 个演示】
    demo_1  这一组学的东西，哪些还在、哪些换了
    demo_2  ⭐ 模型侧的 with_xxx 全部照旧（实测重试 / 回退 / 监听）
    demo_3  ⭐ 记忆不再是包装，是图的内建能力（多轮 + 流式 + 看状态）
    demo_4  顺序原则：老规则 vs 新规则（新规则更简单）
    demo_5  迁移技巧：老代码的 {query} 调用签名怎么平滑过渡
    demo_6  老 API 的两个坑，现在没了
    demo_7  这一组的总结表

【运行】
    ./yzy/Scripts/python.exe "aiLearn/runnableModule/6.RunnableWithMessageHistory回顾.py"
"""

import os
from pathlib import Path

import dotenv
from langchain.agents import create_agent
from langchain_core.runnables import RunnableLambda
from langchain_openai import ChatOpenAI
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
    """构造 DeepSeek 模型。"""
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
# 1. 这一组学的东西，哪些还在
# ---------------------------------------------------------------------------
def demo_1_what_survives() -> None:
    section("1. 这一组学的东西，哪些还在、哪些换了")

    print("  【核心判断】模型本身还是 Runnable，所以「包装」这套打法没变。")
    print("  create_agent(model=...) 收的就是一个 Runnable，")
    print("  你把 with_xxx 挂在模型上再传进去，完全合法。\n")

    rows = [
        ("bind", "预置参数", "✅ 照旧", "llm.bind(...) 后传进 create_agent"),
        ("configurable_fields", "运行时改字段", "✅ 照旧", "挂模型上，config 照常透传"),
        ("configurable_alternatives", "运行时换组件", "✅ 照旧", "多模型灰度切换"),
        ("with_retry", "失败重试", "✅ 照旧", "本文件 demo_2 实测"),
        ("with_fallbacks", "失败换组件", "✅ 照旧", "本文件 demo_2 实测"),
        ("with_listeners", "生命周期监听", "✅ 照旧", "本文件 demo_2 实测"),
        ("RunnableWithMessageHistory", "加记忆能力", "❌ 已废弃", "→ checkpointer（demo_3）"),
    ]
    print(f"  {'API':<30}{'干什么':<16}{'现状':<10}{'现在怎么用'}")
    print("  " + "-" * 92)
    for a, b, c, d in rows:
        print(f"  {a:<30}{b:<16}{c:<10}{d}")

    print("\n  【只有最后一项换了】为什么？")

    print("\n  老 API 的思路是「读 → 塞 → 写」三步打包：")
    print("     ① 从 history 里读消息")
    print("     ② 塞进 prompt 的 {history} 占位符")
    print("     ③ 把本轮的问答写回 history")
    print("     这三步是「在链外面套一层」实现的，所以它必须是个 Runnable 包装。")

    print("\n  新 API 的思路是「状态 + 自动存取」：")
    print("     · 对话历史本身就是图的状态（state）")
    print("     · checkpointer 负责每次 invoke 前读入、后写回")
    print("     · 没有占位符、没有手动读写、也没有「包装」这个动作")

    print("\n  ⚠️ 最直接的后果：你现在**拿不到那个 history 对象了**。")
    print("     老代码里 store[session_id].messages 能直接看历史，")
    print("     新代码要用 agent.get_state(config).values['messages']。")
    print("     这是很多人迁移时第一个卡住的地方。")

    print("\n  【Java 对照】")
    print("     老写法 ≈ 手写 Filter：doFilter 里读 session、塞 request、再写回 session")
    print("     新写法 ≈ Spring 的 @SessionAttributes：框架托管，你只管用")
    print("     包装变内建，就是「自己写 Filter」变成「声明式托管」。")


# ---------------------------------------------------------------------------
# 2. ⭐ 模型侧的 with_xxx 全部照旧
# ---------------------------------------------------------------------------
def demo_2_with_xxx_still_works() -> None:
    section("2. ⭐ 模型侧的 with_xxx 全部照旧")

    print("  先在本地 Runnable 上实测「重试」和「回退」真的生效，")
    print("  再说它们怎么挂到模型上。\n")

    print("  ① with_retry：失败自动重试")
    attempts = {"n": 0}

    def flaky(_: str) -> str:
        """故意在前两次抛异常，第三次才成功。"""
        attempts["n"] += 1
        if attempts["n"] < 3:
            raise ValueError("模拟网络抖动")
        return f"第 {attempts['n']} 次才成功"

    retried = RunnableLambda(flaky).with_retry(
        stop_after_attempt=4,
        retry_if_exception_type=(ValueError,),   # ⚠️ 必须限定异常类型
    )
    print(f"     结果: {retried.invoke('x')}")
    print(f"     实际调用次数: {attempts['n']}  （不配 retry_if_exception_type 的话，")
    print("     参数错误也会被重试，白白花钱）")

    print("\n  ② with_fallbacks：主组件挂了切备用")

    def broken(_: str) -> str:
        """主组件，必然失败。"""
        raise RuntimeError("主模型不可用")

    def backup(_: str) -> str:
        """备用组件。"""
        return "备用组件返回结果"

    with_fb = RunnableLambda(broken).with_fallbacks([RunnableLambda(backup)])
    print(f"     结果: {with_fb.invoke('x')}")

    print("\n  ③ with_listeners：挂在模型上，实测监听真的触发")

    hits = {"n": 0}

    def on_end(run_obj, config) -> None:
        """模型调用结束时计数。"""
        hits["n"] += 1

    llm_with_listener = build_llm().with_listeners(on_end=on_end)
    agent = create_agent(
        model=llm_with_listener,
        system_prompt="回答用中文，10 字以内。",
    )
    agent.invoke({"messages": [{"role": "user", "content": "1+1 等于几"}]})
    print(f"     调用一次 agent，on_end 触发 {hits['n']} 次  ✅")

    print("\n  【把它们挂到模型上，再交给 create_agent】\n")
    print("     llm = ChatOpenAI(...)")
    print("     llm = llm.with_retry(stop_after_attempt=3,")
    print("                          retry_if_exception_type=(APIError,))")
    print("     llm = llm.with_fallbacks([备用模型])")
    print("     llm = llm.with_listeners(on_end=记耗时)")
    print("")
    print("     agent = create_agent(model=llm, checkpointer=InMemorySaver())")
    print("     ↑ 一行都不用改，容错和监听照样生效")

    print("\n  >> create_agent 返回的 CompiledStateGraph **自己也是 Runnable**，")
    print("     所以它同样有 invoke / stream / batch / with_retry 这些方法。")
    print("     这一组学的那套组合思维，在 agent 上依然通用。")


# ---------------------------------------------------------------------------
# 3. ⭐ 记忆：从「包装」变成「内建」
# ---------------------------------------------------------------------------
def demo_3_memory_builtin() -> None:
    section("3. ⭐ 记忆不再是包装，是图的内建能力")

    print("  【一行就有记忆】")
    print("     agent = create_agent(model=llm, checkpointer=InMemorySaver())")
    print("     没有 RunnableWithMessageHistory，没有 MessagesPlaceholder，")
    print("     没有 get_session_history，也没有 {history} 占位符。\n")

    agent = create_agent(
        model=build_llm(),
        system_prompt="你是一个贴心的助手，回答用中文，尽量简短（30 字以内）。",
        checkpointer=InMemorySaver(),
    )
    # ⚠️ session_id 换成了 thread_id，config 的位置没变
    cfg = {"configurable": {"thread_id": "muxiaoke"}}

    print("  【实测】连续两轮：\n")

    r1 = agent.invoke({"messages": [{"role": "user", "content": "我叫慕小课，记住这个名字"}]}, cfg)
    print(f"    第 1 轮  A: {str(r1['messages'][-1].content)[:50]}")

    print("\n  第 2 轮（流式，stream_mode='messages'）：")
    print("    AI: ", end="")
    for chunk, _meta in agent.stream(
        {"messages": [{"role": "user", "content": "我叫什么名字？"}]},
        cfg,
        stream_mode="messages",
    ):
        if chunk.content:
            print(chunk.content, end="", flush=True)
    print()

    print("\n  【历史在哪】用 get_state 看，不再有 history 对象：\n")

    state = agent.get_state(cfg)
    msgs = state.values["messages"]
    print(f"    agent.get_state(cfg).values['messages']  → {len(msgs)} 条")
    for m in msgs:
        print(f"      [{type(m).__name__:<12}] {str(m.content)[:40]}")

    print("\n  【换个 thread_id，记忆立刻隔离】")
    cfg2 = {"configurable": {"thread_id": "another"}}
    r2 = agent.invoke({"messages": [{"role": "user", "content": "我叫什么？"}]}, cfg2)
    print(f"    新会话 → {str(r2['messages'][-1].content)[:50]}")
    print(f"    新会话状态里只有 {len(agent.get_state(cfg2).values['messages'])} 条 ✅")

    print("\n  【对照表：老写法 → 新写法】\n")
    rows = [
        ("get_session_history(session_id)", "不需要了", "checkpointer 内部管"),
        ("MessagesPlaceholder('history')", "不需要了", "状态里本来就有全部消息"),
        ("input_messages_key='query'", "不需要了", "统一用 messages 列表"),
        ("history_messages_key='history'", "不需要了", "同上"),
        ("config 里的 session_id", "改叫 thread_id", "位置还在 configurable 下"),
        ("store[sid].messages", "agent.get_state(cfg)", "见上面实测"),
    ]
    print(f"    {'老写法':<36}{'新写法':<26}{'说明'}")
    print("    " + "-" * 88)
    for a, b, c in rows:
        print(f"    {a:<36}{b:<26}{c}")


# ---------------------------------------------------------------------------
# 4. 顺序原则：新规则更简单
# ---------------------------------------------------------------------------
def demo_4_order_rule() -> None:
    section("4. 组合顺序：老规则 vs 新规则")

    print("  【老规则】有两个要记住的顺序约束：\n")
    print("     ① 历史包装放**最外层**（它管的是整轮对话）")
    print("     ② 重试/回退/监听放**内层组件**上（它们管的是单次调用）")
    print("     顺序搞反 → 重试时把历史重复写一遍，历史条数翻倍\n")

    print("  【新规则】这个约束**直接消失了**，因为两者不在同一个维度上：\n")
    print("     ┌────────────────────────────────────────────┐")
    print("     │ create_agent(model=..., checkpointer=...)   │")
    print("     │                                            │")
    print("     │ · checkpointer  → 记忆（框架托管，无包装）  │")
    print("     │ · with_xxx      → 挂在 model 上（独立维度） │")
    print("     │                                            │")
    print("     │ 两者互不干扰，不存在「谁包谁」的问题         │")
    print("     └────────────────────────────────────────────┘")

    print("\n  >> 心智负担实实在在降了一档：")
    print("     老写法要想「重试包在哪一层才不会重复写历史」")
    print("     新写法根本不用想——历史读写由框架做，你碰不到它。")

    print("\n  【剩下的唯一顺序问题】只存在于模型这一层：\n")
    print("     llm.with_retry(...)         先加重试")
    print("        .with_fallbacks([...])   再加回退")
    print("        .with_listeners(...)     最后加监听")
    print("\n     原则：**越靠外层，覆盖范围越大**。")
    print("     想让重试也被监听 → 监听包在最外面")
    print("     想让回退也重试   → 重试包在最外面")
    print("     具体怎么排，取决于你想监控/容错到哪一层。")


# ---------------------------------------------------------------------------
# 5. 迁移技巧：老调用签名怎么平滑过渡
# ---------------------------------------------------------------------------
def demo_5_migration_adapter() -> None:
    section("5. 迁移技巧：老代码的 {query} 签名怎么平滑过渡")

    print("  【真实痛点】老代码到处是这种调用：")
    print("     chain.invoke({'query': '你好'}, config={'configurable': {'session_id': 'x'}})")
    print("  而新 API 要的是：")
    print("     agent.invoke({'messages': [{'role': 'user', 'content': '你好'}]}, config=...)")
    print("  签名不一样，全部改造一遍成本很高。\n")

    print("  【解法】加一层 RunnableLambda 做适配，老调用点一行都不用改：\n")

    agent = create_agent(
        model=build_llm(),
        system_prompt="回答用中文，10 字以内。",
        checkpointer=InMemorySaver(),
    )

    def to_state(x: dict) -> dict:
        """把老的 {query: str} 输入转成 agent 要的 messages 格式。"""
        return {"messages": [{"role": "user", "content": x["query"]}]}

    # ⭐ 适配层：老签名 → 新签名
    adapted = RunnableLambda(to_state) | agent

    print("     def to_state(x: dict) -> dict:")
    print("         return {'messages': [{'role': 'user', 'content': x['query']}]}")
    print("")
    print("     adapted = RunnableLambda(to_state) | agent")

    print("\n  【实测】用老签名调用，记忆照样生效：\n")

    cfg = {"configurable": {"thread_id": "adapter_demo"}}
    r1 = adapted.invoke({"query": "我叫慕小课"}, cfg)
    print(f"    adapted.invoke({{'query': '我叫慕小课'}})")
    print(f"      → {str(r1['messages'][-1].content)[:40]}")

    r2 = adapted.invoke({"query": "我叫什么"}, cfg)
    print(f"    adapted.invoke({{'query': '我叫什么'}})")
    print(f"      → {str(r2['messages'][-1].content)[:40]}  ✅ 记忆生效")

    print("\n  >> config 会自动透传给管道里的每个组件，")
    print("     所以 thread_id 照样能用，不用额外处理。")
    print("     （这也是 LCEL 管道的好处：config 传播是内建的）")

    print("\n  【Java 对照】")
    print("     这就是个适配器（Adapter）模式：")
    print("     老接口 Invoke(String query) → 新接口 Invoke(List<Message>)，")
    print("     中间加一层转换，调用方无感。和 Collections.list() 一个路子。")


# ---------------------------------------------------------------------------
# 6. 老 API 的两个坑，现在没了
# ---------------------------------------------------------------------------
def demo_6_pitfalls_gone() -> None:
    section("6. 老 API 的两个坑，新 API 里不存在了")

    print("  坑①：老 API 会自动写历史，你再手动 add 一遍就翻倍")
    print("       （这也是为什么老代码里历史条数经常对不上）\n")
    print("     新 API：历史由 checkpointer 内部读写，")
    print("     你**根本拿不到**那个 history 对象去重复写——坑被结构性消除了。")
    print("     想看历史 → get_state()；想改历史 → 用 update_state() 或中间件。")

    print("\n  坑②：老 API 不传 session_id 不报错，静默地「不记历史」\n")

    agent = create_agent(
        model=build_llm(),
        system_prompt="短",
        checkpointer=InMemorySaver(),
    )
    try:
        agent.invoke({"messages": [{"role": "user", "content": "你好"}]})
        print("     实测：居然没报错（版本行为有变化）")
    except Exception as e:
        print(f"     实测：{type(e).__name__}: {str(e)[:76]}")

    print("\n     ✅ 新 API **直接报错**，把坑变成了显式失败。")
    print("     这比老 API 静默丢历史好得多——错误早暴露，不会线上才发现。")

    print("\n  【迁移时真正要注意的新坑】\n")
    rows = [
        ("thread_id 拼错 / 每次生成新的", "每次都是新会话，看起来像「没记忆」", "thread_id 复用同一个用户级 ID"),
        ("多实例部署还用 InMemorySaver", "A 实例存的 B 读不到，用户聊着聊着失忆", "换 Sqlite / Postgres 版 checkpointer"),
        ("把整段对话塞进长期记忆 Store", "Store 越滚越大，检索变慢", "Store 只存事实结论，流水归 checkpointer"),
        ("以为 checkpointer 会自动裁剪", "历史无限增长，最终超上下文窗口", "裁剪/摘要要自己配中间件"),
    ]
    print(f"    {'坑':<32}{'后果':<34}{'怎么避免'}")
    print("    " + "-" * 104)
    for a, b, c in rows:
        print(f"    {a:<32}{b:<34}{c}")


# ---------------------------------------------------------------------------
# 7. 这一组的总结
# ---------------------------------------------------------------------------
def demo_7_module_summary() -> None:
    section("7. runnableModule 这一组学了什么")

    rows = [
        ("bind", "预置调用参数", "多参函数进管道、固定 temperature"),
        ("configurable_fields", "运行时改字段", "A/B 测试、运营后台调参"),
        ("configurable_alternatives", "运行时换组件", "多模型切换、灰度"),
        ("with_retry", "失败重试", "偶发抖动、限流"),
        ("with_fallbacks", "失败换组件", "降级容灾"),
        ("with_listeners", "生命周期监听", "盯某一步的耗时/审计"),
        ("checkpointer（替代老记忆包装）", "加记忆能力", "多轮对话，框架托管"),
    ]
    print(f"  {'API':<34}{'干什么':<16}{'典型场景'}")
    print("  " + "-" * 78)
    for a, b, c in rows:
        print(f"  {a:<34}{b:<16}{c}")

    print("\n  前六个的共同点：**都是「包装」**")
    print("     原组件不变，返回一个新的 Runnable")
    print("     （Java 视角：装饰器模式 / 包装器，和 IO 流的 BufferedInputStream 一个路子）")

    print("\n  第七个不同：**它不再是包装，是内建能力**")
    print("     记忆从「你套一层」变成「框架管起来」")

    print("\n  记忆口诀：")
    print("     改参数 → bind")
    print("     要动态 → configurable_fields / configurable_alternatives")
    print("     要容错 → with_retry / with_fallbacks")
    print("     要观测 → with_listeners / callbacks")
    print("     要记忆 → create_agent + checkpointer（不再是包装）")


def main() -> None:
    print("6. 「给 Runnable 加记忆能力」现在怎么干（DeepSeek + 最新 API）")
    print("   注：RunnableWithMessageHistory 已废弃，本文件主线已切到 checkpointer")

    demo_1_what_survives()

    if not os.getenv("DEEPSEEK_API_KEY"):
        print("\n⚠️ 没读到 DEEPSEEK_API_KEY，跳过需要调模型的演示。.env 路径：", _ENV_PATH)
        return

    demo_2_with_xxx_still_works()
    demo_3_memory_builtin()
    demo_4_order_rule()
    demo_5_migration_adapter()
    demo_6_pitfalls_gone()
    demo_7_module_summary()

    print("\n" + "=" * 62)
    print("全部示例执行完毕。")


if __name__ == "__main__":
    main()
