#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
1. 工具的三种定义方式（DeepSeek + 最新 API）
==========================================
【Python 语法看不懂？】闭包、lambda、** 解包、推导式等见 ../PYTHON_SYNTAX.md

【工具（Tool）到底是什么】
    一句话：**一个「能被模型调用的函数」+ 一份「给模型看的说明书」**。

    说明书包含三样东西，缺一不可：
        ① 工具名      name        —— 模型用它来指定「我要调这个」
        ② 功能描述    description —— 模型靠它判断「该不该调这个」★最关键
        ③ 参数结构    args_schema —— 模型靠它知道「要传什么参数」

    【Java 对照】
        工具 ≈ 一个带 Swagger/OpenAPI 注解的 Controller 接口：
            @Operation(summary = "计算两个数的和")     ← description
            @GetMapping("/add")
            public int add(
                @Parameter int a,                      ← args_schema
                @Parameter int b) { ... }
        模型就是「看着 Swagger 文档决定调哪个接口」的前端。

【⚠️ 最重要的一条认知】
    **description 不是给人看的注释，是给模型看的决策依据。**
    写得含糊 → 模型要么不调、要么调错。
    这是工具用得好不好的第一要素，比代码本身还重要。

【三种定义方式怎么选】
    @tool 装饰器                 最常用，90% 场景用它
    StructuredTool.from_function  要动态造工具、或想显式指定 schema 时
    BaseTool 子类                 要精细控制（重试、缓存、异步、自定义异常）

【运行】
    ./yzy/Scripts/python.exe "aiLearn/tool/1.工具定义三种方式.py"
