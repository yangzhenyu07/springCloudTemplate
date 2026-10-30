#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
5. 人机协同 interrupt：跑到一半停下来等人
=========================================
【Python 语法看不懂？】闭包、lambda、** 解包、推导式等见 ../PYTHON_SYNTAX.md


═══════════════════════════════════════════════════════════════
【什么时候你会需要这一节】
═══════════════════════════════════════════════════════════════

  这是 LangGraph 相对「一条链跑到底」最本质的区别。真实业务里到处是这种需求：

    · 高危操作前要人工确认   —— 取消订单、退款、转账、删数据、发公告
    · 信息不全要用户补充     —— 表单缺字段、地址不完整、需求太模糊
    · 半自动审批流           —— AI 起草 → 主管审批 → 执行
    · 多轮表单填写           —— 一次问一个问题，答完继续
    · 让用户选分支           —— 「要 A 方案还是 B 方案？」

  LCEL 管道做不到这些，因为它一旦跑起来就停不下来。
  图的「可暂停 / 可恢复」才是它区别于普通函数链的核心能力。

═══════════════════════════════════════════════════════════════
机制：interrupt 是用「异常」实现的
═══════════════════════════════════════════════════════════════

  你在节点里调 interrupt(payload)，实际发生的是：

    ① 引擎抛一个内部异常，把整个图**就地冻住**
    ② 当前状态存进 checkpointer（所以**必须配 checkpointer**）
    ③ 把 payload 交给调用方（你的后端 / 前端）
    ④ 调用方拿到人给的答案后，用 Command(resume=答案) 重新 invoke
    ⑤ 引擎**从那个节点的开头重新执行**，interrupt() 这次直接返回答案

  ⚠️ 第 ⑤ 步是重点：**节点会被重跑一遍**。
     这就带来本节最重要的一个坑（demo_3 会实测给你看）。

【Java 对照】

    interrupt ≈ 工作流引擎的「用户任务（User Task）」
                Activiti 里画一个 UserTask，引擎就停在那里等 complete()
                区别：LangGraph 的「任务」是代码里一行 interrupt()，不用画

    checkpoint ≈ 流程实例表（ACT_RU_TASK / ACT_RU_EXECUTION）
                 引擎靠它知道「这个流程停在哪个节点、变量是什么」

    Command(resume=...) ≈ taskService.complete(taskId, variables)

【运行】
    ./yzy/Scripts/python.exe "aiLearn/langGraph/5.人机协同interrupt.py"

    本文件不调模型，零成本。
