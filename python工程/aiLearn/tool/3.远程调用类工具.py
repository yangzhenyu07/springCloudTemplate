#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
3. 远程调用类工具（DeepSeek + 最新 API）
======================================
【Python 语法看不懂？】闭包、lambda、** 解包、推导式等见 ../PYTHON_SYNTAX.md

【什么是「远程调用类」工具】
    工具内部要去**访问外部系统**才能拿到结果：
        · 调公司内部 HTTP 接口（查订单、查库存、查用户）
        · 查数据库 / Redis
        · 调第三方服务（天气、物流、支付、地图）
        · 调搜索引擎

    【Java 对照】就是 Service 层里带 IO 的方法：
        public OrderDTO queryOrder(String orderNo) {
            return restTemplate.getForObject(...);   // 有网络，会失败
        }

【和逻辑公式类工具的本质区别】
    | | 逻辑公式类 | 远程调用类 |
    |---|---|---|
    | 会不会失败 | 几乎不会 | **经常会**（超时、限流、5xx） |
    | 耗时 | 微秒级 | 几十毫秒~几秒 |
    | 幂等 | 天然幂等 | 要自己保证 |
    | 要不要重试 | 不需要 | **必须要有** |
    | 依赖 | 无 | 外部系统可用性 |

    所以这类工具的重点**不在功能，而在容错**。

【本文件用真实网络请求演示】
    用的是 httpbin.org（一个专门用来测试的公开 HTTP 服务），
    真实发包，能真实复现超时、500 错误等情况。

【运行】
    ./yzy/Scripts/python.exe "aiLearn/tool/3.远程调用类工具.py"
