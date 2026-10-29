#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
2. RunnableParallel 模拟检索（RAG 场景，最新 API 版）
====================================================
教材原文（已归档）：old/2.RunnableParallel模拟检索.py
【Python 语法看不懂？】闭包、lambda、** 解包、推导式等见 ../PYTHON_SYNTAX.md

【这个文件在讲什么】
    RAG（检索增强生成）最基础的形态：

        用户提问 ──┬──→ 检索器 ──→ context（参考资料）
                   └──→ 原样透传 ──→ query（原问题）
                                        ↓
                                  组装成 prompt
                                        ↓
                                      模型回答

    难点在于：prompt 需要【两个变量】(context 和 query)，
    但用户的输入只有一个 query。中间要补算出 context 这一项。

    RunnableParallel 就是干这个的：
        输入 {"query": "..."}  →  输出 {"context": "...", "query": "..."}

【旧写法为什么能跑（很多人知其然不知其所以然）】

【新版推荐怎么写】
    显式写 RunnableParallel + RunnableLambda，理由：
    · 类型明确，IDE 能推断
    · 支持 async（RunnableLambda 可以传协程函数）
    · 不容易踩 file 1 第 5 节那个 TypeError

【运行】
    ./yzy/Scripts/python.exe "aiLearn/runnable/new/2.RunnableParallel模拟检索.py"
"""

import os
from operator import itemgetter
from pathlib import Path

import dotenv
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnableLambda, RunnableParallel, RunnablePassthrough
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


# 一个"模拟的知识库"，比旧教学里的固定返回值更真实一点
KNOWLEDGE_BASE = {
    "退款": "退款规则：7天无理由退款，需保证商品完好；超时未发货可申请全额退款。",
    "发货": "发货时效：下单后48小时内发出，节假日顺延。",
    "发票": "发票开具：订单完成后可在「我的订单」申请电子发票，3个工作日内开具。",
    "会员": "会员权益：每月5张优惠券，生日双倍积分，专属客服通道。",
}


def retrieval(query: str) -> str:
    """模拟检索器：按关键词匹配知识库。

    真实项目里这里会换成向量检索（比如 Faiss / Milvus）。
    RunnableParallel 不关心你怎么检索，只要求它是个可调用对象。
    """
    print(f"    [检索器] 收到查询: {query}")
    hits = [text for kw, text in KNOWLEDGE_BASE.items() if kw in query]
    if not hits:
        return "（知识库中没有相关资料）"
    return "\n".join(f"- {h}" for h in hits)


PROMPT = ChatPromptTemplate.from_template("""请根据用户的问题回答，可以参考对应的上下文进行生成。

<context>
{context}
</context>

