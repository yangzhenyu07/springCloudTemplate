#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
6. Agent 与工具实战（DeepSeek + 最新 API）
=========================================
【Python 语法看不懂？】闭包、lambda、** 解包、推导式等见 ../PYTHON_SYNTAX.md

【本文件在整套示例里的位置】
    1.工具定义三种方式.py   → 零件怎么造
    2.逻辑公式类工具.py     → 纯计算类工具
    3.远程调用类工具.py     → 调外部接口的工具
    4.工具绑定与执行闭环.py → bind_tools + 手写循环
    5.工具分组与路由判断.py → 分组 + 判断击中哪个能力域（6 种手法）
    6.Agent与工具实战.py    → 【本文件】把上面全部装成一台能跑的机器
    7.Skill标准规范与渐进式加载.py → Skill 开放标准（目录 + SKILL.md）

【⚠️ 术语说明：本文件的「能力域」不是 Skill】
    按业务域把工具分组（字典），这个分组叫「能力域 / 工具域」，**不叫 Skill**。
    Skill 是另一套东西：开放标准（目录 + SKILL.md），由 deepagents 按需加载，
    见文件 7。两者判断「命中」的方式完全不同：
        能力域 → 看 tool_calls 里的工具名
        Skill  → 看 read_file 读了哪个 SKILL.md
    本文件仍沿用文件 5 的分组做法，因为 Agent 里的工具也需要按域管理。

【Agent 是什么】
    一句话：**框架替你跑那个 while 循环**。

    第 4 个文件里我们手写的循环是这样的：
        while 模型还要调工具:
            ai = llm.invoke(messages)
            执行 ai.tool_calls
            把结果塞回 messages
    这个循环就是 Agent 的全部本质。create_agent 只是把它固化下来，
    再顺手加上：记忆、中间件、流式、中断、重试。

    【Java 对照】
        手写循环 ≈ 自己 while(true) 处理一个任务队列
        create_agent ≈ 把这段逻辑交给一个 ExecutorService / 状态机框架：
            你只提交「任务 + 工具集」，框架负责调度、重试、记状态。

【本文件实测结论（DeepSeek，都是跑出来的，不是猜的）】
    · create_agent + DeepSeek：✅ 正常，多工具并行调用正常
    · 判断 agent 里击中哪个能力域：看 messages / 回调，两种都行
    · LLMToolSelectorMiddleware：❌ 直接在 DeepSeek 上 400（内部用 json_schema）
      ✅ 绕过方案：传一个自定义 ChatOpenAI 子类强制 function_calling（见 demo_5）
    · ToolRetryMiddleware：✅ 生效，本文件用「故意失败两次」的工具实测

【运行】
    ./yzy/Scripts/python.exe "aiLearn/tool/6.Agent与工具实战.py"
