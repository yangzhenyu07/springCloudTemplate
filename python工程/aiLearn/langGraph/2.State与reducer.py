#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
2. State 与 reducer：状态怎么合并（这里坑最多）
==============================================
【Python 语法看不懂？】闭包、lambda、** 解包、推导式等见 ../PYTHON_SYNTAX.md


═══════════════════════════════════════════════════════════════
【什么时候你会需要这一节】
═══════════════════════════════════════════════════════════════

  只要满足下面任意一条，就必须搞懂 reducer：

    · 想让节点往一个**列表**里追加东西（消息历史、检索到的文档、日志）
    · 有**并行**节点，两个节点都要写 state
    · 多个节点都要往「结论」「问题清单」里塞东西
    · 想实现「同一个字段保留最大值 / 取并集」这类特殊合并

  反过来，如果每个字段只有一个节点写、写完就完事，那 reducer 跟你没关系，
  默认的覆盖语义就够了。

═══════════════════════════════════════════════════════════════
一句话原理
═══════════════════════════════════════════════════════════════

  节点返回一个 dict（补丁）。引擎要把它合并进全局 state。
  **怎么合并，由字段的类型注解决定：**

      普通注解              → 覆盖（新值直接替换旧值）
      Annotated[T, reducer] → 调 reducer(旧值, 新值)，用返回值当新值

  就这一条。所有困惑都来自「以为默认是追加，其实是覆盖」。

═══════════════════════════════════════════════════════════════
三种常用的 reducer
═══════════════════════════════════════════════════════════════

  ① 什么都不配      → 覆盖
  ② operator.add    → 列表拼接 / 数字相加
  ③ add_messages    → 消息专用：追加 + 按 id 更新 + 支持删除

  以及：任何 (旧值, 新值) -> 新值 的函数都能当 reducer，比如取最大值。

【Java 对照】

    reducer ≈ Stream 的 reduce / Collectors.toList() 里的那个累加器
              （其实 reduce(identity, accumulator) 的 accumulator 就是 reducer）

    默认覆盖 ≈ map.put(k, v)，后写覆盖先写
    operator.add ≈ list.addAll(other) + 不能用同一个 list 反复 addAll 自己

【运行】
    ./yzy/Scripts/python.exe "aiLearn/langGraph/2.State与reducer.py"

    本文件不调模型，零成本。
