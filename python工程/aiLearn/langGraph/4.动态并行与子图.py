#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
4. 动态并行与子图：分支数量运行时才定
=====================================
【Python 语法看不懂？】闭包、lambda、** 解包、推导式等见 ../PYTHON_SYNTAX.md


═══════════════════════════════════════════════════════════════
【什么时候你会需要这一节】
═══════════════════════════════════════════════════════════════

  前面文件 1-3 的所有分支，都是**你在写代码时就知道有哪几条**。
  但下面这些场景，分支数要到运行时才知道：

    · 一份 PDF 切成 30 段要逐段总结 —— 段数是运行时才知道的
    · 用户上传 N 个文件都要解析 —— N 是运行时才知道的
    · 一次检索召回 12 篇文档都要过一遍模型 —— 12 是运行时才知道的
    · 三个专家并行评审方案 —— 这个倒是固定的，但写法上要并行

  用条件边做不到，因为条件边只能返回**已有的节点名**，
  而这里需要「同一个节点，跑 N 份不同的数据」。

  解法就是 Send —— 图里的「动态 fan-out」。

  另一件事是子图：当一个流程复杂到一张图画不下，或者要复用，
  就把一张图当成另一个图的节点。这两件事经常一起出现，所以放一个文件讲。

═══════════════════════════════════════════════════════════════
Send 和普通边的区别（这是最容易误解的地方）
═══════════════════════════════════════════════════════════════

  普通边：只是「下一个跑谁」，节点拿到的永远是**完整的 state**。

  Send：不只是「下一个跑谁」，还指定「给它什么数据副本」。

        return [Send("work", {"item": "a"}),      # 同一节点，跑两次
                Send("work", {"item": "b"})]      # 各拿各的数据

  ⚠️ 关键：Send 的第二个参数 **arg** 就是那个节点收到的全部入参，
     它**不是**往 parent state 上叠加，而是**独立的一份**。

     实测结论（本文件会跑给你看）：
        · arg 里多塞的字段，不会出现在最终 state 里
        · arg 里没有的 state 字段，那个节点也读不到
        → Send 相当于「开一个只带这份数据的子任务」

【Java 对照】

    Send ≈ 把任务拆成 N 个 Future 提交到线程池，再 collect 结果
           ExecutorService.invokeAll(List<Callable>)
           区别：你不用手写线程，引擎负责调度和合并

    子图 ≈ 一个 Service 方法内部调用另一个 Service，也可以抽成独立微服务
           区别：子图有自己的 state，对外只暴露约定的字段

【运行】
    ./yzy/Scripts/python.exe "aiLearn/langGraph/4.动态并行与子图.py"

    本文件不调模型，零成本。
