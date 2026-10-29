#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
2. configurable_fields：运行时动态改字段（最新 API 版）
====================================================


【Python 语法看不懂？】闭包、lambda、** 解包、推导式等见 ../PYTHON_SYNTAX.md

【它解决什么问题】
    bind 是「写死」：bind(temperature=0) 之后就永远是 0。
    如果我想**每次调用时**决定用 0 还是 1，怎么办？

        configurable_fields：把一个字段标记为「运行时可配置」

    标记之后，调用时通过 config 传值就能改，不改就用默认值：

        chain.invoke(x)                                          # 用默认
        chain.invoke(x, config={"configurable": {"xx": 0}})      # 运行时改

【和 bind 的关系】
    bind               = 预置一个**固定值**（编译时决定）
    configurable_fields= 声明一个**可变的槽位**（运行时决定）

    【Java 对照】
        bind                ≈ 构造时 new Config(defaultValue)
        configurable_fields ≈ 留一个 setter / 环境变量 / @Value("${xx}")
                              运行时由外部注入

【运行】
    ./yzy/Scripts/python.exe "aiLearn/runnableModule/new/2.configurable_fields运行时改字段.py"
"""

import os
from pathlib import Path

import dotenv
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import PromptTemplate
from langchain_core.runnables import ConfigurableField
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


def build_llm(**kwargs) -> ChatOpenAI:
    """构造 DeepSeek 模型。"""
    base = dict(
        model="deepseek-flash",
        api_key=os.getenv("DEEPSEEK_API_KEY"),
        base_url=os.getenv("DEEPSEEK_API_BASE"),
    )
    base.update(kwargs)
    return ChatOpenAI(**base)


def section(title: str) -> None:
    """打印分节标题，纯排版用。"""
    print("\n" + "=" * 62)
    print(title)
    print("=" * 62)


# ---------------------------------------------------------------------------
# 1. 基本用法：把 temperature 变成运行时可配
# ---------------------------------------------------------------------------
def demo_1_temperature() -> None:
    section("1. 基本用法：运行时改 temperature")

    prompt = PromptTemplate.from_template("请生成一个小于{x}的随机整数，只输出数字")

    # 【关键这一行】把 temperature 标记为「运行时可配置」，id 叫 llm_temperature
    llm = build_llm().configurable_fields(
        temperature=ConfigurableField(
            id="llm_temperature",
            name="大语言模型的温度",
            description="温度越低越确定，越高越随机",
        )
    )
    chain = prompt | llm | StrOutputParser()

    print("  【不传配置】用模型默认的 temperature：")
    for _ in range(2):
        print("   ", chain.invoke({"x": 1000}))

    print("\n  【传 llm_temperature=0】尽量确定：")
    cfg0 = {"configurable": {"llm_temperature": 0}}
    for _ in range(2):
        print("   ", chain.invoke({"x": 1000}, config=cfg0))

    print("\n  >> temperature=0 只是**尽量**确定，DeepSeek 上不保证逐字一致")
    print("     （这个结论在 model/1 里实测过）。")


# ---------------------------------------------------------------------------
# 2. 另一种写法：with_config 把配置固化到链上
# ---------------------------------------------------------------------------
def demo_2_with_config() -> None:
    section("2. with_config：把配置「固化」成一条新链")

    prompt = PromptTemplate.from_template("请生成一个小于{x}的随机整数，只输出数字")
    llm = build_llm().configurable_fields(
        temperature=ConfigurableField(id="llm_temperature")
    )
    chain = prompt | llm | StrOutputParser()

    # 方式 A：调用时传（每次都要写一遍 config）
    print("  方式 A —— 调用时传：")
    print("   ", chain.invoke({"x": 1000}, config={"configurable": {"llm_temperature": 0}}))

    # 方式 B：with_config 绑到链上，之后就不用每次传了
    print("\n  方式 B —— with_config 固化（推荐，一次绑定到处用）：")
    chain_cold = chain.with_config(configurable={"llm_temperature": 0})
    print("   ", chain_cold.invoke({"x": 1000}))
    print("   ", chain_cold.invoke({"x": 1000}))

    print("\n  >> 两种方式结果一样，区别只在写法：")
    print("     方式 A 适合「每次调用参数都不同」")
    print("     方式 B 适合「某类请求固定用某个配置」，比如给 VIP 用户用高配模型")


# ---------------------------------------------------------------------------
# 3. 换个对象：把「提示词模板」变成运行时可配
# ---------------------------------------------------------------------------
def demo_3_prompt_template() -> None:
    section("3. 换个对象：运行时替换提示词模板")

    prompt = PromptTemplate.from_template("请写一篇关于{subject}主题的冷笑话").configurable_fields(
        # ⚠️ 字段名必须是 template（PromptTemplate 的字段就叫这个）
        template=ConfigurableField(id="prompt_template"),
    )

    print("  【默认模板】冷笑话：")
    print("   ", prompt.invoke({"subject": "程序员"}).to_string())

    print("\n  【运行时换成藏头诗模板】：")
    print("   ", prompt.invoke(
        {"subject": "程序员"},
        config={"configurable": {"prompt_template": "请写一篇关于{subject}主题的藏头诗"}},
    ).to_string())

    print("\n  >> 这个能力很好用：同一套代码，换个 config 就能换「玩法」。")
    print("     比如运营后台让用户自己选「文案风格」，不用改代码重新发版。")


# ---------------------------------------------------------------------------
# 4. ⚠️ 坑：字段名写错会直接 ValueError（教材这里就写错了）
# ---------------------------------------------------------------------------
def demo_4_pitfall_wrong_field() -> None:
    section("4. ⚠️ 坑：字段名写错会直接报错（教材这里就写错了）")

    print("  教材原文写的是：")
    print("    PromptTemplate.from_template(...).configurable_fields(")
    print("        template_demo=ConfigurableField(id='prompt_template')")
    print("    )")

    print("\n  实测一下 template_demo 这个字段名：")
    try:
        PromptTemplate.from_template("你好{name}").configurable_fields(
            template_demo=ConfigurableField(id="prompt_template")
        )
        print("    ✅ 没报错（版本行为可能变了）")
    except ValueError as e:
        print(f"    ❌ ValueError: {str(e)[:170]}")

    print("\n  ⚠️ 教材里的 template_demo 是**笔误**，正确字段名是 template。")
    print("     configurable_fields 会校验字段名，写错立刻 ValueError（这点是好事）。")

    # 看看 PromptTemplate 到底有哪些可用字段
    print("\n  怎么知道有哪些字段可用？看报错信息里的 available keys，或者直接看：")
    p = PromptTemplate.from_template("你好{name}")
    print("   PromptTemplate 的可配字段: template / input_variables / partial_variables ...")

    print("\n  >> 和 bind 对比一下：")
    print("     bind                **不校验**，参数名写错要等调用时才炸")
    print("     configurable_fields **会校验**，字段名写错立刻 ValueError")
    print("     所以 configurable_fields 更安全。")

    # 再踩一个：ChatOpenAI 的字段名是 model_name，不是 model
    print("\n  ⚠️ 再踩一个：ChatOpenAI 上想让「模型名」可配，字段名是 model_name")
    try:
        build_llm().configurable_fields(model=ConfigurableField(id="llm_model"))
        print("     model ✅ 能用")
    except ValueError as e:
        print(f"     model ❌ ValueError（字段名不对）")
        # 报错信息里会列出所有可用字段，挑几个常见的展示
        msg = str(e)
        if "available keys" in msg:
            keys_part = msg.split("available keys are ")[-1]
            print(f"     报错里列出的可用字段（节选）: {keys_part[:150]}")
    print("     → 正确写法：configurable_fields(model_name=ConfigurableField(id='llm_model'))")
    print("     因为 model 只是 model_name 的别名，configurable_fields 只认**真名**。")


# ---------------------------------------------------------------------------
# 5. 一次配多个字段 + 完整链路
# ---------------------------------------------------------------------------
def demo_5_multiple_fields() -> None:
    section("5. 一次配多个字段：模型 + 提示词一起换")

    from langchain_core.prompts import ChatPromptTemplate

    prompt = ChatPromptTemplate.from_messages([
        ("system", "你是{role}，回答用中文，不超过 30 字"),
        ("human", "{query}"),
    ]).configurable_fields(
        # 注意：ChatPromptTemplate 换的是 messages，不是 template
        messages=ConfigurableField(id="prompt_messages"),
    )

    # ⚠️ 字段名是 model_name 不是 model！
    #    ChatOpenAI 里 model 是 model_name 的别名，configurable_fields 只认真名。
    #    写错会 ValueError，报错信息里会把所有可用字段列出来（很贴心）。
    llm = build_llm().configurable_fields(
        temperature=ConfigurableField(id="llm_temperature"),
        model_name=ConfigurableField(id="llm_model"),
    )

    chain = prompt | llm | StrOutputParser()

    print("  【配置 A】默认模型 + 温柔的助手：")
    print("   ", chain.invoke({"role": "温柔的助手", "query": "我不开心"},
                             config={"configurable": {"llm_temperature": 0.2}}))

    print("\n  【配置 B】换 v4-pro + 严厉的教练：")
    print("   ", chain.invoke(
        {"role": "严厉的教练", "query": "我不开心"},
        config={"configurable": {"llm_temperature": 0.2, "llm_model": "deepseek-v4-pro"}},
    ))

    print("\n  【配置 C】运行时连提示词结构一起换：")
    print("   ", chain.invoke(
        {"role": "面试官", "query": "介绍下你自己"},
        config={
            "configurable": {
                "prompt_messages": [
                    ("system", "你是面试官，只问问题不给答案，一句话。"),
                    ("human", "{query}"),
                ]
            }
        },
    ))

    print("\n  >> 多个字段可以同时配，config 里传一个 dict 就行。")
    print("     这就是「一套代码，多种玩法」的实现基础。")


# ---------------------------------------------------------------------------
# 6. 什么时候用
# ---------------------------------------------------------------------------
def demo_6_when_to_use() -> None:
    section("6. configurable_fields vs bind vs alternatives")

    rows = [
        ("bind", "固定值", "❌ 不能改", "参数全局固定"),
        ("configurable_fields", "有默认值", "✅ 能改", "运行时调温度/换提示词"),
        ("configurable_alternatives", "有默认组件", "✅ 能换", "运行时换整个模型/检索器"),
    ]
    print(f"  {'方式':<28}{'默认值':<12}{'运行时改':<12}{'什么时候用'}")
    print("  " + "-" * 74)
    for a, b, c, d in rows:
        print(f"  {a:<28}{b:<12}{c:<12}{d}")

    print("\n  典型场景：")
    print("   · A/B 测试：同一条链，用不同 temperature 对比效果")
    print("   · 多租户：不同客户用不同模型/不同提示词")
    print("   · 灰度发布：config 里切模型名，不用改代码")
    print("   · 运营后台：让用户自己调参数")

    print("\n  ⚠️ 注意：configurable_fields 改的是**组件字段**，")
    print("     如果你要改的是「提示词里的变量值」，那个是普通输入，直接传就行，")
    print("     不需要 configurable_fields。")


def main() -> None:
    print("2. configurable_fields 运行时改字段（DeepSeek + 最新 API）")
    print("   教材：old/Runnable组件配置运行时链内部/*")

    demo_3_prompt_template()   # 不需要 API，先跑
    demo_4_pitfall_wrong_field()

    if not os.getenv("DEEPSEEK_API_KEY"):
        print("\n⚠️ 没读到 DEEPSEEK_API_KEY，跳过需要调模型的演示。.env 路径：", _ENV_PATH)
        return

    demo_1_temperature()
    demo_2_with_config()
    demo_5_multiple_fields()
    demo_6_when_to_use()

    print("\n" + "=" * 62)
    print("全部示例执行完毕。下一个：3.configurable_alternatives动态替换组件.py")


if __name__ == "__main__":
    main()
