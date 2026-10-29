#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
1. bind：给 Runnable 预置调用参数（最新 API 版）
==============================================


【Python 语法看不懂？】闭包、lambda、** 解包、推导式等见 ../PYTHON_SYNTAX.md

【bind 是什么】
    一句话：**给一个 Runnable 预先绑定好一部分调用参数，返回一个新的 Runnable。**

    函数式编程里叫「偏函数 / partial application」：
        f(a, b, c)  绑定 b=1, c=2  →  得到 f'(a)

    【Java 对照】最接近的是 Builder 预置 + 方法引用：
        // 原来：service.query(a, b, c)
        // 预置 b、c 之后：
        Function<String, Result> f = a -> service.query(a, "摄氏度", "慕小课");
        等价于 Python 的：RunnableLambda(query).bind(unit="摄氏度", name="慕小课")

    注意 bind **不改原对象**，返回一个新的（和 LCEL 里所有 with_xxx 一样）。

【两个主要用途】
    ① 给模型预置调用参数（temperature / max_tokens / stop ...）
    ② 【更常用】给 RunnableLambda 补参数 —— 解决「管道只传一个值，但函数要多个参数」

【运行】
    ./yzy/Scripts/python.exe "aiLearn/runnableModule/new/1.bind绑定默认参数.py"
