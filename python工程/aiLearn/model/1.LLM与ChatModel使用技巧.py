#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
1. LLM 与 ChatModel 使用技巧（最新 API 版）
=============================================

【这个文件和旧版最大的区别】

    新版（LCEL 管道写法）：
        chain = prompt | llm | StrOutputParser()
        result = chain.invoke({"query": "..."})
        ↑ 用 | 把「模板 → 模型 → 解析器」串成一条链路，一步调用

    为什么要用管道？
        · 少写一次中间变量，意图更清晰
        · 链路本身是 Runnable 对象，自动获得 batch / stream / 异步等能力
          （见同目录的 2.Model批处理.py 和 3.Model流式输出.py）
        · 可以在中间任意插拔组件（解析器、记忆、工具）

【关于模型】
    本文件统一用 DeepSeek。DeepSeek 是 OpenAI 兼容协议，
    所以用 ChatOpenAI 换掉 base_url 就能接入，不需要专门的包。

    ⚠️ 实测（2026-10-26）：DeepSeek 当前可用模型只有两个
        - deepseek-flash      （快、便宜，日常首选）
        - deepseek-v4-pro     （强、贵，复杂任务用）
       网上教程里常见的 deepseek-chat 已经不在 /models 列表里了，
       传 deepseek-chat 会被服务端静默映射到 deepseek-flash。
       建议显式写 deepseek-flash，别用那个名字。

【运行】
    ./yzy/Scripts/python.exe aiLearn/model/new/1.LLM与ChatModel使用技巧.py