"""

import time
from typing import Annotated, TypedDict

import operator
from langgraph.graph import END, START, StateGraph
from langgraph.types import Send


def section(title: str) -> None:
    print("\n" + "=" * 62)
    print(title)
    print("=" * 62)


# ═══════════════════════════════════════════════════════════════
# 1. 场景：一段长文档，切成 N 段并行总结
# ═══════════════════════════════════════════════════════════════


class SummarizeState(TypedDict):
    """主图状态。"""

    doc: str
    # 每一段的总结都往这里塞 → 必须用 operator.add，否则并行会炸（见文件 2）
    parts: Annotated[list[str], operator.add]
    # 最终合并后的报告
    report: str


def demo_1_send_map_reduce() -> None:
    section("1. Send：map-reduce 式的动态并行")

    print("  场景：一段文档切成若干段，每段单独总结，最后合并。")
    print("  段数在运行时才知道 —— 条件边做不到，必须用 Send。\n")
    print("  图的结构：")
    print("       START")
    print("         │")
    print("      ┌──▼───┐")
    print("      │split │  按段落切成 N 份，发 N 个 Send")
    print("      └──┬───┘")
    print("     ┌───┼───┐  （N 个并行分支，N 是运行时决定的）")
    print("     ▼   ▼   ▼")
    print("   work work work    同一个节点，跑 N 次")
    print("     └───┼───┘")
    print("      ┌──▼───┐")
    print("      │merge │  合并成一个报告")
    print("      └──────┘\n")

    def split(state: SummarizeState) -> dict:
        """切分节点。

        它本身**不干活**，只是为了给条件边提供一个「出发点」。
        真正的切分逻辑写在下面的 fan_out 里。
        """
        return {}

    def fan_out(state: SummarizeState) -> list[Send]:
        """条件边上的函数：返回 list[Send]。

        每个 Send 指定「用哪个节点、带什么数据」。
        """
        segments = [s.strip() for s in state["doc"].split("。") if s.strip()]
        return [
            Send("work", {"segment": seg, "index": i, "total": len(segments)})
            for i, seg in enumerate(segments)
        ]

    def work(payload: dict) -> dict:
        """工作节点：被并行调用 N 次。

        ⚠️ 注意入参：payload 是 Send 的 arg，**不是** SummarizeState。
        payload 里只有 segment / index / total 三个字段，
        读不到 doc，也读不到 parts。

        真实场景这里会调模型：
            return {'parts': [llm.invoke(f'总结这段：{payload["segment"]}')]}
        """
        # 模拟一下耗时，好让你看到「并行确实省时间」
        time.sleep(0.05)
        summary = f"[{payload['index'] + 1}/{payload['total']}] {payload['segment'][:12]}…"
        # 返回值仍然按**主图**的 reducer 合并进 parts
        return {"parts": [summary]}

    def merge(state: SummarizeState) -> dict:
        """汇总节点：等所有并行分支都完成后才会执行。"""
        # ⚠️ 并行返回的顺序是不确定的，要自己按 index 排
        parts = sorted(state["parts"])
        return {"report": " | ".join(parts)}

    builder = StateGraph(SummarizeState)
    builder.add_node("split", split)     # 占位节点，真正逻辑在条件边上
    builder.add_node("work", work)
    builder.add_node("merge", merge)

    builder.add_edge(START, "split")
    # ⚠️ 第三个参数是「Send 可能去的节点」列表，必须声明
    builder.add_conditional_edges("split", fan_out, ["work"])
    builder.add_edge("work", "merge")
    builder.add_edge("merge", END)
    app = builder.compile()

    doc = "LangGraph 是状态机框架。它用 State 承载数据。节点是普通函数。边决定下一步。Send 可以动态并行。子图可以复用流程"
    print(f"  输入文档（{len(doc)} 字）：{doc[:40]}…")

    t0 = time.time()
    result = app.invoke({"doc": doc, "parts": [], "report": ""})
    cost = time.time() - t0

    print(f"\n  并行结果（{len(result['parts'])} 段）：")
    for p in sorted(result["parts"]):
        print(f"     {p}")
    print(f"\n  合并报告: {result['report']}")
    print(f"  耗时 {cost:.2f}s（每段 sleep 0.05s，如果串行需要 {0.05 * len(result['parts']):.2f}s）")

    print("\n  >> 引擎会等**所有** Send 分支跑完，才进入 merge。")
    print("     merge 里看到的是合并后的完整 parts 列表。")


# ═══════════════════════════════════════════════════════════════
# 2. ⚠️ Send 的边界：arg 不污染主 state
# ═══════════════════════════════════════════════════════════════


class BoundaryState(TypedDict):
    items: list[str]
    results: Annotated[list[str], operator.add]


def demo_2_send_boundary() -> None:
    section("2. ⚠️ Send 的边界：arg 是独立副本，不污染主 state")

    print("  这一点很多人搞错：以为 Send 的 arg 是「往 state 上叠加」。")
    print("  实测一下，往 arg 里多塞一个字段 secret：\n")

    def fan_out(state: BoundaryState) -> list[Send]:
        # 故意多塞一个主 state 里没有的字段
        return [Send("work", {"item": it, "secret": "只给 work 看"}) for it in state["items"]]

    def work(payload: dict) -> dict:
        print(f"     work 收到的入参: {payload}")
        print(f"     （注意：读不到 items，也读不到 results）")
        return {"results": [f"{payload['item']}-处理完"]}

    builder = StateGraph(BoundaryState)
    builder.add_node("split", lambda s: {})
    builder.add_node("work", work)
    builder.add_edge(START, "split")
    builder.add_conditional_edges("split", fan_out, ["work"])
    builder.add_edge("work", END)

    result = builder.compile().invoke({"items": ["a", "b"], "results": []})

    print(f"\n  最终 state: {result}")
    print(f"  有 'secret' 这个字段吗？ {'secret' in result}   ← 没有")

    print("\n  >> 三条规则：")
    print("     ① Send 的 arg 就是这个节点收到的**全部入参**")
    print("     ② arg 里的额外字段**不会**进主 state（不会污染）")
    print("     ③ arg 里没带的 state 字段，那个节点**读不到**")
    print("\n     所以 Send 适合「每个分支只需要一小份数据」的场景。")
    print("     如果分支节点需要读全量 state（比如要看历史消息），")
    print("     就不该用 Send，而应该在 arg 里把这部分数据一起传过去。")

    print("\n  ⚠️ 还有一个坑：并行返回的顺序不确定")
    print("     上面 results 是 ['a-处理完', 'b-处理完'] 只是碰巧。")
    print("     engine 按完成先后合并，10 个分支时顺序可能乱。")
    print("     要保序就在 arg 里带 index，汇总时按 index 排（见上一节 merge 的 sorted）。")


# ═══════════════════════════════════════════════════════════════
# 3. 固定数量的并行：不用 Send，直接连边
# ═══════════════════════════════════════════════════════════════


class ReviewState(TypedDict):
    proposal: str
    reviews: Annotated[list[str], operator.add]
    verdict: str


def demo_3_fixed_parallel() -> None:
    section("3. 固定数量的并行：不用 Send，直接多连几条边就行")

    print("  场景：一份方案，让三个「专家」并行评审（架构/安全/成本）。")
    print("  专家是固定的三个，不需要 Send，直接 START 连三条边：\n")
    print("      START ─┬─> arch ─┬─> merge")
    print("             ├─> sec  ─┤")
    print("             └─> cost ─┘\n")

    def arch(state: ReviewState) -> dict:
        return {"reviews": ["架构：模块划分清晰，建议补一层缓存"]}

    def sec(state: ReviewState) -> dict:
        return {"reviews": ["安全：凭证不能放在 prompt 里"]}

    def cost(state: ReviewState) -> dict:
        return {"reviews": ["成本：每次全量发 50 个工具，token 偏高"]}

    def merge(state: ReviewState) -> dict:
        return {"verdict": f"共 {len(state['reviews'])} 条意见，需逐条回复"}

    builder = StateGraph(ReviewState)
    for name, fn in [("arch", arch), ("sec", sec), ("cost", cost)]:
        builder.add_node(name, fn)
    builder.add_node("merge", merge)

    # 三条边都从 START 出发 → 三个节点并行
    for name in ("arch", "sec", "cost"):
        builder.add_edge(START, name)
        builder.add_edge(name, "merge")     # 三条边都汇到 merge
    builder.add_edge("merge", END)

    result = builder.compile().invoke({"proposal": "上 AI 客服", "reviews": [], "verdict": ""})

    print("  三份评审意见：")
    for r in result["reviews"]:
        print(f"     · {r}")
    print(f"\n  {result['verdict']}")

    print("\n  >> 关键点：**汇合节点会等所有入边都跑完才执行**。")
    print("     merge 有三个入边，所以它一定在三个专家都完成后才跑。")
    print("     这是 LangGraph 的「超步（superstep）」语义：")
    print("       同一超步里能跑的节点并行跑，全跑完再进下一个超步。")

    print("\n  >> Send vs 直接连边 怎么选：")
    rows = [
        ("分支数量固定且少（2-5 个）", "直接连边", "简单直观，一眼看出结构"),
        ("分支数量运行时才定（N 份文件）", "Send", "条件边做不到"),
        ("分支是同一段逻辑跑不同数据", "Send", "一个 work 节点跑 N 次"),
        ("分支是不同逻辑（不同专家）", "直接连边", "每个专家独立可测"),
    ]
    print(f"  {'情况':<32}{'选哪个':<12}{'为什么'}")
    print("  " + "-" * 86)
    for a, b, c in rows:
        print(f"  {a:<32}{b:<12}{c}")


# ═══════════════════════════════════════════════════════════════
# 4. 子图：把一张图当成节点
# ═══════════════════════════════════════════════════════════════


class SubGraphState(TypedDict):
    """子图自己的状态。注意它比父图多了 private_note。"""

    text: str
    private_note: str     # 父图没有这个字段


class ParentState(TypedDict):
    text: str
    stage: str


def demo_4_subgraph() -> None:
    section("4. 子图：把一张编译好的图当成另一个图的节点")

    print("  场景：一个「文本清洗」流程有 3 步，另一个系统也要用它。")
    print("  把它打包成子图，两边都能 add_node 进去复用。\n")

    # ---- 先建一个独立的子图 ----
    def trim(state: SubGraphState) -> dict:
        return {"text": state["text"].strip()}

    def lower(state: SubGraphState) -> dict:
        return {"text": state["text"].lower()}

    def tag(state: SubGraphState) -> dict:
        return {"text": state["text"] + "#cleaned", "private_note": "这三个步骤来自子图"}

    sub_builder = StateGraph(SubGraphState)
    sub_builder.add_node("trim", trim)
    sub_builder.add_node("lower", lower)
    sub_builder.add_node("tag", tag)
    sub_builder.add_edge(START, "trim")
    sub_builder.add_edge("trim", "lower")
    sub_builder.add_edge("lower", "tag")
    sub_builder.add_edge("tag", END)
    sub_app = sub_builder.compile()      # ← 编译后就是一个 Runnable，可以直接当节点

    print("  子图内部：START → trim → lower → tag → END")

    # ---- 把它当节点塞进父图 ----
    def pre(state: ParentState) -> dict:
        return {"text": state["text"] + "   ", "stage": "预处理完"}

    def post(state: ParentState) -> dict:
        return {"stage": "后处理完"}

    parent = StateGraph(ParentState)
    parent.add_node("pre", pre)
    parent.add_node("clean", sub_app)     # ⭐ 子图当节点，名字随便起
    parent.add_node("post", post)
    parent.add_edge(START, "pre")
    parent.add_edge("pre", "clean")
    parent.add_edge("clean", "post")
    parent.add_edge("post", END)

    app = parent.compile()
    result = app.invoke({"text": "  Hello World  ", "stage": ""})

    print(f"\n  父图输入: {{'text': '  Hello World  ', 'stage': ''}}")
    print(f"  最终结果: {result}")
    print(f"  有 'private_note' 吗？ {'private_note' in result}   ← 没有")

    print("\n  >> 状态边界（很重要）：")
    print("     子图有自己的 state schema。**只有父子都声明的同名字段才会传递**。")
    print("     子图里那个 private_note，出了子图就没了 —— 相当于局部变量。")
    print("     这个设计让子图可以有自己的内部状态，不污染父图。")

    print("\n  画出来看看（子图会展开成单独的框）：")
    for line in app.get_graph(xray=True).draw_mermaid().splitlines()[:14]:
        print("    " + line)
    print("    …")
    print("    ↑ 加 xray=True 就能看到子图内部，不加则把子图当黑盒")


# ═══════════════════════════════════════════════════════════════
# 5. 子图 + Send：两个一起用
# ═══════════════════════════════════════════════════════════════


class BatchState(TypedDict):
    files: list[str]
    outputs: Annotated[list[str], operator.add]


def demo_5_combine() -> None:
    section("5. 两个一起用：N 个文件，每个文件跑一遍子流程")

    print("  这是生产里最常见的组合：")
    print("    · Send → 有几个文件就发几个分支")
    print("    · 子图 → 每个分支都跑同一套多步流程\n")

    # ---- 子图：单个文件的处理流程（3 步）----
    class FileState(TypedDict):
        name: str
        content: str
        step: str

    def read_step(state: FileState) -> dict:
        return {"content": f"<{state['name']} 的内容>", "step": "read"}

    def parse_step(state: FileState) -> dict:
        return {"content": state["content"] + " 已解析", "step": "parse"}

    def index_step(state: FileState) -> dict:
        return {"content": state["content"] + " 已入索引", "step": "index"}

    sb = StateGraph(FileState)
    sb.add_node("read", read_step)
    sb.add_node("parse", parse_step)
    sb.add_node("index", index_step)
    sb.add_edge(START, "read")
    sb.add_edge("read", "parse")
    sb.add_edge("parse", "index")
    sb.add_edge("index", END)
    file_pipeline = sb.compile()

    # ---- 父图：对每个文件发一个 Send，指向子图 ----
    def fan_out(state: BatchState) -> list[Send]:
        # ⚠️ 注意 Send 的第一个参数是**节点名**（父图里注册的名字），不是子图对象
        return [Send("process_file", {"name": f, "content": "", "step": ""}) for f in state["files"]]

    builder = StateGraph(BatchState)
    builder.add_node("split", lambda s: {})
    builder.add_node("process_file", file_pipeline)    # ← 子图注册成节点
    builder.add_edge(START, "split")
    builder.add_conditional_edges("split", fan_out, ["process_file"])
    builder.add_edge("process_file", END)

    app = builder.compile()
    result = app.invoke({"files": ["a.md", "b.md", "c.md"], "outputs": []})

    print("  处理结果：")
    for f in result["files"]:
        print(f"     {f} → <{f} 的内容> 已解析 已入索引")

    print("\n  >> 每个文件都独立走完 read→parse→index 三步，三个文件之间并行。")
    print("     这就是「一个请求里跑 N 套子流程」的标准写法。")

    print("\n  ⚠️ 三个注意点：")
    print("     ① Send 的第一个参数写**父图里注册的节点名**（'process_file'），")
    print("        不是子图对象，也不是子图内部的节点名")
    print("     ② 子图的输入 schema 必须能接受你 Send 过去的 arg")
    print("        （这里 FileState 有 name/content/step，arg 也给了这三个）")
    print("     ③ 子图返回值里，父子同名的字段会合并回父图")
    print("        （这里子图的 step 父图没有，所以不影响；outputs 是父图自己的）")


# ═══════════════════════════════════════════════════════════════
# 6. 小结
# ═══════════════════════════════════════════════════════════════


def demo_6_summary() -> None:
    section("6. 小结")

    print("  【并行有两种】")
    print("     固定数量 → START 连多条边，简单直观")
    print("     数量不定 → Send，条件边返回 list[Send]")

    print("\n  【Send 的三条规则】")
    print("     ① arg 是这个节点收到的全部入参，不是往 state 上叠加")
    print("     ② arg 里多塞的字段不会进主 state")
    print("     ③ 返回顺序不确定，要保序就在 arg 里带 index")

    print("\n  【汇合语义】")
    print("     有多条入边的节点，会等所有入边都完成后才执行（超步语义）")
    print("     所以 merge / 汇总节点天然是「等全部完成」")

    print("\n  【子图】")
    print("     编译好的图直接 add_node 就能当节点用")
    print("     状态边界：只有父子同名字段才传递，子图私有字段不冒泡")
    print("     什么时候用：流程要复用、一张图画不下、团队分工、想独立测试")

    print("\n  【什么时候别用这些】")
    print("     如果只是「调 3 次模型然后拼起来」，用 RunnableParallel 更轻：")
    print("         chain = RunnableParallel(a=chain_a, b=chain_b)")
    print("     图适合的是**有状态流转、有分支、要暂停恢复**的场景。")
    print("     纯数据转换用 LCEL 就够，别为了用图而用图。")

    print("\n  下一个文件：5.人机协同interrupt.py")
    print("     图和普通代码最大的不同：它能跑到一半停下来，等人。")


def main() -> None:
    print("4. 动态并行与子图")
    print("   本文件不调模型，零成本")

    demo_1_send_map_reduce()
    demo_2_send_boundary()
    demo_3_fixed_parallel()
    demo_4_subgraph()
    demo_5_combine()
    demo_6_summary()

    print("\n" + "=" * 62)
    print("全部示例执行完毕。")


if __name__ == "__main__":
    main()