"""

import os
from pathlib import Path
from typing import Any

import dotenv
from langchain.agents import create_agent
from langchain.agents.middleware import LLMToolSelectorMiddleware, ToolRetryMiddleware
from langchain_core.callbacks import BaseCallbackHandler
from langchain_core.messages import AIMessage
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.memory import InMemorySaver


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
# 工具集：覆盖前面讲的三种类型
# ===========================================================================
# ---- 类型 A：逻辑公式类（见 2.逻辑公式类工具.py）----
@tool
def calc_shipping_fee(weight_kg: float, distance_km: float) -> str:
    """计算快递运费。

    属于【订单】能力域。运费 = 8 元起步价 + 重量*1.5 + 距离*0.1。
    当用户问「运费多少钱」「寄过去要多少邮费」时使用。
    """
    fee = 8 + weight_kg * 1.5 + distance_km * 0.1
    return f"运费：{fee:.2f} 元（重量 {weight_kg}kg，距离 {distance_km}km）"


@tool
def loan_monthly_payment(principal: float, annual_rate: float, months: int) -> str:
    """计算贷款月供（等额本息）。

    属于【金融】能力域。principal 是本金（元），annual_rate 是年利率（如 0.05 表示 5%）。
    当用户问贷款、月供、房贷、分期时使用。
    """
    r = annual_rate / 12
    if r == 0:
        pay = principal / months
    else:
        pay = principal * r * (1 + r) ** months / ((1 + r) ** months - 1)
    return f"月供：{pay:.2f} 元，共 {months} 期，总还款 {pay * months:.2f} 元"


# ---- 类型 B：远程调用类（见 3.远程调用类工具.py）----
# 这里用假数据代替真实 HTTP（真实写法见第 3 个文件），
# 重点是把「远程工具」接进 Agent 之后是什么样子。
@tool
def logistics_track(order_no: str) -> str:
    """查询物流轨迹（远程接口）。

    属于【订单】能力域。调用第三方物流接口查询运输节点。
    当用户问「到哪了」「什么时候到」「快递单号」时使用。
    """
    # 真实场景这里会是 requests.get(...)，要带超时和重试
    return f"订单 {order_no}：已到达【广州转运中心】，预计明天 18:00 前送达"


@tool
def product_stock(product_id: str) -> str:
    """查询商品库存（远程接口）。

    属于【商品】能力域。调用库存中心接口查询可用库存。
    当用户问「还有货吗」「库存多少」时使用。
    """
    return f"商品 {product_id}：可用库存 42 件，仓库 深圳宝安"


# ---- 类型 C：售后域 ----
@tool
def refund_policy() -> str:
    """查询退款政策。

    属于【售后】能力域。当用户问「能退吗」「几天内可以退」「退款规则」时使用。
    """
    return "7 天无理由退货；已拆封需质量问题才能退；退款 3-5 个工作日到账"


ALL_TOOLS = [
    calc_shipping_fee, loan_monthly_payment,
    logistics_track, product_stock,
    refund_policy,
]

# 能力域分组 + 反查表（和文件 5 完全一样的做法）
DOMAINS: dict[str, list] = {
    "订单": [calc_shipping_fee, logistics_track],
    "金融": [loan_monthly_payment],
    "商品": [product_stock],
    "售后": [refund_policy],
}
TOOL_TO_DOMAIN = {
    t.name: domain for domain, tools in DOMAINS.items() for t in tools
}


# ===========================================================================
# 1. 手写循环 vs Agent
# ===========================================================================
def demo_1_why_agent() -> None:
    section("1. 为什么要有 Agent —— 手写循环 vs create_agent")

    print("  第 4 个文件里我们手写的闭环（简化版）：\n")
    print("    messages = [HumanMessage(q)]")
    print("    while True:")
    print("        ai = llm_with_tools.invoke(messages)")
    print("        messages.append(ai)")
    print("        if not ai.tool_calls:      # 模型不再要工具了，结束")
    print("            break")
    print("        for call in ai.tool_calls: # 执行工具")
    print("            result = TOOLS_BY_NAME[call['name']].invoke(call['args'])")
    print("            messages.append(ToolMessage(content=result, tool_call_id=call['id']))")

    print("\n  这段代码有 5 个坑，你自己写迟早要踩：")
    print("    ① 死循环：模型一直调工具怎么办？         → 要加轮数上限")
    print("    ② 工具报错：整个链崩了                   → 要 try/except 转给模型")
    print("    ③ 并行调用：for 循环是串行的，慢          → 要线程池")
    print("    ④ 多轮对话：messages 自己存               → 要 checkpointer")
    print("    ⑤ 想加中间件：没地方插                    → 要 hook 点")

    print("\n  create_agent 就是把上面这些全包了：\n")
    print("    agent = create_agent(")
    print("        model=llm,")
    print("        tools=[...],          # 工具集")
    print("        system_prompt='...',  # 人设")
    print("        checkpointer=InMemorySaver(),  # 多轮记忆")
    print("        middleware=[...],     # 重试/限流/工具筛选")
    print("    )")
    print("    res = agent.invoke({'messages': [{'role': 'user', 'content': q}]})")

    print("\n  【Java 对照】")
    print("     手写循环 ≈ 自己 new Thread + while(true) 消费队列")
    print("     create_agent ≈ 提交给 ExecutorService / 状态机：")
    print("         声明式配置，调度、重试、状态持久化由框架负责")


# ===========================================================================
# 2. 最小可用 Agent
# ===========================================================================
def demo_2_minimal_agent() -> None:
    section("2. 最小可用 Agent（工具自动闭环）")

    agent = create_agent(
        model=build_llm(),
        tools=ALL_TOOLS,
        system_prompt="你是一个电商客服助手。能用工具就先用工具，不要编造数据。",
    )

    q = "订单 SO001 到哪了？顺便算一下 2kg 寄到 300km 外运费多少"
    print(f"  用户: {q}\n")

    res = agent.invoke({"messages": [{"role": "user", "content": q}]})

    print("  完整消息轨迹（这就是 Agent 内部的执行过程）：")
    for m in res["messages"]:
        calls = getattr(m, "tool_calls", None) or []
        if calls:
            print(f"    {type(m).__name__:<12} 要求调: {[c['name'] for c in calls]}")
        else:
            content = str(getattr(m, "content", ""))[:60]
            print(f"    {type(m).__name__:<12} {content}")

    print(f"\n  最终回复: {res['messages'][-1].content[:120]}")

    print("\n  >> 注意两点：")
    print("     ① 我们**一行循环都没写**，工具是框架自动执行的")
    print("     ② 两个工具是**一次性并行**发起的（模型单次返回 2 个 tool_call）")


# ===========================================================================
# 3. Agent 里怎么判断击中哪个能力域
# ===========================================================================
def _hits_from_messages(messages: list) -> list[str]:
    """从消息轨迹里反查击中过哪些域。

    逻辑：找所有 AIMessage 的 tool_calls → 取工具名 → 查反查表。
    """
    hits = []
    for m in messages:
        if isinstance(m, AIMessage):
            for c in m.tool_calls or []:
                hits.append(TOOL_TO_DOMAIN.get(c["name"], "未知"))
    return hits


class DomainHitTracker(BaseCallbackHandler):
    """回调：统计 Agent 里每个能力域被击中几次。"""

    def __init__(self) -> None:
        self.count: dict[str, int] = {}

    def on_tool_start(self, serialized, input_str, **kwargs) -> None:
        name = serialized.get("name", "unknown")
        domain = TOOL_TO_DOMAIN.get(name, "未知")
        self.count[domain] = self.count.get(domain, 0) + 1


def demo_3_domain_hit_in_agent() -> None:
    section("3. Agent 里怎么判断击中哪个能力域")

    print("  6 种手法的通用原理见 5.工具分组与路由判断.py，这里只讲 **agent 场景的差异**。")
    print("  agent 和手写循环最大的不同：工具是框架自动执行的，你看不到那个 `while` 循环。")
    print("  所以最自然的是「事后扫轨迹」和「挂回调」这两种。\n")

    agent = create_agent(model=build_llm(), tools=ALL_TOOLS)
    q = "买的键盘能退吗？另外帮我算算 100 万贷款 30 年、利率 4.5% 的月供"
    print(f"  用户: {q}\n")

    # ---- 招式①：事后看 messages（最省事）----
    res = agent.invoke({"messages": [{"role": "user", "content": q}]})
    hits = _hits_from_messages(res["messages"])
    print(f"  ① 事后扫 messages → 击中能力域: {hits}")
    print("     这是 agent 场景下最常用的一招：返回的 messages 是全量轨迹，")
    print("     里面已经记着每次 tool_calls，扫一遍就得到结果。")

    # ---- 招式②：回调统计（不侵入，能拿到次数）----
    tracker = DomainHitTracker()
    agent.invoke(
        {"messages": [{"role": "user", "content": q}]},
        config={"callbacks": [tracker]},
    )
    print(f"\n  ② 回调统计        → {tracker.count}")
    print("     回调能直接拿到「次数」；扫 messages 拿到的是列表，还要自己计数。")

    print("\n  >> 为什么这里不演示流式事件（astream_events）？")
    print("     能用，agent.astream_events 同样会吐 on_tool_start（见文件 5 的方法③）。")
    print("     但它适合「实时推给前端」，拿来做统计/审计反而绕，所以不重复写。")

    print("\n  >> 两招本质一样：**工具名 → 反查表 → 域名**")
    print("     所以 TOOL_TO_DOMAIN 那张表是关键，必须维护对。")
    print("     用标准 Skill（文件 7）就不用手工建这张表了——")
    print("     工具归属写在 SKILL.md 的 include_tools 里。")


# ===========================================================================
# 4. Agent + 多轮记忆
# ===========================================================================
def demo_4_memory() -> None:
    section("4. Agent 的多轮记忆（thread_id）")

    agent = create_agent(
        model=build_llm(),
        tools=ALL_TOOLS,
        system_prompt="你是电商客服助手，回答简短。",
        checkpointer=InMemorySaver(),
    )

    # thread_id 就是「会话 ID」：同一个 id 的对话共享历史
    cfg_a = {"configurable": {"thread_id": "user-001"}}
    cfg_b = {"configurable": {"thread_id": "user-002"}}

    print("  会话 A（user-001）：先自报家门，第二轮再考它")
    r1 = agent.invoke(
        {"messages": [{"role": "user", "content": "你好，我叫张三，我的订单号是 SO001"}]},
        config=cfg_a,
    )
    print(f"    Q1: 你好，我叫张三，我的订单号是 SO001")
    print(f"    A1: {str(r1['messages'][-1].content)[:70]}")

    r2 = agent.invoke(
        {"messages": [{"role": "user", "content": "我叫什么？订单号是多少"}]},
        config=cfg_a,
    )
    print(f"    Q2: 我叫什么？订单号是多少   ← 考验记忆")
    print(f"    A2: {str(r2['messages'][-1].content)[:90]}")

    print("\n  会话 B（user-002，全新线程）：同样的问题，没有上文")
    r3 = agent.invoke(
        {"messages": [{"role": "user", "content": "我叫什么？订单号是多少"}]},
        config=cfg_b,
    )
    print(f"    Q1: 我叫什么？订单号是多少   ← 一字不差")
    print(f"    A1: {str(r3['messages'][-1].content)[:90]}")

    print("\n  >> thread_id 就是会话隔离的开关：")
    print("     · 同一个 thread_id → 能记住上文")
    print("     · 不同 thread_id   → 完全隔离（B 不知道 A 说过什么）")
    print("  【Java 对照】thread_id ≈ HttpSession 的 sessionId，")
    print("     checkpointer ≈ 把 session 存进 Redis 的那个 Filter。")


# ===========================================================================
# 5. 中间件：工具筛选（含 DeepSeek 绕过方案）
# ===========================================================================
class DeepSeekForStructured(ChatOpenAI):
    """DeepSeek 专用：强制结构化输出走 function_calling。

    【为什么需要这个类】
        langchain 1.4.7 的 LLMToolSelectorMiddleware 内部写死了：
            model.with_structured_output(schema)      # 默认 method='json_schema'
        而 DeepSeek **不支持** response_format=json_schema，会报：
            BadRequestError: This response_format type is unavailable now
        且它没留参数让我们改 method。

        所以只能从「模型对象」这一侧下手：继承 ChatOpenAI，
        把 with_structured_output 的默认 method 改成 function_calling。

    【Java 对照】这就是装饰器模式（Decorator）：
        不改框架源码，包一层子类把行为改掉。
        类似于继承 RestTemplate 重写一个方法，把默认序列化器换成 Fastjson。
    """

    def with_structured_output(self, schema, **kwargs):
        """固定走 function_calling；DeepSeek 只认这条路。"""
        kwargs.setdefault("method", "function_calling")
        return super().with_structured_output(schema, **kwargs)


def demo_5_tool_selector() -> None:
    section("5. 中间件：给 Agent 装「工具筛选器」")

    print("  场景：Agent 挂了 50 个工具，每次全发给模型又贵又不准。")
    print("  LLMToolSelectorMiddleware = 先用模型把工具筛一遍，再交给主模型。\n")

    # ---- 先复现坑 ----
    print("  ① 直接用（默认配置）：")
    try:
        bad = create_agent(
            model=build_llm(),
            tools=ALL_TOOLS,
            middleware=[LLMToolSelectorMiddleware(max_tools=2)],
        )
        bad.invoke({"messages": [{"role": "user", "content": "能退货吗"}]})
        print("     居然成功了（可能是 DeepSeek 侧更新了）")
    except Exception as e:
        print(f"     ❌ {type(e).__name__}")
        print(f"        {str(e)[:150]}")
        print("     原因：中间件内部用 with_structured_output 默认 json_schema，")
        print("           DeepSeek 不支持 → 400")

    # ---- 再给绕过方案 ----
    print("\n  ② 绕过方案：传一个强制 function_calling 的模型给中间件：")
    print("     class DeepSeekForStructured(ChatOpenAI):")
    print("         def with_structured_output(self, schema, **kwargs):")
    print("             kwargs.setdefault('method', 'function_calling')")
    print("             return super().with_structured_output(schema, **kwargs)")
    print()
    print("     再关思考（function_calling 和思考模式冲突，见文件 4）")

    selector_model = DeepSeekForStructured(
        model="deepseek-flash",
        api_key=os.getenv("DEEPSEEK_API_KEY"),
        base_url=os.getenv("DEEPSEEK_API_BASE"),
        extra_body={"thinking": {"type": "disabled"}},
    )

    agent = create_agent(
        model=build_llm(),                      # 主模型：正常开思考
        tools=ALL_TOOLS,
        middleware=[LLMToolSelectorMiddleware(model=selector_model, max_tools=2)],
    )

    r = agent.invoke({"messages": [{"role": "user", "content": "帮我看看订单 SO001 到哪了"}]})
    called = [c["name"] for m in r["messages"] for c in (getattr(m, "tool_calls", None) or [])]
    print(f"\n     ✅ 成功（没有再 400），实际调用的工具: {called}")
    print(f"     最终回复: {str(r['messages'][-1].content)[:100]}")
    print("     注：这里的工具是「筛完剩下的 2 个」里选出来的，不是全部 5 个。")

    print("\n  >> 常用参数：")
    print("     max_tools       最多保留几个工具")
    print("     model           用哪个模型筛选（传小模型可以省钱，这里传的是 DeepSeek 包装类）")
    print("     always_include  永远保留的工具名（比如「查询当前用户」）")
    print("     on_parsing_failure  筛不出来时怎么办：error / none / all / 工具名列表")


# ===========================================================================
# 6. 中间件：工具重试（实测）
# ===========================================================================
_fail_count = {"n": 0}


def demo_6_tool_retry() -> None:
    section("6. 中间件：工具失败自动重试（实测）")

    # 造一个「前两次必失败」的工具
    @tool
    def flaky_express_query(order_no: str) -> str:
        """查询快递轨迹（不稳定接口）。

        属于【订单】能力域。当用户问快递到哪了时使用。
        """
        _fail_count["n"] += 1
        if _fail_count["n"] <= 2:
            raise RuntimeError(f"物流接口超时（第 {_fail_count['n']} 次）")
        return f"订单 {order_no}：已签收"

    print("  工具 flaky_express_query：前 2 次调用故意抛异常，第 3 次才成功。\n")

    # 装重试中间件
    agent = create_agent(
        model=build_llm(extra_body={"thinking": {"type": "disabled"}}),
        tools=[flaky_express_query],
        middleware=[
            ToolRetryMiddleware(
                max_retries=3,          # 最多重试 3 次
                tools=[flaky_express_query],
                on_failure="continue",  # 最终还失败就继续，不崩（把错误交给模型）
                initial_delay=0.1,      # 首次延迟 0.1s（演示用，别让脚本跑太久）
                backoff_factor=1.0,     # 不放大，省时间
                jitter=False,
            )
        ],
    )

    r = agent.invoke({"messages": [{"role": "user", "content": "订单 SO007 到哪了"}]})
    print(f"  工具被调用了 {_fail_count['n']} 次")
    print(f"  最终回复: {str(r['messages'][-1].content)[:120]}")

    print("\n  >> 关键参数：")
    print("     max_retries     最多重试几次")
    print("     backoff_factor  退避倍数（2.0 = 0.5s/1s/2s 这样涨）")
    print("     on_failure      'continue' 把错误交给模型 / 'error' 直接抛")
    print("     生产建议：backoff_factor=2.0 + jitter=True（抖动，避免雪崩）")

    print("\n  >> 其他几个常用中间件（签名已核对，本文件未逐一实测）：")
    rows = [
        ("ToolCallLimitMiddleware", "限制工具调用次数（thread_limit/run_limit）", "防死循环、防刷接口"),
        ("ModelCallLimitMiddleware", "限制模型调用次数", "控成本"),
        ("ToolErrorMiddleware", "自定义工具报错文案", "把 500 转成模型看得懂的话"),
        ("HumanInTheLoopMiddleware", "高危工具执行前人工确认", "取消订单、转账、删数据"),
        ("PIIMiddleware", "脱敏手机号/身份证", "合规"),
        ("SummarizationMiddleware", "历史太长时自动摘要", "长对话控 token"),
        ("ModelFallbackMiddleware", "主模型挂了切备用", "高可用"),
    ]
    print(f"    {'中间件':<28}{'干什么':<34}{'什么时候用'}")
    print("    " + "-" * 84)
    for a, b, c in rows:
        print(f"    {a:<28}{b:<34}{c}")


# ===========================================================================
# 7. 完整实战：把三种工具类型装进一个客服 Agent
# ===========================================================================
def demo_7_full() -> None:
    section("7. 完整实战：电商客服 Agent")

    agent = create_agent(
        model=build_llm(),
        tools=ALL_TOOLS,
        system_prompt=(
            "你是电商客服助手。规则：\n"
            "1. 涉及订单状态/运费/退款，必须先用工具查，不要凭空回答\n"
            "2. 回答简短，不超过 3 句话\n"
            "3. 算钱的工具优先用工具算，不要自己心算"
        ),
        checkpointer=InMemorySaver(),
        middleware=[ToolRetryMiddleware(max_retries=2, initial_delay=0.1, backoff_factor=1.0)],
    )

    cfg = {"configurable": {"thread_id": "vip-001"}, "callbacks": [DomainHitTracker()]}
    tracker = cfg["callbacks"][0]

    dialog = [
        "我上周买的键盘能退吗？",
        "那帮我看看订单 SO001 到哪了",
        "顺便算下这台键盘 1.2kg 寄回深圳 800km 运费多少",
    ]

    # ⚠️ agent 返回的 messages 是「全量历史」，不是本轮的增量。
    #    想统计「本轮」击中了什么，必须自己记住上一轮的长度再切片。
    seen = 0
    for q in dialog:
        print(f"  用户: {q}")
        r = agent.invoke({"messages": [{"role": "user", "content": q}]}, config=cfg)
        answer = str(r["messages"][-1].content).replace("\n", " ")
        print(f"  客服: {answer[:150]}")
        new_messages = r["messages"][seen:]      # 只取本轮新增的消息
        seen = len(r["messages"])
        hit = _hits_from_messages(new_messages)
        print(f"        （本轮新增消息 {len(new_messages)} 条，击中能力域: {hit or '无'}）\n")

    print(f"  整通对话累计击中: {tracker.count}")
    print("\n  >> 这一套就是生产级 Agent 的骨架：")
    print("     工具（三类） + 能力域分组 + 路由可观测 + 记忆 + 重试 + 系统提示词约束")


# ===========================================================================
# 8. 总结
# ===========================================================================
def demo_8_summary() -> None:
    section("8. 整套工具体系的选型清单")

    print("  【工具定义怎么选】")
    print("    简单函数 + 有类型注解   → @tool（90% 场景够用）")
    print("    要自定义校验/复用到多处 → StructuredTool.from_function")
    print("    需要状态/复杂逻辑       → 继承 BaseTool")
    print("    一组相关工具            → BaseToolkit / 字典分组（能力域）")

    print("\n  【工具类型怎么设计】")
    print("    逻辑公式类 → 纯函数，别放网络/IO，可直接单测")
    print("    远程调用类 → 必带超时 + 重试 + 4xx 不重试/5xx 重试 + 结果裁剪")
    print("    能力域     → 描述里写明「属于哪个域、什么时候用、什么时候别用」")

    print("\n  【能力域路由怎么判断】")
    print("    < 10 个工具  → 平铺 + 看 tool_calls")
    print("    10~30 个     → 分组 + 回调埋点")
    print("    > 30 个      → 两级路由 / LLMToolSelectorMiddleware")
    print("    要 100% 可控 → tool_choice 强制指定")

    print("\n  【DeepSeek 专属坑（本组实测，务必记住）】")
    print("    ① with_structured_output 必须 method='function_calling'")
    print("    ② function_calling / 强制 tool_choice 必须关思考")
    print("       extra_body={'thinking': {'type': 'disabled'}}")
    print("    ③ 但 bind_tools + tool_choice='auto' 可以开思考，不冲突")
    print("    ④ LLMToolSelectorMiddleware 要配自定义 ChatOpenAI 子类才能用")

    print("\n  【三条工程经验】")
    print("    ① 工具描述是**模型唯一的决策依据**，比代码本身更重要")
    print("    ② 有副作用的工具（取消、退款、转账）一定要人工确认")
    print("    ③ 每次路由判断都要**留日志**，否则线上出问题无从查起")


def main() -> None:
    print("6. Agent 与工具实战（DeepSeek + 最新 API）")

    demo_1_why_agent()

    if not os.getenv("DEEPSEEK_API_KEY"):
        print("\n⚠️ 没读到 DEEPSEEK_API_KEY，跳过需要调模型的演示。.env 路径：", _ENV_PATH)
        return

    demo_2_minimal_agent()
    demo_3_domain_hit_in_agent()
    demo_4_memory()
    demo_5_tool_selector()
    demo_6_tool_retry()
    demo_7_full()
    demo_8_summary()

    print("\n" + "=" * 62)
    print("tool 组全部示例执行完毕。")
    print("建议顺序：1 定义 → 2 公式 → 3 远程 → 4 绑定 → 5 分组路由 → 6 Agent → 7 Skill 标准")


if __name__ == "__main__":
    main()
