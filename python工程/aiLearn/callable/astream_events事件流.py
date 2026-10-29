#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
3. astream_events 事件流（官方主推的最新方案）
==============================================

【Python 语法看不懂？】闭包、lambda、** 解包、推导式等见 ../PYTHON_SYNTAX.md

【为什么回调不够用，还要有事件流】
    回调（BaseCallbackHandler）有两个痛点：
        ① 要继承一个类、重写一堆方法，写法重
        ② 拿不到"结构化的每一步"，尤其是嵌套链路的中间结果不好取
        ③ 同步回调在异步链路里用起来别扭

    astream_events 换了个思路：**把链路上发生的一切变成一个事件流**，
    你用 `async for` 遍历它，想看哪个事件就看哪个。

        async for event in chain.astream_events(输入, version="v2"):
            if event["event"] == "on_chat_model_stream":
                print(event["data"]["chunk"].content)

    这就像给整条链路装了个"黑匣子"，所有细节都以事件形式吐出来。

【version 参数】
    必须显式写 version="v2"。v1 是早期版本，字段结构不同且已不推荐。
    不写 version 会有警告。

【注意】
    astream_events 是【异步】的，必须在 async 函数里用 async for 遍历。
    脚本入口用 asyncio.run(...) 启动。

【运行】
    ./yzy/Scripts/python.exe "aiLearn/callable/new/astream_events事件流.py"
