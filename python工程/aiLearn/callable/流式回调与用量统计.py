#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
2. 流式回调与用量统计（实战版）
==============================
教材原文（已归档）：old/回调功能使用技巧.py（旧教材只有基础回调，本文件是新增的实战篇）

【Python 语法看不懂？】闭包、lambda、** 解包、推导式等见 ../PYTHON_SYNTAX.md

【本文件解决两个实际问题】
    ① 流式输出时，怎么在每个字到达时做点什么？（打字机、实时推送前端）
       → 用 on_llm_new_token 钩子

    ② 怎么统计一次/多次调用用了多少 token、花了多久？
       → 在 on_llm_end 里读 usage_metadata，累加到一个统计器里

【关于成本换算的说明】
    本文件只统计【token 数量】，不换算成钱。
    因为各家模型定价会变（而且输入/输出/缓存命中的单价都不一样），
    写死单价容易误导。要算钱请查官方实时定价后再乘。

【⚠️ DeepSeek 的一个注意点】
    实测它的 usage_metadata 里带 output_token_details.reasoning 字段——
    这是模型"思考过程"消耗的 token，【也是要计费的】。
    所以看到 output_tokens 比实际输出文字多很多，别觉得奇怪。

【运行】
    ./yzy/Scripts/python.exe "aiLearn/callable/new/流式回调与用量统计.py"
