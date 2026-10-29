#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
1. 回调功能使用技巧（最新 API 版）
=================================

【Python 语法看不懂？】闭包、lambda、** 解包、推导式等见 ../PYTHON_SYNTAX.md

【回调是干什么的】
    LangChain 的链路跑起来像个黑盒：你只知道 invoke() 进去了、结果出来了，
    中间发生了什么、花了多久、用了多少 token，一概不知道。

    回调（Callback）就是**在链路的关键节点上插钩子**，让你能在这些时刻收到通知：

        链开始 → prompt渲染 → 模型开始 → 模型流式吐字 → 模型结束 → 解析 → 链结束

    典型用途：
        · 打印日志、链路追踪（对接 LangSmith / OpenTelemetry）
        · 统计 token 消耗和耗时（做成本监控）
        · 把流式输出实时推给前端
        · 出错时告警

【新旧对比】

    新版（本文件）：
        chain = ....with_config(callbacks=[处理器])     # 绑定到链上，一次生效
        chain = chain.with_config(callbacks=[...])       # 或者调用时传，两种都行

    核心 API `BaseCallbackHandler` 没变，但：
    ① 新增了一批钩子（on_custom_event / on_stream_event / on_retry 等）
    ② 官方现在更推荐用 astream_events 事件流（见 astream_events事件流.py）
    ③ 有个【很容易踩的坑】见 demo_3

【运行】
    ./yzy/Scripts/python.exe "aiLearn/callable/new/回调功能使用技巧.py"