"""

import asyncio
import os
from pathlib import Path

import dotenv
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI


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
    """构造 DeepSeek 模型"""
    return ChatOpenAI(
        model="deepseek-flash",
        api_key=os.getenv("DEEPSEEK_API_KEY"),
        base_url=os.getenv("DEEPSEEK_API_BASE"),
        temperature=0,
        max_tokens=256,
        timeout=60,
        max_retries=2,
    )


def section(title: str) -> None:
    print("\n" + "=" * 62)
    print(title)
    print("=" * 62)


def build_chain():
    """组装一条最简单的链：prompt → 模型 → 字符串解析器"""
    return ChatPromptTemplate.from_template("{query}") | build_llm() | StrOutputParser()


# ---------------------------------------------------------------------------
# 1. 看一遍完整的事件流
# ---------------------------------------------------------------------------
async def demo_1_all_events() -> None:
    section("1. 完整事件流：一次调用会吐出哪些事件")

    chain = build_chain()
    counts: dict = {}

    # async for 是异步遍历：每产出一个事件就进入一次循环体，不用等全部结束。
    # Java 对照：类似 BlockingQueue 里 while ((e = queue.take()) != null) 不断取，
    # 或 CompletableFuture 的 thenAccept 被回调多次。
    # version="v2" 必须显式指定，v1 结构不同且已过时
    async for event in chain.astream_events({"query": "用一句话介绍 Redis"}, version="v2"):
        name = event["event"]
        counts[name] = counts.get(name, 0) + 1

    print("  实测统计（一次调用产生的事件）：")
    for name, cnt in sorted(counts.items()):
        print(f"    {name:<24} x{cnt}")

    print("\n  >> 事件名的规律：on_<组件>_<阶段>")
    print("     组件：chain / prompt / chat_model / parser / tool / retriever")
    print("     阶段：start / stream / end / error")
    print("  >> on_chat_model_stream 数量最多——模型是一个字一个字吐的")


# ---------------------------------------------------------------------------
# 2. 事件结构解剖
# ---------------------------------------------------------------------------
async def demo_2_event_structure() -> None:
    section("2. 单个事件长什么样")

    chain = build_chain()
    async for event in chain.astream_events({"query": "1+1=?"}, version="v2"):
        if event["event"] == "on_chat_model_start":
            print("  事件的顶层字段:", sorted(event.keys()))
            print()
            for key in ("event", "name", "run_id", "tags"):
                print(f"    {key:<10}: {event.get(key)}")
            print(f"    data 键    : {sorted(event.get('data', {}).keys())}")
            print()
            print("  各字段含义：")
            print("    event     事件类型（用来判断这是哪一步）")
            print("    name      组件名（RunnableSequence / ChatOpenAI 等）")
            print("    run_id    本次运行的唯一 ID，父子链路靠 parent_ids 串起来")
            print("    data      真正的数据，不同事件的 data 结构不同")
            print("    tags      可以给链打标签，用来过滤")
            break


# ---------------------------------------------------------------------------
# 3. 实战一：只关心模型吐字（打字机）
# ---------------------------------------------------------------------------
async def demo_3_typewriter() -> None:
    section("3. 实战：只取模型流式输出做打字机")

    chain = build_chain()
    print("  实时输出: ", end="")
    nonempty = 0
    empty = 0

    async for event in chain.astream_events({"query": "用一句话介绍 Kafka"}, version="v2"):
        # 只处理"模型流式吐字"这一种事件
        if event["event"] == "on_chat_model_stream":
            chunk = event["data"]["chunk"]
            text = chunk.content
            if text:
                nonempty += 1
                print(text, end="", flush=True)
            else:
                empty += 1

    print(f"\n\n  非空片段 {nonempty} 个，空片段 {empty} 个")
    print("\n  ⚠️ 注意那些【空片段】：那是 DeepSeek 的思考(reasoning)阶段，")
    print("     模型在后台打草稿，不吐正文。这一点和 model/3 里的发现一致。")
    print("  >> 做前端时要先显示「思考中...」，否则用户以为卡住了。")


# ---------------------------------------------------------------------------
# 4. 实战二：拿最终输出和 token 用量
# ---------------------------------------------------------------------------
async def demo_4_output_and_usage() -> None:
    section("4. 实战：取最终输出 + token 用量")

    chain = build_chain()
    final_text = None
    usage = None

    async for event in chain.astream_events({"query": "用一句话介绍 Nginx"}, version="v2"):
        # 链结束事件的 data.output 就是最终结果
        if event["event"] == "on_chain_end":
            final_text = event["data"]["output"]

        # 模型结束事件里能拿到 usage_metadata
        if event["event"] == "on_chat_model_end":
            output = event["data"]["output"]
            usage = getattr(output, "usage_metadata", None)

    print("  最终输出:", final_text)
    print("  token 用量:", usage)
    if usage:
        print(f"    输入 {usage.get('input_tokens')} / "
              f"输出 {usage.get('output_tokens')} / "
              f"合计 {usage.get('total_tokens')}")

    print("\n  >> 对比：用回调要继承类、实现 on_llm_end；")
    print("     这里只要判断 event['event'] == 'on_chat_model_end' 就行。")


# ---------------------------------------------------------------------------
# 5. 实战三：区分不同组件（复杂链路才看得出价值）
# ---------------------------------------------------------------------------
async def demo_5_nested_chain() -> None:
    section("5. 实战：嵌套链路里区分每一步")

    # 造一条「先翻译再总结」的两步链（两步都要调模型）
    step1 = ChatPromptTemplate.from_template("把下面内容翻译成英文：\n{query}") | build_llm() | StrOutputParser()
    step2 = ChatPromptTemplate.from_template("用一句话总结这段话：\n{text}") | build_llm() | StrOutputParser()
    two_step = {"text": step1} | step2

    # ---------- ① 先踩坑：只靠 name 分不清谁是谁 ----------
    print("  【踩坑写法】只用 name == RunnableSequence 判断：\n")
    model_calls = 0
    async for event in two_step.astream_events({"query": "分布式锁要防止死锁"}, version="v2"):
        if event["event"] == "on_chat_model_start":
            model_calls += 1
            print(f"    第 {model_calls} 次模型调用（组件: {event['name']}）")
        if event["event"] == "on_chain_end" and event["name"] == "RunnableSequence":
            print(f"    chain 结束 -> {str(event['data']['output'])[:36]}")

    print("\n  ⚠️ 问题：step1、step2、整条链 都叫 RunnableSequence，")
    print("     上面打印了好几次「chain 结束」，根本分不清哪个才是最终结果。")

    # ---------- ② 解法一：用 with_config(run_name=...) 起名字 ----------
    print("\n  【解法一】给每个组件起名字（推荐，最直观）：\n")
    step1_named = (
        ChatPromptTemplate.from_template("把下面内容翻译成英文：\n{query}")
        | build_llm()
        | StrOutputParser()
    ).with_config(run_name="① 翻译")
    step2_named = (
        ChatPromptTemplate.from_template("用一句话总结这段话：\n{text}")
        | build_llm()
        | StrOutputParser()
    ).with_config(run_name="② 总结")
    two_step_named = ({"text": step1_named} | step2_named).with_config(run_name="整条链")

    model_calls = 0
    async for event in two_step_named.astream_events({"query": "分布式锁要防止死锁"}, version="v2"):
        if event["event"] == "on_chat_model_start":
            model_calls += 1
            print(f"    第 {model_calls} 次模型调用")
        # 现在 name 是我们自己起的名字，可以精确匹配
        if event["event"] == "on_chain_end" and event["name"] in ("① 翻译", "② 总结", "整条链"):
            print(f"    [{event['name']}] 完成 -> {str(event['data']['output'])[:40]}")

    print("\n  >> with_config(run_name='xxx') 只是加了个标签，不改任何逻辑，")
    print("     但在事件流 / LangSmith 追踪里能救命——复杂链路必备。")

    # ---------- ③ 解法二：用 parent_ids 判断是不是根链 ----------
    print("\n  【解法二】不想改名？用 parent_ids 判断是不是最外层：\n")
    async for event in two_step.astream_events({"query": "分布式锁要防止死锁"}, version="v2"):
        # 根链（最外层）没有父节点，parent_ids 是空列表
        if event["event"] == "on_chain_end" and not event["parent_ids"]:
            print("    根链结束，这才是最终结果:", event["data"]["output"])

    print(f"\n  共发生 {model_calls} 次模型调用")
    print("  >> 用回调也能统计，但事件流写起来更直观、不用继承类。")
    print("  >> parent_ids 是祖先 run_id 列表，越外层越短，根链为空 []。")


# ---------------------------------------------------------------------------
# 6. 回调 vs 事件流，怎么选
# ---------------------------------------------------------------------------
def demo_6_choose() -> None:
    section("6. 回调 vs 事件流，怎么选")

    print(f"  {'维度':<14}{'回调 BaseCallbackHandler':<32}{'事件流 astream_events'}")
    print("  " + "-" * 78)
    rows = [
        ("写法", "继承类 + 重写方法", "async for 遍历，if 判断"),
        ("适用链路", "同步 / 异步都行", "仅异步（astream_events）"),
        ("拿中间结果", "比较绕", "直接取 event['data']"),
        ("嵌套链路", "靠 run_id 自己串", "parent_ids 自动关联"),
        ("对接监控平台", "LangSmith 就用这个", "也能对接，常用于前端推送"),
        ("学习成本", "要记住一堆方法名", "记住事件名规律即可"),
    ]
    for a, b, c in rows:
        print(f"  {a:<14}{b:<32}{c}")

    print("\n  选型建议：")
    print("   · 做日志/监控/计费这类「旁路」需求     → 回调（更轻，同步异步都能用）")
    print("   · 做流式 UI、进度条、要中间结果     → 事件流（信息最全）")
    print("   · 新项目、全异步架构               → 优先事件流")
    print("   · 要接入 LangSmith 做追踪          → 回调（官方集成方式）")


async def main_async() -> None:
    print("3. astream_events 事件流（DeepSeek + 最新 API）")
    await demo_1_all_events()
    await demo_2_event_structure()
    await demo_3_typewriter()
    await demo_4_output_and_usage()
    await demo_5_nested_chain()
    demo_6_choose()
    print("\n" + "=" * 62)
    print("全部示例执行完毕。")


def main() -> None:
    # asyncio.run 是脚本里启动异步的入口：建事件循环 → 跑 main_async → 跑完关循环。
    # Java 对照：类似 main 里 submit 一个任务到 ExecutorService，再 shutdown() + awaitTermination() 等它跑完。
    asyncio.run(main_async())


if __name__ == "__main__":
    main()