用户的提问是: {query}""")


# ---------------------------------------------------------------------------
# 1. 先看懂：dict 字面量是怎么变成 RunnableParallel 的
# ---------------------------------------------------------------------------
def demo_1_dict_magic() -> None:
    section("1. dict 字面量为什么能接 | ")

    # 这两个 lambda 是本文件里最基础的写法，先解释一次：
    #
    #   lambda x: retrieval(x["query"])
    #   ├─ lambda x:      x 是上游传进来的【整个输入字典】
    #   └─ x["query"]     从字典里取 query 字段去检索
    #
    # 展开写就是：
    #   def get_context(x):
    #       return retrieval(x["query"])
    #
    # 另一个 itemgetter("query") 做的是同样的事（取 x["query"]），
    # 只是它是 C 实现的标准库函数，性能略好、官方示例常用。
    d = {
        "context": lambda x: retrieval(x["query"]),
        "query": itemgetter("query"),
    }
    print("  原始 dict 的类型:", type(d).__name__)

    # 一旦用 | 和 Runnable 组合，dict 就被转换了
    combined = d | PROMPT
    print("  dict | prompt 之后:", type(combined).__name__)
    if hasattr(combined, "steps"):
        print("  管道各段类型:", [type(s).__name__ for s in combined.steps])

    print("\n  >> 关键：dict.__or__ 不存在，Python 改调用右边 prompt 的 __ror__，")
    print("     langchain 在里面把 dict 转成了 RunnableParallel，")
    print("     并把 dict 里的每个 callable 包成 RunnableLambda。")
    print("\n  >> 所以 dict 字面量 == RunnableParallel 的语法糖。")




# ---------------------------------------------------------------------------
# 2. 新版推荐：显式 RunnableParallel + RunnableLambda
# ---------------------------------------------------------------------------
def demo_2_new_style() -> None:
    section("3. 新版推荐：显式 RunnableParallel + RunnableLambda")

    llm = build_llm()
    chain = RunnableParallel(
        # 用 RunnableLambda 包一层，类型明确、可异步
        context=RunnableLambda(lambda x: retrieval(x["query"])),
        query=itemgetter("query"),
    ) | PROMPT | llm | StrOutputParser()

    print("用户输入: {'query': '会员有什么权益？'}")
    res = chain.invoke({"query": "会员有什么权益？"})
    print("\n模型回答:", res)

    print("\n  >> 和旧写法结果一样，但好处是：")
    print("     · 看到了 RunnableParallel 就知道这是并行/多路汇聚点")
    print("     · RunnableLambda 可以接 async 函数，支持异步链路")
    print("     · 避免 'dict | fn' 那种 TypeError")


# ---------------------------------------------------------------------------
# 3. RunnableParallel 的真正价值：多路检索并发
# ---------------------------------------------------------------------------
def demo_3_multi_retrieval() -> None:
    section("3. 多路检索并发 —— RunnableParallel 的用武之地")

    # ===================== 先看懂这个「工厂函数」 =====================
    # fake_vector_search 是「返回函数的函数」，拆开看是这样的：
    #
    #   def fake_vector_search(source):     ← 外层：接收配置（数据源名字）
    #       def search(x):                  ← 内层：真正的执行逻辑
    #           ...
    #           return f"...{source}..."    ← 内层用到了外层的 source
    #       return RunnableLambda(search)   ← 把内层函数包成 Runnable 返回
    #
    # 两个关键点：
    #
    # ① 闭包（closure）
    #    内层 search「记住」了外层传进来的 source，即使外层已经执行完了。
    #    所以调用三次会造出三个不同的检索器，各自记得自己的数据源名。
    #
    # ② 为什么要包一层 RunnableLambda
    #    RunnableParallel 的每个分支必须是 Runnable（要有 invoke/batch/stream），
    #    裸函数没有这些方法。包一层就"升级"成了 Runnable。
    #
    # 用 Java 对照更好懂（唯一区别就是 Python 最后要多包一层 RunnableLambda）：
    #   // 返回一个 Function，捕获的 source 必须是 effectively final
    #   static Runnable fakeVectorSearch(String source) {
    #       return x -> "[" + source + "命中] 关于「" + x.get("query") + "」的资料";
    #   }
    # ================================================================
    def fake_vector_search(source: str):
        """造一个「某数据源的检索器」。

        注意：调用它【不会】执行检索，只是造出一个检索器。
        真正检索发生在后面 chain.invoke() 的时候。
        """
        def search(x: dict) -> str:
            q = x["query"]              # x 是上游传来的整包数据，取 query 字段
            return f"[{source}命中] 关于「{q}」的资料"   # source 来自外层（闭包）

        return RunnableLambda(search)   # 包装成 Runnable 才能放进管道

    llm = build_llm()

    # 三个数据源并发检索
    # 这里调用了 fake_vector_search 三次，得到三个不同的检索器：
    #   docs → 记得 source="产品文档库"
    #   faq  → 记得 source="历史工单库"
    #   wiki → 记得 source="内部Wiki"
    chain = RunnableParallel(
        docs=fake_vector_search("产品文档库"),
        faq=fake_vector_search("历史工单库"),
        wiki=fake_vector_search("内部Wiki"),
    ) | RunnableLambda(
        # 上一步 RunnableParallel 的输出是个 dict：
        #   {"docs": "...", "faq": "...", "wiki": "..."}
        # 但 PROMPT 需要的是 {context, query} 两个变量，
        # 所以这里做一次「字段转换」：把三路结果拼成 context。
        #
        # lambda d: {...} 就是个匿名函数，等价于：
        #   def convert(d):
        #       return {"query": "...", "context": "..."}
        #   RunnableLambda(convert)
        lambda d: {
            "query": "告诉我你检索到了什么",
            "context": f"{d['docs']}\n{d['faq']}\n{d['wiki']}",
        }
    ) | PROMPT | llm | StrOutputParser()

    res = chain.invoke({"query": "退款政策"})
    print("三个数据源并发检索后交给模型：")
    print(res)
    print("\n  >> 真实 RAG 系统里这三路是真去查三个库，")
    print("     并发能把总耗时压到最慢那一路的时间，而不是三者之和。")


# ---------------------------------------------------------------------------
# 4. RunnablePick：只挑需要的字段
# ---------------------------------------------------------------------------
def demo_4_pick() -> None:
    section("4. RunnablePick —— 只保留需要的字段")

    para = RunnableParallel(
        a=lambda x: "A值",
        b=lambda x: "B值",
        c=lambda x: "C值",
    )
    print("全部字段:", para.invoke({}))

    # .pick() 在并行结果里只挑指定字段
    picked = para.pick(["a", "c"])
    print("pick(['a','c']):", picked.invoke({}))

    print("\n  >> 用途：下游只需要部分字段时，用 pick 收窄数据流，")
    print("     管道意图更清晰，也避免把无关数据往后传。")


# ---------------------------------------------------------------------------
# 5. 对比：RunnableParallel 语义 vs RunnablePassthrough.assign 语义
# ---------------------------------------------------------------------------
def demo_5_assign_semantics() -> None:
    section("5. 另一种写法：RunnablePassthrough.assign")

    llm = build_llm()

    # RunnablePassthrough.assign：保留原输入，追加新字段
    # 比 RunnableParallel 更省事——不用手动把其他字段再抄一遍
    chain = (
        RunnablePassthrough.assign(context=lambda x: retrieval(x["query"]))
        | PROMPT
        | llm
        | StrOutputParser()
    )
    print("用 assign 的写法，输入还是 {'query': ...}")
    res = chain.invoke({"query": "发货要多久？"})
    print("模型回答:", res)

    print("\n  >> RunnableParallel   : 你要显式列出所有下游需要的字段")
    print("  >> Passthrough.assign : 原字段自动保留，只追加新的")
    print("  >> 后者在字段多的时候明显更省事，详见 3.RunnablePassthrough*.py")


def main() -> None:
    print("2. RunnableParallel 模拟检索（DeepSeek + 最新 API）")
    demo_1_dict_magic()
    demo_2_new_style()
    demo_3_multi_retrieval()
    demo_4_pick()
    demo_5_assign_semantics()
    print("\n" + "=" * 62)
    print("全部示例执行完毕。")


if __name__ == "__main__":
    main()