"""

import os
import time
from pathlib import Path
from typing import Any, Dict, List, Optional
from uuid import UUID

import dotenv
from langchain_core.callbacks import BaseCallbackHandler, StdOutCallbackHandler
from langchain_core.messages import BaseMessage
from langchain_core.output_parsers import StrOutputParser
from langchain_core.outputs import LLMResult
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough
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
# 自定义回调处理器
# ---------------------------------------------------------------------------
# 写法：继承 BaseCallbackHandler，重写你关心的那几个 on_xxx 方法。
# 不需要全部实现——只重写你感兴趣的即可。
#
# 注意参数里的 * 符号：
#     def on_chat_model_start(self, serialized, messages, *, run_id, ...)
#                                                        ↑
#     * 后面的参数叫「仅关键字参数」，调用时必须写名字，不能按位置传。
#     这是 LangChain 强制的，好处是以后加参数不会破坏你的代码。
# ===========================================================================
class LLMOpsCallbackHandler(BaseCallbackHandler):
    """自定义回调：记录模型调用的开始/结束与耗时"""

    start_at: float = 0      # 类属性，记录开始时间

    def on_chat_model_start(
            self,
            serialized: Dict[str, Any],
            messages: List[List[BaseMessage]],
            *,
            run_id: UUID,
            parent_run_id: Optional[UUID] = None,
            tags: Optional[List[str]] = None,
            metadata: Optional[Dict[str, Any]] = None,
            **kwargs: Any,
    ) -> Any:
        """模型开始调用时触发

        参数说明：
            serialized  模型的配置信息（模型名、参数等）
            messages    本次要发给模型的消息，注意是【二维列表】：
                        外层是"批次"，内层是"一批消息"。单条调用就是 [[m1, m2]]
            run_id      本次运行的唯一 ID，用来串联同一次调用的所有事件
            **kwargs    兜底接收未来新增的参数，防止版本升级报错
        """
        print("  ▶ 模型开始执行")
        print("    模型配置里的 id:", serialized.get("id"))
        print("    本次消息数:", len(messages[0]))
        self.start_at = time.time()

    def on_llm_end(
            self,
            response: LLMResult,
            *,
            run_id: UUID,
            parent_run_id: Optional[UUID] = None,
            **kwargs: Any,
    ) -> Any:
        """模型执行结束时触发（这是拿 token 用量的地方）"""
        end_at = time.time()
        print(f"  ■ 模型执行结束，耗时 {end_at - self.start_at:.2f}s")

        # 从 LLMResult 里取 token 用量，路径比较深：
        #   response.generations[批次下标][候选下标].message.usage_metadata
        try:
            msg = response.generations[0][0].message
            usage = getattr(msg, "usage_metadata", None)
            if usage:
                print(f"    token 用量: 输入 {usage.get('input_tokens')} / "
                      f"输出 {usage.get('output_tokens')} / "
                      f"合计 {usage.get('total_tokens')}")
        except Exception as e:
            print("    取用量失败:", type(e).__name__, e)


# ---------------------------------------------------------------------------
# 1. 基本用法：调用时通过 config 传回调
# ---------------------------------------------------------------------------
def demo_1_basic() -> None:
    section("1. 基本用法：config={'callbacks': [...]}")

    prompt = ChatPromptTemplate.from_template("{query}")
    chain = {"query": RunnablePassthrough()} | prompt | build_llm() | StrOutputParser()

    print("调用时把处理器塞进 config：")
    resp = chain.invoke(
        {"query": "用一句话介绍 Redis"},
        config={"callbacks": [LLMOpsCallbackHandler()]},
    )
    print("\n  最终结果:", resp[:40], "...")


# ---------------------------------------------------------------------------
# 2. 新版推荐：with_config 绑定到链上
# ---------------------------------------------------------------------------
def demo_2_with_config() -> None:
    section("2. 新版推荐：with_config 绑定，一次生效")

    prompt = ChatPromptTemplate.from_template("{query}")
    base_chain = {"query": RunnablePassthrough()} | prompt | build_llm() | StrOutputParser()

    # with_config 返回一个【新的链】，回调被永久绑定在上面
    # 好处：不用每次 invoke 都记得传，也不会漏传
    instrumented = base_chain.with_config(callbacks=[LLMOpsCallbackHandler()])

    print("连续调用两次，回调都会自动生效：")
    for q in ["用一句话介绍 Kafka", "用一句话介绍 Nginx"]:
        print(f"\n  提问: {q}")
        r = instrumented.invoke({"query": q})
        print("  回答:", r[:35], "...")

    print("\n  >> 对比：用 config 传要每次都写一遍，容易漏。")
    print("  >> 生产建议：链路组装完成时统一 with_config 一次。")


# ---------------------------------------------------------------------------
# 3. ⚠️ 大坑：不是所有 on_xxx 都会被调用
# ---------------------------------------------------------------------------
def demo_3_pitfall() -> None:
    section("3. ⚠️ 坑：on_chat_model_end 不会被调用")

    print("  直觉上，既然有 on_chat_model_start，就该有 on_chat_model_end。")
    print("  实测：BaseCallbackHandler 里【根本没有】on_chat_model_end 这个钩子。\n")

    from langchain_core.callbacks import BaseCallbackHandler as BCH

    hooks = sorted(m for m in dir(BCH) if m.startswith("on_"))
    print("  实际存在的 on_* 钩子（共 %d 个）：" % len(hooks))
    # 分两列打印
    for i in range(0, len(hooks), 2):
        row = hooks[i:i + 2]
        print("    " + "".join(f"{h:<28}" for h in row))

    print("\n  >> 所以模型结束要监听的是 on_llm_end，不是 on_chat_model_end。")
    print("  >> 如果你写了 def on_chat_model_end(...)，它【永远不会被调用】，")
    print("     而且不报任何错——静默失效，特别难排查。")

    print("\n  >> 混淆来源：astream_events 事件流里确实有 'on_chat_model_end' 事件，")
    print("     但那是事件流的事件名，和回调 handler 的方法名是两套东西。")
    print("     详见 astream_events事件流.py")

    # 实测验证：定义一个 on_chat_model_end，看看是否被调用
    print("\n  实测验证：")
    class Probe(BaseCallbackHandler):
        def on_chat_model_end(self, response, **kwargs):
            print("    ✅ on_chat_model_end 被调用了")

        def on_llm_end(self, response, **kwargs):
            print("    ✅ on_llm_end 被调用了（这个才是生效的）")

    build_llm().invoke("hi", config={"callbacks": [Probe()], "max_concurrency": 1})
    print("    （上面如果只出现 on_llm_end，就印证了 on_chat_model_end 无效）")


# ---------------------------------------------------------------------------
# 4. 内置处理器 StdOutCallbackHandler
# ---------------------------------------------------------------------------
def demo_4_stdout_handler() -> None:
    section("4. 内置的 StdOutCallbackHandler（调试神器）")

    print("  它会把链路每一步的出入参都打到标准输出，调试时非常好用。")
    print("  下面只跑一次，输出会比较长：\n")

    chain = ChatPromptTemplate.from_template("{query}") | build_llm() | StrOutputParser()
    chain.invoke(
        {"query": "1+1等于几？只回答数字"},
        config={"callbacks": [StdOutCallbackHandler()]},
    )

    print("\n  >> 输出格式是 '> Entering new XXX chain...' / '> Finished chain.'，")
    print("     能看到 RunnableSequence → ChatPromptTemplate → StrOutputParser 的嵌套层次。")
    print("  >> 注意两点：")
    print("     1. 它只打印【链】的进出，模型层的细节要靠 on_llm_* 钩子自己实现")
    print("     2. 生产环境别开——会把用户输入原样打进日志，有隐私问题")


# ---------------------------------------------------------------------------
# 5. 三种绑定方式对比
# ---------------------------------------------------------------------------
def demo_5_three_ways() -> None:
    section("5. 回调的三种绑定方式")

    print("  ① 调用时传（最灵活，也最容易漏）")
    print("     chain.invoke(x, config={'callbacks': [h]})")
    print("     适合：临时给某一次调用加监控\n")

    print("  ② with_config 绑定到链（推荐）")
    print("     chain = chain.with_config(callbacks=[h])")
    print("     适合：整条链路统一加监控\n")

    print("  ③ 构造模型时传")
    print("     ChatOpenAI(..., callbacks=[h])")
    print("     适合：只想监控模型层，不关心链的其他部分")

    print("\n  优先级：三者可以叠加，都会执行。")
    print("  继承性：父链的回调会自动传给子链（所以绑在顶层就能覆盖全链路）。")


def main() -> None:
    print("1. 回调功能使用技巧（DeepSeek + 最新 API）")
    demo_1_basic()
    demo_2_with_config()
    demo_3_pitfall()
    demo_4_stdout_handler()
    demo_5_three_ways()
    print("\n" + "=" * 62)
    print("全部示例执行完毕。")


if __name__ == "__main__":
    main()