"""

import os
import random
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


def build_llm(**kwargs) -> ChatOpenAI:
    """构造 DeepSeek 模型，可传入额外参数覆盖默认值。

    **kwargs 是「收集多余关键字参数成字典」，见 ../PYTHON_SYNTAX.md 第 3 节。
    """
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
# 1. 用途一：给模型预置调用参数
# ---------------------------------------------------------------------------
def demo_1_bind_model_params() -> None:
    section("1. 用途一：给模型预置调用参数")

    prompt = ChatPromptTemplate.from_template("请详细介绍{topic}的特点，至少写 100 字")

    # ① 不 bind
    normal = prompt | build_llm() | StrOutputParser()
    r0 = normal.invoke({"topic": "Redis"})
    print(f"  【不 bind】        输出 {len(r0)} 字")
    print("   ", r0[:70])

    # ② bind temperature=0：让输出更确定
    r1 = (prompt | build_llm().bind(temperature=0) | StrOutputParser()).invoke({"topic": "Redis"})
    print(f"\n  【bind(temperature=0)】输出 {len(r1)} 字")
    print("   ", r1[:70])

    # ③ bind max_tokens：⚠️ 在 DeepSeek 上实测不生效，见下面说明
    r2 = (prompt | build_llm().bind(max_tokens=20) | StrOutputParser()).invoke({"topic": "Redis"})
    print(f"\n  【bind(max_tokens=20)】输出 {len(r2)} 字")
    print("   ", r2[:70])

    print("\n  ⚠️【DeepSeek 实测坑】max_tokens **不限制输出长度**！")
    print("     同一条 prompt 分别用 None / 60 / 20 各跑一次，")
    print("     输出长度和设置值**毫无相关性**（实测几百到一千字不等）。")
    print("     原因：DeepSeek 的思考(reasoning) token 是单独计的，")
    print("     且厂商侧似乎没有对正文做硬截断。")
    print("     → 想控制长度，只能靠**提示词里写「不超过 N 字」**，别指望 max_tokens。")

    print("\n  常用可 bind 的调用参数：")
    print("    max_tokens     限制输出长度 ⚠️ 实测 DeepSeek 上不生效")
    print("    temperature    控制随机性")
    print("    stop           遇到指定字符串就停")
    print("    tools / tool_choice   绑定工具（做 tool calling 时的标准做法）")
    print("    extra_body     传给厂商的私有参数")
    print("          比如 DeepSeek 关思考：extra_body={'thinking': {'type': 'disabled'}}")

    print("\n  >> bind 的是「调用时的参数」，不是「构造时的字段」。")
    print("     这也是它和 ChatOpenAI(temperature=0) 的区别：")
    print("     · 构造时传 = 写死在对象上")
    print("     · bind     = 包一层，原对象还能复用")


# ---------------------------------------------------------------------------
# 2. 用途二（核心）：给 RunnableLambda 补参数
# ---------------------------------------------------------------------------
def demo_2_bind_lambda_multiple_args() -> None:
    section("2. 用途二【核心】：让多参函数能进管道")

    def get_weather(location: str, unit: str, name: str) -> str:
        """根据位置 + 温度单位 + 用户名返回天气信息（模拟）。"""
        return f"{name}你好，{location}今天的天气是 {random.randint(24, 40)}{unit}"

    # ---------------------------------------------------------------
    # 【问题】管道里上游只会传**一个值**给下游。
    #   直接 RunnableLambda(get_weather).invoke("广州")
    #   → TypeError: 缺 unit 和 name 两个参数
    # ---------------------------------------------------------------
    print("  【不 bind】直接放进管道会怎样：")
    try:
        RunnableLambda(get_weather).invoke("广州")
        print("    没报错（版本行为可能变了）")
    except TypeError as e:
        print(f"    TypeError: {str(e)[:90]}")

    # ---------------------------------------------------------------
    # 【解法】用 bind 把多余的参数先喂进去，只留一个「位置」参数给上游传
    # ---------------------------------------------------------------
    weather_runnable = RunnableLambda(get_weather).bind(unit="摄氏度", name="慕小课")

    print("\n  【bind 之后】")
    print("   ", weather_runnable.invoke("广州"))
    print("   ", weather_runnable.invoke("深圳"))

    print("\n  原理（等价于手写一层闭包）：")
    print("    RunnableLambda(get_weather).bind(unit='摄氏度', name='慕小课')")
    print("    ≈ RunnableLambda(lambda loc: get_weather(loc, '摄氏度', '慕小课'))")
    print("\n  >> 这就是教材说的「bind 解决 RunnableLambda 函数多参场景」。")
    print("     真实场景：函数需要数据库连接、用户上下文、配置开关这些")
    print("     「每次调用都一样」的参数，就非常适合用 bind 先喂进去。")


# ---------------------------------------------------------------------------
# 3. 完整链路：bind 过后的 Runnable 可以正常进管道
# ---------------------------------------------------------------------------
def demo_3_bind_in_pipeline() -> None:
    section("3. bind 之后照样能进 LCEL 管道")

    def search(query: str, top_k: int, source: str) -> str:
        """模拟检索：返回 top_k 条来自某个数据源的结果。"""
        return "；".join(f"[{source}]{query}相关结果{i + 1}" for i in range(top_k))

    # 【这是个闭包工厂，看不懂先看 ../PYTHON_SYNTAX.md 第 1 节】
    # 外层接收 source，内层造出「只差 query」的 Runnable
    def make_retriever(source: str, top_k: int):
        return RunnableLambda(search).bind(top_k=top_k, source=source)

    prompt = ChatPromptTemplate.from_template(
        "根据下面的资料回答问题，不超过 30 字。\n资料：{docs}\n问题：{query}"
    )

    chain = (
        {
            "docs": make_retriever("产品文档库", 2),
            "query": lambda x: x["query"],
        }
        | prompt
        | build_llm()
        | StrOutputParser()
    )

    result = chain.invoke({"query": "怎么重置密码"})
    print("  ", result)

    print("\n  >> bind + 闭包工厂 是 LangChain 里非常常见的组合：")
    print("     闭包工厂负责「造出不同配置的组件」，bind 负责「把配置喂进去」。")


# ---------------------------------------------------------------------------
# 4. ⚠️ 坑一：bind 不校验参数，写错要等调用时才炸
# ---------------------------------------------------------------------------
def demo_4_pitfall_no_validation() -> None:
    section("4. ⚠️ 坑一：bind 不做校验，参数名写错调用时才炸")

    prompt = ChatPromptTemplate.from_template("{query}")

    # bind 一个 DeepSeek 上不存在的模型
    print("  bind(model='gpt-4o') 之后调用（DeepSeek 没有这个模型）：\n")
    try:
        chain = prompt | build_llm().bind(model="gpt-4o") | StrOutputParser()
        print("   结果:", chain.invoke({"query": "你好"})[:60])
    except Exception as e:
        print(f"   异常类型: {type(e).__name__}")
        # 错误信息里 DeepSeek 会把支持的模型列出来
        print(f"   异常信息: {str(e)[:150]}")

    print("\n  >> bind 的时候**完全不校验**——它只是把参数存下来，")
    print("     真正发出请求时厂商才会报错。")
    print("     所以 bind 的参数名一定要对着文档写，IDE 补全不一定可靠。")


# ---------------------------------------------------------------------------
# 5. ⚠️ 坑二：bind 会「覆盖」而不是「补充」
# ---------------------------------------------------------------------------
def demo_5_pitfall_override() -> None:
    section("5. ⚠️ 坑二：bind 是覆盖，不是合并")

    def show_params(x: str, temperature: float) -> str:
        return f"收到的 temperature = {temperature}"

    # 先 bind 一次
    r1 = RunnableLambda(show_params).bind(temperature=0.9)
    print("  第一次 bind(temperature=0.9):", r1.invoke("x"))

    # 再 bind 一次不同的值
    r2 = r1.bind(temperature=0.1)
    print("  再 bind(temperature=0.1)   :", r2.invoke("x"))

    print("\n  >> 后 bind 的**覆盖**先 bind 的，不是追加。")
    print("     想合并就得自己把参数攒好再一次性 bind。")

    print("\n  另外：bind 对 RunnableParallel 这种「字典参数」要小心——")
    print("     如果上游传的字典里也有同名 key，行为取决于实现，")
    print("     建议 bind 的 key 和上游字段**不要重名**。")


# ---------------------------------------------------------------------------
# 6. bind vs 其他方案
# ---------------------------------------------------------------------------
def demo_6_when_to_use() -> None:
    section("6. bind 什么时候用，什么时候别用")

    rows = [
        ("构造时传参", "ChatOpenAI(temperature=0)", "这个配置全局固定，不会变"),
        ("bind", "llm.bind(temperature=0)", "同一条链里不同分支要不同配置"),
        ("partial", "prompt.partial(...)", "预填的是**提示词变量**，不是调用参数"),
        ("configurable_fields", "见第 2 个文件", "要**运行时**动态改（不是写死）"),
        ("configurable_alternatives", "见第 3 个文件", "要**运行时**换掉整个组件"),
    ]
    print(f"  {'方式':<26}{'写法':<34}{'什么时候用'}")
    print("  " + "-" * 88)
    for a, b, c in rows:
        print(f"  {a:<26}{b:<34}{c}")

    print("\n  ⚠️ 最容易混的是 bind 和 partial：")
    print("     bind    改的是「调用模型时发的参数」 → temperature / max_tokens / stop")
    print("     partial 改的是「提示词里的占位符」   → prompt 里的 {name} 之类")
    print("     两者作用的对象完全不同。")


def main() -> None:
    print("1. bind 绑定默认参数（DeepSeek + 最新 API）")
    print("   教材：old/Runnable组件动态添加默认调用参数/*")

    if not os.getenv("DEEPSEEK_API_KEY"):
        print("\n❌ 没读到 DEEPSEEK_API_KEY，请检查 .env：", _ENV_PATH)
        return

    demo_1_bind_model_params()
    demo_2_bind_lambda_multiple_args()
    demo_3_bind_in_pipeline()
    demo_4_pitfall_no_validation()
    demo_5_pitfall_override()
    demo_6_when_to_use()

    print("\n" + "=" * 62)
    print("全部示例执行完毕。下一个：2.configurable_fields运行时改字段.py")


if __name__ == "__main__":
    main()
