#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
3. RunnablePassthrough 使用技巧（最新 API 版）
=============================================
【Python 语法看不懂？】闭包、lambda、** 解包、推导式等见 ../PYTHON_SYNTAX.md

【RunnablePassthrough 是什么】
    一个"什么都不做"的 Runnable：输入什么原样输出什么。
    听起来没用，但它的 .assign() 方法非常好用。

【assign 解决什么问题】
    场景：RAG 里 prompt 需要 {context} 和 {query} 两个变量，
          但用户只传进来一个 {"query": "..."}。

    用 RunnableParallel 你得把每个字段都抄一遍：
        RunnableParallel(
            context=检索逻辑,
            query=itemgetter("query"),      # ← 得手动把 query 再列一遍
            user_id=itemgetter("user_id"),  # ← 字段多起来就很啰嗦
            ...
        )

    用 assign 就不用抄了——它自动保留原输入的所有字段，只追加新的：
        RunnablePassthrough.assign(context=检索逻辑)
        # {"query": "...", "user_id": "..."}
        #        ↓
        # {"query": "...", "user_id": "...", "context": "..."}

    一句话区别：
        RunnableParallel       = 「我明确列出要哪些字段」
        Passthrough.assign     = 「原样透传 + 追加新字段」

【本文件会实测的几点】
    · assign 内部是否并发
    · assign 能否链式调用多次
    · RunnableAssign 类和 .assign() 的关系
    · 什么时候该用 assign，什么时候该用 RunnableParallel

【运行】
    ./yzy/Scripts/python.exe "aiLearn/runnable/new/3.RunnablePassthrough使用技巧.py"
"""

import os
import threading
import time
from pathlib import Path

import dotenv
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import (
    RunnableAssign,
    RunnableLambda,
    RunnableParallel,
    RunnablePassthrough,
)
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


KNOWLEDGE_BASE = {
    "退款": "退款规则：7天无理由退款，商品需完好；卖家超时未发货可全额退款。",
    "发货": "发货时效：下单后48小时内发出，节假日顺延。",
    "发票": "发票开具：订单完成后可申请电子发票，3个工作日内开出。",
    "会员": "会员权益：每月5张优惠券，生日双倍积分，专属客服通道。",
}


def retrieval(query: str) -> str:
    """模拟检索器"""
    hits = [t for kw, t in KNOWLEDGE_BASE.items() if kw in query]
    return "\n".join(f"- {h}" for h in hits) if hits else "（无相关资料）"


PROMPT = ChatPromptTemplate.from_template("""请根据用户的问题回答，可以参考对应的上下文进行生成。

<context>
{context}
</context>

