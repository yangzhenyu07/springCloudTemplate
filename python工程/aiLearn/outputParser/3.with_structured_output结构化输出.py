#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
3. with_structured_output 结构化输出（最新 API，推荐方案）
==========================================================
本文件是 outputParser 三个文件里【最重要】的一个。

【这是什么】
    前面两个文件的做法，本质是"在提示词里求模型输出 JSON，然后自己解析"。
    这有个根本问题：模型是"被说服"的，不是"被强制"的，所以随时可能不听话。

    with_structured_output() 换了个思路：
    把你的数据结构（pydantic 类）交给模型，让模型【原生保证】输出格式。
    底层用的是各家厂商的 function calling / structured output 能力，
    格式由 API 层面强制，不再靠提示词恳求。

【三种 method，以及在 DeepSeek 上的实测结果】
    langchain-openai 支持三种模式，本文件会逐个实测（都跑过了）：

    ┌──────────────────┬──────────────────────────────────────────┐
    │ method           │ DeepSeek 实测（2026-10-26）               │
    ├──────────────────┼──────────────────────────────────────────┤
    │ json_schema(默认) │ ❌ 400 response_format type is unavailable│
    │ json_mode        │ ❌ 要求 prompt 必须含 "json" 字样          │
    │ function_calling │ ✅ 可用，但要先关掉思考模式（见下）        │
    └──────────────────┴──────────────────────────────────────────┘

【⚠️ DeepSeek 最大的坑（本文件核心）】
    DeepSeek 的「思考模式(thinking)」和 function calling 是冲突的：
        Error: Thinking mode does not support this tool_choice
    所以要显式关掉思考：
        ChatOpenAI(..., extra_body={"thinking": {"type": "disabled"}})
    关掉之后 function_calling 模式立刻正常。

【运行】
    ./yzy/Scripts/python.exe "aiLearn/outputParser/new/3.with_structured_output结构化输出.py"