"""

from typing import TypedDict

from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command, interrupt


def section(title: str) -> None:
    print("\n" + "=" * 62)
    print(title)
    print("=" * 62)


# ═══════════════════════════════════════════════════════════════
# 1. 最小可用：高危操作前人工确认
# ═══════════════════════════════════════════════════════════════


class RefundState(TypedDict):
    order_no: str
    amount: float
    approver: str      # 谁批的
    result: str        # 最终结果


def demo_1_minimal() -> None:
    section("1. 最小可用：退款前停下来等人批")

    print("  流程：propose（准备退款单）→ approve（等人批）→ execute（执行）\n")

    def propose(state: RefundState) -> dict:
        """准备阶段：查订单、算金额。这步可以自动做。"""
        print(f"     [propose] 查到订单 {state['order_no']}，金额 {state['amount']} 元")
        return {}

    def approve(state: RefundState) -> dict:
        """审批节点：在这里停下来等人。

        interrupt 的返回值 = 调用方 resume 时传进来的值。
        第一次执行到这一行会「冻住」，整个函数在这里中断。
        """
        decision = interrupt({
            "type": "approval",
            "order_no": state["order_no"],
            "amount": state["amount"],
            "question": f"确认给订单 {state['order_no']} 退 {state['amount']} 元吗？",
            # 实际项目里这里会带上审批单 ID、跳转链接、可选操作等
        })
        # ↓ 下面这行只有在 resume 之后才会执行
        return {"approver": decision.get("by", "未知"), "result": "已批准" if decision.get("ok") else "已驳回"}

    def execute(state: RefundState) -> dict:
        """执行阶段：真正动钱。"""
        if state["result"] == "已批准":
            print(f"     [execute] 执行退款 {state['amount']} 元（审批人：{state['approver']}）")
        else:
            print("     [execute] 已驳回，不执行")
        return {}

    builder = StateGraph(RefundState)
    builder.add_node("propose", propose)
    builder.add_node("approve", approve)
    builder.add_node("execute", execute)
    builder.add_edge(START, "propose")
    builder.add_edge("propose", "approve")
    builder.add_edge("approve", "execute")
    builder.add_edge("execute", END)

    # ⚠️ 必须配 checkpointer，否则中断后状态没地方存，resume 会报错
    app = builder.compile(checkpointer=InMemorySaver())
    cfg = {"configurable": {"thread_id": "refund_001"}}

    print("  ── 第一次调用：跑到 approve 就停住 ──")
    r1 = app.invoke({"order_no": "SO001", "amount": 299.0, "approver": "", "result": ""}, cfg)
    print(f"     返回的 state: { {k: v for k, v in r1.items() if k != '__interrupt__'} }")

    # 中断信息在这里
    state = app.get_state(cfg)
    print(f"     引擎停在: {state.next}   ← 下一步要执行的节点")
    for it in state.interrupts:
        print(f"     待处理中断: {it.value}")

    print("\n  ── 后端把上面的 value 丢给前端 / 审批系统，人点了「同意」 ──")
    r2 = app.invoke(Command(resume={"ok": True, "by": "张主管"}), cfg)
    print(f"     最终 state: {r2}")
    print(f"     还有待处理中断吗: {app.get_state(cfg).interrupts}")

    print("\n  >> 三个关键点：")
    print("     ① interrupt 的**返回值**就是 resume 传进来的东西，类型随便（dict 也行）")
    print("     ② 暂停期间进程可以退出，只要有 checkpointer 就能恢复")
    print("     ③ resume 之后引擎从**那个节点的开头**重跑（见 demo_3）")


# ═══════════════════════════════════════════════════════════════
# 2. ⚠️ 坑一：不配 checkpointer 就恢复不了
# ═══════════════════════════════════════════════════════════════


class SimpleState(TypedDict):
    x: str


def demo_2_need_checkpointer() -> None:
    section("2. ⚠️ 坑一：没 checkpointer 就 resume 不了")

    def ask(state: SimpleState) -> dict:
        return {"x": str(interrupt("确认吗？"))}

    builder = StateGraph(SimpleState)
    builder.add_node("ask", ask)
    builder.add_edge(START, "ask")
    builder.add_edge("ask", END)

    # 故意不配 checkpointer
    app = builder.compile()

    r1 = app.invoke({"x": ""})
    print(f"  第一次调用（没配 checkpointer）：")
    print(f"     返回: { {k: v for k, v in r1.items() if k != '__interrupt__'} }")
    print("     注意：**没报错**，也返回了 __interrupt__，看着好像成功了")

    try:
        app.invoke(Command(resume="yes"))
        print("     resume 居然成功了？")
    except Exception as e:
        print(f"\n  resume 时：{type(e).__name__}: {str(e)[:70]}")

    print("\n  >> 这个坑很阴：第一次调用不报错，你在测试环境可能觉得没问题，")
    print("     上线后到 resume 环节才炸。")
    print("\n     **规律：只要用了 interrupt，compile 时就必须给 checkpointer。**")
    print("     生产上换成持久化的（见 memory/3 和 memory/7）：")
    print("        SqliteSaver / PostgresSaver / RedisSaver")


# ═══════════════════════════════════════════════════════════════
# 3. ⚠️⚠️ 最重要的坑：恢复时节点会重跑
# ═══════════════════════════════════════════════════════════════


class RetryState(TypedDict):
    msg: str


def demo_3_node_rerun() -> None:
    section("3. ⚠️⚠️ 最重要的坑：resume 时节点会从头重跑")

    print("  这是 interrupt 最容易出事的地方，也是很多人线上事故的根源。\n")

    # 用一个计数器模拟「有副作用」的操作（发短信 / 写库 / 扣款）
    counter = {"sms_sent": 0}

    def bad_node(state: RetryState) -> dict:
        # ❌ 危险：interrupt 之前就干了有副作用的事
        counter["sms_sent"] += 1
        print(f"     [bad_node 第 {counter['sms_sent']} 次执行] 已经发了确认短信")

        decision = interrupt("这条短信已发出，确认继续吗？")
        return {"msg": f"用户答复={decision}"}

    builder = StateGraph(RetryState)
    builder.add_node("bad_node", bad_node)
    builder.add_edge(START, "bad_node")
    builder.add_edge("bad_node", END)
    app = builder.compile(checkpointer=InMemorySaver())
    cfg = {"configurable": {"thread_id": "rerun"}}

    print("  ── 第一次 invoke ──")
    app.invoke({"msg": ""}, cfg)
    print(f"     短信发送次数: {counter['sms_sent']}")

    print("\n  ── 人工确认，resume ──")
    app.invoke(Command(resume="继续"), cfg)
    print(f"     短信发送次数: {counter['sms_sent']}   ← 发送了两次！")

    print("\n  >> 原因：interrupt 是用异常实现的。resume 时引擎**重新执行整个节点**，")
    print("     从函数第一行开始跑，跑到 interrupt() 时直接拿到已存好的答案继续。")
    print("     所以 interrupt **之前**的代码被执行了两遍。")
    print("\n     这在真实业务里意味着：")
    print("       · 重复发短信 / 重复发邮件")
    print("       · 重复扣款")
    print("       · 重复写数据库（没有唯一约束就变成两条）")
    print("       · 重复调第三方接口（产生费用）")

    # ---- 正确写法 A：副作用放到 interrupt 之后 ----
    print("\n  ── ✅ 正确写法 A：把副作用挪到 interrupt 之后 ──")

    counter2 = {"sms_sent": 0}

    def good_node(state: RetryState) -> dict:
        # interrupt 之前只做「无副作用」的准备：读数据、算参数、拼内容
        decision = interrupt("确认给他发确认短信吗？")
        if decision == "继续":
            # interrupt 之后才真正动手
            counter2["sms_sent"] += 1
            print(f"     [good_node] 现在才发短信（第 {counter2['sms_sent']} 次）")
        return {"msg": f"用户答复={decision}"}

    b2 = StateGraph(RetryState)
    b2.add_node("good_node", good_node)
    b2.add_edge(START, "good_node")
    b2.add_edge("good_node", END)
    app2 = b2.compile(checkpointer=InMemorySaver())
    cfg2 = {"configurable": {"thread_id": "good"}}

    app2.invoke({"msg": ""}, cfg2)
    print(f"     第一次后：短信发送 {counter2['sms_sent']} 次")
    app2.invoke(Command(resume="继续"), cfg2)
    print(f"     resume 后：短信发送 {counter2['sms_sent']} 次  ✅ 只有一次")

    # ---- 正确写法 B：拆成两个节点 ----
    print("\n  ── ✅ 正确写法 B：拆成「执行 → 审批」两个节点 ──")
    print("")
    print("     def do_dangerous(state):        # 副作用在这里")
    print("         return {'done': True, 'txn_id': new_txn()}")
    print("")
    print("     def ask_confirm(state):         # 纯粹问一句，无副作用")
    print("         return {'ok': interrupt('确认吗？')}")
    print("")
    print("     START → do_dangerous → ask_confirm → ...")
    print("")
    print("     这种更好：职责清晰，而且「已执行」这个事实在 resume 后不会变。")

    print("\n  >> 一句话记住：")
    print("     **interrupt 之前只能是「幂等的只读操作」。**")
    print("     要写、要发、要扣钱，一律放在 interrupt 之后，或者另起一个节点。")


# ═══════════════════════════════════════════════════════════════
# 4. 多个 interrupt：一次问一个问题
# ═══════════════════════════════════════════════════════════════


class FormState(TypedDict):
    name: str
    age: str
    city: str
    done: bool


def demo_4_multiple_interrupts() -> None:
    section("4. 多个 interrupt：像多轮表单一样一问一答")

    print("  一个节点里可以有多个 interrupt，按顺序依次暂停。")
    print("  每次 resume 就往下走一步，非常适合「一次只问一个问题」的引导式填写。\n")

    def collect(state: FormState) -> dict:
        # 每次 resume 都会重跑这个节点，但已答过的 interrupt 会直接返回存好的值，
        # 所以只会「推进到下一个未答的问题」。
        name = interrupt("请问您的姓名？")
        print(f"     [collect] 拿到姓名: {name}")

        age = interrupt(f"您好 {name}，请问年龄？")
        print(f"     [collect] 拿到年龄: {age}")

        city = interrupt(f"{age} 岁，请问所在城市？")
        print(f"     [collect] 拿到城市: {city}")

        return {"name": name, "age": age, "city": city, "done": True}

    builder = StateGraph(FormState)
    builder.add_node("collect", collect)
    builder.add_edge(START, "collect")
    builder.add_edge("collect", END)
    app = builder.compile(checkpointer=InMemorySaver())
    cfg = {"configurable": {"thread_id": "form_1"}}

    app.invoke({"name": "", "age": "", "city": "", "done": False}, cfg)

    answers = ["张三", "31", "广州"]
    for i, ans in enumerate(answers, 1):
        st = app.get_state(cfg)
        question = st.interrupts[0].value if st.interrupts else "(没有待答问题)"
        print(f"  第 {i} 问: {question}")
        result = app.invoke(Command(resume=ans), cfg)
        print(f"  第 {i} 答: {ans}")

    print(f"\n  最终 state: {result}")

    print("\n  >> 机制细节：")
    print("     resume 时节点从头重跑，第 1 个 interrupt 直接返回 '张三'（存在 checkpoint 里）")
    print("     第 2 个 interrupt 直接返回 '31'…… 直到遇到**第一个没有答案的** interrupt 才停下")
    print("     所以你看到的 print 会重复出现，这是正常的，不是 bug")

    print("\n  ⚠️ 但带来一个约束：")
    print("     多个 interrupt 时，前面已经答过的内容**必须来自 interrupt 的返回值**，")
    print("     不能是「重跑时重新算出来的」——因为重跑会重新算，可能和上次不一样。")
    print("     所以：interrupt 之前的逻辑必须**确定性**（同样的 state 进来，同样的结果）。")


# ═══════════════════════════════════════════════════════════════
# 5. 配合 stream：停下来的时候怎么感知
# ═══════════════════════════════════════════════════════════════


def demo_5_with_stream() -> None:
    section("5. 配合 stream：中断在流里怎么表现")

    def ask(state: SimpleState) -> dict:
        return {"x": str(interrupt({"need": "approval"}))}

    builder = StateGraph(SimpleState)
    builder.add_node("ask", ask)
    builder.add_edge(START, "ask")
    builder.add_edge("ask", END)
    app = builder.compile(checkpointer=InMemorySaver())
    cfg = {"configurable": {"thread_id": "stream_test"}}

    print("  用 stream 跑，中断会作为特殊事件出现：\n")
    for chunk in app.stream({"x": ""}, cfg, stream_mode="updates"):
        print(f"     {chunk}")

    print("\n  >> 键名是 '__interrupt__'，值是 Interrupt 对象列表。")
    print("     后端典型处理：")
    print("       for chunk in app.stream(...):")
    print("           if '__interrupt__' in chunk:")
    print("               return 前端需要渲染的审批卡片")
    print("           else:")
    print("               SSE 推一段进度")

    print("\n  >> 恢复也可以用 stream，接着看后续事件：")
    for chunk in app.stream(Command(resume="ok"), cfg, stream_mode="updates"):
        print(f"     {chunk}")


# ═══════════════════════════════════════════════════════════════
# 6. 生产形态：这套东西在真实系统里长什么样
# ═══════════════════════════════════════════════════════════════


def demo_6_production_shape() -> None:
    section("6. 生产形态：一个 AI 审批流的完整骨架")

    print("  真实项目里不会是「脚本里调两次 invoke」，而是这样分工：\n")

    print("  ┌─ 后端服务 ─────────────────────────────────────┐")
    print("  │  POST /tickets                                │")
    print("  │    ① 建 thread_id（= 业务单据号，别用随机 UUID）│")
    print("  │    ② app.invoke(input, config)                │")
    print("  │    ③ 如果返回里有 __interrupt__：              │")
    print("  │         把 interrupt.value 存进「待办表」      │")
    print("  │         返回 202 + 待办链接给前端              │")
    print("  │    ④ 否则直接返回结果                          │")
    print("  │                                                │")
    print("  │  POST /tickets/{id}/approve                   │")
    print("  │    ① 校验权限（谁能批）                        │")
    print("  │    ② 幂等校验（这个待办是否已批过）            │")
    print("  │    ③ app.invoke(Command(resume=...), config)  │")
    print("  │    ④ 可能又碰到下一个 interrupt → 回到③的循环 │")
    print("  └────────────────────────────────────────────────┘")

    print("\n  【三个工程要点】")
    print("     ① thread_id 用业务单号，不要每次生成新的")
    print("        用新的 = 每次都从零开始，等于没存状态")
    print("     ② 审批接口必须幂等")
    print("        用户手抖点两次 approve，不能扣两次钱")
    print("        用 checkpoint_id 或自己的一张表做幂等键")
    print("     ③ 在 interrupt 里放足够的信息，让审批人不用查库")
    print("        {type, order_no, amount, risk_score, 历史记录摘要, 可选操作}")

    print("\n  【和 tool/6 的 HumanInTheLoopMiddleware 什么关系】")
    print("     那个中间件就是把这套东西封装好了，专门用于「工具执行前确认」。")
    print("     它的做法是：在工具调用前自动调 interrupt()。")
    print("     如果你只是要给某个工具加确认，直接用中间件；")
    print("     如果流程里有自定义的多步审批，就自己用 interrupt 搭。")

    print("\n  【checkpointer 怎么选】")
    rows = [
        ("本地调试 / 单测", "InMemorySaver", "重启就没了，但够用"),
        ("单机部署", "SqliteSaver", "一个文件，零运维"),
        ("多实例生产", "PostgresSaver", "必须，否则 A 实例的中断 B 恢复不了"),
        ("要 TTL 自动过期", "RedisSaver", "审批单放久了自动清"),
    ]
    print(f"     {'场景':<20}{'用什么':<18}{'为什么'}")
    print("     " + "-" * 74)
    for a, b, c in rows:
        print(f"     {a:<20}{b:<18}{c}")


# ═══════════════════════════════════════════════════════════════
# 7. 小结
# ═══════════════════════════════════════════════════════════════


def demo_7_summary() -> None:
    section("7. 小结")

    print("  【怎么用】")
    print("     节点里：value = interrupt(payload)   ← 停住，payload 交给调用方")
    print("     调用方：app.invoke(Command(resume=答案), config)  ← 继续")
    print("     看中断：app.get_state(config).interrupts")

    print("\n  【两条铁律】")
    print("     ① 用了 interrupt 就必须配 checkpointer，否则 resume 报 RuntimeError")
    print("     ② interrupt 之前的代码必须**无副作用**（因为 resume 会重跑一遍）")

    print("\n  【一个设计建议】")
    print("     能用 HumanInTheLoopMiddleware 就别手写 interrupt；")
    print("     只有「多步审批 / 自定义表单 / 条件分支」才自己搭图。")

    print("\n  最后一个文件：6.拆开create_agent.py")
    print("     到这里图的基本部件全学完了，去看看你一直在用的 create_agent 到底长什么样。")


def main() -> None:
    print("5. 人机协同 interrupt")
    print("   本文件不调模型，零成本")

    demo_1_minimal()
    demo_2_need_checkpointer()
    demo_3_node_rerun()
    demo_4_multiple_interrupts()
    demo_5_with_stream()
    demo_6_production_shape()
    demo_7_summary()

    print("\n" + "=" * 62)
    print("全部示例执行完毕。")


if __name__ == "__main__":
    main()
