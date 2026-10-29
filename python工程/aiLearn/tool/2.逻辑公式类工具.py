#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
2. 逻辑公式类工具（DeepSeek + 最新 API）
======================================
【Python 语法看不懂？】闭包、lambda、** 解包、推导式等见 ../PYTHON_SYNTAX.md

【什么是「逻辑公式类」工具】
    纯本地计算、无副作用、不联网、不依赖外部状态的工具：
        · 数学计算（四则运算、贷款月供、复利）
        · 单位换算（温度、汇率、长度）
        · 日期计算（相差天数、算年龄）
        · 字符串/正则处理
        · 业务规则判断（折扣计算、运费计算、资格校验）

    【Java 对照】就是个纯静态方法 / 工具类：
        public final class CalcUtils {
            public static double monthlyPayment(...) { ... }   // 无 IO、无状态
        }

【这类工具为什么最值得优先做】
    LLM 最不擅长的恰恰是**精确计算**：
        · 算数容易算错（尤其多位数、小数）
        · 日期推算经常错
        · 业务规则（阶梯费率）几乎必错
    把这些交给代码，准确率从「大概对」变成「必然对」。

    ⚠️ 反过来说：**不要让模型自己算**。
       用户问「贷款 100 万 30 年 5% 月供多少」，
       正确做法是让模型调工具算，而不是让它心算。

【本文件会实测】
    模型到底会不会乖乖调工具（而不是自己心算）

【运行】
    ./yzy/Scripts/python.exe "aiLearn/tool/2.逻辑公式类工具.py"
