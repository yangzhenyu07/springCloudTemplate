#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
1. RunnableParallel 使用技巧（最新 API 版）
==========================================


【RunnableParallel 是干什么的】
    一句话：**同一个输入，同时跑多条链，结果汇总成一个字典**。

        输入 ──┬──→ 链A ──→ joke
               └──→ 链B ──→ poem         汇总成 {"joke": ..., "poem": ...}

    典型场景：
        · 同一份材料，让模型同时做「摘要 + 翻译 + 提取关键词」
        · RAG 里同时检索多个数据源
        · 一次拿到模型的多种视角，再综合判断


【本文件最重要的实测结论】
    RunnableParallel 在 .invoke() 下是【真并发】，不是串行模拟。
    实测：两个各阻塞 1.5s 的分支，总耗时 1.54s（串行应为 3.0s），
    且两个分支跑在不同的线程池线程上。

【运行】
    ./yzy/Scripts/python.exe "aiLearn/runnable/new/1.RunnableParallel使用技巧.py"
"""

import asyncio
import os
import threading
import time
from pathlib import Path

import dotenv
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnableLambda, RunnableParallel
from langchain_core.runnables.base import coerce_to_runnable
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
        max_tokens=256,
        timeout=60,
        max_retries=2,
    )


def section(title: str) -> None:
    print("\n" + "=" * 62)
    print(title)
    print("=" * 62)


# 统一的管道工厂：prompt → 模型 → 字符串
def make_chain(template: str):
    return ChatPromptTemplate.from_template(template) | build_llm() | StrOutputParser()


# ---------------------------------------------------------------------------
# 1. 两种写法：显式类 vs 字典字面量（以及"等价"的前提）
# ---------------------------------------------------------------------------
def demo_1_two_styles() -> None:
    section("1. 两种写法：RunnableParallel(...) vs 字典字面量")

    llm = build_llm()
    parser = StrOutputParser()
    joke_chain = ChatPromptTemplate.from_template(
        "请讲一个关于{subject}的冷笑话，尽可能短一些") | llm | parser
    poem_chain = ChatPromptTemplate.from_template(
        "请写一篇关于{subject}的诗，尽可能短一些") | llm | parser

    # ================= 写法一：显式 RunnableParallel =================
    map_chain = RunnableParallel(joke=joke_chain, poem=poem_chain)
    print("【写法一】RunnableParallel(joke=..., poem=...)")
    print("  构造出来的类型 :", type(map_chain).__name__)
    print("  有 invoke 方法 :", hasattr(map_chain, "invoke"), " <-- 直接就能用")
    res1 = map_chain.invoke({"subject": "程序员"})
    print("  结果键         :", list(res1.keys()))

    # ================= 写法二：字典字面量 =================
    d = {"joke": joke_chain, "poem": poem_chain}
    print("\n【写法二】{'joke': ..., 'poem': ...}")
    print("  拿在手里是什么 :", type(d).__name__)
    print("  有 invoke 方法 :", hasattr(d, "invoke"), " <-- 裸 dict 不是 Runnable！")

    try:
        d.invoke({"subject": "程序员"})
    except AttributeError as e:
        print("  直接 invoke 会炸:", e)

    # ============ 关键：dict 什么时候会变成 RunnableParallel ============
    print("\n>> 所以「两种写法等价」是有【前提】的：")
    print("   裸 dict 本身不是 Runnable，只有在参与 LCEL 组合时才会被自动转换。\n")
    print("   把 dict 变成 Runnable 的两种方式：")

    # ① 与 Runnable 组合时自动转换（日常最常用）
    c1 = d | RunnableLambda(lambda x: x)
    print("    ① dict | RunnableLambda(fn)  →", type(c1.steps[0]).__name__)

    # ② 显式调用底层的转换函数
    c2 = coerce_to_runnable(d)
    print("    ② coerce_to_runnable(dict)   →", type(c2).__name__)

    print("\n   （原理：| 的运算符重载。dict 没有 __or__，Python 转而调用")
    print("     右边 Runnable 的 __ror__，langchain 在其中完成转换。）")

    # ================= 验证：两种写法结果一致 =================
    res2 = coerce_to_runnable(d).invoke({"subject": "程序员"})
    print("\n【验证】两种写法跑出来的结果:")
    print("  RunnableParallel 版 →", list(res1.keys()))
    print("  字典转换版         →", list(res2.keys()))
    print("  joke 分支:", res1["joke"][:40], "...")
    print("  poem 分支:", res1["poem"][:40], "...")

    print("\n>> 结论：")
    print("   · 单独放着：RunnableParallel 是 Runnable，dict 不是 —— 不等价")
    print("   · 放进管道：dict 会被自动转成 RunnableParallel —— 等价")
    print("   · 日常推荐写 {'joke': ..., 'poem': ...} | 后续处理，更简洁")


# ---------------------------------------------------------------------------
# 2. 实测：真的并行吗
# ---------------------------------------------------------------------------
def demo_2_is_it_really_parallel() -> None:
    section("2. 实测：RunnableParallel 到底是不是真并发")

    # 【工厂函数】调用 make_slow("A", 1.5) 不会立刻执行，
    # 而是返回一个"能阻塞 1.5 秒"的 Runnable，供后面放进管道里跑。
    def make_slow(name: str, sec: float):
        """造一个阻塞指定秒数的 Runnable，顺便记录它在哪个线程执行。

        结构：外层接收参数 → 内层 f 是真正被执行的逻辑 → 包成 Runnable 返回。
        内层 f 用到了外层的 name 和 sec，这叫闭包（变量被"记住"了）。
        """
        def f(_x):
            # 参数 _x 是上游传来的输入，这里用不到，所以用 _ 开头表示"忽略"
            t0 = time.perf_counter()
            time.sleep(sec)     # 模拟 IO 等待（调模型、查库都是这种）
            return f"{name} 线程={threading.current_thread().name} 耗时={time.perf_counter()-t0:.2f}s"

        return RunnableLambda(f)    # 包成 Runnable 才能放进 RunnableParallel

    # 调用两次，得到两个不同的 Runnable：一个叫 A、一个叫 B
    para = RunnableParallel(
        a=make_slow("A", 1.5),
        b=make_slow("B", 1.5),
    )
    t0 = time.perf_counter()
    r = para.invoke({"x": 1})
    cost = time.perf_counter() - t0

    print("  分支A:", r["a"])
    print("  分支B:", r["b"])
    print(f"\n  总耗时: {cost:.2f}s")
    print("  串行预期: 3.00s  |  并行预期: 1.50s")
    if cost < 2.2:
        print("\n  ✅ 结论：是真并发。invoke() 内部用线程池跑各个分支。")
        print("     >> 两个分支跑在不同的线程上（看上面的线程名）。")
        print("     >> 所以 IO 密集的场景（调模型、调 API）收益很大。")
    else:
        print("\n  ⚠️ 本次未观察到并发（可能是机器繁忙）")


# ---------------------------------------------------------------------------
# 3. 真实场景：一次调用拿到多种结果
# ---------------------------------------------------------------------------
def demo_3_multi_perspective() -> None:
    section("3. 实战：同一份材料，同时产出多种结果")

    # 一次调用，同时让模型做三件事
    analysis = RunnableParallel(
        summary=make_chain("用一句话总结以下内容：\n\n{text}"),
        keywords=make_chain("从下面内容提取3个关键词，用逗号分隔：\n\n{text}"),
        sentiment=make_chain("判断下面内容的情感倾向，只回答「正面/负面/中性」：\n\n{text}"),
    )

    text = "这个版本的支付接口改动很大，上线后超时率从2%降到了0.1%，客户反馈明显变好了。"
    t0 = time.perf_counter()
    res = analysis.invoke({"text": text})
    cost = time.perf_counter() - t0

    print("原文:", text)
    print(f"\n三条链并发执行，总耗时 {cost:.2f}s")
    print("  摘要  :", res["summary"])
    print("  关键词:", res["keywords"])
    print("  情感  :", res["sentiment"])
    print("\n  >> 如果串行跑这三条链，耗时会是现在的约 3 倍。")


# ---------------------------------------------------------------------------
# 4. max_concurrency：限制并发度
# ---------------------------------------------------------------------------
def demo_4_max_concurrency() -> None:
    section("4. max_concurrency —— 限制同时跑几个分支")

    # 同上一个 demo 的工厂函数：调用后返回一个"会睡 0.8 秒"的 Runnable
    def slow_with_tag(i: int):
        def f(_x):
            time.sleep(0.8)
            return f"任务{i}完成"      # i 来自外层（闭包捕获）
        return RunnableLambda(f)

    # 8 个分支
    # 这一行有两个 Python 语法点，Java 里没有直接对应的写法：
    #
    # ① 字典推导式
    #    {f"t{i}": slow_with_tag(i) for i in range(8)}
    #    一次性生成 {"t0": Runnable, "t1": Runnable, ... "t7": Runnable}
    #    等价于：手动写 t0=..., t1=..., ... t7=... 八遍
    #
    # ② ** 解包
    #    RunnableParallel(**dict) 把字典「拆成关键字参数」传进去
    #    等价于 RunnableParallel(t0=..., t1=..., ...)
    #    如果不加 **，就会把整个字典当成第一个位置参数，那就错了
    para = RunnableParallel(**{f"t{i}": slow_with_tag(i) for i in range(8)})

    # 不限制：8 个一起飞
    t0 = time.perf_counter()
    r1 = para.invoke({})
    cost_all = time.perf_counter() - t0

    # 限制最多 2 个并发
    t0 = time.perf_counter()
    r2 = para.invoke({}, config={"max_concurrency": 2})
    cost_limited = time.perf_counter() - t0

    print(f"  不限制并发  : {cost_all:.2f}s（{len(r1)}个分支）")
    print(f"  限制并发=2  : {cost_limited:.2f}s（{len(r2)}个分支）")
    print("\n  >> 为什么要限制？厂商有 RPM/并发限额，一次性打太猛会被限流(429)。")
    print("  >> 建议：并发数按厂商限额定，配合重试机制。")


# ---------------------------------------------------------------------------
# 5. 一个容易踩的坑
# ---------------------------------------------------------------------------
def demo_5_pitfall() -> None:
    section("5. 坑：dict 和 fn 组合时的 TypeError")

    print("  | 是运算符重载，要求【两边至少一边是 Runnable】。")
    print("  dict 和 function 都是 Python 内置类型，谁都没有 __or__，于是报错。\n")

    # lambda x: x 是「匿名函数」，等价于：
    #   def fn(x):
    #       return x
    # 就是原样返回输入，什么都不做。这里只是拿来凑一个最简单的函数。
    d = {"a": lambda x: x}      # 字典里放一个匿名函数
    fn = lambda x: x            # 单独一个匿名函数

    # 下面这个列表里，每个元组的第三项又是一个 lambda：
    #   lambda: d | ChatPromptTemplate...   ← 注意冒号前【没有参数】
    # 这是"零参数的匿名函数"，写成 lambda: 表达式，
    # 作用是「把这段代码包起来先不执行」，等下面循环里再调用它（延迟执行）。
    # 这么写是为了：即使某一项会抛异常，也不会影响列表本身的构造。
    cases = [
        ("dict | Runnable(fn)", "✅", lambda: d | ChatPromptTemplate.from_template("{a}")),
        ("RunnableParallel | fn", "✅", lambda: RunnableParallel(a=fn) | fn),
        ("dict | RunnableLambda(fn)", "✅", lambda: d | RunnableLambda(fn)),
        ("dict | fn", "❌", lambda: d | fn),
    ]
    print(f"  {'写法':<30}{'结果'}")
    print("  " + "-" * 46)
    for name, flag, f in cases:
        try:
            r = f()
            print(f"  {name:<30}{flag} -> {type(r).__name__}")
        except TypeError:
            print(f"  {name:<30}{flag} TypeError: unsupported operand type(s) for |")

    print("\n  >> 解法很简单：保证至少一边是 Runnable")
    print("     ① 右边自带 Runnable（实际项目最常见，因为右边是 prompt/model）")
    print("     ② 右边包一层 RunnableLambda(fn)")
    print("     ③ 左边显式写 RunnableParallel(a=fn)")
    print("\n  >> 顺带解释了为什么旧文件 2 能跑：")
    print("     它写的是 {dict} | prompt，右边 prompt 是 Runnable，所以自动转换生效。")


# ---------------------------------------------------------------------------
# 6. 异步版本（Web 服务里用这个）
# ---------------------------------------------------------------------------
def demo_6_async() -> None:
    section("6. 异步并发 ainvoke")

    async def run():
        para = RunnableParallel(
            a=make_chain("用一句话介绍：{topic}"),
            b=make_chain("用一句话吐槽：{topic}"),
        )
        t0 = time.perf_counter()
        res = await para.ainvoke({"topic": "Redis"})
        cost = time.perf_counter() - t0
        print(f"  ainvoke 总耗时 {cost:.2f}s")
        print("  a:", res["a"][:45])
        print("  b:", res["b"][:45])
        print("\n  >> Web 服务里一律用 ainvoke：async 下是协程并发，")
        print("     不会占用线程池，吞吐量比 invoke 高得多。")

    asyncio.run(run())


# ---------------------------------------------------------------------------
# 7. 顺带一提：Runnable 的通用工程能力
# ---------------------------------------------------------------------------
def demo_7_runnable_utils() -> None:
    section("7. RunnableParallel 自带的工程能力")

    para = RunnableParallel(a=lambda x: "A", b=lambda x: "B")
    print("所有 Runnable 都有的方法（不只是 RunnableParallel）：")
    # (真实属性名, 展示名, 说明)
    for attr, display, desc in [
        ("with_retry", "with_retry(...)", "失败自动重试，网络抖动时救命"),
        ("with_fallbacks", "with_fallbacks(...)", "降级：主链路挂了走备用链路"),
        ("with_config", "with_config(...)", "绑定配置，如并发数、回调、标签"),
        ("with_types", "with_types(...)", "显式声明输入/输出类型"),
        ("batch", "batch / abatch", "批量并发处理多组输入"),
        ("stream", "stream / astream", "流式输出"),
    ]:
        print(f"  {display:<24}{desc}  {'✓' if hasattr(para, attr) else '✗'}")

    print("\n  示例：给并行链加重试和降级")
    chain = RunnableParallel(
        joke=make_chain("讲个关于{topic}的冷笑话"),
    ).with_retry(stop_after_attempt=2)
    try:
        print("  →", chain.invoke({"topic": "Bug"})["joke"][:40])
    except Exception as e:
        print("  失败:", type(e).__name__, str(e)[:80])


def main() -> None:
    print("1. RunnableParallel 使用技巧（DeepSeek + 最新 API）")
    demo_1_two_styles()
    demo_2_is_it_really_parallel()
    demo_3_multi_perspective()
    demo_4_max_concurrency()
    demo_5_pitfall()
    demo_6_async()
    demo_7_runnable_utils()
    print("\n" + "=" * 62)
    print("全部示例执行完毕。")


if __name__ == "__main__":
    main()
