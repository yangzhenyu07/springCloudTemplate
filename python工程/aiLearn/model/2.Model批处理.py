#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
2. Model 批处理（最新 API 版）
==============================


    新版：
        chain = prompt | llm | StrOutputParser()
        chain.batch([{"query": "..."}, {"query": "..."}])
        ↑ 直接传「原始变量字典列表」，渲染由链路内部完成

    这个差别看着小，但在有几十个输入时，旧写法要写一长串 prompt.invoke()，
    新写法就是干净的一个列表。

【为什么要用 batch 而不是 for 循环？】
    batch() 内部是并发的。本文件会实测给你看：
    同样的 N 个请求，串行和并发的耗时差距有多大。

【运行】
    ./yzy/Scripts/python.exe aiLearn/model/new/2.Model批处理.py
"""

import os
import time
from pathlib import Path

import dotenv
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnableConfig
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
    """构造 DeepSeek 模型（参数含义见 1.LLM与ChatModel使用技巧.py）"""
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
# 1. 最基本的 batch
# ---------------------------------------------------------------------------
def demo_1_basic_batch() -> None:
    section("1. 基础用法：一次并发处理多组输入")

    prompt = ChatPromptTemplate.from_messages([
        ("system", "你是一个翻译助手，只输出译文，不要解释。"),
        ("human", "把下面这句话翻译成{target}：\n\n{text}"),
    ])
    chain = prompt | build_llm() | StrOutputParser()

    # 注意：这里传的是「变量字典的列表」，不需要预先渲染
    inputs = [
        {"target": "英语", "text": "分布式锁要注意死锁问题"},
        {"target": "日语", "text": "数据库连接池满了"},
        {"target": "法语", "text": "接口响应超时"},
    ]

    start = time.perf_counter()
    results = chain.batch(inputs)
    cost = time.perf_counter() - start

    for inp, out in zip(inputs, results):
        print(f"  [{inp['target']}] {out}")
    print(f"\n  共 {len(results)} 条，耗时 {cost:.2f}s")
    print("  >> batch 返回的是列表，顺序和输入一一对应（不会乱序）")


# ---------------------------------------------------------------------------
# 2. 串行 vs 并发：实测对比
# ---------------------------------------------------------------------------
def demo_2_serial_vs_batch() -> None:
    section("2. 实测：串行 invoke 循环 vs 并发 batch")

    prompt = ChatPromptTemplate.from_template("用一句话解释：{topic}")
    llm = build_llm()
    chain = prompt | llm | StrOutputParser()

    topics = [{"topic": t} for t in ["Redis", "Kafka", "Nginx", "Docker"]]

    # 串行：一个一个跑，每个都要等上一个返回
    start = time.perf_counter()
    for t in topics:
        chain.invoke(t)
    serial_cost = time.perf_counter() - start

    # 并发：batch 内部并发发出请求
    start = time.perf_counter()
    chain.batch(topics)
    batch_cost = time.perf_counter() - start

    print(f"  串行 invoke 循环 : {serial_cost:.2f}s")
    print(f"  并发 batch       : {batch_cost:.2f}s")
    if batch_cost > 0:
        print(f"  提速             : {serial_cost / batch_cost:.2f}x")
    print("\n  >> 请求越多，差距越明显。批量标注/翻译场景必用 batch。")
    print("  >> 注意：别一次塞太多，容易触发厂商限流（429）。")


# ---------------------------------------------------------------------------
# 3. max_concurrency：控制并发上限
# ---------------------------------------------------------------------------
def demo_3_max_concurrency() -> None:
    section("3. max_concurrency —— 限制并发数，防止被限流")

    prompt = ChatPromptTemplate.from_template("用10个字概括：{topic}")
    chain = prompt | build_llm() | StrOutputParser()

    # 用真实的技术名词，主题太抽象模型会反问"请补充内容"
    inputs = [{"topic": t} for t in ["Redis", "Kafka", "Nginx", "Docker", "gRPC", "etcd"]]

    # RunnableConfig 里的 max_concurrency 控制同时最多几个请求在飞
    # 这是对接限流严格的厂商时最重要的参数
    config = RunnableConfig(max_concurrency=2)

    start = time.perf_counter()
    results = chain.batch(inputs, config=config)
    cost = time.perf_counter() - start

    print(f"  {len(inputs)} 个请求，并发上限=2，耗时 {cost:.2f}s")
    print("  前两条结果预览:")
    for r in results[:2]:
        print("   -", r)
    print("\n  >> 生产经验：并发数按厂商的 RPM/TPM 限额来定，")
    print("     先小后大试探，遇到 429 就降并发 + 加重试。")


# ---------------------------------------------------------------------------
# 4. return_exceptions：部分失败不拖垮整批
# ---------------------------------------------------------------------------
def demo_4_return_exceptions() -> None:
    section("4. return_exceptions —— 单条失败不影响整批")

    prompt = ChatPromptTemplate.from_template("{q}")
    chain = prompt | build_llm() | StrOutputParser()

    inputs = [
        {"q": "说下 Java 里 try-with-resources 的关闭顺序"},
        {"q": "说下 MySQL 索引的最左前缀原则"},
    ]

    # 默认行为：任何一条失败，整个 batch 抛异常
    # 加上 return_exceptions=True：失败的那一格返回异常对象，其余正常返回
    results = chain.batch(inputs, config=RunnableConfig(return_exceptions=True))

    for i, r in enumerate(results, 1):
        if isinstance(r, Exception):
            print(f"  [{i}] ❌ 失败: {type(r).__name__}: {r}")
        else:
            print(f"  [{i}] ✅ {r[:50]}...")

    print("\n  >> 批量跑几千条时这个参数很重要：")
    print("     不会因为一条脏数据导致前面几千条结果全丢。")


# ---------------------------------------------------------------------------
# 5. 成本提醒
# ---------------------------------------------------------------------------
def demo_5_cost_tip() -> None:
    section("5. 批处理成本提醒（重要）")

    llm = build_llm()
    r = llm.invoke("用一句话解释什么是幂等性")
    usage = r.usage_metadata or {}
    print("  单次调用的 token 消耗:", usage)
    if usage.get("output_token_details"):
        print("  输出明细:", usage["output_token_details"])
        print("  >> 注意 reasoning 字段：DeepSeek 会输出「思考过程」的 token，")
        print("     这部分也是要计费的，所以 max_tokens 别设太小，否则思考被截断。")

    print("\n  >> batch 只是【并发】，【不会】帮你省钱。")
    print("     每条请求照样独立计费。")
    print("\n  >> 真正省钱的三个手段：")
    print("     1. 缩短上下文（用 trim_messages 裁剪历史，见 prompts 目录的示例）")
    print("     2. 限制输出长度（max_tokens）")
    print("     3. 命中厂商的缓存（DeepSeek 的 usage 里有 cache_read 字段）")


def main() -> None:
    print("2. Model 批处理（DeepSeek + 最新 API）")
    demo_1_basic_batch()
    demo_2_serial_vs_batch()
    demo_3_max_concurrency()
    demo_4_return_exceptions()
    demo_5_cost_tip()
    print("\n" + "=" * 62)
    print("全部示例执行完毕。")


if __name__ == "__main__":
    main()