"""

import os
from datetime import datetime
from pathlib import Path

import dotenv
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI

# 加载项目根目录的 .env（用绝对路径，避免从不同目录运行时找不到）
# 注意：load_dotenv() 不带参数时靠调用栈猜位置，在交互式 stdin 里会失败；
# 显式传路径是最稳的写法。
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


def build_llm(model: str = "deepseek-flash", temperature: float = 0.0) -> ChatOpenAI:
    """构造一个指向 DeepSeek 的聊天模型。

    参数说明（这几个是日常最常调的）：
        model         模型名，实测可用 deepseek-flash / deepseek-v4-pro
        temperature   温度，0=稳定确定（适合提取/分类），0.7~1=更有创意
        max_tokens    单次回复的最大 token 上限，防止输出失控
        timeout       超时秒数，生产必填，否则可能一直挂住
        max_retries   失败自动重试次数，网络抖动时很有用
    """
    return ChatOpenAI(
        model=model,
        api_key=os.getenv("DEEPSEEK_API_KEY"),
        base_url=os.getenv("DEEPSEEK_API_BASE"),   # https://api.deepseek.com
        temperature=temperature,
        max_tokens=1024,
        timeout=60,
        max_retries=2,
    )


def section(title: str) -> None:
    print("\n" + "=" * 62)
    print(title)
    print("=" * 62)


# ---------------------------------------------------------------------------
# 1. 新旧写法对比（本文件最重要的一节）
# ---------------------------------------------------------------------------
def demo_1_old_vs_new() -> None:
    section("1. 1.4.7 新写法")

    prompt = ChatPromptTemplate.from_messages([
        ("system", "你是DeepSeek开发的聊天机器人，回答要简洁。现在的时间是{now}"),
        ("human", "{query}"),
    ]).partial(now=datetime.now())   # partial 把"当前时间"固定住，调用时就不用传了

    llm = build_llm()
    query = "请讲一个关于程序员的冷笑话"

    # ---- 新写法：LCEL 管道一步到位 ----
    print("\n【新写法】prompt | llm | parser 串成链路")
    chain = prompt | llm | StrOutputParser()
    print("  链路类型:", type(chain).__name__)
    new_result = chain.invoke({"query": query})     # 一步：直接传变量字典
    print("  结果:", new_result[:60], "...")

    print("\n>> 链路是 Runnable 对象，")
    print("   后面 2、3 两个文件的 batch / stream 都是白送的能力。")


# ---------------------------------------------------------------------------
# 2. 返回值 AIMessage 详解
# ---------------------------------------------------------------------------
def demo_2_ai_message() -> None:
    section("2. 返回值 AIMessage 里都有什么")

    llm = build_llm()
    msg: AIMessage = llm.invoke("用一句话解释什么是幂等性")

    print("type（角色）        :", msg.type, " <-- 固定是 'ai'")
    print("content（正文）     :", msg.content)
    print("id                  :", msg.id, " <-- 本次调用的唯一标识，用于追踪")
    print("\nresponse_metadata（服务端返回的元信息）:")
    for k in ("model_name", "finish_reason"):
        print(f"   {k:<16}: {msg.response_metadata.get(k)}")

    # usage_metadata 是 token 消耗，做成本统计必须看它
    print("\nusage_metadata（token 消耗，计费依据）:")
    if msg.usage_metadata:
        for k, v in msg.usage_metadata.items():
            if not isinstance(v, dict):
                print(f"   {k:<16}: {v}")

    print("\n>> 要点：")
    print("   · 不带解析器时拿到的是 AIMessage，要取文本用 .content")
    print("   · 加了 StrOutputParser 就直接拿到字符串，省掉 .content")
    print("   · usage_metadata 里 input/output tokens 是算钱和限流的依据")


# ---------------------------------------------------------------------------
# 3. temperature 参数的效果对比
# ---------------------------------------------------------------------------
def demo_3_temperature() -> None:
    section("3. temperature 参数：稳定性的开关")

    question = "用一句话描述春天"
    print("temperature=0（偏稳定，适合抽取/分类/格式化输出）:")
    for i in range(2):
        r = build_llm(temperature=0).invoke(question)
        print(f"   第{i+1}次: {r.content[:40]}")

    print("\ntemperature=1（更有随机性，适合创意写作）:")
    for i in range(2):
        r = build_llm(temperature=1).invoke(question)
        print(f"   第{i+1}次: {r.content[:40]}")

    print("\n>> 经验值：0=确定性任务，0.3~0.7=日常对话，1+=创意生成")
    print(">> ⚠️ 实测提醒：temperature=0 也【不保证】逐字一致。")
    print("   刚才两次输出就不完全相同——模型服务端仍有采样不确定性。")
    print("   所以：需要严格稳定输出时，别只靠 temperature=0，")
    print("   要靠 JsonOutputParser / with_structured_output() 在格式层面兜底。")


# ---------------------------------------------------------------------------
# 4. 多轮对话：直接把消息列表喂给模型
# ---------------------------------------------------------------------------
def demo_4_multi_turn() -> None:
    section("4. 多轮对话（不套模板，直接给消息列表）")

    llm = build_llm()
    # 模型没有"记忆"，所谓记忆就是把历史消息一起发过去
    messages = [
        SystemMessage("你是一名资深 DBA，回答不超过50字。"),
        HumanMessage("我叫小明"),
        AIMessage("你好小明，有什么数据库问题需要帮忙？"),
        HumanMessage("我叫什么名字？"),
    ]
    r = llm.invoke(messages)
    print("问：我叫什么名字？（前面几轮说过我叫小明）")
    print("答:", r.content)
    print("\n>> 这就是为什么 messages 是记忆的载体——模型本身是无状态的。")


# ---------------------------------------------------------------------------
# 5. 输出解析器：让模型按格式输出
# ---------------------------------------------------------------------------
def demo_5_output_parser() -> None:
    section("5. 输出解析器 StrOutputParser / JsonOutputParser")

    llm = build_llm()

    # StrOutputParser：把 AIMessage 转成纯字符串，最常用
    print("StrOutputParser —— 直接拿到 str:")
    chain = ChatPromptTemplate.from_template("{q}") | llm | StrOutputParser()
    r = chain.invoke({"q": "用10个字介绍Redis"})
    print("  类型:", type(r).__name__, "| 内容:", r)

    # JsonOutputParser：要求模型输出 JSON，并自动解析成 dict
    print("\nJsonOutputParser —— 自动解析成 dict:")
    from langchain_core.output_parsers import JsonOutputParser

    json_chain = (
        ChatPromptTemplate.from_messages([
            ("system", "你是一个结构化信息抽取器。只输出 JSON，不要任何解释。"),
            ("human", "从下面这句话里抽取城市和天气，字段：city, weather\n\n{sentence}"),
        ])
        | llm
        | JsonOutputParser()
    )
    try:
        data = json_chain.invoke({"sentence": "杭州今天晴，25度，适合出门"})
        print("  类型:", type(data).__name__, "| 内容:", data)
        print("  取字段:", data.get("city"), "/", data.get("weather"))
    except Exception as e:
        # 小模型偶尔会输出不合规的 JSON，这里兜个底
        print("  解析失败（模型没返回合法JSON）:", type(e).__name__, e)

    print("\n>> 生产建议：关键场景用 JsonOutputParser + 重试，")
    print("   或者用 with_structured_output() 走模型原生的结构化输出能力。")


def main() -> None:
    print("1. LLM 与 ChatModel 使用技巧（DeepSeek + 最新 API）")
    print("模型:", os.getenv("DEEPSEEK_API_BASE"))
    demo_1_old_vs_new()
    demo_2_ai_message()
    demo_3_temperature()
    demo_4_multi_turn()
    demo_5_output_parser()
    print("\n" + "=" * 62)
    print("全部示例执行完毕。")


if __name__ == "__main__":
    main()
