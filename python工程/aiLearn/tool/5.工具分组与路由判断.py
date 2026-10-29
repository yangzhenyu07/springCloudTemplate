#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
5. 工具分组与路由判断（DeepSeek + 最新 API）
===========================================
【Python 语法看不懂？】闭包、lambda、** 解包、推导式等见 ../PYTHON_SYNTAX.md

        本文件讲的是另一件事：**工具一多，怎么分组、怎么知道模型调了哪一组。**
        这组工具我叫「能力域 / 工具域」（domain），不叫 Skill，避免和标准混淆。

【两者的区别（很重要，别混）】

    |            | 本文件的「能力域」              | 文件 7 的「Skill」              |
    |------------|-------------------------------|-------------------------------|
    | 是什么      | 工具的分组（一个 Python 字典）    | 独立目录 + SKILL.md + 脚本/资料 |
    | 谁加载      | 你手动塞给 create_agent(tools=...) | deepagents 按需读取        |
    | 怎么判断命中 | 看 tool_calls 里的工具名        | 看 read_file 读了哪个 SKILL.md  |
    | 适合什么    | 工具 10~50 个，要管住选择范围    | 能力需要配套说明文档/脚本/参考    |

    一句话：**本文件管「发给模型哪些工具」，文件 7 管「怎么把知识按需喂给模型」。**
    两者可以叠加：用能力域管工具选择范围，用 Skill 加载业务知识。

【本文件的三件事】
    ① 工具怎么分组（三种落地方式，都实测过）
    ② 怎么判断模型调了哪一组（6 种方法）
    ③ 工具太多怎么办（两级路由 / 官方中间件）

【Java 对照】
    能力域 ≈ 一个 Maven 模块 / 一个微服务：
        订单服务 提供 queryOrder / cancelOrder / refundOrder 三个接口
        库存服务 提供 checkStock / lockStock
    模型就是「看着服务清单决定调哪个服务的哪个接口」的网关。

【本文件的重点：怎么判断击中了哪个能力域】
    这是做工具系统时**最常被问**的问题，本文件给 6 种方法：
        ① 看 AIMessage.tool_calls（最直接）
        ② 回调 on_tool_start / on_tool_end
        ③ astream_events 的 on_tool_start
        ④ 工具内部自己打印/埋点
        ⑤ 用 tool_choice 强制指定（不靠模型选）
        ⑥ 自己做一层「意图路由」（模型只做分类，不直接选工具）

【运行】
    ./yzy/Scripts/python.exe "aiLearn/tool/5.工具分组与路由判断.py"
