#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
4. 工具绑定与执行闭环（DeepSeek + 最新 API）
==========================================
【Python 语法看不懂？】闭包、lambda、** 解包、推导式等见 ../PYTHON_SYNTAX.md

【bind_tools 干了什么】
    把「工具说明书」（name + description + args_schema）发给模型，
    模型就能在回答时说「我要调某个工具，参数是 xxx」。

        llm.bind_tools([t1, t2])  →  返回一个新的模型对象，调用时会带上工具定义

    ⚠️ 注意：**模型不会替你执行工具**。
       它只返回「我想调什么、参数是什么」，真正执行是我们自己的事。
       这是新手最容易误解的地方——以为 bind 了就自动跑完了。

【完整闭环四步】
    ① 模型决定：返回 AIMessage，里面带 tool_calls
    ② 我们执行：按 name 找到工具，invoke(args)
    ③ 结果回传：包装成 ToolMessage，**tool_call_id 必须对应**
    ④ 模型作答：拿着结果生成最终回答

【本文件的 DeepSeek 实测重点】
    ⚠️ tool_choice 强制模式**必须关掉思考**，否则报
       "Thinking mode does not support this tool_choice"

【运行】
    ./yzy/Scripts/python.exe "aiLearn/tool/4.工具绑定与执行闭环.py"
