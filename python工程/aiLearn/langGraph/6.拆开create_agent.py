#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
6. 拆开 create_agent：你一直在用的东西就是这张图
================================================
【Python 语法看不懂？】闭包、lambda、** 解包、推导式等见 ../PYTHON_SYNTAX.md


═══════════════════════════════════════════════════════════════
本文件要回答三个问题
═══════════════════════════════════════════════════════════════

   ① create_agent 到底给了我什么？（它是怎么实现的）
   ② 既然有 create_agent，为什么还要学 LangGraph？
   ③ 什么情况下必须自己搭图，不能只用 create_agent？

  这三个问题的答案其实是同一个：
     **create_agent 就是「一张固定的图」的语法糖。**

  本文件会先把它拆开给你看，再手搭一遍证明，
  最后给你一个「create_agent 表达不了」的真实例子。

═══════════════════════════════════════════════════════════════
先看结论（后面的 demo 会逐个验证）
═══════════════════════════════════════════════════════════════

     create_agent(...) 返回的类型  =  CompiledStateGraph
     你自己 StateGraph(...).compile() 返回的  =  CompiledStateGraph
                                                    ↑ 同一个类

     create_agent 内部就是搭了这么一张图：

         __start__ ──> model ──(没有 tool_calls)──> __end__
                         │  ▲
                (有 tool_calls)│
                         ▼  │
                        tools

     只有四个节点，其中两个（__start__ / __end__）是引擎自带的。

     所以：
       · 你之前学的 State / Node / Edge / 条件边 / 循环 —— 全都在里面
       · 你之前用的 checkpointer / store / middleware —— 都是挂在图上的
       · 「agent」不是一个神秘的东西，就是一个 model ⇄ tools 的循环

【Java 对照】

    create_agent ≈ @EnableWebMvc / @SpringBootApplication
                   —— 一行注解帮你装配好一整套东西，你也能自己 new 出来

    自己搭图     ≈ 手动 new DispatcherServlet + 配 HandlerMapping
                   —— 更啰嗦，但能改任何细节

    平时用注解，需要定制时回到手写。两者不是对立的。

【运行】
    ./yzy/Scripts/python.exe "aiLearn/langGraph/6.拆开create_agent.py"

    ⚠️ 本文件调 DeepSeek（需要 API key），约 8-10 次调用。
