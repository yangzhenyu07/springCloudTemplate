#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
2. JsonOutputParser 使用技巧（最新 API 版）
===========================================


    新版：prompt | llm | parser                             管道

【本文件会演示三种 JSON 解析路线，各有适用场景】
    1. JsonOutputParser        → 解析成 dict，最灵活，不校验字段
    2. PydanticOutputParser    → 解析成你定义的 pydantic 对象，会校验字段
    3. with_structured_output  → 最新最推荐，交给模型原生能力（见 3.*.py）

【运行】
    ./yzy/Scripts/python.exe "aiLearn/outputParser/new/2.JsonOutputParser使用技巧.py"
"""

import os
from pathlib import Path
from typing import List

import dotenv
from langchain_core.output_parsers import JsonOutputParser, PydanticOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field

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


# 用 pydantic 定义"你期望模型输出什么结构"
# Field 的 description 会被写进提示词里，告诉模型每个字段该填什么
class Joke(BaseModel):
    """冷笑话的数据结构"""
    joke: str = Field(description="回答用户的冷笑话")
    punchline: str = Field(description="这个冷笑话的笑点")




# ---------------------------------------------------------------------------
# 1. JsonOutputParser：解析成 dict
# ---------------------------------------------------------------------------
def demo_1_json_output_parser() -> None:
    section("1. JsonOutputParser —— 解析成 dict")

    parser = JsonOutputParser(pydantic_object=Joke)

    # get_format_instructions() 会生成一段"输出格式说明"，
    # 用 partial 固定到 prompt 里，模型就知道该输出什么 JSON
    print("自动生成的格式说明（get_format_instructions）:")
    print("  ", parser.get_format_instructions()[:80].replace("\n", " "), "...")

    prompt = ChatPromptTemplate.from_messages([
        ("system", "你是一个冷笑话生成器。\n{format_instructions}"),
        ("human", "{query}"),
    ]).partial(format_instructions=parser.get_format_instructions())

    chain = prompt | build_llm() | parser
    result = chain.invoke({"query": "请讲一个关于程序员的冷笑话"})

    print("\n解析结果类型:", type(result).__name__)
    print("结果:", result)
    print("取字段:", result.get("punchline"))
    print("\n  >> 拿到的是普通 dict，灵活但不做字段校验。")
    print("     若模型漏了字段，这里不会报错，要自己判断。")


# ---------------------------------------------------------------------------
# 3. PydanticOutputParser：解析成对象，带校验
# ---------------------------------------------------------------------------
def demo_2_pydantic_output_parser() -> None:
    section("2. PydanticOutputParser —— 解析成对象，自带校验")

    parser = PydanticOutputParser(pydantic_object=Joke)
    prompt = ChatPromptTemplate.from_messages([
        ("system", "你是一个冷笑话生成器。\n{format_instructions}"),
        ("human", "{query}"),
    ]).partial(format_instructions=parser.get_format_instructions())

    chain = prompt | build_llm() | parser
    joke: Joke = chain.invoke({"query": "请讲一个关于程序员的冷笑话"})

    print("解析结果类型:", type(joke).__name__, " <-- 是你定义的 Joke 类")
    print("笑话  :", joke.joke)
    print("笑点  :", joke.punchline)
    print("\n  >> 比 dict 好在哪：")
    print("     · 有属性提示，写 joke.xxx 时 IDE 能补全")
    print("     · 字段缺失或类型不对会直接抛校验错误，问题暴露得更早")
    print("     · 后面要接数据库/接口时，直接 .model_dump() 转 dict")


# ---------------------------------------------------------------------------
# 3. 复杂结构：嵌套 + 列表
# ---------------------------------------------------------------------------
def demo_3_nested_schema() -> None:
    section("3. 复杂结构：嵌套对象和列表")

    # 定义一个稍微复杂点的结构，展示 pydantic 的表达能力
    class Author(BaseModel):
        name: str = Field(description="作者姓名")
        era: str = Field(description="所处朝代或年代")

    class Poem(BaseModel):
        title: str = Field(description="诗名")
        author: Author = Field(description="作者信息")
        lines: List[str] = Field(description="诗句列表，按顺序")
        themes: List[str] = Field(description="这首诗表达的主题，1-3个")

    parser = PydanticOutputParser(pydantic_object=Poem)
    prompt = ChatPromptTemplate.from_messages([
        ("system", "你是一位古典文学学者。\n{format_instructions}"),
        ("human", "{query}"),
    ]).partial(format_instructions=parser.get_format_instructions())

    try:
        poem: Poem = (prompt | build_llm() | parser).invoke({"query": "介绍一首描写秋天的唐诗"})
        print("标题  :", poem.title)
        print("作者  :", poem.author.name, f"（{poem.author.era}）")
        print("诗句  :", poem.lines[:2], "...")
        print("主题  :", poem.themes)
        print("\n  >> 嵌套对象、列表都能定义。但结构越复杂，小模型越容易漏字段，")
        print("     这时应该改用 with_structured_output（见下一个文件）。")
    except Exception as e:
        print("  解析失败:", type(e).__name__, str(e)[:200])
        print("  >> 复杂结构下这是常态，所以才有下一个文件的方案。")


# ---------------------------------------------------------------------------
# 5. 解析失败的兜底
# ---------------------------------------------------------------------------
def demo_4_fallback() -> None:
    section("4. 解析失败怎么办（生产必看）")

    print("解析失败的两个常见原因：")
    print("  1. 模型没听话，在 JSON 外面包了 ```json 代码块或解释文字")
    print("  2. 字段缺漏 / 类型不对，pydantic 校验不过")

    print("\n常见的三种兜底手段：")
    print("  A. 提示词里写死约束（只输出JSON、不要代码块），最廉价")
    print("  B. 加重试：用 RunnableRetry 或自己 try/except 重跑 1-2 次")
    print("  C. 换 with_structured_output：让模型原生保证格式，最可靠")

    # 演示 B：自己包一层重试
    parser = JsonOutputParser(pydantic_object=Joke)
    prompt = ChatPromptTemplate.from_messages([
        ("system", "你是冷笑话生成器。只输出纯 JSON，不要代码块，不要解释。\n{format_instructions}"),
        ("human", "{query}"),
    ]).partial(format_instructions=parser.get_format_instructions())
    chain = prompt | build_llm() | parser

    result = None
    for attempt in range(1, 4):
        try:
            result = chain.invoke({"query": "讲一个关于测试的冷笑话"})
            print(f"\n  第 {attempt} 次尝试成功:", result.get("joke", "")[:35], "...")
            break
        except Exception as e:
            print(f"  第 {attempt} 次失败: {type(e).__name__}")
    if result is None:
        print("  三次都失败，走降级逻辑（比如返回默认值或人工介入）")


def main() -> None:
    print("JsonOutputParser 使用技巧（DeepSeek + 最新 API）")
    demo_1_json_output_parser()
    demo_2_pydantic_output_parser()
    demo_3_nested_schema()
    demo_4_fallback()
    print("\n" + "=" * 62)
    print("全部示例执行完毕。")


if __name__ == "__main__":
    main()