用户的提问是: {query}""")


# ---------------------------------------------------------------------------
# 1. RunnablePassthrough 本身：原样透传
# ---------------------------------------------------------------------------
def demo_1_passthrough_alone() -> None:
    section("1. RunnablePassthrough 单独用：输入=输出")

    r = RunnablePassthrough()
    data = {"a": 1, "b": 2}
    print("  输入:", data)
    print("  输出:", r.invoke(data))
    print("\n  >> 单独用确实没意义，它的价值在 .assign() 和管道里的占位：")
    print("     想在管道中间什么都不做地透传一段，就用它。")


# ---------------------------------------------------------------------------
# 2. assign 基本用法
# ---------------------------------------------------------------------------
def demo_2_assign_basic() -> None:
    section("2. assign：保留原字段 + 追加新字段")

    # lambda x: retrieval(x["query"]) 里的 x 是【上游传来的整个输入字典】，
    # 展开写就是：
    #   def get_context(x):
    #       return retrieval(x["query"])
    # assign 会给这个返回值起个名字（这里叫 context），追加到原输入里。
    chain = RunnablePassthrough.assign(
        context=lambda x: retrieval(x["query"]),
    )
    out = chain.invoke({"query": "退款政策是什么？", "user_id": "u_001"})

    print("  输入: {'query': ..., 'user_id': 'u_001'}")
    print("  输出键:", list(out.keys()))
    print("  context 字段:", out["context"][:40], "...")
    print("  user_id 是否在原样保留:", "user_id" in out)

    print("\n  >> 注意 user_id 完全没动——这就是 assign 和 RunnableParallel")
    print("     最大的区别：不用把每个原字段抄一遍。")


# ---------------------------------------------------------------------------
# 3. 对比：同样的事用 RunnableParallel 要怎么写
# ---------------------------------------------------------------------------
def demo_3_compare_with_parallel() -> None:
    section("3. 对比：RunnableParallel 要手写所有字段")

    inp = {"query": "怎么开发票？", "user_id": "u_001", "session_id": "s_9"}

    # assign 版：只写新增的
    out_assign = RunnablePassthrough.assign(
        context=lambda x: retrieval(x["query"]),
    ).invoke(inp)

    # RunnableParallel 版：得把每个字段都抄一遍
    out_parallel = RunnableParallel(
        context=lambda x: retrieval(x["query"]),
        query=lambda x: x["query"],          # ← 抄
        user_id=lambda x: x["user_id"],      # ← 抄
        session_id=lambda x: x["session_id"]  # ← 抄
    ).invoke(inp)

    print("  输入字段:", list(inp.keys()))
    print("  assign 输出字段   :", list(out_assign.keys()))
    print("  parallel 输出字段 :", list(out_parallel.keys()))
    print("  两者是否等价:", out_assign == out_parallel)

    print("\n  >> 字段越多，assign 越省事。")
    print("     实战建议：需要保留大部分原字段 → assign；")
    print("              只要少数几个字段     → RunnableParallel + pick")


# ---------------------------------------------------------------------------
# 4. 实测：assign 的多个字段是并发算的吗
# ---------------------------------------------------------------------------
def demo_4_assign_is_parallel() -> None:
    section("4. 实测：assign 多个字段时并发吗")

    # 【工厂函数】slow("A", 1.2) 不执行，只是造出一个"会睡 1.2 秒"的 Runnable
    def slow(name, sec):
        """外层接收参数，内层 f 才是真正被执行的逻辑（闭包捕获 name/sec）"""
        def f(_x):
            time.sleep(sec)     # sec 来自外层
            return f"{name}@{threading.current_thread().name}"   # name 也来自外层
        return RunnableLambda(f)

    # 两次调用得到两个不同的 Runnable，分别赋给 a 和 b 两个分支
    chain = RunnablePassthrough.assign(a=slow("A", 1.2), b=slow("B", 1.2))

    t0 = time.perf_counter()
    out = chain.invoke({"origin": "keep"})
    cost = time.perf_counter() - t0

    print("  结果:", out)
    print(f"  总耗时: {cost:.2f}s（串行应为 2.40s，并发约 1.20s）")
    if cost < 1.8:
        print("\n  ✅ assign 内部也是并发的。")
        print("     >> 它等价于 RunnableAssign(RunnableParallel(...))，")
        print("        所以天然继承了 RunnableParallel 的线程池并发。")
    else:
        print("\n  ⚠️ 本次未观察到并发")


# ---------------------------------------------------------------------------
# 5. 多次 assign 链式调用
# ---------------------------------------------------------------------------
def demo_5_chained_assign() -> None:
    section("5. 多次 assign 链式叠加")

    # 每一步都可以依赖上一步算出来的字段
    chain = (
        RunnablePassthrough.assign(ctx=lambda x: retrieval(x["query"]))
        .assign(ctx_len=lambda x: len(x["ctx"]))          # 依赖上一步的 ctx
        .assign(summary=lambda x: f"检索到 {x['ctx_len']} 字资料")
    )
    out = chain.invoke({"query": "会员权益有哪些？"})
    print("  最终字段:", list(out.keys()))
    print("  summary:", out["summary"])
    print("  ctx_len:", out["ctx_len"])

    print("\n  >> assign 可以无限往后接，后面的能读到前面算出来的字段。")
    print("     这让你能把复杂的数据准备过程拆成一串小步骤，可读性好。")


# ---------------------------------------------------------------------------
# 6. RunnableAssign 类：assign 的底层实现
# ---------------------------------------------------------------------------
def demo_6_runnable_assign() -> None:
    section("6. RunnableAssign —— assign 的底层类")

    # 这两者是等价的：
    a = RunnablePassthrough.assign(extra=lambda x: 42)
    b = RunnableAssign(RunnableParallel(extra=lambda x: 42))

    print("  Passthrough.assign(...)          :", type(a).__name__)
    print("  RunnableAssign(RunnableParallel) :", type(b).__name__)
    print("  两者输出是否一致:", a.invoke({}) == b.invoke({}))
    print("\n  >> 平时写 .assign() 就够，知道有这个类是为了看懂别人的代码和报错栈。")


# ---------------------------------------------------------------------------
# 7. 完整实战：RAG 链路
# ---------------------------------------------------------------------------
def demo_7_full_rag() -> None:
    section("7. 完整实战：RAG 链路（对比旧文件 3）")

    llm = build_llm()

    # 旧文件的写法：
    #   RunnablePassthrough.assign(context=lambda x: retrieval(x["query"])) | prompt | llm | parser
    # 新版推荐把 lambda 包成 RunnableLambda，其余结构完全一致
    chain = (
        RunnablePassthrough.assign(
            context=RunnableLambda(lambda x: retrieval(x["query"]))
        )
        | PROMPT
        | llm
        | StrOutputParser()
    )

    res = chain.invoke({"query": "我想开发票，怎么弄？"})
    print("  问题: 我想开发票，怎么弄？")
    print("  回答:", res)

    print("\n  >> 这就是最经典的 RAG 最小链路。")
    print("     真实项目里 retrieval 换成向量库查询即可，管道结构不变。")


def main() -> None:
    print("3. RunnablePassthrough 使用技巧（DeepSeek + 最新 API）")
    demo_1_passthrough_alone()
    demo_2_assign_basic()
    demo_3_compare_with_parallel()
    demo_4_assign_is_parallel()
    demo_5_chained_assign()
    demo_6_runnable_assign()
    demo_7_full_rag()
    print("\n" + "=" * 62)
    print("全部示例执行完毕。")


if __name__ == "__main__":
    main()
