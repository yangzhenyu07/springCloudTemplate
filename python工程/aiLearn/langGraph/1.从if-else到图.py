#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
1. 从 if-else 到图：三个概念
============================
【Python 语法看不懂？】闭包、lambda、** 解包、推导式等见 ../PYTHON_SYNTAX.md


═══════════════════════════════════════════════════════════════
先说【什么时候你会需要 LangGraph】
═══════════════════════════════════════════════════════════════

先看一段真实项目里最常见的 Python 代码 —— 它往往是一个客服 / 审批 / 数据处理
系统的早期形态：

    def handle(text):
        if "退款" in text:
            r = refund(text)
            if r["ok"]:
                notify(r)
            else:
                retry(3)                 # 重试几次
        elif "物流" in text:
            info = track(text)
            answer(info)
        else:
            answer("我不太明白")

   问题不在「能不能跑」，问题在这四条：

     ① 流程散落在 if-else 里，**画不出来**
        新人接手只能一行行读代码，还得在脑子里连成流程图。

     ② 想加「人工审批」「断点续跑」「重试」得在每一层加代码
        而且每加一个能力，所有分支都要改一遍。

     ③ 想并行跑两个分支，得自己上线程池
        然后开始处理线程安全、超时、部分失败。

     ④ 跑到一半挂了，只能从头再来
        前面的模型调用白花钱。

   LangGraph 干的事就一句话：
      **把这段 if-else 显式画成一张图，交给一个引擎去跑。**
   流程变成数据结构（可画、可存、可暂停），而不是控制流（只能读代码）。

   代价是：要写的东西更啰嗦了。所以它**不是所有场景都该用**，
   什么时候不该用，见本目录 README.md 的判断表。

═══════════════════════════════════════════════════════════════
三个概念（整个 LangGraph 就这三个 + 一个编译动作）
═══════════════════════════════════════════════════════════════

    State（状态）
        一个 TypedDict，图里所有节点共享。它是唯一的「数据载体」。

    Node（节点）
        一个**普通 Python 函数**：入参是 state，出参是「要更新的字段」。

    Edge（边）
        连线，决定下一步跑谁。分两种：
          固定边   add_edge("a", "b")      永远 a → b
          条件边   add_conditional_edges() 看 state 决定去哪

    compile()
        把上面的「定义」变成一个可执行对象（CompiledStateGraph）。

═══════════════════════════════════════════════════════════════
⚠️ 最容易误解的一条：节点返回的不是「新状态」，是「状态补丁」
═══════════════════════════════════════════════════════════════

        def my_node(state):
            return {"n": state["n"] + 1}     # ← 只返回要改的字段
            # 不是 return new_state            错的

    引擎拿到这个 dict，按 key 合并进全局 state。
    没返回的字段保持原样。这就是「部分更新」（partial update）。

    这个设计的好处：并行节点各写各的字段，互不冲突（前提是字段不重叠）。

【Java 对照】

    | LangGraph      | Java 里对应什么                              |
    |----------------|--------------------------------------------|
    | State          | Camel 的 Exchange / 一个可变的 Context 对象   |
    | Node           | 一个 Processor / Handler（无状态，靠入参）    |
    | Edge           | 路由规则（Camel 的 choice/when、Spring 的 Router）|
    | compile()      | 把配置编译成可执行的 ProcessDefinition        |
    | 整个东西        | Spring StateMachine / Activiti / Camel Route |
    |                | 区别：节点里可以调 LLM，可以随时暂停等人      |

    如果你用过 Activiti / Flowable，心智模型几乎一样：
        你画 BPMN（这里用代码画）→ 部署 → 引擎按定义跑 → 每步留痕。
    只是 LangGraph 的「表单」「网关」换成了 Python 函数。

【运行】
    ./yzy/Scripts/python.exe "aiLearn/langGraph/1.从if-else到图.py"

    本文件不调模型，零成本，随便跑。