"""

import os
import re
from datetime import date, datetime
from pathlib import Path

import dotenv
from langchain_core.messages import HumanMessage, ToolMessage
from langchain_core.tools import tool
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
# 工具定义：一批纯计算工具
# ---------------------------------------------------------------------------
@tool
def calc(expression: str) -> float:
    """计算数学表达式的值。

    当用户需要做加减乘除、幂运算等**精确计算**时使用。
    支持 + - * / ** 和括号，例如：(1000 * 1.05) ** 3。
    输入是表达式字符串，不要包含中文和等号。
    """
    # ⚠️ 安全提醒：生产环境**绝对不能**直接 eval 用户输入。
    #   这里为了演示简洁用了 eval，真实项目要用 ast 解析或专门的表达式库
    #  （如 simpleeval），并且要限制字符集、限制长度、设超时。
    allowed = set("0123456789+-*/(). **")
    if not set(expression) <= allowed:
        return "表达式含非法字符"
    try:
        return round(eval(expression, {"__builtins__": {}}, {}), 6)  # noqa: S307
    except Exception as e:
        return f"计算失败：{e}"


@tool
def loan_monthly_payment(principal: float, annual_rate: float, years: int) -> float:
    """计算等额本息贷款的月供。

    当用户询问房贷、车贷、贷款的月供/每月还款额时使用。
    principal 是贷款总额（元），annual_rate 是年利率（百分数，如 5 表示 5%）。
    """
    monthly_rate = annual_rate / 100 / 12
    months = years * 12
    if monthly_rate == 0:
        return round(principal / months, 2)
    payment = principal * monthly_rate * (1 + monthly_rate) ** months / (
        (1 + monthly_rate) ** months - 1
    )
    return round(payment, 2)


@tool
def days_between(start_date: str, end_date: str) -> int:
    """计算两个日期之间相差的天数。

    当用户问「还有多少天」「距离某天多久」「两个日期差多少天」时使用。
    日期格式必须是 YYYY-MM-DD。
    """
    try:
        d1 = datetime.strptime(start_date, "%Y-%m-%d").date()
        d2 = datetime.strptime(end_date, "%Y-%m-%d").date()
    except ValueError:
        return -1
    return abs((d2 - d1).days)


@tool
def convert_temperature(value: float, from_unit: str, to_unit: str) -> float:
    """温度单位换算。

    支持摄氏度、华氏度、开尔文之间的互相转换。
    from_unit / to_unit 取值：C（摄氏）、F（华氏）、K（开尔文）。
    """
    def to_celsius(v: float, u: str) -> float:
        if u == "C":
            return v
        if u == "F":
            return (v - 32) * 5 / 9
        if u == "K":
            return v - 273.15
        raise ValueError(f"不支持的单位: {u}")

    c = to_celsius(value, from_unit)
    if to_unit == "C":
        return round(c, 2)
    if to_unit == "F":
        return round(c * 9 / 5 + 32, 2)
    if to_unit == "K":
        return round(c + 273.15, 2)
    raise ValueError(f"不支持的单位: {to_unit}")


@tool
def shipping_fee(weight_kg: float, distance_km: float, is_remote: bool = False) -> float:
    """计算运费（阶梯计价规则）。

    规则：首重 1kg 内 10 元；超出部分每 kg 加 5 元；
    距离超过 1000km 每 km 加 0.01 元；偏远地区加收 20 元。
    """
    fee = 10.0
    if weight_kg > 1:
        fee += (weight_kg - 1) * 5
    if distance_km > 1000:
        fee += (distance_km - 1000) * 0.01
    if is_remote:
        fee += 20
    return round(fee, 2)


CALC_TOOLS = [calc, loan_monthly_payment, days_between, convert_temperature, shipping_fee]


# ---------------------------------------------------------------------------
# 1. 先单独验证工具算得对不对
# ---------------------------------------------------------------------------
def demo_1_tools_self_check() -> None:
    section("1. 先确认工具本身算得对（不依赖模型）")

    checks = [
        ("calc", lambda: calc.invoke({"expression": "(1000 * 1.05) ** 3"})),
        ("月供", lambda: loan_monthly_payment.invoke(
            {"principal": 1000000, "annual_rate": 5, "years": 30})),
        ("日期差", lambda: days_between.invoke(
            {"start_date": "2026-01-01", "end_date": "2026-12-31"})),
        ("温度换算", lambda: convert_temperature.invoke(
            {"value": 100, "from_unit": "C", "to_unit": "F"})),
        ("运费", lambda: shipping_fee.invoke(
            {"weight_kg": 3.5, "distance_km": 1500, "is_remote": True})),
    ]
    for name, fn in checks:
        print(f"    {name:<10} → {fn()}")

    print("\n  >> 这一步很重要：**工具本身必须先测对**。")
    print("     工具算错了，模型再聪明也白搭，而且这种错很难查。")


# ---------------------------------------------------------------------------
# 2. 实测：模型会不会乖乖调工具
# ---------------------------------------------------------------------------
def demo_2_will_model_use_tool() -> None:
    section("2. 实测：模型会调工具还是自己心算")

    llm_with_tools = build_llm().bind_tools(CALC_TOOLS)

    questions = [
        "贷款 100 万，年利率 5%，30 年，等额本息月供是多少？",
        "2026年春节是2月17日，从2026年1月1日到那天还有多少天？",
        "100 摄氏度等于多少华氏度？",
        "寄一个 3.5 公斤的包裹到 1500 公里外的偏远地区，运费多少？",
        "今天天气不错",       # 应该**不**调工具
    ]

    for q in questions:
        ai = llm_with_tools.invoke(q)
        if ai.tool_calls:
            calls = ", ".join(f"{c['name']}({c['args']})" for c in ai.tool_calls)
            print(f"  Q: {q[:34]}")
            print(f"     → 调工具: {calls}")
        else:
            print(f"  Q: {q[:34]}")
            print(f"     → 没调工具（直接回答）: {str(ai.content)[:40]}")

    print("\n  >> 观察结论：")
    print("     ① 涉及精确计算的问题，模型**基本都会**去调工具")
    print("     ② 无关的问题不会硬调（说明 description 起了作用）")
    print("     ⚠️ 但这不保证 100%，需要 tool_choice 强制的场景见第 4、5 个文件")


# ---------------------------------------------------------------------------
# 3. 完整闭环：调工具 → 执行 → 回传 → 生成答案
# ---------------------------------------------------------------------------
def demo_3_full_loop() -> None:
    section("3. 完整闭环：选择 → 执行 → 回传 → 作答")

    llm_with_tools = build_llm().bind_tools(CALC_TOOLS)
    by_name = {t.name: t for t in CALC_TOOLS}

    question = "贷款 100 万，年利率 5%，30 年，等额本息月供是多少？"
    print(f"  用户问题: {question}\n")

    # ① 模型决定调哪个工具
    messages = [HumanMessage(question)]
    ai = llm_with_tools.invoke(messages)
    messages.append(ai)
    print(f"  ① 模型决定调用: {[(c['name'], c['args']) for c in ai.tool_calls]}")

    # ② 我们执行工具
    for call in ai.tool_calls:
        result = by_name[call["name"]].invoke(call["args"])
        print(f"  ② 执行 {call['name']} → 结果: {result}")
        # ③ 把结果包装成 ToolMessage 回传（tool_call_id 必须对上！）
        messages.append(ToolMessage(content=str(result), tool_call_id=call["id"]))

    # ④ 模型基于结果作答
    final = llm_with_tools.invoke(messages)
    print(f"\n  ③ 最终回答: {final.content}")

    print("\n  >> 这就是工具调用的完整链条（四步）：")
    print("     问题 → 模型选工具 → 我们执行 → 结果回传 → 模型作答")
    print("     ⚠️ ToolMessage 的 tool_call_id **必须**和 tool_calls[].id 一致，")
    print("        对不上模型 API 会直接报错。")


# ---------------------------------------------------------------------------
# 4. 一次要算多个 → 并行调用
# ---------------------------------------------------------------------------
def demo_4_parallel_calls() -> None:
    section("4. 一次问多个 → 模型会并行调多个工具")

    llm_with_tools = build_llm().bind_tools(CALC_TOOLS)
    by_name = {t.name: t for t in CALC_TOOLS}

    question = "100摄氏度是多少华氏度？另外 2026-01-01 到 2026-03-01 有多少天？"
    print(f"  问题: {question}\n")

    messages = [HumanMessage(question)]
    ai = llm_with_tools.invoke(messages)
    messages.append(ai)

    print(f"  模型一次返回了 {len(ai.tool_calls)} 个工具调用：")
    for c in ai.tool_calls:
        print(f"    - {c['name']}({c['args']})  id={c['id'][:16]}...")

    for call in ai.tool_calls:
        result = by_name[call["name"]].invoke(call["args"])
        messages.append(ToolMessage(content=str(result), tool_call_id=call["id"]))

    final = llm_with_tools.invoke(messages)
    print(f"\n  最终回答: {final.content}")

    print("\n  >> 多个工具**互不依赖**时，模型会一次性全返回，")
    print("     我们可以并发执行（用线程池），不用一个个等。")
    print("     这点和 Java 里的 CompletableFuture.allOf 思路一致。")


# ---------------------------------------------------------------------------
# 5. 这类工具的设计原则
# ---------------------------------------------------------------------------
def demo_5_design_principles() -> None:
    section("5. 逻辑公式类工具的设计原则")

    print("  ✅ 该做的：")
    print("   ① 幂等：同样的输入永远同样的输出（方便重试、缓存）")
    print("   ② 无副作用：不写库、不发消息、不改状态")
    print("   ③ 入参用基础类型，加默认值")
    print("   ④ 返回值说清楚单位（是元还是分？是摄氏度还是华氏度？）")
    print("   ⑤ 参数非法时返回**可读的错误说明**，让模型知道怎么改")

    print("\n  ❌ 不该做的：")
    print("   ① 别让模型传复杂结构（嵌套对象、数组能免则免）")
    print("   ② 别在工具里再调一次大模型（会指数级放大延迟和成本）")
    print("   ③ 别把业务规则写死在 prompt 里，应该写进工具代码")
    print("   ④ 别直接 eval 用户输入（安全问题，见 calc 里的注释）")

    print("\n  💡 一个很实用的判断标准：")
    print("     「这段代码如果写错了，是**逻辑错误**还是**算错**？」")
    print("       算错 → 做成工具（模型算不准）")
    print("       需要外部数据 → 做成远程调用工具（下一个文件）")
    print("       需要判断语义 → 别做工具，让模型自己来")


def main() -> None:
    print("2. 逻辑公式类工具（DeepSeek + 最新 API）")

    demo_1_tools_self_check()

    if not os.getenv("DEEPSEEK_API_KEY"):
        print("\n⚠️ 没读到 DEEPSEEK_API_KEY，跳过需要调模型的演示。.env 路径：", _ENV_PATH)
        return

    demo_2_will_model_use_tool()
    demo_3_full_loop()
    demo_4_parallel_calls()
    demo_5_design_principles()

    print("\n" + "=" * 62)
    print("全部示例执行完毕。下一个：3.远程调用类工具.py")


if __name__ == "__main__":
    main()
