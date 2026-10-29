#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
3. Model 流式输出（最新 API 版）
================================

    新版：
        chain = prompt | llm | StrOutputParser()
        for chunk in chain.stream({"query": "..."}):
            print(chunk, end="")
        ↑ 直接拿到 str 片段，不用 .content

    关键差别：管道里加了 StrOutputParser 之后，
    流出来的就不再是消息对象，而是可以直接显示的字符串片段。
    前端打字机效果要的正是这个。

【什么是流式？】
    普通调用：等模型把整段话全部生成完，一次性返回（用户盯着空白等几秒）
    流式调用：模型生成一个 token 就推一个过来（用户立刻看到字在往外冒）

    流式不减少总耗时，但大幅改善体感 —— 这是对话类产品的标配。

【运行】
    ./yzy/Scripts/python.exe aiLearn/model/new/3.Model流式输出.py
"""

import os
import time
from pathlib import Path

import dotenv
from langchain_core.messages import AIMessageChunk
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI

def _find_env() -> Path:
    """从本文件所在目录向上逐层查找 .env，不依赖固定的目录层级。

    好处：文件被移动、目录结构调整后依然能找到配置，不用回来改代码。
    """
    current = Path(__file__).resolve()
    for parent in [current.parent, *current.parents]:
        candidate = parent / ".env"
        if candidate.exists():
            return candidate
    return current.parent / ".env"   # 兜底：找不到就放同级


_ENV_PATH = _find_env()
dotenv.load_dotenv(_ENV_PATH)


def build_llm() -> ChatOpenAI:
    """构造 DeepSeek 模型"""
    return ChatOpenAI(
        model="deepseek-flash",
        api_key=os.getenv("DEEPSEEK_API_KEY"),
        base_url=os.getenv("DEEPSEEK_API_BASE"),
        temperature=0,
        max_tokens=512,
        timeout=60,
        max_retries=2,
    )


def section(title: str) -> None:
    print("\n" + "=" * 62)
    print(title)
    print("=" * 62)


# ---------------------------------------------------------------------------
# 1. 最基础的流式（打字机效果）
# ---------------------------------------------------------------------------
def demo_1_basic_stream() -> None:
    section("1. 基础流式：一个个字符往外冒")

    prompt = ChatPromptTemplate.from_messages([
        ("system", "你是技术讲师，用通俗的话解释。"),
        ("human", "{query}"),
    ])
    chain = prompt | build_llm() | StrOutputParser()

    print("问题: 你能简单介绍下 LLM 和 LLMOps 吗？")
    print("回答: ", end="", flush=True)

    # end="" 不换行，flush=True 强制立刻输出到屏幕
    # 这两个参数缺一个就看不到打字机效果
    for chunk in chain.stream({"query": "你能简单介绍下LLM和LLMOps吗?"}):
        print(chunk, end="", flush=True)
    print("\n")


# ---------------------------------------------------------------------------
# 2. 不带解析器时，流出来的是什么
# ---------------------------------------------------------------------------
def demo_2_chunk_type() -> None:
    section("2. 不带 StrOutputParser 时，流出来的是 AIMessageChunk")

    llm = build_llm()
    chunks = list(llm.stream("用一句话介绍Redis"))
    total = len(chunks)
    nonempty_idx = [i for i, c in enumerate(chunks, 1) if c.content]

    print(f"  chunk 总数   : {total}")
    print(f"  非空 chunk   : {len(nonempty_idx)} 个")
    print(f"  首个非空位置 : 第 {nonempty_idx[0] if nonempty_idx else '-'} 个")
    print(f"  拼接后内容   : {''.join(c.content for c in chunks)[:60]}...")

    print("\n  ⚠️ 实测发现（很重要）：前面一大批 chunk 的 content 是空的！")
    print("     那是 DeepSeek 的「思考(reasoning)阶段」——模型在后台打草稿，")
    print("     不吐给前端。真正的正文要等它想完才开始流出来。")
    print("     对应 usage_metadata 里的 output_token_details.reasoning 字段。")
    print("\n  >> 做前端打字机时要考虑这点：前面会有一段「看起来没反应」的时间，")
    print("     最好先显示一个「思考中...」的占位，别让用户以为卡了。")
    print("  >> 加了 StrOutputParser 后，流出来的直接就是 str，这才是前端要的。")


# ---------------------------------------------------------------------------
# 3. 累积拼接：把 chunk 拼回完整消息
# ---------------------------------------------------------------------------
def demo_3_accumulate() -> None:
    section("3. 把 chunk 累积成完整内容")

    llm = build_llm()
    full = None          # 用来累积
    count = 0

    for chunk in llm.stream("用一句话介绍Kafka"):
        # AIMessageChunk 重载了 + 运算符，可以直接相加
        full = chunk if full is None else full + chunk
        count += 1

    print(f"  共收到 {count} 个 chunk")
    print(f"  累积后类型: {type(full).__name__}")
    print(f"  完整内容: {full.content}")

    # 用 StrOutputParser 时，自己拼字符串就行
    print("\n  >> 带解析器版本：自己 += 拼字符串即可")
    text = ""
    for s in (llm | StrOutputParser()).stream("用一句话介绍etcd"):
        text += s
    print(f"     {text}")


# ---------------------------------------------------------------------------
# 4. 实测：首 token 到达时间 (TTFT)
# ---------------------------------------------------------------------------
def demo_4_ttft() -> None:
    section("4. 实测：首 token 延迟 vs 完整响应延迟")

    chain = ChatPromptTemplate.from_template("{q}") | build_llm() | StrOutputParser()
    q = {"q": "用三句话介绍什么是分布式锁"}

    # 非流式：拿到全部内容的时间
    start = time.perf_counter()
    chain.invoke(q)
    total_cost = time.perf_counter() - start

    # 流式：分别测「首个 chunk」和「首个非空内容」
    # 注意这两个不是一回事！见上一节的实测：前面会有一批空 chunk（思考阶段）
    start = time.perf_counter()
    first_chunk_at = None
    first_text_at = None
    for i, chunk in enumerate(chain.stream(q)):
        if i == 0:
            first_chunk_at = time.perf_counter() - start
        if chunk and first_text_at is None:      # chunk 是 str，非空才算真内容
            first_text_at = time.perf_counter() - start
    stream_cost = time.perf_counter() - start

    print(f"  非流式          ：{total_cost:.2f}s 后拿到全部内容")
    print(f"  流式-首个chunk  ：{first_chunk_at:.2f}s（但内容可能是空的）")
    print(f"  流式-首个文字   ：{first_text_at:.2f}s（这才是用户真正看到的）")
    print(f"  流式-全部收完   ：{stream_cost:.2f}s")

    if first_text_at and first_text_at > 0:
        print(f"\n  >> 用户等待感知从 {total_cost:.2f}s 降到 {first_text_at:.2f}s，")
        print(f"     体感提升约 {total_cost / first_text_at:.1f}x。")
    print("  >> 结论：流式总耗时没变，但用户不用干等，这才是它的价值。")
    print("  >> 提醒：别把「首个 chunk」当 TTFT，会被思考阶段的空 chunk 骗到。")


# ---------------------------------------------------------------------------
# 5. 异步流式（Web 服务里用得最多）
# ---------------------------------------------------------------------------
def demo_5_async_stream() -> None:
    section("5. 异步流式 astream（FastAPI/Flask 里用这个）")

    import asyncio

    chain = ChatPromptTemplate.from_template("{q}") | build_llm() | StrOutputParser()

    async def run() -> None:
        print("  异步流式输出: ", end="", flush=True)
        async for chunk in chain.astream({"q": "用一句话介绍Nacos"}):
            print(chunk, end="", flush=True)
        print()

    asyncio.run(run())

    print("\n  >> Web 服务里必须用 astream 而不是 stream：")
    print("     stream 是阻塞的，会卡住整个事件循环，把并发能力直接废掉。")
    print("\n  >> 更进一步可以用 astream_events(version='v2')，")
    print("     它能区分「模型开始/输出中/结束」等生命周期事件，")
    print("     做 token 统计、进度条、链路追踪（LangSmith）都靠它。")


def main() -> None:
    print("3. Model 流式输出（DeepSeek + 最新 API）")
    demo_1_basic_stream()
    demo_2_chunk_type()
    demo_3_accumulate()
    demo_4_ttft()
    demo_5_async_stream()
    print("\n" + "=" * 62)
    print("全部示例执行完毕。")


if __name__ == "__main__":
    main()