"""

import operator
from typing import Annotated, TypedDict

from langchain_core.messages import AIMessage, AnyMessage, HumanMessage, RemoveMessage
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import REMOVE_ALL_MESSAGES, add_messages


def section(title: str) -> None:
    print("\n" + "=" * 62)
    print(title)
    print("=" * 62)


# ═══════════════════════════════════════════════════════════════
# 1. 默认语义：覆盖
# ═══════════════════════════════════════════════════════════════


class CoverState(TypedDict):
    """什么都没配 → 每个字段都是「后写覆盖先写」。"""

    step: str
    status: str


def demo_1_default_cover() -> None:
    section("1. 默认语义 = 覆盖（last write wins）")

    def node_a(state: CoverState) -> dict:
        return {"step": "a", "status": "跑过 a"}

    def node_b(state: CoverState) -> dict:
        # 注意：这里没返回 step，所以 step 保持 "a" 不变
        return {"status": "跑过 b"}

    builder = StateGraph(CoverState)
    builder.add_node("a", node_a)
    builder.add_node("b", node_b)
    builder.add_edge(START, "a")
    builder.add_edge("a", "b")
    builder.add_edge("b", END)

    result = builder.compile().invoke({"step": "", "status": ""})
    print(f"  初始: {{'step': '', 'status': ''}}")
    print(f"  a 返回: {{'step': 'a', 'status': '跑过 a'}}")
    print(f"  b 返回: {{'status': '跑过 b'}}          ← 没写 step")
    print(f"  最终: {result}")
    print("\n  >> status 被 b 覆盖了（这是你想要的）；step 因为 b 没返回所以还是 'a'。")
    print("     **没返回的字段不是被清空，是保持原样。** 这点很重要。")


# ═══════════════════════════════════════════════════════════════
# 2. 列表累加：operator.add
# ═══════════════════════════════════════════════════════════════


class AddState(TypedDict):
    # Annotated[类型, reducer] —— 这个字段的合并方式由 adder 决定
    log: Annotated[list[str], operator.add]
    final: str        # 这个还是覆盖


def demo_2_operator_add() -> None:
    section("2. operator.add：列表拼接")

    print("  写法：log: Annotated[list[str], operator.add]\n")

    def node_x(state: AddState) -> dict:
        return {"log": ["x"]}          # ← 只返回「新增的那部分」

    def node_y(state: AddState) -> dict:
        return {"log": ["y"], "final": "完成"}

    builder = StateGraph(AddState)
    builder.add_node("x", node_x)
    builder.add_node("y", node_y)
    builder.add_edge(START, "x")
    builder.add_edge("x", "y")
    builder.add_edge("y", END)

    result = builder.compile().invoke({"log": [], "final": ""})
    print(f"  初始 log=[]")
    print(f"  x 返回 {{'log': ['x']}}  → 引擎算 [] + ['x']")
    print(f"  y 返回 {{'log': ['y']}}  → 引擎算 ['x'] + ['y']")
    print(f"  最终: {result}")


# ═══════════════════════════════════════════════════════════════
# 3. ⚠️ 最容易踩的坑：配了 add 却返回全量
# ═══════════════════════════════════════════════════════════════


class AddState2(TypedDict):
    log: Annotated[list[str], operator.add]


def demo_3_the_classic_bug() -> None:
    section("3. ⚠️ 最经典的坑：配了 add 却返回全量列表")

    print("  很多人凭直觉这么写（因为他们记得「节点要返回完整值」）：\n")
    print("      def node(state):")
    print("          return {'log': state['log'] + ['x']}    ← 全量！错！\n")

    def correct(state: AddState2) -> dict:
        """正确：只返回新增的。"""
        return {"log": ["x"]}

    def wrong(state: AddState2) -> dict:
        """错误：把旧值也带上了。"""
        return {"log": state["log"] + ["x"]}

    for name, fn in [("只返回新增（对）", correct), ("返回全量（错）", wrong)]:
        builder = StateGraph(AddState2)
        builder.add_node("n", fn)
        builder.add_edge(START, "n")
        builder.add_edge("n", END)
        result = builder.compile().invoke({"log": ["a"]})
        print(f"  {name:<18} 初始 ['a'] → {result['log']}")

    print("\n  >> 第二个结果是 ['a', 'a', 'x']：旧值被算了两遍。")
    print("     原因：引擎执行的是 旧值 + 你的返回值 = ['a'] + ['a','x']。")
    print("\n  ⚠️ 记忆规则：")
    print("     **配了 reducer 的字段，节点只返回「增量」；")
    print("       没配 reducer 的字段，节点返回「要设置成的值」。**")
    print("     两条规则不一样，这是最容易混的地方。")
    print("\n     而且这个 bug 不会报错，只是数据悄悄变多。")
    print("     长对话场景下表现为「消息越滚越长」「token 突然暴涨」。")


# ═══════════════════════════════════════════════════════════════
# 4. 并行节点写同一个字段：无 reducer 直接报错
# ═══════════════════════════════════════════════════════════════


class NoReducerState(TypedDict):
    value: str


class WithReducerState(TypedDict):
    values: Annotated[list[str], operator.add]


def demo_4_parallel_conflict() -> None:
    section("4. 并行节点写同一字段：没 reducer 会炸")

    print("  场景：START 同时连到两个节点，它们都要写 value")
    print("        START ──┬──> p1 ──┬──> END")
    print("                └──> p2 ──┘\n")

    # ---- 没配 reducer ----
    def p1(state: NoReducerState) -> dict:
        return {"value": "from p1"}

    def p2(state: NoReducerState) -> dict:
        return {"value": "from p2"}

    builder = StateGraph(NoReducerState)
    builder.add_node("p1", p1)
    builder.add_node("p2", p2)
    builder.add_edge(START, "p1")
    builder.add_edge(START, "p2")
    builder.add_edge("p1", END)
    builder.add_edge("p2", END)

    try:
        builder.compile().invoke({"value": ""})
        print("  没 reducer：居然没报错")
    except Exception as e:
        print(f"  没 reducer → {type(e).__name__}")
        print(f"    {str(e).splitlines()[0]}")
        print("    ↑ 引擎明确告诉你：一个字段一步只能收到一个值，")
        print("      要么加 Annotated，要么别让两个节点写同一个字段。")

    # ---- 配了 reducer ----
    def q1(state: WithReducerState) -> dict:
        return {"values": ["from p1"]}

    def q2(state: WithReducerState) -> dict:
        return {"values": ["from p2"]}

    builder2 = StateGraph(WithReducerState)
    builder2.add_node("q1", q1)
    builder2.add_node("q2", q2)
    builder2.add_edge(START, "q1")
    builder2.add_edge(START, "q2")
    builder2.add_edge("q1", END)
    builder2.add_edge("q2", END)

    result = builder2.compile().invoke({"values": []})
    print(f"\n  配了 reducer → {result}")
    print("    ↑ 两个都保住了。顺序按节点完成先后，**不要依赖顺序**。")

    print("\n  >> 实战含义：")
    print("     做「多个专家并行评审」「多路检索汇总」时，")
    print("     结果字段必须是 Annotated[list, operator.add]，否则一上来就炸。")


# ═══════════════════════════════════════════════════════════════
# 5. add_messages：消息专用的智能合并
# ═══════════════════════════════════════════════════════════════


class ChatState(TypedDict):
    messages: Annotated[list[AnyMessage], add_messages]


def demo_5_add_messages() -> None:
    section("5. add_messages：消息专用的 reducer（比 operator.add 聪明）")

    print("  为什么消息不能直接用 operator.add？")
    print("  因为真实场景需要三件事，operator.add 都做不到：\n")
    print("    · 按 id 更新某条消息（流式输出时不断更新最后一条 AI 消息）")
    print("    · 按 id 删除某条消息（裁剪历史、移除敏感内容）")
    print("    · 自动给没有 id 的消息补 id")
    print("\n  add_messages 全包了：\n")

    # ---- ① 追加 ----
    msgs = add_messages([], [HumanMessage("你好", id="m1")])
    msgs = add_messages(msgs, [AIMessage("你好，有什么可以帮你", id="m2")])
    print(f"  ① 追加两条       → {[(type(m).__name__, m.content, m.id) for m in msgs]}")

    # ---- ② 同 id = 更新，不是追加 ----
    msgs = add_messages(msgs, [AIMessage("你好，有什么可以帮你（改成这句）", id="m2")])
    print(f"  ② 同 id m2 更新  → {[(type(m).__name__, m.content) for m in msgs]}")
    print("     ↑ 条数没变，m2 被替换了。这就是流式更新最后一条消息的原理。")

    # ---- ③ 没 id 会怎样 ----
    no_id = add_messages([], [HumanMessage("同一句话"), HumanMessage("同一句话")])
    print(f"\n  ③ 两条内容相同、都没 id → {len(no_id)} 条（各算一条，不会去重）")
    print("     ↑ 内容是内容，id 是身份。没有 id 就是两个不同的消息。")

    # ---- ④ 删除 ----
    msgs = add_messages(msgs, [RemoveMessage(id="m1")])
    print(f"\n  ④ RemoveMessage(id='m1') → 剩 {[(type(m).__name__, m.content[:12]) for m in msgs]}")

    # ---- ⑤ 全清 ----
    print("\n  ⑤ 想全清不能传空字符串（会报 ValueError: ID doesn't exist），")
    print("     要用专门的哨兵常量 REMOVE_ALL_MESSAGES：\n")
    print("        from langgraph.graph.message import REMOVE_ALL_MESSAGES")
    print("        add_messages(msgs, [RemoveMessage(id=REMOVE_ALL_MESSAGES)])")
    cleared = add_messages(msgs, [RemoveMessage(id=REMOVE_ALL_MESSAGES)])
    print(f"        实测结果 → {cleared}")

    print("\n  >> 标准写法：状态里永远这样声明消息字段")
    print("        messages: Annotated[list[AnyMessage], add_messages]")
    print("     或者直接用官方给的 MessagesState（就是这一个字段）：")
    print("        from langgraph.graph import MessagesState")
    print("        class MyState(MessagesState):")
    print("            extra: str        # 在 messages 之外加自己的字段")


# ═══════════════════════════════════════════════════════════════
# 6. 自定义 reducer：任何 (旧, 新) -> 新 都能当
# ═══════════════════════════════════════════════════════════════


def demo_6_custom_reducer() -> None:
    section("6. 自定义 reducer：不限于加法")

    print("  reducer 就是个二元函数 (旧值, 新值) -> 合并后的值。")
    print("  所以「取最大」「取最新」「取并集」都能写成 reducer：\n")

    def keep_max(old: int, new: int) -> int:
        """分数只升不降。"""
        return max(old, new)

    def union(old: list[str], new: list[str]) -> list[str]:
        """去重并集：多个节点给出不同的标签，合并成不重复的集合。"""
        return old + [x for x in new if x not in old]

    class ScoreState(TypedDict):
        score: Annotated[int, keep_max]
        tags: Annotated[list[str], union]

    def scorer(state: ScoreState) -> dict:
        return {"score": 10, "tags": ["urgent"]}

    builder = StateGraph(ScoreState)
    builder.add_node("scorer", scorer)
    builder.add_edge(START, "scorer")
    builder.add_edge("scorer", END)

    result = builder.compile().invoke({"score": 50, "tags": ["vip"]})
    print(f"  初始: score=50, tags=['vip']")
    print(f"  节点返回: score=10, tags=['urgent']")
    print(f"  最终: {result}")
    print("\n  >> keep_max 保住了 50（节点想降分也降不下来）；")
    print("     union 合并成 ['vip', 'urgent']，且不会重复。")

    print("\n  【实战场景】")
    print("     · keep_max → 置信度分数、风险等级（只升不降，防止被后续节点降级）")
    print("     · union    → 多个分类器打标签、多个规则引擎命中项合并")
    print("     · 取最新   → 用 lambda old, new: new 就等价于覆盖，没意义")
    print("                真正有用的是「按时间戳选新的」这种带逻辑的比较")

    print("\n  ⚠️ reducer 必须是**纯函数、幂等**：")
    print("     引擎可能因为重试 / 恢复执行让你同一个补丁跑两次，")
    print("     如果 reducer 有副作用（比如往全局变量里塞），结果就不可复现了。")


# ═══════════════════════════════════════════════════════════════
# 7. 小结
# ═══════════════════════════════════════════════════════════════


def demo_7_summary() -> None:
    section("7. 小结：reducer 决策表")

    rows = [
        ("什么都不配", "覆盖", "单节点写、写完就算", "最容易"),
        ("operator.add", "列表拼接", "append 日志/文档/中间结果", "返回增量！"),
        ("add_messages", "追加+按id更新+可删", "消息历史（几乎必用）", "别用 operator.add 代替"),
        ("自定义函数", "你说了算", "取最大/去重并集/按时间戳选", "必须纯函数"),
        ("无效（并行写）", "—", "—", "InvalidUpdateError"),
    ]
    print(f"  {'配置':<16}{'合并语义':<20}{'什么时候用':<26}{'注意'}")
    print("  " + "-" * 92)
    for a, b, c, d in rows:
        print(f"  {a:<16}{b:<20}{c:<26}{d}")

    print("\n  ⚠️ 一句话记住：")
    print("     **配了 reducer → 节点返回增量；没配 → 节点返回最终值。**")
    print("     混了就是数据悄悄重复，而且不报错，最难查。")

    print("\n  下一个文件：3.条件边与循环.py")
    print("     state 会合并了，接下来解决「下一步去谁」和「什么时候停」。")


def main() -> None:
    print("2. State 与 reducer：状态怎么合并")
    print("   本文件不调模型，零成本")

    demo_1_default_cover()
    demo_2_operator_add()
    demo_3_the_classic_bug()
    demo_4_parallel_conflict()
    demo_5_add_messages()
    demo_6_custom_reducer()
    demo_7_summary()

    print("\n" + "=" * 62)
    print("全部示例执行完毕。")


if __name__ == "__main__":
    main()
