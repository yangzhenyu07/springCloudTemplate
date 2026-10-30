#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
3. 条件边与循环：下一步去谁，什么时候停
=======================================
【Python 语法看不懂？】闭包、lambda、** 解包、推导式等见 ../PYTHON_SYNTAX.md


═══════════════════════════════════════════════════════════════
【什么时候你会需要这一节】
═══════════════════════════════════════════════════════════════

  只要流程里出现下面任意一个词，就是这一节的内容：

    · 分流 / 分类 / 走不同分支    —— 客服意图路由、工单分派
    · 重试 / 返工 / 再审一次      —— 质检不通过重写、翻译不满意重译
    · 循环直到满足条件            —— ReAct 的「调工具→看结果→再调」
    · 够好了就提前结束            —— 达到置信度就别再跑了，省钱
    · 人工介入后再继续            —— 见文件 5

  图里有个硬约束：**边不能凭空连，必须有人决定下一步**。
  决定的方式就两种：条件边（边里判断）和 Command（节点里判断）。
  这一节把两种都讲清楚，并告诉你什么时候用哪种。

═══════════════════════════════════════════════════════════════
两种路由方式的本质区别
═══════════════════════════════════════════════════════════════

  ① 条件边 add_conditional_edges
        节点只管干活，**不知道**自己下一步去哪。
        路由逻辑是**边上**的一个独立函数：f(state) -> 下一个节点名。

        ┌────────┐   路由函数看 state   ┌────────┐
        │ 节点 A │ ──────────────────> │ 节点 B │
        └────────┘                       └────────┘

  ② Command（节点自己决定）
        节点干完活，直接返回「我干完了，顺便告诉你下一步去哪」。

        ┌──────────────────────────┐
        │ 节点 A                   │
        │   return Command(        │
        │       goto="B",          │
        │       update={...})      │
        └──────────┬───────────────┘
                   └──────────────> 节点 B

  怎么选：
    · 路由只需要看 state 里的现有字段 → 条件边（职责更清晰，路由可单测）
    · 路由要看节点「刚算出来的中间结果」，而这个结果不想放进 state
      → Command（少一个 state 字段，少一个路由函数）
    · 要做多 agent 交接（agent A 干完把活给 agent B）→ Command 更自然

【Java 对照】

    条件边 ≈ Camel 的 choice/when，或者 Spring Integration 的 Router
             —— 路由规则独立于处理器，配置在「连线」上
    Command ≈ 处理器自己 return 一个 "next" 指令
             —— 类似状态机里 handler 返回 nextState

【运行】
    ./yzy/Scripts/python.exe "aiLearn/langGraph/3.条件边与循环.py"

    本文件不调模型，零成本。