"""

import os
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import dotenv
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
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


def build_llm_no_thinking() -> ChatOpenAI:
    """关掉思考模式的模型。

    ⚠️ DeepSeek 上「强制调用工具」必须关思考，否则 400。
    """
    return build_llm(extra_body={"thinking": {"type": "disabled"}})


def section(title: str) -> None:
    """打印分节标题，纯排版用。"""
    print("\n" + "=" * 62)
    print(title)
    print("=" * 62)


# ---------------------------------------------------------------------------
# 工具集
# ---------------------------------------------------------------------------
@tool
def add(a: int, b: int) -> int:
    """计算两个数的和。遇到加法、求和需求时使用。"""
    return a + b


@tool
def weather(city: str) -> str:
    """查询指定城市的天气。问天气、气温、要不要带伞时使用。"""
    return f"{city}：晴，26 摄氏度"


@tool
def order_status(order_no: str) -> str:
    """查询订单状态和物流进度。问「我的订单到哪了」「发货了吗」时使用。"""
    return f"订单 {order_no}：已发货，预计明天送达"


TOOLS = [add, weather, order_status]
TOOLS_BY_NAME = {t.name: t for t in TOOLS}


# ---------------------------------------------------------------------------
# 1. bind_tools 到底做了什么
# ---------------------------------------------------------------------------
def demo_1_what_bind_does() -> None:
    section("1. bind_tools 到底做了什么")

    llm = build_llm()
    llm_with_tools = llm.bind_tools(TOOLS)

    print(f"  bind 之前: {type(llm).__name__}")
    print(f"  bind 之后: {type(llm_with_tools).__name__}")
    print("  → 返回的是**新对象**，原 llm 没被改动（和所有 with_xxx 一样）")

    ai = llm_with_tools.invoke("1 加 2 等于多少")
    print(f"\n  调用后返回的其实是 AIMessage: {type(ai).__name__}")
    print(f"    ai.content   = {ai.content!r}   ← 空的！")
    print(f"    ai.tool_calls = {ai.tool_calls}")

    print("\n  ⚠️ 关键认知：bind_tools 只是把工具说明书发给模型，")
    print("     模型返回的**不是答案**，而是「我要调什么工具」的**意图**。")
    print("     工具得我们自己去执行——这是新手最常见的误解。")


# ---------------------------------------------------------------------------
# 2. tool_calls 的结构
# ---------------------------------------------------------------------------
def demo_2_tool_calls_structure() -> None:
    section("2. tool_calls 里有什么")

    ai = build_llm().bind_tools(TOOLS).invoke("广州天气怎么样？3 加 4 呢？")

    print(f"  本次返回 {len(ai.tool_calls)} 个调用：\n")
    for i, call in enumerate(ai.tool_calls, 1):
        print(f"    调用 {i}:")
        print(f"      name = {call['name']:<12}  ← 工具名，用来查表")
        print(f"      args = {str(call['args']):<30}  ← 模型填的参数")
        print(f"      id   = {call['id'][:24]}...  ← 回传结果时要对上这个")

    print("\n  【Java 对照】tool_calls 就是个 List<ToolCall>：")
    print("     record ToolCall(String name, Map<String,Object> args, String id) {}")

    print("\n  ⚠️ 三点要注意：")
    print("     ① args 是** dict**，但值是模型填的，可能不合法（要校验）")
    print("     ② id 必须原样带回，模型靠它把结果和调用对上")
    print("     ③ 一次可能返回**多个**（互不依赖时会并行）")


# ---------------------------------------------------------------------------
# 3. 完整闭环（手写版，把每一步摊开）
# ---------------------------------------------------------------------------
def demo_3_manual_loop() -> None:
    section("3. 完整闭环，一步步手写")

    llm_with_tools = build_llm().bind_tools(TOOLS)
    messages = [HumanMessage("广州天气怎么样？")]

    print("  ① 把问题发给模型：")
    ai = llm_with_tools.invoke(messages)
    messages.append(ai)
    print(f"     模型要求调用: {[(c['name'], c['args']) for c in ai.tool_calls]}")

    print("\n  ② 我们执行工具：")
    for call in ai.tool_calls:
        fn = TOOLS_BY_NAME[call["name"]]
        # ⚠️ 找不到工具时要有兜底，否则 KeyError 直接崩
        if fn is None:
            print(f"     ❌ 未知工具: {call['name']}")
            continue
        result = fn.invoke(call["args"])
        print(f"     {call['name']}{call['args']} → {result}")

        print("\n  ③ 把结果包装成 ToolMessage 回传：")
        messages.append(ToolMessage(content=str(result), tool_call_id=call["id"]))
        print(f"     ToolMessage(content={result!r}, tool_call_id={call['id'][:20]}...)")

    print("\n  ④ 模型基于结果作答：")
    final = llm_with_tools.invoke(messages)
    print(f"     {final.content}")

    print("\n  >> 这四步是所有 Agent 框架内部在做的事。")
    print("     手写一遍，再看 LangGraph / create_agent 就全是透明的。")


# ---------------------------------------------------------------------------
# 4. 多工具并行执行
# ---------------------------------------------------------------------------
def demo_4_parallel_execution() -> None:
    section("4. 多个工具要并发执行，别串行等")

    llm_with_tools = build_llm().bind_tools(TOOLS)
    ai = llm_with_tools.invoke("广州天气？订单 SO001 到哪了？3 加 4 等于多少？")

    calls = ai.tool_calls
    print(f"  模型一次返回 {len(calls)} 个调用：{[c['name'] for c in calls]}\n")

    def run_one(call):
        fn = TOOLS_BY_NAME[call["name"]]
        return call, fn.invoke(call["args"])

    # 串行
    import time
    t0 = time.time()
    serial_results = [run_one(c) for c in calls]
    serial_cost = time.time() - t0

    # 并发（线程池）
    t0 = time.time()
    with ThreadPoolExecutor(max_workers=4) as pool:
        parallel_results = list(pool.map(run_one, calls))
    parallel_cost = time.time() - t0

    print(f"  串行耗时: {serial_cost:.3f}s")
    print(f"  并发耗时: {parallel_cost:.3f}s")

    print("\n  执行结果：")
    for call, result in parallel_results:
        print(f"    {call['name']:<14} → {result}")

    print("\n  >> 工具是 IO 密集型的（等网络），并发能显著提速。")
    print("     Java 视角：ThreadPoolExecutor + CompletableFuture.allOf")
    print("     ⚠️ 线程池大小要限制，别来 100 个调用就开 100 个线程。")


# ---------------------------------------------------------------------------
# 5. tool_choice：控制「必须调 / 不许调 / 调某个」
# ---------------------------------------------------------------------------
def demo_5_tool_choice() -> None:
    section("5. tool_choice：强制控制是否调工具")

    print("  四个取值：")
    print("    'auto'   让模型自己决定（默认）")
    print("    'none'   不许调工具，只能直接回答")
    print("    'any'    必须调至少一个工具")
    print("    指定名字  必须调这一个工具")

    print("\n  ⚠️【DeepSeek 实测坑】开思考模式下，强制模式会 400：\n")

    # ① 开思考 + auto：OK
    try:
        r = build_llm().bind_tools(TOOLS, tool_choice="auto").invoke("你好")
        print(f"    开思考 + auto → 成功，tool_calls={[c['name'] for c in r.tool_calls]}")
    except Exception as e:
        print(f"    开思考 + auto → {type(e).__name__}")

    # ② 开思考 + any：报错
    try:
        build_llm().bind_tools(TOOLS, tool_choice="any").invoke("你好")
        print("    开思考 + any  → 成功")
    except Exception as e:
        msg = str(e)
        print(f"    开思考 + any  → {type(e).__name__}")
        if "Thinking mode" in msg:
            print("       错误信息含: 'Thinking mode does not support this tool_choice'")

    print("\n  ✅ 解法：强制模式用**关思考**的模型：\n")

    no_think = build_llm_no_thinking()
    question = "你好，随便说点什么"
    for choice in ("auto", "none", "any", "weather"):
        try:
            r = no_think.bind_tools(TOOLS, tool_choice=choice).invoke(question)
            names = [c["name"] for c in r.tool_calls]
            extra = f"，正文={str(r.content)[:20]!r}" if not names else ""
            print(f"    关思考 + {choice:<9} → tool_calls={names}{extra}")
        except Exception as e:
            print(f"    关思考 + {choice:<9} → {type(e).__name__}: {str(e)[:60]}")

    print("\n  >> 什么时候用强制模式：")
    print("     · 'none'    → 做纯聊天/摘要，不想让它调工具")
    print("     · 'any'     → 确定必须查外部数据才能答")
    print("     · 指定名字  → 做「信息抽取」：强制它把结果填进工具参数里")
    print("  ⚠️ DeepSeek 上用这几个，记得关思考。")


# ---------------------------------------------------------------------------
# 6. 多轮工具调用（工具调完还要再调）
# ---------------------------------------------------------------------------
def demo_6_multi_round() -> None:
    section("6. 多轮：工具的结果决定下一步调什么")

    llm_with_tools = build_llm().bind_tools(TOOLS)

    # 造一个「必须先查订单、再根据结果算」的场景
    messages = [HumanMessage("查询订单 SO001 的状态，另外算一下 100 加 200")]
    print("  用户:", messages[0].content)

    for round_no in range(1, 4):     # 最多 3 轮，防止死循环
        ai = llm_with_tools.invoke(messages)
        messages.append(ai)

        if not ai.tool_calls:
            print(f"\n  第 {round_no} 轮：模型没再调工具，结束")
            print(f"  最终回答: {str(ai.content)[:120]}")
            break

        print(f"\n  第 {round_no} 轮：调用 {[c['name'] for c in ai.tool_calls]}")
        for call in ai.tool_calls:
            fn = TOOLS_BY_NAME[call["name"]]
            result = fn.invoke(call["args"])
            print(f"     → {call['name']}: {result}")
            messages.append(ToolMessage(content=str(result), tool_call_id=call["id"]))

    print("\n  >> 真实 Agent 就是这么循环：")
    print("     调工具 → 看结果 → 再决定调什么 → 直到不需要调为止")
    print("     ⚠️ 生产必须设**最大轮数**，否则模型可能无限循环烧钱。")


def main() -> None:
    print("4. 工具绑定与执行闭环（DeepSeek + 最新 API）")

    if not os.getenv("DEEPSEEK_API_KEY"):
        print("\n❌ 没读到 DEEPSEEK_API_KEY，请检查 .env：", _ENV_PATH)
        return

    demo_1_what_bind_does()
    demo_2_tool_calls_structure()
    demo_3_manual_loop()
    demo_4_parallel_execution()
    demo_5_tool_choice()
    demo_6_multi_round()

    print("\n" + "=" * 62)
    print("全部示例执行完毕。下一个：5.工具分组与路由判断.py")


if __name__ == "__main__":
    main()