"""

import asyncio
from typing import Optional

from langchain_core.tools import BaseTool, StructuredTool, ToolException, tool
from pydantic import BaseModel, Field


def section(title: str) -> None:
    """打印分节标题，纯排版用。"""
    print("\n" + "=" * 62)
    print(title)
    print("=" * 62)


# ---------------------------------------------------------------------------
# 方式一：@tool 装饰器（最常用）
# ---------------------------------------------------------------------------
@tool
def add(a: int, b: int) -> int:
    """计算两个数的和。

    当遇到加法、求和、相加等需求时使用这个工具。
    """
    return a + b


def demo_1_decorator() -> None:
    section("1. 方式一：@tool 装饰器（最常用）")

    print("  定义：")
    print("    @tool")
    print("    def add(a: int, b: int) -> int:")
    print("        '''计算两个数的和。'''")
    print("        return a + b")

    print("\n  LangChain 自动从函数里抽出了三样东西：")
    print(f"    ① name        = {add.name}")
    print(f"    ② description = {add.description}")
    print(f"    ③ args_schema = {list(add.args_schema.model_fields.keys())}")

    print("\n  调用方式（三种等价）：")
    print(f"    add.invoke({{'a': 3, 'b': 5}})      → {add.invoke({'a': 3, 'b': 5})}")
    print(f"    add.run({{'a': 3, 'b': 5}})         → {add.run({'a': 3, 'b': 5})}")
    print(f"    add.func(3, 5)  (原始函数)          → {add.func(3, 5)}")

    print("\n  ⚠️ 注意：@tool 装饰之后，add 已经**不是原来的函数**了，")
    print("     它是一个 BaseTool 对象。想拿原函数用 add.func。")
    print("     （Java 视角：被代理对象包了一层，直接调用行为变了）")

    print("\n  >> 小知识：docstring 的**第一行**是简述，后面是详细说明，")
    print("     两者拼起来都会给模型。所以第一行写清干什么，后面写什么时候用。")


# ---------------------------------------------------------------------------
# 方式二：StructuredTool.from_function
# ---------------------------------------------------------------------------
class WeatherInput(BaseModel):
    """天气查询的入参。

    【Java 对照】这就是个 DTO / request body。
    Field 里的 description 会进 JSON Schema，**模型看得到**，要写清楚。
    """

    city: str = Field(description="城市名，例如：广州、北京。不要带「市」字以外的修饰")
    unit: str = Field(default="摄氏度", description="温度单位：摄氏度 或 华氏度")


def _query_weather(city: str, unit: str = "摄氏度") -> str:
    return f"{city}：晴，26{unit}"


def demo_2_structured_tool() -> None:
    section("2. 方式二：StructuredTool.from_function")

    weather = StructuredTool.from_function(
        func=_query_weather,
        name="query_weather",                       # 不写就用函数名
        description="查询指定城市的当前天气。用户问天气、气温、要不要带伞时用。",
        args_schema=WeatherInput,                   # 显式指定 schema
    )

    print("  用 from_function 显式指定三要素：")
    print(f"    name        = {weather.name}")
    print(f"    description = {weather.description}")
    print(f"    args_schema = {list(weather.args_schema.model_fields.keys())}")

    print(f"\n  调用: {weather.invoke({'city': '广州'})}")
    print(f"  带单位: {weather.invoke({'city': '广州', 'unit': '华氏度'})}")

    print("\n  生成的 JSON Schema（这就是发给模型的「接口文档」）：")
    schema = weather.args_schema.model_json_schema()
    for prop, detail in schema.get("properties", {}).items():
        print(f"    {prop}: {detail.get('description', '(无描述)')}")

    print("\n  >> 什么时候用这种方式：")
    print("     · 想让工具名和函数名不一样")
    print("     · 想给参数加详细约束（Field(description=...)、默认值）")
    print("     · 工具是**运行时动态生成**的（比如从数据库读配置造一批工具）")


# ---------------------------------------------------------------------------
# 方式三：BaseTool 子类
# ---------------------------------------------------------------------------
class PriceInput(BaseModel):
    product: str = Field(description="商品名称")
    vip: bool = Field(default=False, description="是否是 VIP 用户")


class PriceTool(BaseTool):
    """商品计价工具（继承 BaseTool，全程可控）。

    什么时候需要继承：
        · 要同时提供 sync / async 两个版本
        · 要自定义错误处理（抛 ToolException）
        · 工具本身有状态（连接、缓存）
    """

    name: str = "query_price"
    description: str = "查询商品价格。问「多少钱」「价格」「报价」时使用。"
    args_schema: type[BaseModel] = PriceInput

    def _run(self, product: str, vip: bool = False) -> str:
        """同步执行。

        ⚠️ 方法名必须是 _run，LangChain 靠这个约定找执行逻辑。
        """
        base = 100
        if vip:
            base = base * 0.8
        return f"{product} 的价格是 {base:.0f} 元"

    async def _arun(self, product: str, vip: bool = False) -> str:
        """异步执行。不写的话，异步调用会自动退化成线程池跑 _run。"""
        await asyncio.sleep(0.01)      # 模拟异步 IO
        return self._run(product, vip)


def demo_3_base_tool_subclass() -> None:
    section("3. 方式三：BaseTool 子类（完全可控）")

    price = PriceTool()
    print(f"    name        = {price.name}")
    print(f"    description = {price.description}")
    print(f"    同步调用    : {price.invoke({'product': '键盘'})}")
    print(f"    VIP 价      : {price.invoke({'product': '键盘', 'vip': True})}")

    async def run_async():
        result = await price.ainvoke({"product": "鼠标"})
        print(f"    异步调用    : {result}")

    asyncio.run(run_async())

    print("\n  必须实现的：**_run**（可选：**_arun**）")
    print("  ⚠️ 坑：方法名写错成 run / execute 不会报错，但调用时报 NotImplementedError。")


# ---------------------------------------------------------------------------
# 4. 异常处理：ToolException
# ---------------------------------------------------------------------------
def demo_4_tool_exception() -> None:
    section("4. 异常处理：ToolException 是干什么的")

    @tool
    def divide(a: int, b: int) -> float:
        """计算 a 除以 b。"""
        if b == 0:
            # handle_tool_error=True 时，这个消息会**回传给模型**，
            # 让模型自己决定怎么补救（比如换个参数重试）
            raise ToolException("除数不能为 0，请换一个非零的除数")
        return a / b


    print("  普通异常 vs ToolException：\n")
    print("    · 普通 Exception  → 整个链路崩掉，调用方收到异常")
    print("    · ToolException   → 可以被「捕获」成一条消息回传给模型")

    print("\n  实测：直接 invoke 抛 ToolException：")
    try:
        divide.invoke({"a": 1, "b": 0})
    except ToolException as e:
        print(f"    ToolException: {e}")

    print("\n  如果想让它变成「回传给模型的消息」，要这样构造工具：")

    def _div(a: int, b: int) -> float:
        if b == 0:
            raise ToolException("除数不能为 0，请换一个非零的除数")
        return a / b

    safe_divide = StructuredTool.from_function(
        func=_div,
        name="divide",
        description="计算 a 除以 b",
        handle_tool_error=True,     # ← 关键参数
    )
    print(f"    handle_tool_error=True → invoke 返回: {safe_divide.invoke({'a': 1, 'b': 0})!r}")

    print("\n  >> 生产建议：工具内部**自己消化**可预期的错误，")
    print("     返回「出错原因」字符串让模型重试，比直接抛异常更稳。")


# ---------------------------------------------------------------------------
# 5. description 怎么写（最重要的一节）
# ---------------------------------------------------------------------------
def demo_5_description_matters() -> None:
    section("5. description 怎么写（最重要的一节）")

    print("  description 是模型判断「用不用这个工具」的**唯一依据**。\n")

    bad = StructuredTool.from_function(
        func=lambda x: "结果", name="search", description="搜索"
    )
    good = StructuredTool.from_function(
        func=lambda x: "结果",
        name="search_product_doc",
        description=(
            "在【产品文档库】中检索相关内容。"
            "当用户询问产品功能、使用方法、参数配置、报错含义时使用。"
            "不适用于：订单查询、物流查询（那些有专门的工具）。"
            "输入是检索关键词，不是完整句子。"
        ),
    )

    print("  ❌ 反面例子：")
    print(f"    name={bad.name}  description={bad.description}")
    print("    → 模型不知道什么时候该调它，也不知道不该调它\n")

    print("  ✅ 正面例子：")
    print(f"    name={good.name}")
    print(f"    description={good.description}\n")

    print("  写 description 的四要素（记住这个模板）：")
    print("    ① 干什么       → 「在【产品文档库】中检索相关内容」")
    print("    ② 什么时候用   → 「当用户询问产品功能、使用方法...时使用」")
    print("    ③ 什么时候别用 → 「不适用于：订单查询、物流查询」")
    print("    ④ 参数怎么给   → 「输入是检索关键词，不是完整句子」")

    print("\n  ⚠️ 第③条「什么时候别用」最容易被忽略，但**最有用**：")
    print("     工具一多，描述重叠，模型就会乱选。显式划清边界能大幅提升准确率。")

    print("\n  另外：name 也要起得有区分度。")
    print("     ❌ search / query / get      → 十几个工具都这么叫，模型分不清")
    print("     ✅ search_product_doc / query_order_status")


# ---------------------------------------------------------------------------
# 6. 三种方式怎么选
# ---------------------------------------------------------------------------
def demo_6_summary() -> None:
    section("6. 三种方式怎么选")

    rows = [
        ("@tool", "最少", "低", "90% 的日常场景"),
        ("StructuredTool.from_function", "中等", "中", "要指定 schema / 动态造工具"),
        ("BaseTool 子类", "最多", "高", "要异步、有状态、自定义异常处理"),
    ]
    print(f"  {'方式':<32}{'代码量':<8}{'可控性':<8}{'什么时候用'}")
    print("  " + "-" * 78)
    for a, b, c, d in rows:
        print(f"  {a:<32}{b:<8}{c:<8}{d}")

    print("\n  还有两个实用变体：")
    print("    · create_retriever_tool(检索器, 名字, 描述)  → 把 RAG 检索器变成工具")
    print("    · convert_runnable_to_tool(链)               → 把一条 LCEL 链变成工具")

    print("\n  ⚠️ 通用注意事项：")
    print("    ① 参数尽量用**基础类型**（str/int/bool/float/枚举），别塞复杂对象")
    print("    ② 参数能设默认值就设，减少模型填错的几率")
    print("    ③ 返回值尽量是**字符串或可序列化对象**，模型要读得懂")
    print("    ④ 耗时长的工具要设超时，否则整个链路挂住")


def main() -> None:
    print("1. 工具的三种定义方式（无需 API key，纯本地）")

    demo_1_decorator()
    demo_2_structured_tool()
    demo_3_base_tool_subclass()
    demo_4_tool_exception()
    demo_5_description_matters()
    demo_6_summary()

    print("\n" + "=" * 62)
    print("全部示例执行完毕。下一个：2.逻辑公式类工具.py")


if __name__ == "__main__":
    main()
