#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
5. with_listeners：给单个组件挂生命周期监听（最新 API 版）
========================================================

【Python 语法看不懂？】闭包、lambda、** 解包、推导式等见 ../PYTHON_SYNTAX.md

【它和回调（callable 组）有什么区别】
    callable 组学的 BaseCallbackHandler 和这个很像，都是「在某些时刻收到通知」，
    但**作用范围**不一样：

    | | BaseCallbackHandler | with_listeners |
    |---|---|---|
    | 挂在哪 | 整条链（通过 config 传） | **某一个具体的 Runnable** |
    | 传递性 | **会传给子链**（绑顶层就覆盖全链路） | 只管自己 |
    | 写法 | 继承类 + 重写 on_xxx | 直接传三个函数 |
    | 适合 | 全局的日志/追踪/计费 | 针对某一步的特殊处理 |

    简单说：想监控**整条链**用回调；只想盯**某个组件**用 listeners。

【三个时机】
    on_start  开始执行前
    on_end    成功执行后
    on_error  抛异常时

【运行】
    ./yzy/Scripts/python.exe "aiLearn/runnableModule/new/5.生命周期监听器with_listeners.py"
"""

import os
import time
from pathlib import Path

import dotenv
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnableConfig, RunnableLambda
from langchain_core.runnables import RunnableSequence
from langchain_core.tracers.schemas import Run
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
# 1. 最小示例：三个时机都被触发
# ---------------------------------------------------------------------------
def demo_1_basic() -> None:
    section("1. 最小示例：on_start / on_end / on_error")

    def on_start(run_obj: Run, config: RunnableConfig) -> None:
        print(f"    ▶ on_start  name={run_obj.name}")

    def on_end(run_obj: Run, config: RunnableConfig) -> None:
        print(f"    ■ on_end    name={run_obj.name}")

    def on_error(run_obj: Run, config: RunnableConfig) -> None:
        print(f"    ✖ on_error  name={run_obj.name}")

    runnable = RunnableLambda(lambda x: time.sleep(0.1)).with_listeners(
        on_start=on_start,
        on_end=on_end,
        on_error=on_error,
    )

    print("  正常执行：")
    runnable.invoke(1, config={"configurable": {"name": "yangzhenyu"}})

    print("\n  抛异常时（只有 on_start 和 on_error 会触发）：")

    def boom(x):
        raise ValueError("故意失败")

    bad = RunnableLambda(boom).with_listeners(
        on_start=on_start, on_end=on_end, on_error=on_error
    )
    try:
        bad.invoke(1)
    except ValueError as e:
        print(f"    （异常向外抛出: {e}）")

    print("\n  >> 注意：on_error 触发后，异常**照样会往外抛**，")
    print("     listener 只是「通知」，不会吞掉异常。要吞就得用 with_fallbacks。")


# ---------------------------------------------------------------------------
# 2. Run 对象和 config 里有什么
# ---------------------------------------------------------------------------
def demo_2_what_inside() -> None:
    section("2. Run 对象和 config 里到底有什么")

    captured = {}

    def on_start(run_obj: Run, config: RunnableConfig) -> None:
        captured["run"] = run_obj
        captured["config"] = config

    RunnableLambda(lambda x: x).with_listeners(on_start=on_start).invoke(
        "hello", config={"configurable": {"user": "yangzhenyu"}, "tags": ["demo"]}
    )

    run_obj = captured["run"]
    cfg = captured["config"]

    print("  【Run 对象】常用字段：")
    for field in ("id", "name", "run_type", "start_time"):
        value = getattr(run_obj, field, None)
        print(f"    {field:<12}: {str(value)[:56]}")
    print(f"    inputs      : {run_obj.inputs}")
    print(f"    {'（outputs/end_time 在 on_end 里才有）'}")

    print("\n  【config 对象】常用字段：")
    print(f"    configurable: {cfg.get('configurable')}")
    print(f"    tags        : {cfg.get('tags')}")
    print(f"    metadata    : {cfg.get('metadata')}")
    print(f"    callbacks   : {cfg.get('callbacks')}")

    print("\n  >> 最有价值的是 config['configurable']：")
    print("     业务参数（user_id / trace_id）都从这里取，listener 里能做审计日志。")

    # 再看 on_end 里的 outputs
    def on_end(run_obj: Run, config: RunnableConfig) -> None:
        print(f"\n  【on_end 里】outputs={run_obj.outputs} / end_time 有值={run_obj.end_time is not None}")

    RunnableLambda(lambda x: x * 2).with_listeners(on_end=on_end).invoke(21)


# ---------------------------------------------------------------------------
# 3. 实战：给慢组件加耗时监控
# ---------------------------------------------------------------------------
def demo_3_timing() -> None:
    section("3. 实战：监控某个组件的耗时")

    # 用闭包保存开始时间（listeners 之间要传数据就靠闭包/外部变量）
    timings: dict[str, float] = {}

    def make_listeners(step_name: str):
        """【闭包工厂】为每个步骤造一对监听器。

        看不懂闭包工厂？见 ../PYTHON_SYNTAX.md 第 1 节。
        """
        def on_start(run_obj: Run, config: RunnableConfig) -> None:
            timings[step_name] = time.time()

        def on_end(run_obj: Run, config: RunnableConfig) -> None:
            cost = time.time() - timings.get(step_name, time.time())
            print(f"    [{step_name}] 耗时 {cost:.2f}s")

        return on_start, on_end

    s1_start, s1_end = make_listeners("步骤1-检索")
    s2_start, s2_end = make_listeners("步骤2-生成")

    step1 = RunnableLambda(lambda x: (time.sleep(0.3), x + " 资料")[1]).with_listeners(
        on_start=s1_start, on_end=s1_end
    )
    step2 = RunnableLambda(lambda x: f"答案：{x}").with_listeners(
        on_start=s2_start, on_end=s2_end
    )

    chain = step1 | step2
    print("  执行整条链：")
    print("   ", chain.invoke("问题"))

    print("\n  >> 这是 listener 最典型的用途：**单独盯住某一步的耗时**。")
    print("     用回调也能做，但要在 on_chain_start 里判断 name，写起来更绕。")


# ---------------------------------------------------------------------------
# 4. ⚠️ 关键区别：listener 只管自己，不会传给子链
# ---------------------------------------------------------------------------
def demo_4_scope() -> None:
    section("4. ⚠️ 关键区别：只管自己，不传给子链")

    hits = {"start": 0}

    def on_start(run_obj: Run, config: RunnableConfig) -> None:
        hits["start"] += 1
        print(f"    ▶ on_start: {run_obj.name}")

    # 把 listener 挂在**外层链**上
    inner1 = RunnableLambda(lambda x: x + "1")
    inner2 = RunnableLambda(lambda x: x + "2")
    outer = (inner1 | inner2).with_listeners(on_start=on_start)

    print("  挂在整条链上，看触发几次：")
    outer.invoke("x")
    print(f"    → on_start 触发了 {hits['start']} 次")

    print("\n  再把 listener 挂到**内层组件**上：")
    hits["start"] = 0
    inner1_l = RunnableLambda(lambda x: x + "1").with_listeners(on_start=on_start)
    outer2 = inner1_l | inner2
    outer2.invoke("x")
    print(f"    → on_start 触发了 {hits['start']} 次（只有内层的那一次）")

    print("\n  ⚠️ 对比一下回调：")
    print("     callback 绑在顶层，**会**自动传给所有子链")
    print("     listener 绑在哪，就**只**盯那一个 Runnable")
    print("\n  >> 所以：")
    print("     要全链路追踪 → 用回调（callable 组）")
    print("     要盯某一步   → 用 listener")


# ---------------------------------------------------------------------------
# 5. 真实场景：给模型调用加审计日志
# ---------------------------------------------------------------------------
def demo_5_audit_log() -> None:
    section("5. 实战：给模型调用加审计日志")

    audit_log: list[dict] = []

    def on_start(run_obj: Run, config: RunnableConfig) -> None:
        audit_log.append({"event": "start", "ts": time.time()})

    def on_end(run_obj: Run, config: RunnableConfig) -> None:
        audit_log.append({
            "event": "end",
            "ts": time.time(),
            # 模型调用的输出里能拿到 token 用量
            "outputs_type": type(run_obj.outputs).__name__,
        })

    llm_with_audit = build_llm().with_listeners(on_start=on_start, on_end=on_end)
    chain = ChatPromptTemplate.from_template("{query}") | llm_with_audit | StrOutputParser()

    print("  调用一次带审计的模型：")
    result = chain.invoke({"query": "用一句话介绍 Redis"})
    print("   ", result[:60])

    print("\n  审计日志：")
    for item in audit_log:
        print("   ", item)

    if len(audit_log) >= 2:
        print(f"\n    本次耗时约 {audit_log[-1]['ts'] - audit_log[0]['ts']:.2f}s")

    print("\n  >> 生产上可以把这个换成写 Kafka / 日志文件 / 监控系统。")
    print("     注意 listener 里别做太重的操作，会拖慢主流程。")


# ---------------------------------------------------------------------------
# 6. 使用场景与注意事项
# ---------------------------------------------------------------------------
def demo_6_summary() -> None:
    section("6. 什么时候用 listener")

    print("  适合：")
    print("   · 盯某个具体组件的耗时 / 成功率")
    print("   · 某一步执行完要发个通知（比如检索完成推进度）")
    print("   · 针对某一步做审计日志")
    print("   · 某一步失败要告警（但不想吞异常）")

    print("\n  不适合：")
    print("   · 全链路追踪        → 用回调或 LangSmith")
    print("   · 想吞掉异常        → 用 with_fallbacks（第 4 个文件）")
    print("   · 想重试            → 用 with_retry（第 4 个文件）")

    print("\n  ⚠️ 三个注意事项：")
    print("   ① listener 里抛异常会**中断主流程**，务必自己 try/except")
    print("   ② listener 是同步执行的，别在里面做重 IO（会拖慢链路）")
    print("   ③ on_error 触发后异常仍会向外抛，listener 不是 try/catch")

    print("\n  和回调的对照：")
    rows = [
        ("作用范围", "某一个 Runnable", "整条链 + 所有子链"),
        ("写法", "传三个函数", "继承类 + 重写方法"),
        ("传递性", "❌ 不传递", "✅ 自动传给子链"),
        ("典型用途", "盯某一步", "全链路日志/追踪/计费"),
    ]
    print()
    print(f"    {'维度':<10}{'with_listeners':<22}{'BaseCallbackHandler'}")
    print("    " + "-" * 56)
    for a, b, c in rows:
        print(f"    {a:<10}{b:<22}{c}")


def main() -> None:
    print("5. with_listeners 生命周期监听器（DeepSeek + 最新 API）")
    print("   教材：old/Runnable组件生命周期监听器与使用场景/1.*")

    demo_1_basic()
    demo_2_what_inside()
    demo_3_timing()
    demo_4_scope()

    if not os.getenv("DEEPSEEK_API_KEY"):
        print("\n⚠️ 没读到 DEEPSEEK_API_KEY，跳过需要调模型的演示。.env 路径：", _ENV_PATH)
        return

    demo_5_audit_log()
    demo_6_summary()

    print("\n" + "=" * 62)
    print("全部示例执行完毕。下一个：6.RunnableWithMessageHistory回顾.py")


if __name__ == "__main__":
    main()