"""

import os
from pathlib import Path
from typing import Annotated, TypedDict

import dotenv
from langchain.agents import create_agent
from langchain_core.messages import AnyMessage, ToolMessage
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode


def _find_env() -> Path:
    """从本文件所在目录向上逐层查找 .env。"""
    current = Path(__file__).resolve()
    for parent in [current.parent, *current.parents]:
        candidate = parent / ".env"
        if candidate.exists():
            return candidate
    return current.parent / ".env"


_ENV_PATH = _find_env()
dotenv.load_dotenv(_ENV_PATH)


def build_llm(**kwargs) -> ChatOpenAI:
    base = dict(
        model="deepseek-flash",
        api_key=os.getenv("DEEPSEEK_API_KEY"),
        base_url=os.getenv("DEEPSEEK_API_BASE"),
        temperature=0,
    )
    base.update(kwargs)
    return ChatOpenAI(**base)


def section(title: str) -> None:
    print("\n" + "=" * 62)
    print(title)
    print("=" * 62)


# ═══════════════════════════════════════════════════════════════
# 工具集（简单、确定性，方便看清流程）
# ═══════════════════════════════════════════════════════════════


@tool
def get_weather(city: str) -> str:
    """查询指定城市的当前天气。"""
    return f"{city}：晴，26 度"


@tool
def get_time(city: str) -> str:
    """查询指定城市的当前时间。"""
    return f"{city}：14:30"


TOOLS = [get_weather, get_time]


# ═══════════════════════════════════════════════════════════════
# 1. create_agent 到底是什么 —— 直接问它要图结构
# ═══════════════════════════════════════════════════════════════


def demo_1_inspect_agent() -> None:
    section("1. 直接把 create_agent 的内部结构打印出来")

    agent = create_agent(
        model=build_llm(),
        tools=TOOLS,
        system_prompt="你是一个助手，回答简短。",
        checkpointer=InMemorySaver(),
    )

    print("  agent 的类型：", type(agent).__name__)
    print("\n  它有哪些节点（这就是图的全部内容）：")
    for name in agent.get_graph().nodes:
        print(f"     · {name}")

    print("\n  它的图长这样（Mermaid）：")
    for line in agent.get_graph().draw_mermaid().splitlines():
        if line.strip().startswith(("graph", "__", "model", "tools")):
            print("     " + line.strip())

    print("\n  >> 就四个节点：__start__ / model / tools / __end__")
    print("     __start__ 和 __end__ 是引擎自带的虚拟节点，")
    print("     真正干活的只有 model 和 tools 两个。")
    print("\n  >> 虚线表示**条件边**：")
    print("     model -.-> __end__   没有 tool_calls 就结束")
    print("     model -.-> tools     有 tool_calls 就去执行工具")
    print("     tools -.-> model     工具执行完回到模型")
    print("\n     这不就是文件 3 里我们手搭的那个 ReAct 循环吗？")


# ═══════════════════════════════════════════════════════════════
# 2. 手搭一遍（手写工具执行，把每一步都摊开）
# ═══════════════════════════════════════════════════════════════


class AgentState(TypedDict):
    """agent 的状态。

    只有一个字段 messages —— 因为 agent 的所有信息（用户说的话、
    模型的思考、工具的结果）全在消息列表里。

    这就是为什么 create_agent 内部用 MessagesState：
        它本质上就是 「messages: Annotated[list, add_messages]」。
    """

    messages: Annotated[list[AnyMessage], add_messages]


def demo_2_hand_built() -> None:
    section("2. 手搭一个 agent（手写工具执行，看清每一步）")

    llm = build_llm()
    llm_with_tools = llm.bind_tools(TOOLS)

    # ---- 节点 1：调模型 ----
    def call_model(state: AgentState) -> dict:
        """把整个消息历史发给模型，把回复追加进去。

        注意返回值：{'messages': [一条新消息]}。
        add_messages 会把它追加到列表末尾（不是覆盖，见文件 2）。
        """
        response = llm_with_tools.invoke(state["messages"])
        return {"messages": [response]}

    # ---- 节点 2：执行工具（手写版，看清原理）----
    def call_tools_manual(state: AgentState) -> dict:
        """执行模型要求的工具调用。

        真实项目别这么写，用下面的 ToolNode。
        这里手写是为了让你看清 ToolNode 到底做了什么。
        """
        last = state["messages"][-1]
        by_name = {t.name: t for t in TOOLS}
        results = []
        for call in last.tool_calls:
            # call 长这样：{'name': 'get_weather', 'args': {'city': '北京'}, 'id': 'call_xxx'}
            fn = by_name[call["name"]]
            output = fn.invoke(call["args"])
            # ⚠️ ToolMessage 必须带上 tool_call_id，模型靠它把结果和调用对上
            results.append(ToolMessage(content=str(output), tool_call_id=call["id"]))
        return {"messages": results}

    # ---- 路由：还要不要调工具 ----
    def should_continue(state: AgentState) -> str:
        """看最后一条消息有没有 tool_calls。

        这就是 create_agent 内部那个条件边的判断逻辑。
        """
        last = state["messages"][-1]
        if getattr(last, "tool_calls", None):
            return "tools"
        return END

    # ---- 组装 ----
    builder = StateGraph(AgentState)
    builder.add_node("model", call_model)
    builder.add_node("tools", call_tools_manual)
    builder.add_edge(START, "model")
    builder.add_conditional_edges("model", should_continue, {"tools": "tools", END: END})
    builder.add_edge("tools", "model")     # ⭐ 这就是循环
    app = builder.compile(checkpointer=InMemorySaver())

    print("  手搭的图：")
    for line in app.get_graph().draw_mermaid().splitlines():
        if line.strip().startswith(("graph", "__", "model", "tools")):
            print("     " + line.strip())

    cfg = {"configurable": {"thread_id": "hand_1"}}
    question = "北京天气怎么样？现在几点了？"
    print(f"\n  提问: {question}")

    result = app.invoke({"messages": [{"role": "user", "content": question}]}, cfg)

    print("\n  完整执行轨迹：")
    for i, m in enumerate(result["messages"], 1):
        calls = getattr(m, "tool_calls", None) or []
        if calls:
            desc = "要求调工具 " + str([c["name"] for c in calls])
        else:
            desc = str(getattr(m, "content", "")).replace("\n", " ")[:56]
        print(f"     {i}. {type(m).__name__:<12} {desc}")

    print("\n  >> 五个节点调用，引擎跑了三轮循环：")
    print("     model（说要调工具）→ tools（执行）→ model（不需要了）→ 结束")

    print("\n  >> 注意一处差别：`tools --> model` 这里是**实线**（我用了固定边），")
    print("     create_agent 那边是**虚线**（它用条件边）。功能等价 ——")
    print("     官方用条件边是为了在工具执行异常时也能统一走路由，")
    print("     我们自己写固定边完全够用。")

    return app


# ═══════════════════════════════════════════════════════════════
# 3. 换成官方 ToolNode：更省事，但结构一模一样
# ═══════════════════════════════════════════════════════════════


def demo_3_toolnode() -> None:
    section("3. 换成官方 ToolNode：代码更短，结构不变")

    llm_with_tools = build_llm().bind_tools(TOOLS)

    def call_model(state: AgentState) -> dict:
        return {"messages": [llm_with_tools.invoke(state["messages"])]}

    def should_continue(state: AgentState) -> str:
        return "tools" if getattr(state["messages"][-1], "tool_calls", None) else END

    builder = StateGraph(AgentState)
    builder.add_node("model", call_model)
    # ⭐ 就这一行，替代了手写的那 10 行
    builder.add_node("tools", ToolNode(TOOLS))
    builder.add_edge(START, "model")
    builder.add_conditional_edges("model", should_continue, {"tools": "tools", END: END})
    builder.add_edge("tools", "model")
    app = builder.compile()

    result = app.invoke({"messages": [{"role": "user", "content": "上海天气"}]})
    print(f"  提问: 上海天气")
    print(f"  回复: {str(result['messages'][-1].content)[:80]}")

    print("\n  >> ToolNode 帮你做了这些（手写版里都要自己处理）：")
    print("     · 按 name 找工具")
    print("     · 并行执行多个 tool_calls")
    print("     · 捕获异常并转成 ToolMessage 交回模型（不会让整条链崩）")
    print("     · 处理 tool_call_id 对应关系")
    print("     · 支持 astream 时逐个产出")
    print("\n     生产代码用 ToolNode，别手写。")


# ═══════════════════════════════════════════════════════════════
# 4. 对比：两者是同一个类
# ═══════════════════════════════════════════════════════════════


def demo_4_same_type(hand_built) -> None:
    section("4. 关键证据：两者返回的对象是同一个类")

    official = create_agent(model=build_llm(), tools=TOOLS, system_prompt="你是助手")

    print(f"  手搭的:        {type(hand_built).__name__}")
    print(f"  create_agent:  {type(official).__name__}")
    print(f"  是同一个类吗:  {type(hand_built) is type(official)}")

    print("\n  节点对比：")
    hand_nodes = sorted(hand_built.get_graph().nodes)
    off_nodes = sorted(official.get_graph().nodes)
    print(f"     手搭:         {hand_nodes}")
    print(f"     create_agent: {off_nodes}")
    print(f"     完全一致吗:   {hand_nodes == off_nodes}")

    print("\n  所以 create_agent 不是什么魔法，就是帮你把这张图搭好了。")
    print("  ⚠️ 但注意：**结构一致 ≠ 功能一致**。")
    print("     create_agent 在那两个节点里塞了很多你没写的东西（见下一节）。")


# ═══════════════════════════════════════════════════════════════
# 5. create_agent 额外帮你做了什么
# ═══════════════════════════════════════════════════════════════


def demo_5_what_agent_adds() -> None:
    section("5. create_agent 额外帮你做了什么（诚实清单）")

    print("  手搭那 30 行代码只覆盖了主干。create_agent 还包了这些：\n")

    rows = [
        ("system_prompt 注入", "✅ 帮你", "自动拼成 SystemMessage 放在最前面"),
        ("工具错误处理", "✅ 帮你", "工具抛异常不崩，转成 ToolMessage 交回模型"),
        ("并行工具调用", "✅ 帮你", "一次返回多个 tool_calls 时并发执行"),
        ("结构化输出", "✅ 帮你", "response_format 参数，自动加一个收尾节点"),
        ("中间件", "✅ 帮你", "重试/限流/脱敏/摘要/工具筛选都挂得上"),
        ("state_schema 扩展", "✅ 帮你", "能加自定义字段（比如用户 ID、计数器）"),
        ("context_schema", "✅ 帮你", "运行时上下文注入（用户身份、db 连接）"),
        ("interrupt_before/after", "✅ 帮你", "调试用，在指定节点前后暂停"),
        ("流式", "⚠️ 打平", "两者都支持，agent 的封装更顺手"),
        ("自定义节点", "❌ 做不到", "← 这是必须自己搭图的唯一理由"),
        ("自定义循环控制", "❌ 做不到", "比如「审校不通过就回到起草」"),
        ("多阶段流水线", "❌ 做不到", "研究→起草→审核→发布，每阶段不同模型"),
    ]
    print(f"  {'能力':<26}{'create_agent':<14}{'说明'}")
    print("  " + "-" * 86)
    for a, b, c in rows:
        print(f"  {a:<26}{b:<14}{c}")

    print("\n  >> 结论很清楚：")
    print("     只要你的需求是「模型 + 工具反复循环」，用 create_agent，别手搭。")
    print("     一旦需要**加自己的节点**（模型和工具之外的处理步骤），就必须搭图。")
    print("     而真实业务里，几乎都需要加 —— 这就是学 LangGraph 的理由。")


# ═══════════════════════════════════════════════════════════════
# 6. create_agent 表达不了的例子
# ═══════════════════════════════════════════════════════════════


class ArticleState(TypedDict):
    topic: str
    notes: list[str]        # 调研收集的要点
    draft: str              # 草稿
    issues: list[str]       # 审校发现的问题
    rounds: int
    final: str


def demo_6_beyond_agent() -> None:
    section("6. create_agent 做不到的例子：带审校回环的写作流水线")

    print("  需求：给定主题 → 调研 → 起草 → 审校 → 不合格就改 → 合格就输出")
    print("\n  为什么 create_agent 做不到：")
    print("     · 它只有 model / tools 两个节点，插不进「审校」这一步")
    print("     · 它没有「不合格回到起草」的循环（它的循环只有 model⇄tools）")
    print("     · 不同阶段想用不同提示词 / 不同模型，它表达不了\n")
    print("  用图就能直接画出来：")
    print("       START → research → draft → review ─(合格)→ finalize → END")
    print("                            ▲         │")
    print("                            └─(不合格)┘   （带轮数上限）")

    MAX_ROUNDS = 2
    llm = build_llm()

    def research(state: ArticleState) -> dict:
        """调研节点：真实项目这里会调搜索工具，这里直接用模型生成要点。"""
        r = llm.invoke(f"关于「{state['topic']}」，列出 2 条最关键的事实，每条不超过 15 字，"
                       f"只输出内容，不要编号。")
        notes = [line.strip("- ").strip() for line in str(r.content).splitlines() if line.strip()][:2]
        print(f"     [research] 收集到 {len(notes)} 条要点")
        return {"notes": notes}

    def draft(state: ArticleState) -> dict:
        """起草节点：基于要点写一段。"""
        prompt = f"基于这些要点写一段介绍：{state['notes']}"
        if state["issues"]:
            prompt += f"\n上一版的问题（必须改掉）：{'；'.join(state['issues'])}"
        r = llm.invoke(prompt)
        n = state["rounds"] + 1
        print(f"     [draft] 第 {n} 稿完成（{len(str(r.content))} 字）")
        return {"draft": str(r.content), "rounds": n}

    def review(state: ArticleState) -> dict:
        """审校节点：检查硬性规则（用规则而非模型，保证可控、可复现）。

        规则刻意设计成第一稿大概率不合格，好让你看到返工循环真的会转。
        真实项目里这类「格式/长度/必含要素」的检查就该用规则，别让模型自己判断。
        """
        draft = state["draft"]
        paragraphs = [p for p in draft.split("\n") if p.strip()]
        issues = []
        if len(draft) < 120:
            issues.append("内容太单薄，至少要 120 字")
        if len(paragraphs) < 2:
            issues.append("没有分段，请拆成两段以上")
        if state["notes"] and state["notes"][-1][:4] not in draft:
            issues.append(f"没有覆盖要点「{state['notes'][-1][:8]}」")
        print(f"     [review] 发现 {len(issues)} 个问题"
              + (f"：{'；'.join(issues)}" if issues else "，通过"))
        return {"issues": issues}

    def route_after_review(state: ArticleState) -> str:
        if not state["issues"]:
            return "pass"
        if state["rounds"] >= MAX_ROUNDS:
            return "give_up"
        return "retry"

    def finalize(state: ArticleState) -> dict:
        tag = "审校通过" if not state["issues"] else f"达上限仍有 {len(state['issues'])} 个问题"
        print(f"     [finalize] {tag}，共 {state['rounds']} 稿")
        return {"final": state["draft"]}

    builder = StateGraph(ArticleState)
    builder.add_node("research", research)
    builder.add_node("draft", draft)
    builder.add_node("review", review)
    builder.add_node("finalize", finalize)
    builder.add_edge(START, "research")
    builder.add_edge("research", "draft")
    builder.add_edge("draft", "review")
    builder.add_conditional_edges(
        "review",
        route_after_review,
        {"pass": "finalize", "retry": "draft", "give_up": "finalize"},
    )
    builder.add_edge("finalize", END)

    app = builder.compile()

    print()
    result = app.invoke({
        "topic": "LangGraph 是什么",
        "notes": [], "draft": "", "issues": [], "rounds": 0, "final": "",
    })

    print(f"\n  最终文章（{len(result['final'])} 字）：")
    print("     " + result["final"].replace("\n", " ")[:220])

    print("\n  >> 这张图里有两个 create_agent 表达不了的东西：")
    print("     ① research / review / finalize 三个自定义节点")
    print("     ② review → draft 的返工循环（不是 model⇄tools 那种循环）")
    print("\n     如果把这个需求硬塞给 create_agent，你得：")
    print("       把 research 写成一个工具，让模型「记得」去调；")
    print("       把 review 也写成工具，指望模型自己判断要不要重写。")
    print("     → 靠提示词约束流程，脆弱且不可控。图把流程变成结构，可靠得多。")


# ═══════════════════════════════════════════════════════════════
# 7. 选型：什么时候用哪个
# ═══════════════════════════════════════════════════════════════


def demo_7_decision() -> None:
    section("7. 选型：create_agent 还是自己搭图")

    print("  【用 create_agent】只要满足「模型 + 工具循环」就够：")
    print("     · 客服问答（查到信息就答）")
    print("     · 数据查询助手（SQL / API 调用）")
    print("     · 文档问答（RAG + 少量工具）")
    print("     · 代码助手（读文件 / 执行命令）")
    print("     → 这些占了实际项目的 80%")

    print("\n  【自己搭图】出现下面任意一条：")
    print("     · 需要在模型之外加处理步骤（审校、格式化、规则校验、人工审批）")
    print("     · 需要非 model⇄tools 的循环（返工、重试不同策略、多轮澄清）")
    print("     · 需要多阶段用不同模型 / 不同提示词（便宜模型先筛，贵模型再审）")
    print("     · 需要多个 agent 协作（规划者 + 执行者 + 审核者）")
    print("     · 需要精确控制「哪一步能停、停在哪」")

    print("\n  【混合用法（最常见）】")
    print("     大图里把 create_agent 当成一个节点塞进去：")
    print("")
    print("         sub_agent = create_agent(model=llm, tools=TOOLS)")
    print("         builder.add_node('research_agent', sub_agent)   # ← 就这么用")
    print("         builder.add_node('review', my_review_node)")
    print("")
    print("     这样「agent 的部分」用现成的，「流程的部分」自己控。")
    print("     文件 4 讲过子图，这就是子图最实用的用法。")

    print("\n  【最后一句】")
    print("     create_agent 是图的**特例**，不是替代品。")
    print("     学会图，你就知道 create_agent 什么时候会不够用、")
    print("     以及不够用时该在哪儿加东西。")


def main() -> None:
    print("6. 拆开 create_agent")
    print("   ⚠️ 需要 API key，约 8-10 次模型调用")

    if not os.getenv("DEEPSEEK_API_KEY"):
        print(f"\n⚠️ 没读到 DEEPSEEK_API_KEY，.env 路径：{_ENV_PATH}")
        print("   本文件必须调模型，请先配置 key。")
        return

    demo_1_inspect_agent()
    hand = demo_2_hand_built()
    demo_3_toolnode()
    demo_4_same_type(hand)
    demo_5_what_agent_adds()
    demo_6_beyond_agent()
    demo_7_decision()

    print("\n" + "=" * 62)
    print("全部示例执行完毕。")
    print("回头看：1-5 学的每个部件，都在这个文件里出现了。")
    print("  State/reducer → AgentState + add_messages")
    print("  Node          → call_model / call_tools / research / review")
    print("  Edge          → add_edge")
    print("  条件边        → should_continue / route_after_review")
    print("  循环          → tools → model、review → draft")
    print("  checkpointer  → compile(checkpointer=...)")


if __name__ == "__main__":
    main()