"""

import os
from pathlib import Path

import dotenv
from langchain_core.callbacks import BaseCallbackHandler
from langchain_core.messages import HumanMessage, ToolMessage
from langchain_core.runnables import RunnableLambda
from langchain_core.runnables.config import RunnableConfig
from langchain_core.tools import BaseToolkit, tool
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


# ===========================================================================
# 工具集：按「能力域」分组
# ===========================================================================
# ---- 域 A：订单 ----
@tool
def order_query(order_no: str) -> str:
    """查询订单详情。

    属于【订单】能力域。当用户询问订单状态、订单金额、下单时间时使用。
    """
    return f"订单 {order_no}：已付款，金额 299 元"


@tool
def order_cancel(order_no: str, reason: str) -> str:
    """取消订单。

    属于【订单】能力域。当用户明确要求取消订单、退款时使用。
    这是**有副作用**的操作，执行前必须确认。
    """
    return f"订单 {order_no} 已取消，原因：{reason}"


@tool
def logistics_query(order_no: str) -> str:
    """查询物流进度。

    属于【订单】能力域。当用户问「到哪了」「什么时候到」「快递」时使用。
    """
    return f"订单 {order_no}：已到达广州转运中心，预计明天送达"


# ---- 域 B：商品 ----
@tool
def product_search(keyword: str) -> str:
    """搜索商品。

    属于【商品】能力域。当用户想找某个商品、问有没有货、问价格时使用。
    """
    return f"搜到 3 个与「{keyword}」相关商品：键盘 199、鼠标 99、显示器 899"


@tool
def product_stock(product_id: str) -> str:
    """查询商品库存。

    属于【商品】能力域。当用户问「还有货吗」「库存多少」时使用。
    """
    return f"商品 {product_id}：库存 42 件"


@tool
def product_spec(product_id: str) -> str:
    """查询商品规格参数。

    属于【商品】能力域。当用户问尺寸、材质、参数、配置时使用。
    """
    return f"商品 {product_id} 规格：尺寸 30x15cm，重量 800g，材质 ABS"


# ---- 域 C：售后 ----
@tool
def ticket_create(issue: str, order_no: str) -> str:
    """创建售后工单。

    属于【售后】能力域。当用户投诉、报故障、要求人工介入时使用。
    """
    return f"已创建工单：{issue}（关联订单 {order_no}），工单号 TK20261028001"


@tool
def refund_policy() -> str:
    """查询退款政策。

    属于【售后】能力域。当用户问「能退吗」「几天内可以退」「退款规则」时使用。
    """
    return "7 天无理由退货；已拆封商品需质量问题才能退；退款 3-5 个工作日到账"


# 把工具按「域」分组 —— 这就是本文件的核心做法
DOMAINS: dict[str, list] = {
    "订单": [order_query, order_cancel, logistics_query],
    "商品": [product_search, product_stock, product_spec],
    "售后": [ticket_create, refund_policy],
}

ALL_TOOLS = [t for tools in DOMAINS.values() for t in tools]
TOOLS_BY_NAME = {t.name: t for t in ALL_TOOLS}

# 反查表：工具名 → 属于哪个域（用来「判断击中了哪个能力域」）
TOOL_TO_DOMAIN = {
    t.name: domain for domain, tools in DOMAINS.items() for t in tools
}


# ===========================================================================
# 方式二：用 BaseToolkit 打包（官方的「工具包」抽象）
# ===========================================================================
class OrderToolkit(BaseToolkit):
    """订单工具包。

    BaseToolkit 是 LangChain 官方提供的「工具打包」抽象，
    实现 get_tools() 返回一组工具。
    """

    def get_tools(self) -> list:
        return DOMAINS["订单"]


def demo_1_grouping() -> None:
    section("1. 工具怎么分组（三种落地方式）")

    print("  ⚠️ 再次强调：这里的「分组」是**工具的组织方式**，不是 Skill。")
    print("     Skill 是标准格式（目录 + SKILL.md）→ 见 7.Skill标准规范与渐进式加载.py\n")

    print("  【方式一】平铺：全部塞进一个列表")
    print("     >>> tools = [t1, t2, t3, ...]")
    print("     优点：最简单。缺点：超过 20 个就管不住了，而且每次全发给模型。\n")

    print("  【方式二】BaseToolkit：官方提供的工具包抽象")
    toolkit = OrderToolkit()
    print(f"     OrderToolkit().get_tools() → {[t.name for t in toolkit.get_tools()]}")
    print("     适合：要给某个工具包单独做安装/注册/权限控制\n")

    print("  【方式三】按业务域分字典（本文件的用法，推荐）")
    for domain, tools in DOMAINS.items():
        names = [t.name for t in tools]
        print(f"     【{domain}】{names}")

    print(f"\n     全部工具共 {len(ALL_TOOLS)} 个，分 {len(DOMAINS)} 个域")

    print("\n  >> 分组的价值有两个：")
    print("     ① 管理：几十个工具不分组根本没法维护")
    print("     ② 路由：可以按域筛选，只把相关工具发给模型（省钱 + 提准，见 demo_7）")

    print("\n  >> 分域的一个副作用：**要自己维护一张反查表**")
    print("     TOOL_TO_DOMAIN = {工具名: 域名}，用来事后判断击中了谁。")
    print("     这是手工活，容易漏。如果你用标准 Skill（文件 7），")
    print("     工具的归属写在 SKILL.md 的 include_tools 里，不用另建表。")


# ===========================================================================
# 判断击中了哪个域 —— 方法①：看 tool_calls
# ===========================================================================
def demo_2_method1_tool_calls() -> None:
    section("2. 【方法①】看 tool_calls —— 最直接")

    llm_with_tools = build_llm().bind_tools(ALL_TOOLS)

    questions = [
        "我的订单 SO001 到哪了？",
        "你们这儿的键盘还有货吗？",
        "买了三天能退货吗？",
        "今天天气不错",
    ]

    for q in questions:
        ai = llm_with_tools.invoke(q)
        if not ai.tool_calls:
            print(f"  Q: {q}")
            print("     → 没击中任何域（直接回答）\n")
            continue
        domains = [TOOL_TO_DOMAIN[c["name"]] for c in ai.tool_calls]
        print(f"  Q: {q}")
        print(f"     → 击中工具: {[c['name'] for c in ai.tool_calls]}")
        print(f"     → 归属能力域: {domains}\n")

    print("  >> 这就是最基本的判断方式：")
    print("     tool_calls[i]['name'] → 查反查表 → 得到域名")
    print("     前提是你要自己维护一张「工具 → 域」的反查表。")


# ===========================================================================
# 判断击中了哪个域 —— 方法②：回调
# ===========================================================================
class DomainTracker(BaseCallbackHandler):
    """回调：记录每次工具调用属于哪个域。

    【Java 对照】这就是个 AOP 切面，在工具执行前后插桩。
    """

    def __init__(self, tool_to_domain: dict[str, str]) -> None:
        self.tool_to_domain = tool_to_domain
        self.hits: list[str] = []      # 记录击中的域

    def on_tool_start(self, serialized, input_str, **kwargs) -> None:
        name = serialized.get("name", "unknown")
        domain = self.tool_to_domain.get(name, "未知")
        self.hits.append(domain)
        print(f"    [回调] on_tool_start: {name} → 属于【{domain}】")

    def on_tool_end(self, output, **kwargs) -> None:
        print(f"    [回调] on_tool_end: 返回 {str(output)[:40]}")


def demo_3_method2_callback() -> None:
    section("3. 【方法②】回调 —— 全链路自动埋点")

    tracker = DomainTracker(TOOL_TO_DOMAIN)
    llm_with_tools = build_llm().bind_tools(ALL_TOOLS)

    question = "查一下订单 SO001 物流，顺便看看键盘还有多少库存"
    print(f"  用户: {question}\n")

    messages = [HumanMessage(question)]
    ai = llm_with_tools.invoke(messages, config={"callbacks": [tracker]})
    messages.append(ai)

    print(f"\n  模型要求调用: {[c['name'] for c in ai.tool_calls]}\n")

    print("  执行工具（回调会自动记录）：")
    for call in ai.tool_calls:
        fn = TOOLS_BY_NAME[call["name"]]
        result = fn.invoke(call["args"], config={"callbacks": [tracker]})
        messages.append(ToolMessage(content=str(result), tool_call_id=call["id"]))

    print(f"\n  本次击中过的域: {tracker.hits}")

    print("\n  >> 回调的好处：**不用改工具代码**，挂在 config 上就生效，")
    print("     还能自动传给子链（这是它比 with_listeners 强的地方，见 runnableModule/5）。")


# ===========================================================================
# 判断击中了哪个域 —— 方法③：astream_events
# ===========================================================================
async def _execute_tool_calls(ai, config: RunnableConfig):
    """执行模型要求的工具调用。

    【关键】第二个参数 config 必须写上，LangChain 才会把回调/事件上下文
    注入进来；再把它传给 tool.ainvoke(...)，工具事件才会真正触发。

    【Java 对照】类似 Spring 的 AOP：方法签名里声明了 ProceedingJoinPoint，
    框架才会把上下文递给你，你不声明它就不传。
    """
    results = []
    for call in ai.tool_calls:
        fn = TOOLS_BY_NAME[call["name"]]
        # ↓ config 透传是 on_tool_start / on_tool_end 能触发的原因
        results.append(await fn.ainvoke(call["args"], config=config))
    return results


async def _demo4_async() -> None:
    question = "我想退货，买了三天了"
    print(f"  用户: {question}\n")

    # ---- ① 只 bind_tools，不执行 ----
    print("  ① 只 bind_tools 不执行（很多人的第一反应）：")
    kinds = set()
    async for event in build_llm().bind_tools(ALL_TOOLS).astream_events(question, version="v2"):
        kinds.add(event["event"])
    print(f"     事件类型: {sorted(kinds)}")
    print("     ↑ 没有 on_tool_*！因为 bind_tools 只让模型「说出想调谁」，")
    print("       真正执行是我们自己调 invoke() 才发生的，这一步不属于链。\n")

    # ---- ② 把「执行工具」也放进链里 ----
    print("  ② 把执行工具也放进链里（正确用法）：")
    chain = (
        build_llm(extra_body={"thinking": {"type": "disabled"}}).bind_tools(ALL_TOOLS)
        | RunnableLambda(_execute_tool_calls)
    )

    async for event in chain.astream_events(question, version="v2"):
        if event["event"] == "on_tool_start":
            name = event["name"]
            print(f"    on_tool_start: {name} → 属于【{TOOL_TO_DOMAIN.get(name, '未知')}】")
            print(f"       入参: {event['data'].get('input')}")
        elif event["event"] == "on_tool_end":
            print(f"    on_tool_end  : {str(event['data'].get('output'))[:50]}")


def demo_4_method3_events() -> None:
    section("4. 【方法③】astream_events —— 适合流式推送给前端")

    import asyncio
    asyncio.run(_demo4_async())

    print("\n  ⚠️ 踩坑点（本节最重要的一条）：")
    print("     llm.bind_tools(...).astream_events() 只会有 on_chat_model_*，")
    print("     **不会有 on_tool_*** —— 因为工具压根没被执行。")
    print("     必须把「执行工具」这一步也接进链（RunnableLambda / ToolNode / agent），")
    print("     并且把 config 透传给 tool.ainvoke(...)。")

    print("\n  >> 适合做「进度提示」：")
    print("     前端可以显示「正在查询订单...」「正在查库存...」")
    print("     比回调更适合实时 UI。")


# ===========================================================================
# 判断击中了哪个域 —— 方法④：工具内部埋点（最可控）
# ===========================================================================
def demo_5_method4_inside_tool() -> None:
    section("5. 【方法④】工具内部埋点 —— 最可控")

    hit_log: list[dict] = []

    @tool
    def tracked_order_query(order_no: str) -> str:
        """查询订单详情（带埋点）。"""
        hit_log.append({"domain": "订单", "tool": "order_query", "arg": order_no})
        return f"订单 {order_no}：已付款"

    print("  在工具函数第一行写日志/埋点：")
    print("    @tool")
    print("    def tracked_order_query(order_no):")
    print("        hit_log.append({'domain': '订单', ...})   ← 就这一行")
    print("        return ...")

    tracked_order_query.invoke({"order_no": "SO002"})
    print(f"\n  执行后埋点记录: {hit_log}")

    print("\n  >> 优缺点：")
    print("     ✅ 最可控，能记任意业务字段（用户 ID、耗时、结果码）")
    print("     ❌ 侵入工具代码，每个工具都要写一遍")
    print("     适合：需要业务级埋点/计费的场景")


# ===========================================================================
# 判断击中了哪个域 —— 方法⑤：tool_choice 强制（不让模型选）
# ===========================================================================
def demo_6_method5_force() -> None:
    section("6. 【方法⑤】tool_choice 强制指定 —— 不靠模型选")

    print("  有时候你**不希望**模型自己选，比如：")
    print("    · 确定这一步必须查订单 → 强制调 order_query")
    print("    · 做信息抽取 → 强制它把抽取结果填进工具参数\n")

    # ⚠️ DeepSeek 强制模式必须关思考
    no_think = build_llm(extra_body={"thinking": {"type": "disabled"}})

    # 造一个「信息抽取工具」：把用户的话抽成结构化字段
    @tool
    def extract_order_intent(order_no: str, intent: str) -> str:
        """从用户的话里抽取订单号和操作意图。

        intent 取值：查询 / 取消 / 物流 / 退款
        """
        return f"抽取结果：订单={order_no}，意图={intent}"

    llm = no_think.bind_tools([extract_order_intent], tool_choice="extract_order_intent")

    for q in ["帮我把订单 SO003 取消了吧", "SO004 到哪了？"]:
        ai = llm.invoke(q)
        for c in ai.tool_calls:
            print(f"  Q: {q}")
            print(f"     → 强制抽出: {c['args']}")

    print("\n  >> 这个技巧非常实用：**用工具调用做结构化抽取**。")
    print("     比让模型输出 JSON 再解析稳得多（schema 由 API 层保证）。")
    print("  ⚠️ DeepSeek 上必须关思考，否则 400。")


# ===========================================================================
# 判断击中了哪个域 —— 方法⑥：自己做意图路由（两级）
# ===========================================================================
class IntentResult(BaseModel):
    """意图分类结果。

    【Java 对照】就是个 enum + 置信度：
        enum Domain { ORDER, PRODUCT, AFTER_SALE, NONE }
    """

    domain: str = Field(description="命中哪个能力域：订单 / 商品 / 售后 / 无")
    reason: str = Field(description="判断理由，一句话")


def demo_7_method6_two_stage() -> None:
    section("7. 【方法⑥】自己做两级路由（最可控，推荐）")

    print("  问题：工具一多（比如 50 个），全塞给模型会：")
    print("    · 浪费 token（每次都要发 50 份说明书）")
    print("    · 准确率下降（选择太多，模型会犹豫）\n")

    print("  解法：**两级路由**")
    print("    第一级：让模型（可以用小模型）判断「属于哪个域」")
    print("    第二级：只把这个域的工具发给模型去选\n")

    # ⚠️⚠️ DeepSeek 的两个坑（都已实测踩过）：
    #   1) with_structured_output 默认走 json_schema，DeepSeek 直接 400：
    #      BadRequestError: This response_format type is unavailable now
    #      → 必须显式写 method="function_calling"
    #   2) function_calling 又和「思考模式」冲突 → 必须关思考
    # 两条缺一不可，否则就是 400。
    llm_no_think = build_llm(extra_body={"thinking": {"type": "disabled"}})
    router = llm_no_think.with_structured_output(IntentResult, method="function_calling")

    questions = [
        "我的订单 SO001 到哪了？",
        "键盘还有货吗？",
        "买了三天能退吗？",
        "你好呀",
    ]

    for q in questions:
        intent = router.invoke(f"判断下面这句话属于哪个能力域（订单/商品/售后/无）：\n{q}")
        print(f"  Q: {q}")
        print(f"     第一级路由 → {intent.domain}  （理由：{intent.reason}）")

        if intent.domain in DOMAINS:
            tools = DOMAINS[intent.domain]
            ai = llm_no_think.bind_tools(tools).invoke(q)
            names = [c["name"] for c in ai.tool_calls]
            print(f"     第二级选工具 → 只从【{intent.domain}】的 {len(tools)} 个工具里选 → {names}")
        else:
            print("     第二级 → 无匹配域，直接回答")
        print()

    print("  >> 两级的收益：")
    print("     · token 省一大截（只发一个域的工具）")
    print("     · 准确率更高（选择范围小了）")
    print("     · 路由过程**可观测、可干预**（域判错了能人工兜底）")
    print("  ⚠️ 代价：多一次模型调用（第一级可以用便宜的小模型）")
    print("  ⚠️ DeepSeek 专属坑：with_structured_output 必须 method='function_calling'")
    print("     + 关思考，漏一个都是 400（详见上面代码注释）")


# ===========================================================================
# 8. 官方中间件
# ===========================================================================
def demo_8_llm_tool_selector() -> None:
    section("8. 官方方案：LLMToolSelectorMiddleware")

    print("  langchain 1.4.7 自带了一个中间件，干的就是「先筛工具」这件事：\n")

    try:
        from langchain.agents.middleware import LLMToolSelectorMiddleware
        import inspect
        print("    LLMToolSelectorMiddleware")
        print(f"    参数: {list(inspect.signature(LLMToolSelectorMiddleware.__init__).parameters)}")
        print("\n    用法：")
        print("      middleware = LLMToolSelectorMiddleware(max_tools=3)")
        print("      agent = create_agent(model=..., tools=50个工具, middleware=[middleware])")
        print("\n    作用：先用模型把 50 个工具筛到 3 个，再交给主模型")
        print("    （这其实就是上一节「两级路由」的官方实现——不用自己写）")
        print("\n    常用参数：")
        print("      max_tools       最多保留几个工具")
        print("      model           用哪个模型筛选（可以指定小模型省钱）")
        print("      always_include  永远保留的工具（比如查用户信息）")
        print("\n    ⚠️ DeepSeek 上直接用会 400（内部走 json_schema）。")
        print("       绕过方案见 6.Agent与工具实战.py 的 demo_5（自定义 ChatOpenAI 子类）。")
    except ImportError as e:
        print(f"    导入失败: {e}")


# ===========================================================================
# 9. 总结
# ===========================================================================
def demo_9_summary() -> None:
    section("9. 六种判断方式怎么选")

    rows = [
        ("① 看 tool_calls", "零成本", "低", "调试、简单场景"),
        ("② 回调", "零成本", "中", "全链路自动埋点、计费"),
        ("③ astream_events", "零成本", "中", "流式 UI、进度提示"),
        ("④ 工具内埋点", "改代码", "高", "业务级埋点、需要业务字段"),
        ("⑤ tool_choice 强制", "零成本", "最高", "确定必须调某个时"),
        ("⑥ 两级路由", "多一次调用", "最高", "工具多（>20）时"),
    ]
    print(f"  {'方式':<22}{'成本':<12}{'可控性':<8}{'什么时候用'}")
    print("  " + "-" * 76)
    for a, b, c, d in rows:
        print(f"  {a:<22}{b:<12}{c:<8}{d}")

    print("\n  💡 我的建议（实用排序）：")
    print("     工具 < 10 个     → 平铺 + 看 tool_calls 就够了")
    print("     工具 10~30 个    → 按域分组 + 回调埋点")
    print("     工具 > 30 个     → 两级路由 / LLMToolSelectorMiddleware")
    print("     要 100% 可控     → tool_choice 强制指定")

    print("\n  ⚠️ 三条经验：")
    print("   ① 工具描述**划清边界**（写明「不适用于...」）比什么都重要")
    print("   ② 名字要有区分度，别都叫 query_xxx")
    print("   ③ 路由判断一定要**留日志**，否则出问题无从查起")

    print("\n  【什么时候该升级到标准 Skill（文件 7）】")
    print("     如果除了工具，你还想给模型**配套的说明文档、脚本、参考资料**，")
    print("     或者希望「工具 + 知识」一起按需加载 → 那就别用本文件的分组了，")
    print("     改用标准 Skill：目录 + SKILL.md，配置 include_tools 绑工具。")
    print("     好处：工具的归属写在 SKILL.md 里，不用自己维护反查表。")


def main() -> None:
    print("5. 工具分组与路由判断（DeepSeek + 最新 API）")
    print("   注：本文件的「分组」是工具组织方式，不是 Skill —— Skill 标准见文件 7")

    demo_1_grouping()

    if not os.getenv("DEEPSEEK_API_KEY"):
        print("\n⚠️ 没读到 DEEPSEEK_API_KEY，跳过需要调模型的演示。.env 路径：", _ENV_PATH)
        return

    demo_2_method1_tool_calls()
    demo_3_method2_callback()
    demo_4_method3_events()
    demo_5_method4_inside_tool()
    demo_6_method5_force()
    demo_7_method6_two_stage()
    demo_8_llm_tool_selector()
    demo_9_summary()

    print("\n" + "=" * 62)
    print("全部示例执行完毕。下一个：6.Agent与工具实战.py")


if __name__ == "__main__":
    main()