"""

from typing import TypedDict

from langgraph.graph import END, START, StateGraph

# ═══════════════════════════════════════════════════════════════
# 1. 先看「原来的写法」有多难受
# ═══════════════════════════════════════════════════════════════


def demo_1_the_old_way() -> None:
    """不调模型，纯演示 if-else 版本的问题。"""

    print("=" * 62)
    print("1. 原来的写法：一个函数包住所有分支")
    print("=" * 62)

    # ---- 模拟几个业务函数（真实项目里就是调模型 / 调接口）----
    def classify(text: str) -> str:
        if "退款" in text:
            return "refund"
        if "物流" in text:
            return "logistics"
        return "other"

    def do_refund(text: str) -> str:
        return f"[退款] 已受理：{text}"

    def do_logistics(text: str) -> str:
        return f"[物流] 已查询：{text}"

    def do_other(text: str) -> str:
        return f"[兜底] 转人工：{text}"

    # ---- 这是要重构的那段代码 ----
    def handle(text: str) -> str:
        kind = classify(text)
        if kind == "refund":
            return do_refund(text)
        elif kind == "logistics":
            return do_logistics(text)
        else:
            return do_other(text)

    for q in ["我要退款", "我的快递到哪了", "你好"]:
        print(f"  输入: {q:<14} → {handle(q)}")

    print("\n  【问题不在结果，在这段代码的形状】")
    print("   · classify 的结果是字符串，写错了（比如拼成 'refnd'）编译期不报错，跑起来才炸")
    print("   · 三个分支的返回值混在一起，想给每个分支加日志得改三处")
    print("   · 流程只存在于这段代码里，**没有任何结构化的表示**")
    print("   · 想知道「刚才跑到哪一步了」，只能靠 print")
    print("   · 想加一个「退款前先确认」的人工环节 → 整个函数要改成 async + 状态机")


# ═══════════════════════════════════════════════════════════════
# 2. 同一件事，用图写
# ═══════════════════════════════════════════════════════════════


class TicketState(TypedDict):
    """图的状态。

    就一个 TypedDict，所有节点共享。字段就是你「要沿着流程传下去的东西」。

    【Java 对照】相当于定义一个 Context / Exchange 类：
        class TicketContext { String text; String kind; String answer; }
    区别：Python 这里只是类型提示，运行时就是 dict，不需要 getter/setter。
    """

    text: str        # 用户输入
    kind: str        # 分类结果
    answer: str      # 最终答复
    trace: list[str] # 走过的节点名（演示用，方便看轨迹）


# ---- 节点：每个都是普通函数，入参 state，出参「补丁」 ----
def node_classify(state: TicketState) -> dict:
    """分类节点。

    注意返回值：只返回 kind 和 trace 两个字段。
    text 不动，引擎会自动保留。
    """
    text = state["text"]
    if "退款" in text:
        kind = "refund"
    elif "物流" in text or "快递" in text:
        kind = "logistics"
    else:
        kind = "other"
    return {"kind": kind, "trace": state["trace"] + ["classify"]}


def node_refund(state: TicketState) -> dict:
    return {"answer": f"[退款] 已受理：{state['text']}",
            "trace": state["trace"] + ["refund"]}


def node_logistics(state: TicketState) -> dict:
    return {"answer": f"[物流] 已查询：{state['text']}",
            "trace": state["trace"] + ["logistics"]}


def node_other(state: TicketState) -> dict:
    return {"answer": f"[兜底] 转人工：{state['text']}",
            "trace": state["trace"] + ["other"]}


def route_by_kind(state: TicketState) -> str:
    """路由函数（条件边用）。

    它不修改状态，只回答一个问题：**下一步去哪个节点**。
    返回值必须是 add_conditional_edges 里注册过的 key。

    【Java 对照】这就是个纯路由（Camel 的 choice/when），
    只做判断不做业务。
    """
    # state["kind"] 已经是 classify 写进去的值，直接当路由 key 用
    return state["kind"]


def demo_2_the_graph_way() -> None:
    """同一个业务，改用图。"""

    print("\n" + "=" * 62)
    print("2. 图版本：State + Node + Edge")
    print("=" * 62)

    # ① 建图，指定状态类型
    builder = StateGraph(TicketState)

    # ② 加节点：名字 → 函数
    builder.add_node("classify", node_classify)
    builder.add_node("refund", node_refund)
    builder.add_node("logistics", node_logistics)
    builder.add_node("other", node_other)

    # ③ 连边
    builder.add_edge(START, "classify")          # 固定边：从入口进 classify
    builder.add_conditional_edges(
        "classify",                               # 从哪个节点出发
        route_by_kind,                            # 用哪个函数判断
        {                                         # 返回值 → 目标节点
            "refund": "refund",
            "logistics": "logistics",
            "other": "other",
        },
    )
    builder.add_edge("refund", END)               # 三个分支都到出口
    builder.add_edge("logistics", END)
    builder.add_edge("other", END)

    # ④ 编译。这一步会把上面所有定义校验一遍（节点名写错会在这里报）
    app = builder.compile()

    for q in ["我要退款", "我的快递到哪了", "你好"]:
        result = app.invoke({"text": q, "kind": "", "answer": "", "trace": []})
        print(f"  输入: {q:<14} → {result['answer']}")
        print(f"  {'':14}   轨迹: {' → '.join(result['trace'])}")

    print("\n  【同样的业务，图版本多了什么】")
    print("   · 流程变成数据结构：可以画图、可以存库、可以传给前端渲染")
    print("   · 每个节点可以单独测试：app.nodes['refund'] 就是个函数，直接调")
    print("   · 加日志只改一处（在引擎层挂中间件，见文件 6）")
    print("   · 能随时暂停等人（见文件 5），能并行（见文件 4）")

    return app   # 返回给下一个 demo 用


# ═══════════════════════════════════════════════════════════════
# 3. 把「图」画出来 —— 这是最直观的一步
# ═══════════════════════════════════════════════════════════════


def demo_3_draw(graph) -> None:
    print("\n" + "=" * 62)
    print("3. 把图打印出来（Mermaid 格式，粘到支持 Mermaid 的地方就能看）")
    print("=" * 62)

    mermaid = graph.get_graph().draw_mermaid()
    for line in mermaid.splitlines():
        print("  " + line)

    print("\n  >> 这就是「流程变成数据结构」的直接证据：")
    print("     同一张图你还能 draw_mermaid_png() 存成图片、")
    print("     或者 get_graph().nodes / .edges 拿到结构化数据，")
    print("     丢给前端做可视化编排界面。")
    print("\n     如果这里画出来的图和你脑子里想的不一样 —— 说明代码写错了，")
    print("     这就是图比 if-else 强的地方：**流程可验证**。")


# ═══════════════════════════════════════════════════════════════
# 4. 每一步都看得见（图的杀手锏）
# ═══════════════════════════════════════════════════════════════


def demo_4_stream_each_step(app) -> None:
    print("\n" + "=" * 62)
    print("4. stream：看引擎每一步在干什么")
    print("=" * 62)

    print("  invoke 只给你最终结果，看不到中间过程。用 stream 就能逐步看：\n")
    print("  for chunk in app.stream(input, stream_mode='updates'):")
    print("      print(chunk)\n")

    for chunk in app.stream(
        {"text": "我要退款", "kind": "", "answer": "", "trace": []},
        stream_mode="updates",
    ):
        # updates 模式：每个节点跑完后吐一次 {节点名: 它返回的补丁}
        for node_name, patch in chunk.items():
            print(f"  节点 [{node_name:<10}] 返回补丁: {patch}")

    print("\n  >> 注意每一条都是一个节点的**增量**，不是全量状态。")
    print("     这个模式非常适合做「执行进度」推给前端：")
    print("       收到 classify → 显示「识别意图中…」")
    print("       收到 refund   → 显示「正在办理退款…」")

    print("\n  另一种模式 values（每次吐全量快照）：")
    for chunk in app.stream(
        {"text": "我的快递到哪了", "kind": "", "answer": "", "trace": []},
        stream_mode="values",
    ):
        print(f"    trace={chunk['trace']}  answer={chunk['answer'][:24]!r}")

    print("\n  >> values 适合「调试时看状态怎么变」，updates 适合「做进度条」。")
    print("     更多模式（messages / custom / debug）见文件 6。")


# ═══════════════════════════════════════════════════════════════
# 5. 节点能单独测 —— 这是工程上最实在的好处
# ═══════════════════════════════════════════════════════════════


def demo_5_testable() -> None:
    print("\n" + "=" * 62)
    print("5. 节点可以脱离图单独测（工程上最实在的好处）")
    print("=" * 62)

    print("  节点就是普通函数，直接调就行，不需要建图、不需要跑引擎：\n")

    fake_state = {"text": "我要退款", "kind": "", "answer": "", "trace": []}
    out = node_classify(fake_state)
    print(f"    node_classify({{'text': '我要退款'}}) → {out}")

    out2 = node_refund({**fake_state, "kind": "refund"})
    print(f"    node_refund(...)                     → {out2['answer']}")

    print("\n  >> 换成 if-else 版本，你想单测「退款分支」就得把整个 handle() 跑一遍，")
    print("     还得 mock 掉另外两个分支的依赖。图版本没这个问题。")
    print("     Java 视角：这就是「把大方法拆成可注入的 Handler」，")
    print("     拆完之后可以一个个用 Mockito 单测，而不是集成测整个流程。")


# ═══════════════════════════════════════════════════════════════
# 6. 小结：三个概念记住就够了
# ═══════════════════════════════════════════════════════════════


def demo_6_summary() -> None:
    print("\n" + "=" * 62)
    print("6. 小结")
    print("=" * 62)

    rows = [
        ("State", "TypedDict", "流程里要传的所有数据", "Camel Exchange / Context 类"),
        ("Node", "普通函数 f(state) -> dict", "一步做什么", "Processor / Handler"),
        ("Edge", "add_edge / 条件边", "下一步去哪", "路由规则 / 网关"),
        ("compile", "builder.compile()", "校验并生成可执行对象", "部署 BPMN 得到 ProcessDefinition"),
    ]
    print(f"  {'概念':<10}{'写成什么':<28}{'负责什么':<18}{'Java 里像什么'}")
    print("  " + "-" * 100)
    for a, b, c, d in rows:
        print(f"  {a:<10}{b:<28}{c:<18}{d}")

    print("\n  ⚠️ 三条最容易踩的：")
    print("   ① 节点返回的是**补丁**（部分字段），不是完整 state")
    print("   ② 状态字段默认是**覆盖**语义，要累加必须配 reducer（见文件 2）")
    print("   ③ 节点名写错、条件边返回值没注册，都要到 compile() 或运行才报错")

    print("\n  接下来看什么：")
    print("   2.State与reducer.py      ← 状态怎么合并（这里坑最多）")
    print("   3.条件边与循环.py        ← 分支怎么写、死循环怎么防")
    print("   4.动态并行与子图.py      ← 不知道有几个分支时怎么办")
    print("   5.人机协同interrupt.py   ← 跑到一半停下来等人")
    print("   6.拆开create_agent.py    ← 你一直在用的 create_agent 就是这张图")


def main() -> None:
    print("1. 从 if-else 到图：State / Node / Edge")
    print("   本文件不调模型，零成本")

    demo_1_the_old_way()
    app = demo_2_the_graph_way()
    demo_3_draw(app)
    demo_4_stream_each_step(app)
    demo_5_testable()
    demo_6_summary()

    print("\n" + "=" * 62)
    print("全部示例执行完毕。")


if __name__ == "__main__":
    main()