"""

import os
import time
from pathlib import Path
from typing import Any, Dict, List, Optional
from uuid import UUID

import dotenv
from langchain_core.callbacks import BaseCallbackHandler
from langchain_core.messages import BaseMessage
from langchain_core.output_parsers import StrOutputParser
from langchain_core.outputs import LLMResult
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


# ===========================================================================
# 处理器一：流式逐字回调
# ---------------------------------------------------------------------------
# on_llm_new_token 会在模型每吐出一个片段时被调用一次。
# 注意：它【只在流式调用时触发】（stream / astream），invoke 不会触发。
# ===========================================================================
class StreamPrinter(BaseCallbackHandler):
    """每来一个 token 就打印出来（打字机效果的底层原理）"""

    def __init__(self) -> None:
        self.chunk_count = 0
        self.text = ""

    def on_llm_new_token(self, token: str, **kwargs: Any) -> None:
        """模型流式吐出片段时触发

        参数：
            token   本次到达的文本片段（通常 1~几个字）
            kwargs  其他上下文（run_id 等）
        """
        self.chunk_count += 1
        self.text += token
        # end="" 不换行，flush=True 立刻输出——打字机效果的关键
        print(token, end="", flush=True)


# ===========================================================================
# 处理器二：用量统计器（生产最常用的形态）
# ---------------------------------------------------------------------------
# 思路：把统计状态存在实例属性里，on_llm_end 时累加。
# 同一个 handler 实例在多次调用间复用，就能做累计统计。
# ===========================================================================
class UsageTracker(BaseCallbackHandler):
    """累计统计 token 消耗与耗时"""

    def __init__(self, name: str = "统计器") -> None:
        self.name = name
        self.total_input = 0
        self.total_output = 0
        self.total_calls = 0
        self.total_seconds = 0.0
        self._start_at = 0.0

    def on_chat_model_start(
            self,
            serialized: Dict[str, Any],
            messages: List[List[BaseMessage]],
            **kwargs: Any,
    ) -> None:
        self._start_at = time.time()
        self.total_calls += 1

    def on_llm_end(self, response: LLMResult, **kwargs: Any) -> None:
        self.total_seconds += time.time() - self._start_at

        # usage_metadata 的取用路径：
        #   response.generations[批次][候选].message.usage_metadata
        try:
            usage = response.generations[0][0].message.usage_metadata
        except Exception:
            usage = None

        if usage:
            self.total_input += usage.get("input_tokens", 0) or 0
            self.total_output += usage.get("output_tokens", 0) or 0

            # DeepSeek 会把思考(reasoning)消耗的 token 单列出来
            details = usage.get("output_token_details") or {}
            reasoning = details.get("reasoning", 0)
            if reasoning:
                print(f"    （其中思考过程消耗 {reasoning} tokens）")

    def report(self) -> None:
        """打印累计报表"""
        print(f"\n  ── {self.name} 累计报表 ──")
        print(f"    调用次数  : {self.total_calls}")
        print(f"    输入 token: {self.total_input}")
        print(f"    输出 token: {self.total_output}")
        print(f"    合计 token: {self.total_input + self.total_output}")
        print(f"    总耗时    : {self.total_seconds:.2f}s")


# ---------------------------------------------------------------------------
# 1. on_llm_new_token 流式逐字
# ---------------------------------------------------------------------------
def demo_1_stream_token() -> None:
    section("1. on_llm_new_token —— 流式逐字回调")

    llm = build_llm()
    chain = ChatPromptTemplate.from_template("{query}") | llm | StrOutputParser()

    printer = StreamPrinter()

    # ⚠️ 实测结论：必须用 stream()，用 invoke() 一个片段都收不到！
    #    第一次写这个 demo 时我用了 invoke，结果 chunk_count=0，
    #    说明 on_llm_new_token 只在【流式调用】时才会被触发。
    print("  [错误示范] 用 invoke：")
    chain.invoke({"query": "用一句话介绍 Kafka"}, config={"callbacks": [printer]})
    print(f"    → 收到 {printer.chunk_count} 个片段（可见 invoke 不触发）\n")

    # 正确做法：用 stream 消费
    printer2 = StreamPrinter()
    print("  [正确示范] 用 stream：")
    print("    实时输出: ", end="")
    for _ in chain.stream({"query": "用一句话介绍 etcd"}, config={"callbacks": [printer2]}):
        pass    # 内容已经在回调里打印了，这里只是把流消费完

    print(f"\n\n    共收到 {printer2.chunk_count} 个片段，拼接后 {len(printer2.text)} 字")
    print("  >> 这就是前端打字机效果的原理：每个片段推给前端即可。")
    print("  >> 记住：on_llm_new_token 只在 stream/astream 时触发。")


# ---------------------------------------------------------------------------
# 2. 用量统计：单次
# ---------------------------------------------------------------------------
def demo_2_single_call_usage() -> None:
    section("2. 单次调用的 token 统计")

    llm = build_llm()
    chain = ChatPromptTemplate.from_template("{query}") | llm | StrOutputParser()

    tracker = UsageTracker("单次统计")
    print("  调用中...")
    chain.invoke({"query": "用三句话解释什么是分布式锁"}, config={"callbacks": [tracker]})
    tracker.report()

    print("\n  >> 想换算成金额：查官方定价 × 上面这些 token 数。")
    print("     输入和输出单价通常不一样，缓存命中的更便宜。")


# ---------------------------------------------------------------------------
# 3. 用量统计：多轮累计（handler 实例复用）
# ---------------------------------------------------------------------------
def demo_3_multi_call_usage() -> None:
    section("3. 多轮累计统计 —— 复用同一个 handler")

    llm = build_llm()
    chain = ChatPromptTemplate.from_template("{query}") | llm | StrOutputParser()

    # 关键：handler 实例在循环外创建，状态就能跨调用保留
    tracker = UsageTracker("多轮统计")
    questions = [
        "什么是幂等性？一句话",
        "什么是看门狗续期？一句话",
        "Redis 和 etcd 做分布式锁的区别？两句话",
    ]

    for i, q in enumerate(questions, 1):
        print(f"  第 {i} 次调用: {q}")
        chain.invoke({"query": q}, config={"callbacks": [tracker]})

    tracker.report()

    print("\n  >> 用法要点：把 handler 实例放在循环【外面】，")
    print("     它内部的累加器才能跨多次调用保留。")
    print("  >> 如果每次调用都新建一个 handler，就只能统计单次。")


# ---------------------------------------------------------------------------
# 4. 对比：回调统计 vs 直接读返回值
# ---------------------------------------------------------------------------
def demo_4_two_ways() -> None:
    section("4. 拿 token 用量的两种途径")

    llm = build_llm()

    print("  途径一：从返回值直接读（最简单，但只能拿单次）")
    msg = llm.invoke("用一句话介绍 Consul")
    usage = msg.usage_metadata or {}
    print(f"    input={usage.get('input_tokens')} "
          f"output={usage.get('output_tokens')} "
          f"total={usage.get('total_tokens')}")

    print("\n  途径二：用回调 handler（推荐）")
    print("    · 能在一次调用里覆盖链路上的【所有】模型调用")
    print("    · 链式调用（比如先摘要再翻译）时，返回值只能拿到最后一个，")
    print("      而回调能分别统计每一次")
    print("    · 出错时也能统计（配合 on_llm_error）")

    print("\n  >> 选型：只要单次结果 → 读返回值；")
    print("           要做监控/计费/链路追踪 → 用回调。")


# ---------------------------------------------------------------------------
# 5. 生产实践提醒
# ---------------------------------------------------------------------------
def demo_5_production_tips() -> None:
    section("5. 生产实践提醒")

    tips = [
        ("线程安全", "回调可能被多个线程同时触发，累加要用锁（threading.Lock）"),
        ("别打敏感信息", "on_chat_model_start 能拿到完整用户输入，别直接写日志"),
        ("回调要快", "回调是同步阻塞的，里面别做耗时 IO，否则拖慢主链路"),
        ("异常隔离", "回调里抛异常可能中断主流程，建议内部 try/except"),
        ("配合追踪平台", "生产一般用 LangSmith / OpenTelemetry，不用自己造轮子"),
    ]
    for title, desc in tips:
        print(f"  · {title:<12} {desc}")

    print("\n  >> 简单场景自己写 handler 够用；")
    print("     要做完整的链路追踪、回放、评测，直接上 LangSmith。")


def main() -> None:
    print("2. 流式回调与用量统计（DeepSeek + 最新 API）")
    demo_1_stream_token()
    demo_2_single_call_usage()
    demo_3_multi_call_usage()
    demo_4_two_ways()
    demo_5_production_tips()
    print("\n" + "=" * 62)
    print("全部示例执行完毕。")


if __name__ == "__main__":
    main()