"""

import os
from pathlib import Path
from typing import List, Optional

import dotenv
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


def build_llm(disable_thinking: bool = False) -> ChatOpenAI:
    """构造 DeepSeek 模型。

    disable_thinking=True 时，额外传 extra_body 关掉思考模式。
    DeepSeek 的思考模式和 function calling 冲突，做结构化输出时必须关掉。
    """
    kwargs = {}
    if disable_thinking:
        kwargs["extra_body"] = {"thinking": {"type": "disabled"}}

    return ChatOpenAI(
        model="deepseek-flash",
        api_key=os.getenv("DEEPSEEK_API_KEY"),
        base_url=os.getenv("DEEPSEEK_API_BASE"),
        temperature=0,
        max_tokens=512,
        timeout=60,
        max_retries=2,
        **kwargs,
    )


def section(title: str) -> None:
    print("\n" + "=" * 62)
    print(title)
    print("=" * 62)


class Joke(BaseModel):
    """冷笑话"""
    joke: str = Field(description="冷笑话的内容")
    punchline: str = Field(description="这个冷笑话的笑点")


PROMPT = ChatPromptTemplate.from_messages([
    ("system", "你是一个冷笑话生成器。请用 JSON 格式回答。"),
    ("human", "{query}"),
])


# ---------------------------------------------------------------------------
# 1. 默认模式（json_schema）—— 实测失败
# ---------------------------------------------------------------------------
def demo_1_default_mode() -> None:
    section("1. 默认模式 json_schema —— 实测：DeepSeek 不支持")

    llm = build_llm()
    try:
        result = (PROMPT | llm.with_structured_output(Joke)).invoke({"query": "讲个程序员冷笑话"})
        print("  成功:", result)
    except Exception as e:
        print("  ❌ 失败:", type(e).__name__)
        print("  原因:", str(e)[:150])
        print("\n  >> langchain-openai 默认优先用 json_schema 模式，")
        print("     但 DeepSeek 目前不支持这个 response_format 类型。")
        print("     所以接 DeepSeek 时【必须】显式指定 method。")


# ---------------------------------------------------------------------------
# 2. json_mode —— 实测：要求 prompt 含 "json"
# ---------------------------------------------------------------------------
def demo_2_json_mode() -> None:
    section("2. json_mode —— 实测：prompt 必须出现 json 这个词")

    llm = build_llm()

    #  prompt 里没有 "json" 字样
    print("prompt 里不含 json:")
    bad_prompt = ChatPromptTemplate.from_messages([
        ("system", "你是冷笑话生成器。"),
        ("human", "{query}"),
    ])
    try:
        r = (bad_prompt | llm.with_structured_output(Joke, method="json_mode")).invoke(
            {"query": "讲个程序员冷笑话"})
        print("  成功:", r.joke[:40])
    except Exception as e:
        print("  ❌ 失败:", str(e)[:130])

    # prompt 里加了 "json"
    print("\n【2b】prompt 里明确写了 JSON:")
    try:
        r = (PROMPT | llm.with_structured_output(Joke, method="json_mode")).invoke(
            {"query": "讲个程序员冷笑话"})
        print("  成功:", type(r).__name__, "|", r.joke[:40])
    except Exception as e:
        print("  ❌ 失败:", type(e).__name__, str(e)[:180])
        print("  >> 注意：json_mode 只是「要求输出 JSON 对象」，并不强制 schema，")
        print("     小模型仍可能漏字段或加多余字段。实测它就多输出了 type 字段。")

    print("\n  >> 这个限制是 OpenAI 系 API 的通用规则（OpenAI 也一样），")
    print("     不算 DeepSeek 独有的坑，但很容易踩到。")


# ---------------------------------------------------------------------------
# 3. function_calling —— 实测：要先关掉思考模式
# ---------------------------------------------------------------------------
def demo_3_function_calling() -> None:
    section("3. function_calling —— 实测：必须关掉思考模式才可用")

    # 3a. 不关思考 → 报错
    print("不关思考模式:")
    llm = build_llm()
    try:
        r = (PROMPT | llm.with_structured_output(Joke, method="function_calling")).invoke(
            {"query": "讲个程序员冷笑话"})
        print("  成功:", r.joke[:40])
    except Exception as e:
        print("  ❌ 失败:", str(e)[:150])
        print("  >> 关键信息：Thinking mode does not support this tool_choice")

    # 3b. 关掉思考 → 成功
    print("\n【3b】关掉思考模式（extra_body 传 thinking.disabled）:")
    llm_off = build_llm(disable_thinking=True)
    try:
        r = (PROMPT | llm_off.with_structured_output(Joke, method="function_calling")).invoke(
            {"query": "讲个程序员冷笑话"})
        print("  ✅ 成功:", type(r).__name__)
        print("  笑话:", r.joke)
        print("  笑点:", r.punchline)
    except Exception as e:
        print("  ❌ 失败:", type(e).__name__, str(e)[:180])

    print("\n  >> 这就是 DeepSeek 做结构化输出的【正确姿势】：")
    print("     ChatOpenAI(..., extra_body={'thinking': {'type': 'disabled'}})")
    print("     + with_structured_output(Schema, method='function_calling')")


# ---------------------------------------------------------------------------
# 4. 推荐写法：封装成一个可复用的函数
# ---------------------------------------------------------------------------
def demo_4_recommended() -> None:
    section("4. 推荐写法：封装成可复用的结构化输出函数")

    def structured_llm(schema, **kwargs):
        """DeepSeek 结构化输出的一行封装（把上面那些坑都藏在这里）

        **kwargs 是「收集多余的关键字参数」：
            调用 structured_llm(BugReport, temperature=0.5, max_tokens=800)
            时，temperature 和 max_tokens 会被收进 kwargs 这个字典，
            再通过下面的 **kwargs 「拆散」传给 ChatOpenAI。
        Java 里没有对应语法，可以类比成 Map<String, Object> 接收可选配置，
        再用反射把 map 展开成构造参数（或 Builder 逐个 .xxx(v)）。
        """
        llm = ChatOpenAI(
            model="deepseek-flash",
            api_key=os.getenv("DEEPSEEK_API_KEY"),
            base_url=os.getenv("DEEPSEEK_API_BASE"),
            temperature=0,
            timeout=60,
            extra_body={"thinking": {"type": "disabled"}},   # 关键：关思考
            **kwargs,        # ← 把调用方传来的额外参数原样透传给 ChatOpenAI
        )
        # with_structured_output 返回一个"新的链"，输出直接就是 schema 类型的对象
        return llm.with_structured_output(schema, method="function_calling")

    class BugReport(BaseModel):
        """线上问题的结构化提取结果"""
        service: str = Field(description="出问题的是哪个服务")
        severity: str = Field(description="严重程度：P0/P1/P2/P3")
        symptom: str = Field(description="现象，一句话描述")
        possible_causes: List[str] = Field(description="可能的原因，2-3条")
        need_restart: Optional[bool] = Field(default=None, description="是否需要重启服务")

    prompt = ChatPromptTemplate.from_messages([
        ("system", "你是 SRE 专家，从故障描述里提取结构化信息。"),
        ("human", "{desc}"),
    ])

    try:
        report = (prompt | structured_llm(BugReport)).invoke({
            "desc": "支付服务今天下午开始大量超时，接口响应从50ms涨到8秒，"
                    "怀疑是数据库连接池打满了，日志里有 connection pool exhausted"
        })
        print("  提取结果类型:", type(report).__name__)
        print("  服务      :", report.service)
        print("  等级      :", report.severity)
        print("  现象      :", report.symptom)
        print("  可能原因  :", report.possible_causes)
        print("  需重启    :", report.need_restart)
        print("\n  >> 嵌套/列表/可选字段全都支持，而且由 API 层面保证格式。")
        print("  >> 生产环境建议：外层再包一层重试，应对偶发的解析失败。")
    except Exception as e:
        print("  失败:", type(e).__name__, str(e)[:200])


# ---------------------------------------------------------------------------
# 5. 三条路线的选型建议
# ---------------------------------------------------------------------------
def demo_5_choose() -> None:
    section("5. 三条路线怎么选")

    rows = [
        ("StrOutputParser", "只要纯文本", "最简单，做打字机必备"),
        ("JsonOutputParser", "要 dict，字段简单", "灵活，不校验字段"),
        ("PydanticOutputParser", "要对象 + 字段校验", "IDE 补全好，缺字段会报错"),
        ("with_structured_output", "字段多/结构复杂/要求稳", "API 层强制格式，最可靠"),
    ]
    print(f"  {'方案':<24}{'适用场景':<22}{'特点'}")
    print("  " + "-" * 78)
    for a, b, c in rows:
        print(f"  {a:<24}{b:<22}{c}")

    print("\n  决策建议：")
    print("   · 只是要一段文字            → StrOutputParser")
    print("   · 1-3 个简单字段            → JsonOutputParser / PydanticOutputParser")
    print("   · 嵌套结构、列表、可选字段  → with_structured_output")
    print("   · 要接数据库/下游接口       → with_structured_output（格式有保证）")

    print("\n  另外两个实用参数：")
    print("   · include_raw=True   同时返回原始 AIMessage，方便排查问题")
    print("   · 传 TypedDict 或 JSON Schema 也行，不一定要 pydantic 类")


def main() -> None:
    print("3. with_structured_output 结构化输出（DeepSeek + 最新 API）")
    demo_1_default_mode()
    demo_2_json_mode()
    demo_3_function_calling()
    demo_4_recommended()
    demo_5_choose()
    print("\n" + "=" * 62)
    print("全部示例执行完毕。")


if __name__ == "__main__":
    main()
