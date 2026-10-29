#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
4. 重试与回退：让程序更抗造（最新 API 版）
========================================


【Python 语法看不懂？】闭包、lambda、** 解包、推导式等见 ../PYTHON_SYNTAX.md

【两个东西解决两件事】
    with_retry      同一个组件失败了，**再试几次**（对付偶发抖动）
    with_fallbacks  这个组件彻底挂了，**换一个**（对付组件不可用）

    【Java 对照】
        with_retry      ≈ Spring Retry 的 @Retryable / Resilience4j 的 Retry
        with_fallbacks  ≈ Resilience4j 的 Fallback / Hystrix 的 getFallback()

    判断标准很简单：
        这次失败是**随机的**吗？→ 重试
        这次失败是**必然的**吗？→ 回退

【⚠️ 先说一个重要认知】
    重试不是越多越好。LLM 场景下：
        · 参数写错（400）→ 重试 100 次也是错，白烧钱
        · 限流（429）    → 适合重试，但要退避
        · 网络抖动       → 适合重试
    所以**一定要用 retry_if_exception_type 限定只重试特定异常**。

【运行】
    ./yzy/Scripts/python.exe "aiLearn/runnableModule/new/4.重试与回退机制.py"
"""

import os
import time
from pathlib import Path

import dotenv
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnableLambda
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


def build_llm(model: str = "deepseek-flash") -> ChatOpenAI:
    """构造 DeepSeek 模型。"""
    return ChatOpenAI(
        model=model,
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
# 1. with_retry 基本用法
# ---------------------------------------------------------------------------
def demo_1_retry_basic() -> None:
    section("1. with_retry：失败了自动重试")

    # 造一个「前两次必失败，第三次成功」的函数
    # 【这是个闭包工厂，看不懂先看 ../PYTHON_SYNTAX.md 第 1 节】
    def make_flaky(fail_times: int):
        state = {"count": 0}

        def flaky(x):
            state["count"] += 1
            print(f"    第 {state['count']} 次调用...", end="")
            if state["count"] <= fail_times:
                print(" 失败")
                raise ConnectionError("模拟网络抖动")
            print(" 成功")
            return f"成功：{x}"

        return flaky

    print("  失败 2 次后成功，设置 stop_after_attempt=3：\n")
    chain = RunnableLambda(make_flaky(2)).with_retry(stop_after_attempt=3)
    print("   结果:", chain.invoke("hello"))

    print("\n  --------------------------------------------------------")

    print("\n  失败 5 次，但只让重试 3 次：\n")
    chain2 = RunnableLambda(make_flaky(5)).with_retry(stop_after_attempt=3)
    try:
        chain2.invoke("hello")
    except Exception as e:
        print(f"   最终抛出: {type(e).__name__}: {e}")

    print("\n  >> stop_after_attempt = **总尝试次数**（含第一次），不是「额外重试几次」。")
    print("     写 3 = 最多跑 3 次 = 失败 2 次后第 3 次成功。")


# ---------------------------------------------------------------------------
# 2. ⚠️ 重要：限定只重试特定异常
# ---------------------------------------------------------------------------
def demo_2_retry_if_exception_type() -> None:
    section("2. ⚠️ 关键参数：只重试该重试的异常")

    print("  默认行为是「任何异常都重试」——这在 LLM 场景很危险。")
    print("  比如参数写错导致的 400，重试 3 次就是白花 3 倍的钱。\n")

    def make_bad_param():
        """造一个「参数错误、永远失败」的函数，自带计数器。"""
        state = {"n": 0}

        def f(x):
            state["n"] += 1
            raise ValueError("参数错误：model 不存在")

        return f, state

    # ① 默认：什么异常都重试
    print("  【默认】ValueError 也会被重试（❌ 不应该）：")
    fn1, s1 = make_bad_param()
    try:
        RunnableLambda(fn1).with_retry(stop_after_attempt=3).invoke("x")
    except ValueError as e:
        print(f"    最终抛出: {e}")
    print(f"    → 白跑了 {s1['n']} 次（参数错误重试 3 次纯属浪费）\n")

    # ② 限定只重试 ConnectionError
    print("  【限定 retry_if_exception_type=(ConnectionError,)】")
    print("    参数错误（ValueError）会**立刻**抛出，不重试：")
    fn2, s2 = make_bad_param()
    try:
        RunnableLambda(fn2).with_retry(
            stop_after_attempt=3,
            retry_if_exception_type=(ConnectionError,),   # ← 只重试网络类异常
        ).invoke("x")
    except ValueError as e:
        print(f"    最终抛出: {e}")
    print(f"    → 只跑了 {s2['n']} 次 ✅")

    # 单独验证：ConnectionError 时确实会重试
    print("\n  验证 ConnectionError 时确实重试了：")
    counter3 = {"n": 0}

    def net_error(x):
        counter3["n"] += 1
        raise ConnectionError("网络抖动")

    try:
        RunnableLambda(net_error).with_retry(
            stop_after_attempt=3, retry_if_exception_type=(ConnectionError,)
        ).invoke("x")
    except ConnectionError:
        pass
    print(f"    → ConnectionError 一共跑了 {counter3['n']} 次 ✅")

    print("\n  生产建议的可重试异常：")
    print("    · 网络类：ConnectionError / Timeout / socket.timeout")
    print("    · 限流类：HTTP 429（RateLimitError）")
    print("    · 服务端：HTTP 500 / 502 / 503")
    print("  不该重试：")
    print("    · HTTP 400 参数错误（重试也没用）")
    print("    · HTTP 401 鉴权失败（重试也没用）")
    print("    · 自己代码的逻辑错误")


# ---------------------------------------------------------------------------
# 3. 重试的等待策略（退避 + 抖动）
# ---------------------------------------------------------------------------
def demo_3_backoff() -> None:
    section("3. 重试间隔：退避 + 抖动")

    print("  with_retry 默认就开了 **指数退避 + 抖动**（wait_exponential_jitter=True）。")
    print("  意思是：第 1 次失败等一会儿，第 2 次等更久，且加随机量。\n")

    print("  为什么要「抖动(jitter)」？")
    print("    如果 1000 个请求同时失败、同时重试，会形成**重试风暴**，")
    print("    把刚恢复的服务再次打垮。加随机量能把重试时间打散。\n")

    # 实测一下带退避的重试耗时
    counter = {"n": 0}

    def flaky(x):
        counter["n"] += 1
        if counter["n"] < 3:
            raise ConnectionError("抖动")
        return "ok"

    t0 = time.time()
    try:
        RunnableLambda(flaky).with_retry(stop_after_attempt=3).invoke("x")
    except Exception:
        pass
    cost = time.time() - t0
    print(f"  实测：失败 2 次后成功，总耗时 {cost:.2f}s（含退避等待）")
    print(f"        尝试了 {counter['n']} 次")

    print("\n  参数说明：")
    print("    wait_exponential_jitter   默认 True，指数退避 + 随机抖动")
    print("    exponential_jitter_params 可以细调（initial/max/jitter/exp_base）")
    print("    stop_after_attempt        总尝试次数（含第一次）")
    print("\n  ⚠️ 注意：退避等待是**同步阻塞**的，")
    print("     在高并发服务里要算好它对线程池的占用。")


# ---------------------------------------------------------------------------
# 4. with_fallbacks：这个挂了换那个
# ---------------------------------------------------------------------------
def demo_4_fallbacks() -> None:
    section("4. with_fallbacks：主组件挂了自动换备用")

    # ① 先用普通函数看清楚机制
    print("  【函数版】主函数必失败，看会不会切到备用：\n")

    def primary(x):
        print("    主组件：执行中...", end="")
        raise RuntimeError("主组件挂了")

    def backup(x):
        print("    备用组件：执行中...", end="")
        return "备用结果"

    chain = RunnableLambda(primary).with_fallbacks([RunnableLambda(backup)])
    print("   ", chain.invoke("x"))

    print("\n  >> 机制：按顺序试，第一个成功的就用，全失败才抛异常。")

    # ② 真实场景：主模型不可用，切备用模型
    print("\n  【实战】主模型用了不存在的模型名，自动切到备用模型：\n")

    prompt = ChatPromptTemplate.from_template("{query}")

    # 主模型：故意用一个 DeepSeek 上不存在的模型名
    bad_llm = ChatOpenAI(
        model="not-a-real-model",
        api_key=os.getenv("DEEPSEEK_API_KEY"),
        base_url=os.getenv("DEEPSEEK_API_BASE"),
    )
    good_llm = build_llm()

    chain2 = prompt | bad_llm.with_fallbacks([good_llm]) | StrOutputParser()

    t0 = time.time()
    result = chain2.invoke({"query": "用一句话介绍 Redis"})
    cost = time.time() - t0

    print(f"    结果: {result[:70]}")
    print(f"    耗时: {cost:.2f}s（先试主模型失败，再试备用）")

    print("\n  >> 这就是教材里「切换为不存在的模型引发出错 → 回退」的写法。")
    print("     生产上典型用法：")
    print("       · 主用贵的强模型，挂了切便宜的")
    print("       · 主用自家部署，挂了切公有云")
    print("       · 主用国外模型，被墙/超时切国内模型")


# ---------------------------------------------------------------------------
# 5. 多个备用 + 拿到底哪个失败了
# ---------------------------------------------------------------------------
def demo_5_multiple_fallbacks() -> None:
    section("5. 多个备用 + exception_key")

    print("  fallback 可以是一串，按顺序依次尝试：\n")

    def make_failing(name):
        def f(x):
            print(f"    {name} 失败")
            raise RuntimeError(f"{name} 挂了")
        return f

    def last(x):
        print("    最后备用成功")
        return "终于成功了"

    chain = RunnableLambda(make_failing("A")).with_fallbacks([
        RunnableLambda(make_failing("B")),
        RunnableLambda(make_failing("C")),
        RunnableLambda(last),
    ])
    print("   ", chain.invoke("x"))

    print("\n  --------------------------------------------------------")
    print("\n  exception_key：想知道「到底为什么失败」时用\n")

    def always_fail(x):
        raise RuntimeError("原始错误信息")

    def handler(payload):
        """兜底处理器：拿到「原始输入 + 异常」，返回一个友好结果。

        ⚠️ 实测：开了 exception_key 之后，传进来的是一个 **dict**：
            {'query': 'x', 'exception': RuntimeError('原始错误信息')}
        也就是「业务输入 + exception 键」合在一起，不是单独的异常对象。
        """
        exception = payload.get("exception") if isinstance(payload, dict) else payload
        return f"抱歉，服务暂时不可用（原因：{exception}）"

    chain2 = RunnableLambda(always_fail).with_fallbacks(
        [RunnableLambda(handler)],
        exception_key="exception",      # ← 把异常作为 exception 参数传进去
    )

    # ⚠️ 实测坑：开了 exception_key 之后，输入**必须是 dict**，
    #    传字符串会报 ValueError: If 'exception_key' is specified then input must be a dictionary
    print("  先试传字符串（会报错）：")
    try:
        chain2.invoke("x")
    except ValueError as e:
        print(f"    ❌ ValueError: {str(e)[:90]}")

    print("\n  改成传 dict：")
    print("   ", chain2.invoke({"query": "x"}))

    print("\n  >> exception_key 实测总结（两点都不太直观）：")
    print("     ① 开了它，输入**必须是 dict**，传字符串直接 ValueError")
    print("     ② 兜底函数收到的是「原始输入 + exception 键」组成的 dict，")
    print("        不是单独的异常对象，要自己 .get('exception') 取出来")


# ---------------------------------------------------------------------------
# 6. 重试 + 回退 组合 + 选型
# ---------------------------------------------------------------------------
def demo_6_combine_and_choose() -> None:
    section("6. 组合使用 + 怎么选")

    print("  【组合】先重试几次，都不行再回退：\n")

    counter = {"n": 0}

    def flaky(x):
        counter["n"] += 1
        if counter["n"] <= 3:
            print(f"    主组件第 {counter['n']} 次，失败")
            raise ConnectionError("抖动")
        print(f"    主组件第 {counter['n']} 次，成功")
        return "主组件结果"

    def backup(x):
        print("    备用组件执行")
        return "备用结果"

    chain = (
        RunnableLambda(flaky)
        .with_retry(stop_after_attempt=4, retry_if_exception_type=(ConnectionError,))
        .with_fallbacks([RunnableLambda(backup)])
    )
    print("   ", chain.invoke("x"))

    print("\n  顺序很重要：")
    print("    with_retry 包在里面  → 先重试，重试完还失败才回退  ✅ 正确")
    print("    with_fallbacks 包在里面 → 每次失败立刻回退，重试没机会  ❌")

    print("\n" + "-" * 62)
    print("  选型表：\n")

    rows = [
        ("with_retry", "同一个东西再试几次", "偶发抖动、限流", "限定异常类型"),
        ("with_fallbacks", "换一个东西", "组件彻底不可用", "备用组件要真的能兜住"),
        ("二者组合", "先重试再换", "生产标准做法", "注意嵌套顺序"),
    ]
    print(f"    {'方式':<18}{'干什么':<22}{'什么时候用':<18}{'注意'}")
    print("    " + "-" * 76)
    for a, b, c, d in rows:
        print(f"    {a:<18}{b:<22}{c:<18}{d}")

    print("\n  ⚠️ 三条生产经验：")
    print("   ① 重试一定要配 retry_if_exception_type，别啥都重试")
    print("   ② 要设总超时，否则重试 + 退避可能让请求挂很久")
    print("   ③ 回退链路也要打日志，否则「为什么变慢了」查不出来")


def main() -> None:
    print("4. 重试与回退机制（DeepSeek + 最新 API）")
    print("   教材：old/Runnable组件重试与回退机制降低程序错误率/*")

    demo_1_retry_basic()
    demo_2_retry_if_exception_type()
    demo_3_backoff()

    if not os.getenv("DEEPSEEK_API_KEY"):
        print("\n⚠️ 没读到 DEEPSEEK_API_KEY，跳过需要调模型的演示。.env 路径：", _ENV_PATH)
        return

    demo_4_fallbacks()
    demo_5_multiple_fallbacks()
    demo_6_combine_and_choose()

    print("\n" + "=" * 62)
    print("全部示例执行完毕。下一个：5.生命周期监听器with_listeners.py")


if __name__ == "__main__":
    main()
