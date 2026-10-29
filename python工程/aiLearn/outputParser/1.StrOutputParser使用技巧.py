#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
1. StrOutputParser 使用技巧（最新 API 版）
=========================================

    新版是 LCEL 管道，从左到右读一遍就懂：
        chain = prompt | llm | StrOutputParser()
        content = chain.invoke({"query": "你好，你是?"})

    为什么管道更好？
        · 读起来是正向的（数据从左流到右），而不是从内往外剥洋葱
        · 加/删组件只改一处：想去掉解析器就把末尾一段删掉
        · 链路上任何一段都能单独替换，比如把 llm 换成假模型做单测

【StrOutputParser 到底做了什么】
    模型返回的是 AIMessage 对象，不是字符串。
    StrOutputParser 做的事就是：AIMessage → 它的 .content 字符串。
    听起来很简单，但它在流式场景下是必需品，

【运行】
    ./yzy/Scripts/python.exe "aiLearn/outputParser/new/1.StrOutputParser使用技巧.py"
"""

import os
from pathlib import Path

import dotenv
from langchain_core.output_parsers import CommaSeparatedListOutputParser, StrOutputParser
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
    """构造 DeepSeek 模型（参数含义见 model/new/1.LLM与ChatModel使用技巧.py）"""
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
# 1. 新旧写法对比
# ---------------------------------------------------------------------------
def demo_1_old_vs_new() -> None:
    section("1. 旧写法（三层套娃） vs 新写法（管道）")

    prompt = ChatPromptTemplate.from_template("{query}")
    llm = build_llm()
    parser = StrOutputParser()
    query = "你好，你是?"



    # ---- 新写法：管道，从左往右执行 ----
    print("\n【新写法】chain = prompt | llm | parser")
    chain = prompt | llm | parser
    content_new = chain.invoke({"query": query})
    print("  结果:", content_new[:60])

    print("\n>> 两段代码做的事完全一样，但管道版本：")
    print("   · 读起来是正向的数据流，不是从内往外剥")
    print("   · 想去掉解析器，删掉末尾的 | parser 即可")
    print("   · 想换模型做单测，只替换中间那一段")


# ---------------------------------------------------------------------------
# 2. 有没有 parser 的区别
# ---------------------------------------------------------------------------
def demo_2_with_or_without() -> None:
    section("2. 加不加 StrOutputParser 的差别")

    llm = build_llm()
    prompt = ChatPromptTemplate.from_template("{query}")

    print("不加解析器 —— 拿到 AIMessage:")
    r1 = (prompt | llm).invoke({"query": "用一句话介绍Redis"})
    print("  类型:", type(r1).__name__)
    print("  取文本要写 .content:", r1.content[:40])

    print("\n加解析器 —— 直接拿到字符串:")
    r2 = (prompt | llm | StrOutputParser()).invoke({"query": "用一句话介绍Redis"})
    print("  类型:", type(r2).__name__, "| isinstance(str):", isinstance(r2, str))
    print("  直接用:", r2[:40])

    print("\n>> 注意类型是 TextAccessor 而不是 str —— 它是 str 的子类，")
    print("   打印、拼接、切片都跟 str 一样，不用管这个细节。")


# ---------------------------------------------------------------------------
# 3. 流式场景：StrOutputParser 的真正价值
# ---------------------------------------------------------------------------
def demo_3_stream() -> None:
    section("3. 流式输出时必须加 StrOutputParser")

    llm = build_llm()
    prompt = ChatPromptTemplate.from_template("{query}")

    print("不加解析器流式 —— 流出来的是 AIMessageChunk 对象:")
    chunks = []
    for c in (prompt | llm).stream({"query": "用一句话介绍Kafka"}):
        chunks.append(c)
    print(f"  共 {len(chunks)} 个 chunk，第1个类型: {type(chunks[0]).__name__}")
    print("  前端拿到这个对象没法直接显示，还得自己取 .content")

    print("\n加解析器流式 —— 流出来的直接是字符串片段:")
    text = ""
    for s in (prompt | llm | StrOutputParser()).stream({"query": "用一句话介绍Kafka"}):
        text += s
    print("  直接拼接的结果:", text[:60])

    print("\n>> 结论：做打字机效果时，管道末尾一定要挂 StrOutputParser，")
    print("   否则前端收到的是一堆消息对象，不是能显示的文字。")


# ---------------------------------------------------------------------------
# 4. 补充：其他简单解析器
# ---------------------------------------------------------------------------
def demo_4_other_parsers() -> None:
    section("4. 顺带一提：CommaSeparatedListOutputParser")

    # 这个解析器把模型返回的 "a, b, c" 解析成 Python 列表
    # 适合让模型返回枚举值、标签列表这类简单结构
    parser = CommaSeparatedListOutputParser()
    chain = (
        ChatPromptTemplate.from_messages([
            ("system", "你是标签生成器。只输出逗号分隔的标签，不要任何其他文字。"),
            ("human", "给这篇文章打3个标签：{title}"),
        ])
        | build_llm()
        | parser
    )
    try:
        tags = chain.invoke({"title": "Redis分布式锁的实现原理与踩坑总结"})
        print("  解析结果类型:", type(tags).__name__)
        print("  内容:", tags)
        print("\n  >> 简单列表够用；结构复杂、字段多时应该用")
        print("     JsonOutputParser 或 with_structured_output（见后两个文件）。")
    except Exception as e:
        print("  解析失败:", type(e).__name__, e)


def main() -> None:
    print("1. StrOutputParser 使用技巧（DeepSeek + 最新 API）")
    demo_1_old_vs_new()
    demo_2_with_or_without()
    demo_3_stream()
    demo_4_other_parsers()
    print("\n" + "=" * 62)
    print("全部示例执行完毕。")


if __name__ == "__main__":
    main()
