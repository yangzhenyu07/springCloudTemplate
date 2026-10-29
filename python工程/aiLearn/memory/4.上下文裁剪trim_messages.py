#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
4. 上下文裁剪：trim_messages（最新 API 版）
==========================================

【Python 语法看不懂？】闭包、lambda、** 解包、推导式等见 ../PYTHON_SYNTAX.md

【为什么必须裁剪】
    历史是越攒越多的。攒到第 50 轮，prompt 里塞几万 token：
        ① 贵（按 token 计费）
        ② 慢（首字延迟明显变长）
        ③ 可能直接超模型上下文窗口报错


    新版（本文件）：
        trimmed = trim_messages(history, max_tokens=300, token_counter="approximate", strategy="last")
        # 配合 LangGraph checkpointer，存和取全自动（见第 3 个文件）

    本质变化：**从一个「帮你管一切的大类」变成「一个纯函数」**。
    纯函数更好测、更好组合，这也是 LCEL 的整体思路。

【运行】
    ./yzy/Scripts/python.exe "aiLearn/memory/new/4.上下文裁剪trim_messages.py"
"""

import os
from pathlib import Path

import dotenv
from langchain.agents import create_agent
from langchain.agents.middleware import AgentMiddleware
from langchain_core.messages import (
    AIMessage,
    HumanMessage,
    SystemMessage,
    filter_messages,
    get_buffer_string,
    merge_message_runs,
    trim_messages,
)
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
    """构造 DeepSeek 模型（OpenAI 兼容协议，改 base_url 即可）。"""
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


def make_long_history(rounds: int = 10) -> list:
    """造一段很长的历史，用来观察裁剪效果。

    【这是个普通函数不是闭包工厂】外层没参数要捕获，直接返回列表即可。
    """
    messages = [SystemMessage("你是一个贴心的助手，回答用中文。")]
    for i in range(1, rounds + 1):
        messages.append(HumanMessage(f"第 {i} 轮：我想了解一下第 {i} 号话题的详细内容和背景"))
        messages.append(AIMessage(f"第 {i} 轮回复：关于第 {i} 号话题，这里有一段比较长的说明文字给你参考"))
    return messages


def show(messages: list, label: str) -> None:
    """打印一批消息的概览（角色 + 前 20 字）。"""
    print(f"\n  {label}（共 {len(messages)} 条）：")
    for m in messages[:4]:
        print(f"    [{type(m).__name__}] {str(m.content)[:34]}")
    if len(messages) > 4:
        print(f"    ... 省略 {len(messages) - 4} 条")
        for m in messages[-2:]:
            print(f"    [{type(m).__name__}] {str(m.content)[:34]}")




# ---------------------------------------------------------------------------
# 1. trim_messages 基本用法
# ---------------------------------------------------------------------------
def demo_1_basic_trim() -> None:
    section("1. trim_messages 基本用法")

    history = make_long_history(10)
    show(history, "裁剪前")

    # ---------------------------------------------------------------
    # token_counter 有三种给法：
    #   ① "approximate" —— 内置的粗略估算，**不用装 tiktoken**，省事
    #   ② 一个函数      —— 自己实现，比如 len(get_buffer_string(m))
    #   ③ 一个模型对象  —— 用模型的计数 API，最准但要多一次调用
    # ---------------------------------------------------------------
    trimmed = trim_messages(
        history,
        max_tokens=120,
        token_counter="approximate",
        strategy="last",          # 保留【最近】的，丢掉老的
        include_system=True,      # ⚠️ 默认 False！不写就把系统提示词丢了（见 demo_2）
    )
    show(trimmed, "裁剪后（max_tokens=120, strategy=last）")

    print("\n  参数含义：")
    print("    max_tokens      上限（token 数）")
    print("    token_counter   怎么数 token")
    print("    strategy        'last' 保留最近的 / 'first' 保留最早的")
    print("    include_system  是否保留开头的 system 消息 ⚠️ 默认 False")
    print("    allow_partial   允许把一条消息截断一半（默认 False，要么整条留要么整条丢）")

    print("\n  >> trim_messages 是**纯函数**：输入 list，输出 list，不改原对象。")
    print("     （Java 视角：类似 Collections.unmodifiableList 那类工具方法，无副作用）")


# ---------------------------------------------------------------------------
# 2. ⚠️ include_system 的坑 + strategy 对比
# ---------------------------------------------------------------------------
def demo_2_system_and_strategy() -> None:
    section("2. ⚠️ include_system 默认 False，会把人设丢掉")

    history = make_long_history(10)

    without = trim_messages(history, max_tokens=120, token_counter="approximate", strategy="last")
    with_sys = trim_messages(history, max_tokens=120, token_counter="approximate",
                             strategy="last", include_system=True)

    print("  不写 include_system：")
    print("    第 1 条是", type(without[0]).__name__, "→", str(without[0].content)[:30])
    print("    系统提示词还在吗:", any(isinstance(m, SystemMessage) for m in without))

    print("\n  写了 include_system=True：")
    print("    第 1 条是", type(with_sys[0]).__name__, "→", str(with_sys[0].content)[:30])
    print("    系统提示词还在吗:", any(isinstance(m, SystemMessage) for m in with_sys))

    print("\n  ⚠️ 这是最隐蔽的坑：不报错、不警告，只是模型突然「忘了自己是谁」。")
    print("     表现是人设丢失、语气变了、答非所问，很难联想到是裁剪导致的。")
    print("     **生产代码里显式写 include_system=True。**")

    print("\n" + "-" * 62)
    print("  strategy 对比：")

    last = trim_messages(history, max_tokens=120, token_counter="approximate",
                         strategy="last", include_system=True)
    first = trim_messages(history, max_tokens=120, token_counter="approximate",
                          strategy="first")

    print(f"    strategy='last'  → 保留最后几条，末尾是: {str(last[-1].content)[:24]}")
    print(f"    strategy='first' → 保留最前几条，末尾是: {str(first[-1].content)[:24]}")

    print("\n  >> 对话场景几乎都用 'last'：用户关心的是最近说了什么。")
    print("     'first' 适合「开头有重要设定」的场景（比如一段固定的任务说明）。")

    # ⚠️ 实测：include_system 不能配 strategy='first'
    print("\n  ⚠️ 实测再踩一个坑：include_system 配 strategy='first' 会直接报错")
    try:
        trim_messages(history, max_tokens=120, token_counter="approximate",
                      strategy="first", include_system=True)
        print("    没报错（版本行为可能变了）")
    except ValueError as e:
        print(f"    ValueError: {e}")
    print("    原因很好理解：strategy='first' 本来就是从头保留，")
    print("    系统消息必然在里面，再单独说「要保留 system」就没意义了。")


# ---------------------------------------------------------------------------
# 3. allow_partial 和 end_on / start_on
# ---------------------------------------------------------------------------
def demo_3_advanced_options() -> None:
    section("3. 进阶参数：allow_partial / end_on / start_on")

    history = make_long_history(6)

    # ① allow_partial：允许把「边界那条消息」切一半
    #    ⚠️ 实测：光写 allow_partial=True **没有任何效果**，必须同时给 text_splitter。
    long_history = (
        [SystemMessage("你是助手")]
        + [HumanMessage("QUESTION " + "word " * 30) for _ in range(3)]
        + [AIMessage("ANSWER " + "word " * 30) for _ in range(3)]
    )

    def split_by_20(text: str) -> list[str]:
        """text_splitter：把文本切成 20 字符一段（trim_messages 会按段往回塞）。"""
        return [text[i:i + 20] for i in range(0, len(text), 20)]

    strict = trim_messages(long_history, max_tokens=40, token_counter="approximate",
                           strategy="last", include_system=True)
    partial = trim_messages(long_history, max_tokens=40, token_counter="approximate",
                            strategy="last", include_system=True,
                            allow_partial=True, text_splitter=split_by_20)

    print("  max_tokens=40 时（每条原文约 154 字符）：")
    print(f"    allow_partial=False → {len(strict)} 条，各条长度 {[len(str(m.content)) for m in strict]}")
    print(f"    allow_partial=True  → {len(partial)} 条，各条长度 {[len(str(m.content)) for m in partial]}")
    print(f"    被切开的那条内容: {str(partial[-1].content)[:46]} ...")
    print("\n  ⚠️ 实测结论：allow_partial **必须配合 text_splitter 才生效**，")
    print("     只写 allow_partial=True 结果和不写完全一样（我第一次也以为它坏了）。")
    print("  >> 开 partial 能塞得更满，但会切出半句话，一般不开。")

    # ② end_on：保证裁剪结果**以某种消息结尾**
    #    这很重要——很多模型要求历史最后一条是 user，否则行为会很怪
    end_on_human = trim_messages(
        history, max_tokens=100, token_counter="approximate",
        strategy="last", include_system=True,
        end_on=HumanMessage,     # 结尾必须是 HumanMessage
    )
    print(f"\n  end_on=HumanMessage → {len(end_on_human)} 条，最后一条是 {type(end_on_human[-1]).__name__}")

    # ③ start_on：保证以某种消息开头（常配合 strategy='first'）
    print("\n  用法小结：")
    print("    end_on=HumanMessage   结尾必须是用户消息（最常用）")
    print("    end_on=[HumanMessage, SystemMessage]  结尾是这几种之一都行")
    print("    start_on=HumanMessage 开头必须是用户消息")
    print("  >> 这两个参数是为了保证裁剪后的历史**结构合法**，")
    print("     否则可能出现「AI 消息孤零零在最后」这种畸形上下文。")


# ---------------------------------------------------------------------------
# 5. filter_messages 与 merge_message_runs
# ---------------------------------------------------------------------------
def demo_4_filter_and_merge() -> None:
    section("4. 另外两个常用工具：filter_messages / merge_message_runs")

    messages = [
        SystemMessage("你是助手"),
        HumanMessage("我叫yangzhenyu"),
        HumanMessage("我住在广州"),        # 连续两条 human
        AIMessage("你好"),
        AIMessage("很高兴认识你"),         # 连续两条 ai
        HumanMessage("我喜欢打篮球"),
    ]

    # ① merge_message_runs：把连续的同角色消息合并成一条
    merged = merge_message_runs(messages)
    print(f"  merge_message_runs: {len(messages)} 条 → {len(merged)} 条")
    for m in merged:
        print(f"    [{type(m).__name__}] {str(m.content)[:44]}")
    print("  >> 合并能省 token，也能让上下文更干净。")

    # ② filter_messages：按条件过滤
    only_human = filter_messages(messages, include_types=[HumanMessage])
    print(f"\n  filter_messages(include_types=[HumanMessage]) → {len(only_human)} 条")

    no_system = filter_messages(messages, exclude_types=[SystemMessage])
    print(f"  filter_messages(exclude_types=[SystemMessage]) → {len(no_system)} 条")

    by_name = filter_messages(messages, exclude_names=["yangzhenyu"])   # 按 name 过滤
    print(f"  filter_messages(exclude_names=['yangzhenyu']) → {len(by_name)} 条")

    print("\n  常见用途：")
    print("    · 把 tool 调用消息过滤掉再展示给用户看")
    print("    · 只保留 human/ai，丢掉 system（做摘要时常用）")
    print("    · 按 name 区分多智能体（谁说的）")


# ---------------------------------------------------------------------------
# 5. 实战：把裁剪挂到带记忆的 agent 上（最新 API）
# ---------------------------------------------------------------------------
class TrimMessagesMiddleware(AgentMiddleware):
    """每次模型调用前裁剪历史。

    【为什么用 wrap_model_call，不用 before_model】
        before_model 返回的是 **state 更新**，会被写回 checkpointer ——
        那等于把存储里的历史真的删了，违背了「裁剪只影响送给模型的内容」。
        wrap_model_call 只改**本次发给模型**的消息，state 和存储都不动。

        【Java 对照】
            before_model ≈ 改数据库里的数据
            wrap_model_call ≈ 改这次 HTTP 请求的 body，数据库不动
        我们要的是后者。

    ⚠️ 实测坑：request.messages = xxx **已废弃**，必须：
           request.override(messages=trimmed)
        （直接赋值会打 DeprecationWarning）
    """

    def __init__(self, max_tokens: int = 60) -> None:
        self.max_tokens = max_tokens
        self.last_before = 0
        self.last_after = 0

    def wrap_model_call(self, request, handler):
        """模型调用前裁一刀，然后交给下一环。"""
        before = len(request.messages)
        trimmed = trim_messages(
            request.messages,
            max_tokens=self.max_tokens,
            token_counter="approximate",   # 内置近似计数器，不用装 tiktoken
            strategy="last",
            include_system=True,           # ⚠️ 别忘了，否则人设会丢
            end_on=HumanMessage,           # 保证结尾是用户消息
        )
        self.last_before, self.last_after = before, len(trimmed)
        print(f"    [裁剪中间件] 存储 {before} 条 → 送进模型 {len(trimmed)} 条")
        return handler(request.override(messages=trimmed))


def demo_5_wire_into_agent() -> None:
    section("5. 实战：裁剪 + checkpointer 组合（最新 API）")

    print("  老写法是 RunnableWithMessageHistory + RunnablePassthrough.assign，")
    print("  那两个都已废弃。现在这么搭：")
    print()
    print("    class TrimMessagesMiddleware(AgentMiddleware):")
    print("        def wrap_model_call(self, request, handler):")
    print("            trimmed = trim_messages(request.messages, ...)")
    print("            return handler(request.override(messages=trimmed))   # <- override")
    print()
    print("    agent = create_agent(")
    print("        model=llm,")
    print("        checkpointer=InMemorySaver(),              # 记忆")
    print("        middleware=[TrimMessagesMiddleware(60)],    # 裁剪")
    print("    )")

    print()
    print("  ⚠️ 三个实测踩到的点：")
    print("    ① request.messages = xxx 已废弃 → 用 request.override(messages=...)")
    print("    ② 别用 before_model 做裁剪 → 它返回的 state 更新会改存储")
    print("    ③ langgraph 的 create_react_agent 也已废弃 → 用 langchain.agents.create_agent")

    trimmer = TrimMessagesMiddleware(max_tokens=60)
    agent = create_agent(
        model=build_llm(),
        system_prompt="你是助手，回答用中文，尽量简短。",
        checkpointer=InMemorySaver(),
        middleware=[trimmer],
    )

    cfg = {"configurable": {"thread_id": "trim_demo"}}
    questions = [
        "我叫yangzhenyu，记住这个名字",
        "我住在广州，是一座很热闹的城市",
        "我喜欢打篮球，也喜欢游泳，还喜欢跑步",
        "我最喜欢的编程语言是 Java，已经写了九年了",
        "我平时喜欢喝美式咖啡",
    ]

    print()
    print("  连聊 5 轮，观察「存储条数」vs「送进模型的条数」：")
    print()
    for i, q in enumerate(questions, 1):
        r = agent.invoke({"messages": [{"role": "user", "content": q}]}, cfg)
        stored = len(r["messages"])
        print(f"  第 {i} 轮  存储 {stored} 条 → 送进模型 {trimmer.last_after} 条")
        print(f"          Q: {q[:36]}")
        print(f"          A: {str(r['messages'][-1].content)[:44]}")

    print()
    print("  最后一轮结束时：")
    print(f"    checkpointer 里完整历史: {stored} 条（一直都在，没丢）")
    print(f"    实际送进模型: {trimmer.last_after} 条")

    print()
    print("  >> 关键理解：裁剪只影响送给模型的内容，不动存储。")
    print("     所以用户看到的「历史记录」仍是完整的，只是模型看不到那么早的内容。")
    print("     这也是为什么裁剪比「直接删历史」更安全。")
    print()
    print("     对比一下：如果用 before_model 返回裁剪结果，")
    print("     存储会真的被改小 —— 那就不是裁剪，是删历史了。")


def main() -> None:
    print("4. 上下文裁剪 trim_messages（DeepSeek + 最新 API）")
    print("   教材：old/LangChain缓冲记忆组件的使用与解析/1.*")

    demo_1_basic_trim()
    demo_2_system_and_strategy()
    demo_3_advanced_options()
    demo_4_filter_and_merge()

    if os.getenv("DEEPSEEK_API_KEY"):
        demo_5_wire_into_agent()
    else:
        print("\n⚠️ 没读到 DEEPSEEK_API_KEY，跳过第 6 个实战演示。")

    print("\n" + "=" * 62)
    print("全部示例执行完毕。下一个：5.摘要记忆.py")


if __name__ == "__main__":
    main()