"""

import os
import time
from pathlib import Path
from typing import Optional

import dotenv
import requests
from langchain_core.messages import HumanMessage, ToolMessage
from langchain_core.tools import StructuredTool, tool
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field


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
# 工具一：最朴素的远程调用（❌ 反面教材）
# ---------------------------------------------------------------------------
@tool
def fetch_url_naive(url: str) -> str:
    """抓取指定 URL 的内容。

    当需要获取网页或接口数据时使用。url 必须是完整的 http/https 地址。
    """
    response = requests.get(url)          # ❌ 没设超时！
    return response.text[:200]


# ---------------------------------------------------------------------------
# 工具二：生产可用的远程调用（✅ 正确写法）
# ---------------------------------------------------------------------------
class FetchInput(BaseModel):
    url: str = Field(description="完整的 http/https 地址")
    timeout: float = Field(default=5.0, description="超时秒数，默认 5 秒")


def _fetch_with_retry(url: str, timeout: float = 5.0, retries: int = 2) -> str:
    """带超时 + 重试 + 错误分类的远程调用。

    【这是个普通函数，不是工具】工具在外面包装它。
    这样拆开的好处：函数可以单独单测，工具只负责「描述 + 暴露」。
    """
    last_error = None
    for attempt in range(retries + 1):
        try:
            response = requests.get(url, timeout=timeout)
            # 4xx 是「请求有问题」，重试没用，直接返回给模型让它改
            if 400 <= response.status_code < 500:
                return f"请求失败（客户端错误 {response.status_code}）：地址可能不对，请换个 URL"
            # 5xx 是「服务端有问题」，可以重试
            if response.status_code >= 500:
                last_error = f"服务端错误 {response.status_code}"
                time.sleep(0.3 * (attempt + 1))   # 简单退避
                continue
            return response.text[:300]
        except requests.Timeout:
            last_error = f"请求超时（超过 {timeout} 秒）"
            time.sleep(0.3 * (attempt + 1))
        except requests.RequestException as e:
            last_error = f"网络错误：{type(e).__name__}"
            time.sleep(0.3 * (attempt + 1))

    return f"远程调用失败，已重试 {retries} 次。最后错误：{last_error}"


fetch_url = StructuredTool.from_function(
    func=_fetch_with_retry,
    name="fetch_url",
    description=(
        "抓取指定 URL 的内容（HTTP GET）。"
        "当需要获取网页内容、调用接口查询数据时使用。"
        "不适用于：需要登录才能访问的页面、POST 请求。"
        "如果返回失败信息，可以换个地址重试。"
    ),
    args_schema=FetchInput,
)


# ---------------------------------------------------------------------------
# 1. 为什么必须设超时
# ---------------------------------------------------------------------------
def demo_1_why_timeout() -> None:
    section("1. 为什么远程工具必须设超时")

    print("  ❌ 反面教材：requests.get(url) 不设 timeout")
    print("     Python 的 requests **默认没有超时**！")
    print("     对端不响应 → 这个请求会一直挂着 → 整个链路卡死")
    print("     在高并发服务里，几个这样的请求就能拖垮整个线程池。")

    print("\n  ✅ 正确写法：requests.get(url, timeout=5)")
    print("     超时后抛 requests.Timeout，我们捕获后返回错误信息给模型。")

    print("\n  实测两种写法（用一个**故意延迟 10 秒**的 URL）：")
    slow_url = "https://httpbin.org/delay/10"

    print("\n  【不设超时】——为了不真卡死，这里只演示 5 秒就放弃观察：")
    try:
        # 用线程模拟：不设超时真的会一直等，这里我们不实际跑
        print(f"    requests.get('{slow_url}')  → 会一直等到对端响应（可能永远）")
        print("    ⚠️ 不实际执行，否则脚本会卡住")
    except Exception:
        pass

    print("\n  【设 2 秒超时】真实执行：")
    t0 = time.time()
    try:
        requests.get(slow_url, timeout=2)
        print("    竟然成功了")
    except requests.Timeout:
        print(f"    requests.Timeout —— 耗时 {time.time() - t0:.2f}s 后放弃 ✅")

    print("\n  >> 经验值：内部服务 2~5 秒，第三方 5~10 秒，")
    print("     并且一定要小于整个链路的超时时间。")


# ---------------------------------------------------------------------------
# 2. 错误分类：哪些该重试，哪些不该
# ---------------------------------------------------------------------------
def demo_2_error_classification() -> None:
    section("2. 错误分类：哪些该重试，哪些不该")

    rows = [
        ("超时 Timeout", "✅ 该重试", "可能是网络抖动或对端临时慢"),
        ("5xx 服务端错误", "✅ 该重试", "对端挂了，可能马上恢复"),
        ("429 限流", "✅ 该重试（要退避）", "退避等待后再试"),
        ("4xx 客户端错误", "❌ 别重试", "参数错了，重试一万次也错"),
        ("401/403 鉴权", "❌ 别重试", "权限问题，重试没用"),
        ("DNS 失败", "❌ 别重试", "地址写错了"),
    ]
    print(f"  {'错误类型':<18}{'重试？':<20}{'原因'}")
    print("  " + "-" * 72)
    for a, b, c in rows:
        print(f"  {a:<18}{b:<20}{c}")

    print("\n  实测三种情况（真实请求 httpbin.org）：\n")

    cases = [
        ("正常 200", "https://httpbin.org/get"),
        ("客户端 404", "https://httpbin.org/status/404"),
        ("服务端 500", "https://httpbin.org/status/500"),
    ]
    for label, url in cases:
        result = _fetch_with_retry(url, timeout=5, retries=1)
        print(f"    {label:<12} → {result[:70]}")

    print("\n  >> 关键设计：把「错误信息」当成字符串返回给模型，")
    print("     而不是抛异常终止链路。模型看到错误会自己换个参数重试。")


# ---------------------------------------------------------------------------
# 3. 完整闭环：模型调远程工具
# ---------------------------------------------------------------------------
def demo_3_model_calls_remote_tool() -> None:
    section("3. 完整闭环：让模型去调远程接口")

    llm_with_tools = build_llm().bind_tools([fetch_url])
    by_name = {"fetch_url": fetch_url}

    question = "帮我看看 https://httpbin.org/get 这个接口返回什么"
    print(f"  用户: {question}\n")

    messages = [HumanMessage(question)]
    ai = llm_with_tools.invoke(messages)
    messages.append(ai)

    if not ai.tool_calls:
        print("  模型没调工具，直接回答：", ai.content[:80])
        return

    print(f"  ① 模型决定调用: {[(c['name'], c['args']) for c in ai.tool_calls]}")
    for call in ai.tool_calls:
        t0 = time.time()
        result = by_name[call["name"]].invoke(call["args"])
        print(f"  ② 执行耗时 {time.time() - t0:.2f}s，返回 {len(str(result))} 字符")
        messages.append(ToolMessage(content=str(result), tool_call_id=call["id"]))

    final = llm_with_tools.invoke(messages)
    print(f"\n  ③ 模型总结: {str(final.content)[:150]}")


# ---------------------------------------------------------------------------
# 4. ⚠️ 安全问题：凭据不要进 schema
# ---------------------------------------------------------------------------
def demo_4_credentials() -> None:
    section("4. ⚠️ 安全：凭据绝不能当工具参数")

    print("  ❌ 危险写法：把 api_key 做成工具参数")
    print("     @tool")
    print("     def query_order(order_no: str, api_key: str) -> str: ...")
    print("     问题：")
    print("       · api_key 会出现在发给模型的 JSON Schema 里（泄露给模型厂商）")
    print("       · 模型可能「幻觉」出一个假的 key")
    print("       · 对话日志里会留下明文凭据")

    print("\n  ✅ 正确写法：凭据从**环境/配置**注入，不进 schema")

    class OrderInput(BaseModel):
        order_no: str = Field(description="订单号")

    def _query_order(order_no: str) -> str:
        # 凭据从配置里拿，模型完全看不到
        api_key = os.getenv("ORDER_API_KEY", "demo-key")
        # 真实场景：requests.get(..., headers={"Authorization": api_key})
        return f"订单 {order_no}：已发货（用 key={api_key[:4]}*** 查询）"

    order_tool = StructuredTool.from_function(
        func=_query_order, name="query_order",
        description="查询订单状态和物流信息。",
        args_schema=OrderInput,
    )

    print(f"     schema 字段: {list(order_tool.args_schema.model_fields.keys())}")
    print(f"     → 模型只看到 order_no，看不到任何凭据 ✅")
    print(f"     调用结果: {order_tool.invoke({'order_no': 'SO20261028001'})}")

    print("\n  还有一条：**用户输入不要直接拼进 URL / SQL**。")
    print("     ❌ f'SELECT * FROM orders WHERE no={order_no}'   → SQL 注入")
    print("     ✅ 用参数化查询 / URL 编码")


# ---------------------------------------------------------------------------
# 5. 这类工具的设计清单
# ---------------------------------------------------------------------------
def demo_5_checklist() -> None:
    section("5. 远程调用类工具的设计清单")

    checklist = [
        ("设超时", "必须", "不设会拖垮整个服务"),
        ("错误分类", "必须", "4xx 不重试，5xx/超时才重试"),
        ("重试 + 退避", "必须", "退避避免重试风暴"),
        ("降级方案", "建议", "挂了返回兜底值，别让整轮对话失败"),
        ("结果裁剪", "必须", "别把整个 HTML 塞回给模型，浪费 token"),
        ("缓存", "建议", "相同查询缓存几秒，省钱又提速"),
        ("超时日志", "必须", "否则「为什么变慢」查不出来"),
        ("幂等", "看情况", "写操作要保证重复执行不出问题"),
        ("凭据隔离", "必须", "不进 schema，从配置注入"),
    ]
    print(f"  {'项':<14}{'重要度':<10}{'说明'}")
    print("  " + "-" * 66)
    for a, b, c in checklist:
        print(f"  {a:<14}{b:<10}{c}")

    print("\n  ⚠️ 最容易被忽略的一条：**结果裁剪**")
    print("     远程接口经常返回一大坨 JSON/HTML，")
    print("     全塞回给模型 = 白花 token + 干扰模型判断。")
    print("     正确做法是只挑**需要的字段**再回传。")

    print("\n  💡 一个实用模式：工具里再包一层「精简函数」")
    print("     原始响应 → 提取关键字段 → 转成简短文本 → 回传模型")


def main() -> None:
    print("3. 远程调用类工具（DeepSeek + 最新 API，会真实发 HTTP 请求）")

    demo_1_why_timeout()
    demo_2_error_classification()
    demo_4_credentials()
    demo_5_checklist()

    if not os.getenv("DEEPSEEK_API_KEY"):
        print("\n⚠️ 没读到 DEEPSEEK_API_KEY，跳过需要调模型的演示。.env 路径：", _ENV_PATH)
        return

    demo_3_model_calls_remote_tool()

    print("\n" + "=" * 62)
    print("全部示例执行完毕。下一个：4.工具绑定与执行闭环.py")


if __name__ == "__main__":
    main()