"""

from typing import Annotated, TypedDict

import operator
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command


def section(title: str) -> None:
    print("\n" + "=" * 62)
    print(title)
    print("=" * 62)


# ═══════════════════════════════════════════════════════════════
# 1. 条件边的三种写法
# ═══════════════════════════════════════════════════════════════


class RouteState(TypedDict):
    text: str
    kind: str


def demo_1_three_styles() -> None:
    section("1. add_conditional_edges 的三种写法")

    def classify(state: RouteState) -> dict:
        t = state["text"]
        if "退款" in t:
            return {"kind": "refund"}
        if "物流" in t or "快递" in t:
            return {"kind": "logistics"}
        return {"kind": "other"}

    def refund(state: RouteState) -> dict:
        return {"text": state["text"] + " → 已转退款组"}

    def logistics(state: RouteState) -> dict:
        return {"text": state["text"] + " → 已转物流组"}

    def other(state: RouteState) -> dict:
        return {"text": state["text"] + " → 已转人工"}

    # ---- 写法 A：只给函数，函数直接返回节点名 ----
    print("  【写法 A】path 函数直接返回节点名（最常用）")
    b1 = StateGraph(RouteState)
    b1.add_node("classify", classify)
    b1.add_node("refund", refund)
    b1.add_node("logistics", logistics)
    b1.add_node("other", other)
    b1.add_edge(START, "classify")
    # 这里 state["kind"] 的值正好等于节点名，所以直接返回它
    b1.add_conditional_edges("classify", lambda s: s["kind"])
    for n in ("refund", "logistics", "other"):
        b1.add_edge(n, END)
    print(f"     add_conditional_edges('classify', lambda s: s['kind'])")
    print(f"     → {b1.compile().invoke({'text': '我要退款', 'kind': ''})['text']}")

    # ---- 写法 B：给 path_map，做「返回值 → 节点名」的映射 ----
    print("\n  【写法 B】带 path_map，做一层映射（推荐）")
    print("     好处：路由函数可以返回业务语义的短值，不用和节点名绑死")
    b2 = StateGraph(RouteState)
    b2.add_node("classify", classify)
    b2.add_node("refund", refund)
    b2.add_node("logistics", logistics)
    b2.add_node("other", other)
    b2.add_edge(START, "classify")
    b2.add_conditional_edges(
        "classify",
        lambda s: s["kind"],
        {                                   # ← path_map：返回值 → 节点名
            "refund": "refund",
            "logistics": "logistics",
            "other": "other",
        },
    )
    for n in ("refund", "logistics", "other"):
        b2.add_edge(n, END)
    print(f"     → {b2.compile().invoke({'text': '快递到哪了', 'kind': ''})['text']}")

    # ---- 写法 C：给 list，返回值必须在这个列表里 ----
    print("\n  【写法 C】只给 list，做白名单校验")
    print("     好处：返回值不在列表里会直接报错，能提前发现拼写错误")
    b3 = StateGraph(RouteState)
    b3.add_node("classify", classify)
    b3.add_node("refund", refund)
    b3.add_node("logistics", logistics)
    b3.add_node("other", other)
    b3.add_edge(START, "classify")
    b3.add_conditional_edges("classify", lambda s: s["kind"], ["refund", "logistics", "other"])
    for n in ("refund", "logistics", "other"):
        b3.add_edge(n, END)
    print(f"     → {b3.compile().invoke({'text': '你好', 'kind': ''})['text']}")

    print("\n  ⚠️ 三种写法都能跑，但差别在「错了什么时候发现」：")
    print("     A：返回值拼错 → 运行时才报「没这个节点」")
    print("     B：path_map 里少写一个 key → 运行时报 KeyError，但错在哪很清楚")
    print("     C：返回值不在列表 → 运行时报错，且列表本身就是文档")
    print("     生产代码建议用 B 或 C，别用 A。")


# ═══════════════════════════════════════════════════════════════
# 2. 循环：返工直到合格
# ═══════════════════════════════════════════════════════════════


class ReviewState(TypedDict):
    draft: str
    score: int
    rounds: int
    history: Annotated[list[str], operator.add]   # 累加！


def demo_2_loop() -> None:
    section("2. 循环：质检不通过就返工（最典型的循环场景）")

    print("  流程：写 → 审 → (不合格) 回写 → 再审 …… 直到合格或轮数用完\n")
    print("     ┌──────────────────────────────┐")
    print("     ▼                              │")
    print("   write ──> review ──(合格)──> END  │")
    print("                │                  │")
    print("                └──(不合格，未超轮数)┘")

    MAX_ROUNDS = 3

    def write(state: ReviewState) -> dict:
        """写作节点：每轮写得更长一点，模拟「改进」。"""
        n = state["rounds"] + 1
        return {
            "draft": "草稿" + "!" * n,
            "rounds": n,
            "history": [f"第{n}轮：写了 {n} 个感叹号"],
        }

    def review(state: ReviewState) -> dict:
        """审核节点：感叹号 >= 2 个才算合格（模拟打分）。"""
        score = state["draft"].count("!")
        ok = "合格" if score >= 2 else "不合格"
        return {
            "score": score,
            "history": [f"    审核：得分 {score} → {ok}"],
        }

    def decide(state: ReviewState) -> str:
        """路由：合格 or 轮数用完就结束，否则回去重写。"""
        if state["score"] >= 2:
            return "pass"
        if state["rounds"] >= MAX_ROUNDS:
            return "give_up"
        return "retry"

    builder = StateGraph(ReviewState)
    builder.add_node("write", write)
    builder.add_node("review", review)
    builder.add_edge(START, "write")
    builder.add_edge("write", "review")
    builder.add_conditional_edges(
        "review",
        decide,
        {
            "pass": END,        # 合格 → 结束
            "retry": "write",   # ⭐ 指回自己，这就是循环
            "give_up": END,     # 轮数用完 → 强制结束
        },
    )

    app = builder.compile()
    result = app.invoke({"draft": "", "score": 0, "rounds": 0, "history": []})

    print()
    for line in result["history"]:
        print(f"  {line}")
    print(f"\n  最终草稿: {result['draft']!r}  得分 {result['score']}  共 {result['rounds']} 轮")

    print("\n  >> 循环就是这么实现的：**把条件边的目标指回上游节点**。")
    print("     没有任何特殊的 loop 语法。")

    print("\n  >> 但循环必须有两个出口，缺一不可：")
    print("     ① 成功出口（合格就出）")
    print("     ② 兜底出口（轮数/时间用完强制出）")
    print("     只写①不写② → 模型一直不合格就永不停止（见下一节）。")


# ═══════════════════════════════════════════════════════════════
# 3. ⚠️ 死循环：引擎的保护机制
# ═══════════════════════════════════════════════════════════════


class LoopState(TypedDict):
    count: int


def demo_3_recursion_limit() -> None:
    section("3. ⚠️ 忘记写出口会怎样：GraphRecursionError")

    def always_loop(state: LoopState) -> dict:
        return {"count": state["count"] + 1}

    builder = StateGraph(LoopState)
    builder.add_node("loop", always_loop)
    builder.add_edge(START, "loop")
    # 无条件回到自己 —— 故意写错
    builder.add_conditional_edges("loop", lambda s: "loop")
    app = builder.compile()

    print("  故意写一个没有出口的循环，看引擎怎么处理：\n")

    try:
        app.invoke({"count": 0}, {"recursion_limit": 5})
        print("  居然没报错？")
    except Exception as e:
        print(f"  {type(e).__name__}:")
        print(f"    {str(e).splitlines()[0]}")

    print("\n  >> 引擎有默认上限（25 步），超过就抛 GraphRecursionError。")
    print("     这是一道**保险丝**，不是让你依赖它。")
    print("\n     为什么必须有这道保险丝：")
    print("       · 每次循环大概率要调模型，失控就是烧钱")
    print("       · ReAct 场景里模型可能反复调同一个工具")
    print("       · 循环里如果有写数据库/发消息，重复执行后果严重")

    print("\n  >> 正确做法：**自己数轮数**，别依赖 recursion_limit")
    print("     · recursion_limit 是「整个图的步数上限」，包含所有节点")
    print("     · 一个 8 节点的图跑 4 轮循环就 32 步了，很容易误伤")
    print("     · 在 state 里放一个 rounds 字段，自己判断，语义才清晰")
    print("     · recursion_limit 只当最后一道保险，设成你业务上能接受的最大值")


# ═══════════════════════════════════════════════════════════════
# 4. Command：节点自己决定去哪
# ═══════════════════════════════════════════════════════════════


class HandoffState(TypedDict):
    text: str
    log: Annotated[list[str], operator.add]


def demo_4_command() -> None:
    section("4. Command：让节点自己决定下一步")

    print("  场景：一个「分流器」节点，它判断完直接把人交给对应的专家。")
    print("  这时候路由逻辑和业务逻辑是同一件事，拆成两个函数反而别扭。\n")

    def triage(state: HandoffState) -> Command:
        """分流节点：既写入 state，又指定下一个节点。

        Command(goto=..., update=...) 一次干两件事：
          update → 相当于普通节点的返回值（写 state）
          goto   → 相当于条件边的返回值（指定下一个节点）
        """
        text = state["text"]
        if "退款" in text:
            # 交接前顺手打个标，说明为什么转过去
            return Command(goto="refund_expert", update={"log": ["分流：命中退款 → 交给退款专家"]})
        if "物流" in text:
            return Command(goto="logistics_expert", update={"log": ["分流：命中物流 → 交给物流专家"]})
        return Command(goto="general", update={"log": ["分流：没命中 → 交给通用客服"]})

    def refund_expert(state: HandoffState) -> dict:
        return {"log": ["退款专家：已受理"]}

    def logistics_expert(state: HandoffState) -> dict:
        return {"log": ["物流专家：已查询"]}

    def general(state: HandoffState) -> dict:
        return {"log": ["通用客服：您好，请问具体什么问题？"]}

    builder = StateGraph(HandoffState)
    builder.add_node("triage", triage)
    builder.add_node("refund_expert", refund_expert)
    builder.add_node("logistics_expert", logistics_expert)
    builder.add_node("general", general)

    builder.add_edge(START, "triage")
    # ⚠️ 注意：triage 后面**没有** add_conditional_edges，
    #    Command 的 goto 会直接生效。但目标节点仍然要注册。
    builder.add_edge("refund_expert", END)
    builder.add_edge("logistics_expert", END)
    builder.add_edge("general", END)

    app = builder.compile()

    for q in ["我要退款", "快递到哪了", "你们几点上班"]:
        result = app.invoke({"text": q, "log": []})
        print(f"  输入: {q:<12}")
        for line in result["log"]:
            print(f"     {line}")

    print("\n  ⚠️ 两个坑：")
    print("     ① Command 的目标节点**必须先 add_node 注册**，")
    print("        否则运行时报错（compile 时不检查，因为 goto 是动态的）")
    print("     ② 用了 Command 就不要在同一条上再写 add_conditional_edges，")
    print("        两者是竞争关系，会互相打架")

    print("\n  【Command vs 条件边 怎么选】")
    rows = [
        ("路由只看 state 现有字段", "条件边", "路由函数可单测，节点不需要知道下游"),
        ("路由要看节点刚算的中间结果", "Command", "省一个 state 字段 + 一个函数"),
        ("一个节点要交接到多个下游之一", "两者都行", "Command 写起来更连贯"),
        ("多个节点共用同一套路由规则", "条件边", "一个路由函数复用，改一处生效"),
        ("多 agent 交接（handoff）", "Command", "官方多 agent 示例都用这个"),
    ]
    print(f"  {'情况':<28}{'选哪个':<12}{'为什么'}")
    print("  " + "-" * 88)
    for a, b, c in rows:
        print(f"  {a:<28}{b:<12}{c}")


# ═══════════════════════════════════════════════════════════════
# 5. 串起来：一个 ReAct 循环的骨架（不调模型，看清结构）
# ═══════════════════════════════════════════════════════════════


class ReActState(TypedDict):
    question: str
    thoughts: Annotated[list[str], operator.add]
    answer: str


def demo_5_react_skeleton() -> None:
    section("5. 串起来：ReAct 循环的骨架（这就是 agent 的本质）")

    print("  ReAct 就是「想 → 做 → 看结果 → 再想」，一个标准循环。")
    print("  **你一直在用的 create_agent，内部就是这张图**（文件 6 会亲手搭一遍）。\n")

    def think(state: ReActState) -> dict:
        """思考节点：决定要不要调工具、调哪个。

        真实实现里这里是 llm.invoke()，返回 AIMessage 带 tool_calls。
        这里用固定逻辑模拟，让你看清结构。
        """
        # 模拟：第一轮想查天气，第二轮就得出答案
        if len(state["thoughts"]) == 0:
            return {"thoughts": ["需要查天气 → 调 get_weather"]}
        return {"thoughts": ["信息够了 → 可以回答"], "answer": "北京晴，26 度"}

    def act(state: ReActState) -> dict:
        """行动节点：执行工具，把结果写回。"""
        return {"thoughts": ["工具返回：北京晴 26 度"]}

    def should_act(state: ReActState) -> str:
        """路由：还要调工具吗？"""
        last = state["thoughts"][-1]
        # 真实实现里判断的是：last_message.tool_calls 是否为空
        return "act" if "调" in last else "answer"

    builder = StateGraph(ReActState)
    builder.add_node("think", think)
    builder.add_node("act", act)
    builder.add_edge(START, "think")
    builder.add_conditional_edges("think", should_act, {"act": "act", "answer": END})
    builder.add_edge("act", "think")     # ⭐ 行动完回到思考，这就是 ReAct 的循环
    app = builder.compile()

    print("  图结构：")
    print("     START → think ─(要调工具)→ act ─┐")
    print("               ▲                    │")
    print("               └────────────────────┘")
    print("               └─(不需要了)────────→ END\n")

    result = app.invoke({"question": "北京天气", "thoughts": [], "answer": ""})
    for i, t in enumerate(result["thoughts"], 1):
        print(f"     {i}. {t}")
    print(f"  最终答案: {result['answer']}")

    print("\n  >> 看清了吗？所谓 agent 就是：")
    print("     think（调模型）→ 判断有没有 tool_calls → 有就 act（执行工具）→ 回到 think")
    print("     没有特殊机制，就是一个带出口的循环。")
    print("\n     文件 6 会把这套换成真模型 + 真工具跑一遍，")
    print("     然后你会发现 create_agent 返回的对象和手搭的是**同一个类**。")


# ═══════════════════════════════════════════════════════════════
# 6. 小结
# ═══════════════════════════════════════════════════════════════


def demo_6_summary() -> None:
    section("6. 小结")

    print("  【路由】两种方式，按「判断依据在哪」来选")
    print("     条件边   → 判断依据是 state 现有字段，路由函数独立可测")
    print("     Command  → 判断依据是节点刚算出的结果，或要多 agent 交接")

    print("\n  【循环】没有专门语法，就是「条件边指回上游节点 + 两个出口」")
    print("     成功出口 + 兜底出口，缺一不可")
    print("     自己数轮数（state 里放 rounds），别指望 recursion_limit")

    print("\n  【保险丝】recursion_limit 默认 25 步，超了抛 GraphRecursionError")
    print("     它是兜底，不是设计手段。生产环境按业务最大步数显式设置：")
    print("       app.invoke(input, {'recursion_limit': 50})")

    print("\n  下一个文件：4.动态并行与子图.py")
    print("     上面所有分支都是「提前知道的」。如果分支数量要到运行时才知道呢？")


def main() -> None:
    print("3. 条件边与循环：下一步去谁，什么时候停")
    print("   本文件不调模型，零成本")

    demo_1_three_styles()
    demo_2_loop()
    demo_3_recursion_limit()
    demo_4_command()
    demo_5_react_skeleton()
    demo_6_summary()

    print("\n" + "=" * 62)
    print("全部示例执行完毕。")


if __name__ == "__main__":
    main()
