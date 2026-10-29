#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
7. Skill 标准规范与渐进式加载（Agent Skills 开放标准 + DeepSeek）
================================================================
【Python 语法看不懂？】闭包、lambda、** 解包、推导式等见 ../PYTHON_SYNTAX.md

【⚠️ 先更正前面文件 5/6 的一个错误结论】


    真实情况：**Agent Skills 是开放标准**
        · 由 Anthropic 发起，**2025-12-18 发布为 open standard**（跨产品可移植）
        · 规范站：https://skill.md
        · 已被 LangChain(Deep Agents)、Claude Code、Codex 等几十家产品支持
        · 你本机 ~/.workbuddy/skills/ 下就是这套标准的实例

【标准长什么样】
    my-skill/
    ├── SKILL.md        # 必需：YAML frontmatter + Markdown 正文
    ├── scripts/        # 可选：可执行代码（执行，不读入上下文）
    ├── references/     # 可选：文档（按需读）
    └── assets/         # 可选：模板/素材

    SKILL.md 的 frontmatter 只有两个必需字段：
        name        ≤64 字符，小写字母/数字/连字符
        description ≤1024 字符，**必须同时写清「做什么」和「什么时候用」**
                    （这是模型判断是否加载的唯一依据，最重要）

【核心机制：渐进式披露（progressive disclosure）】
    L1 元数据  启动时加载   只有 name+description 进系统提示   ~100 tokens/skill
    L2 指令    命中才加载   用 read_file 读完整 SKILL.md        <5k tokens
    L3 资源    需要才加载   scripts 执行 / references 读       脚本 0 token

    所以「判断击中哪个 Skill」的标准答案变了：
        不是查自己维护的反查表，而是**看 agent 读了哪个 SKILL.md**。

【本文件用的官方实现】
    deepagents 0.7.32（LangChain 官方，要求 Python>=3.11）
        create_deep_agent(model=..., tools=..., skills=["skills"])
        SkillsMiddleware：注入元数据、处理 read_file、绑定工具、pinned_skills

【运行】
    ./yzy/Scripts/python.exe "aiLearn/tool/7.Skill标准规范与渐进式加载.py"
"""

import os
import re
from pathlib import Path

import dotenv
from deepagents import create_deep_agent
from deepagents.backends import FilesystemBackend
from deepagents.middleware import SkillsMiddleware
from langchain_core.messages import AIMessage
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI

# skills 目录：本文件所在目录下的 skills/
HERE = Path(__file__).resolve().parent


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
# 工具（和 SKILL.md 里 metadata.include_tools 声明的名字一致）
# ===========================================================================
@tool
def logistics_track(order_no: str) -> str:
    """查询订单的物流轨迹。传入订单号，返回当前所在节点与预计送达时间。"""
    return f"订单 {order_no}：已到达【广州转运中心】，预计明天 18:00 前送达"


@tool
def calc_shipping_fee(weight_kg: float, distance_km: float) -> str:
    """计算快递运费。weight_kg 是重量（公斤），distance_km 是距离（公里）。"""
    fee = 8 + weight_kg * 1.5 + distance_km * 0.1
    return f"运费：{fee:.2f} 元（重量 {weight_kg}kg，距离 {distance_km}km）"


@tool
def product_stock(product_id: str) -> str:
    """查询商品库存。传入商品 ID，返回可用库存数量与所在仓库。"""
    return f"商品 {product_id}：可用库存 42 件，仓库 深圳宝安"


ALL_TOOLS = [logistics_track, calc_shipping_fee, product_stock]


# ===========================================================================
# 1. 标准长什么样 + 和之前硬编码方案的对比
# ===========================================================================
def demo_1_what_is_standard() -> None:
    section("1. Skill 的标准是什么（以及我前面错在哪）")

    print("  【事实】Agent Skills 是开放标准，不是某个库的类：")
    print("    · Anthropic 发起，2025-12-18 发布为 open standard")
    print("    · 规范站 https://skill.md，几十家 agent 产品支持")
    print("    · LangChain 官方实现：deepagents 包（本文件用的就是它）\n")

    print("  一个 skill 就是一个目录，核心是 SKILL.md：\n")
    print("    order-service/")
    print("    ├── SKILL.md              ← 必需")
    print("    ├── scripts/quote.py      ← 可选，被执行不读入上下文")
    print("    └── references/           ← 可选，按需读\n")

    print("  SKILL.md 的结构：\n")
    print("    ---")
    print("    name: order-service")
    print("    description: >")
    print("      订单域能力。查询订单状态与物流轨迹、计算快递运费。")
    print("      触发场景：用户问「订单到哪了」「运费多少钱」...")
    print("    ---")
    print("    # 订单服务")
    print("    （正文：流程、规范、注意事项）\n")

    print("  只有 name 和 description 是必需字段。")
    print("  description 最关键 —— 它是模型判断是否加载的唯一依据。\n")

    print("  【对比：标准方案 vs 文件 5 的硬编码方案】")
    rows = [
        ("Skill 从哪来", "扫描目录读 SKILL.md", "Python 字典写死"),
        ("能不能复用", "换个目录就能换一套", "改代码"),
        ("上下文开销", "L1 只 ~100 tokens/skill", "全量工具描述常驻"),
        ("工具何时可见", "读了 skill 才出现", "一开始就全给"),
        ("判断击中", "看读了哪个 SKILL.md", "查自己维护的反查表"),
        ("跨产品", "标准是开放的，可移植", "只在这份代码里有效"),
    ]
    print(f"    {'维度':<14}{'标准方案':<26}{'硬编码方案'}")
    print("    " + "-" * 62)
    for a, b, c in rows:
        print(f"    {a:<14}{b:<26}{c}")


# ===========================================================================
# 2. L1：解析 frontmatter
# ===========================================================================
def parse_frontmatter(path: Path) -> tuple[dict, str]:
    """解析 SKILL.md 的 YAML frontmatter。

    标准规定 SKILL.md 必须以 `---` 开头的 **YAML** frontmatter 开始，
    所以这里直接用 PyYAML 解析，**不要手写**。

    ⚠️ 我第一版就是手写的正则解析，结果两个 bug：
       ① `description: >` 这种 YAML 折叠块语法，折叠标记 `>` 被当成内容
       ② 多行值把后面的注释行也吞进去了
    结论：frontmatter 是标准 YAML，就老实用 yaml 解析，别自己造轮子。

    返回：(元数据字典, 正文)
    """
    import yaml

    text = path.read_text(encoding="utf-8")
    m = re.match(r"^---\s*\n(.*?)\n---\s*\n(.*)$", text, re.DOTALL)
    if not m:
        return {}, text
    meta_text, body = m.group(1), m.group(2)
    meta = yaml.safe_load(meta_text) or {}
    if not isinstance(meta, dict):
        meta = {}
    return meta, body


def demo_2_level1_metadata() -> None:
    section("2. L1 元数据：启动时只加载 name + description")

    skills_root = HERE / "skills"
    print(f"  扫描目录: {skills_root}\n")

    total_meta = 0
    total_body = 0
    for d in sorted(skills_root.iterdir()):
        if not d.is_dir():
            continue
        f = d / "SKILL.md"
        if not f.exists():
            print(f"    ⚠️ {d.name} 没有 SKILL.md，不是合法 skill，跳过")
            continue
        meta, body = parse_frontmatter(f)
        name = meta.get("name", "?")
        desc = meta.get("description", "")
        # 粗略估算：中文按字符数算，英文按 4 字符 1 token
        meta_len, body_len = len(name) + len(desc), len(body)
        total_meta += meta_len
        total_body += body_len
        print(f"    【{name}】元数据 {meta_len} 字符 / 正文 {body_len} 字符")
        print(f"      desc: {desc[:70]}...")

    print(f"\n  L1 元数据合计 {total_meta} 字符，L2 正文合计 {total_body} 字符")
    print(f"  → 启动时只花 {total_meta} 的开销，{total_body} 的内容**一个字都不进上下文**")
    print(f"  → 这就是渐进式披露：装 100 个 skill 也不怕撑爆上下文")

    print("\n  >> 关键点：description 写得好不好，直接决定 skill 会不会被命中。")
    print("     标准建议：同时写清「做什么」+「什么时候用」，必要时写明「不适用于什么」。")


# ===========================================================================
# 3. 建 agent：官方 SkillsMiddleware 自动接管
# ===========================================================================
def build_skill_agent():
    """建一个按标准加载 skill 的 agent。"""
    backend = FilesystemBackend(root_dir=HERE, virtual_mode=True)
    return create_deep_agent(
        model=build_llm(),
        tools=ALL_TOOLS,
        skills=["skills"],          # ← 指向**包含** skill 目录的父目录
        backend=backend,
        system_prompt="你是电商客服助手。优先使用 skill 里的规范来回答。",
    )


def demo_3_create_agent() -> None:
    section("3. create_deep_agent：把标准接进 agent")

    print("  代码就这几行：\n")
    print("    from deepagents import create_deep_agent")
    print("    from deepagents.backends import FilesystemBackend")
    print("")
    print("    backend = FilesystemBackend(root_dir=HERE, virtual_mode=True)")
    print("    agent = create_deep_agent(")
    print("        model=build_llm(),")
    print("        tools=ALL_TOOLS,")
    print("        skills=['skills'],       # 包含 skill 目录的父目录")
    print("        backend=backend,")
    print("    )\n")

    print("  ⚠️ 两个容易踩的点：")
    print("     ① skills 要指向**父目录**，直接指向某个 skill 目录不会被加载")
    print("     ② 路径用 forward slash（/），Windows 反斜杠不认\n")

    try:
        agent = build_skill_agent()
        print("  ✅ agent 构建成功")
        names = sorted(n for n in agent.nodes) if hasattr(agent, "nodes") else []
        print(f"     图节点: {names}")
    except Exception as e:
        print(f"  ❌ 构建失败: {type(e).__name__}: {e}")


# ===========================================================================
# 4. L2 + 判断击中哪个 skill（本组的核心问题，标准答案）
# ===========================================================================
def hits_from_messages(messages: list) -> list[str]:
    """从消息轨迹里判断 agent 读了哪些 SKILL.md —— 这是标准答案。

    原理：agent 命中某个 skill 时，会用 read_file 去读它的 SKILL.md。
    所以扫 tool_calls 里的 read_file，从路径里提取 skill 名即可。
    """
    hits = []
    for m in messages:
        if not isinstance(m, AIMessage):
            continue
        for c in m.tool_calls or []:
            if c["name"] not in ("read_file", "read"):
                continue
            path = str(c["args"].get("file_path", "") or c["args"].get("path", ""))
            if "SKILL.md" in path or "SKILL.MD" in path.upper():
                # 路径形如 /skills/order-service/SKILL.md → 取倒数第二段
                parts = path.replace("\\", "/").split("/")
                for p in parts:
                    if p and p != "skills" and p.upper() != "SKILL.MD":
                        hits.append(p)
                        break
    return hits


def demo_4_level2_and_hit() -> None:
    section("4. L2 命中加载 + 怎么判断击中哪个 Skill")

    print("  标准方案里，「击中哪个 Skill」的答案是：")
    print("      **看 agent 读了哪个 SKILL.md**")
    print("  不再是查自己维护的反查表 —— 那是硬编码方案的做法。\n")

    agent = build_skill_agent()
    questions = [
        "我的订单 SO001 到哪了？",
        "商品 P100 还有多少库存？",
        "买了三天能退货吗？",
    ]

    for q in questions:
        print(f"  用户: {q}")
        try:
            res = agent.invoke({"messages": [{"role": "user", "content": q}]})
            msgs = res.get("messages", [])
            hits = hits_from_messages(msgs)
            reads = [
                c["args"].get("file_path", "")
                for m in msgs if isinstance(m, AIMessage)
                for c in (m.tool_calls or [])
                if c["name"] in ("read_file", "read")
            ]
            print(f"    read_file: {reads or '（没读任何文件）'}")
            print(f"    → 击中 Skill: {hits or '无'}")
            final = msgs[-1].content if msgs else ""
            print(f"    → 回答: {str(final)[:100]}")
        except Exception as e:
            print(f"    ❌ {type(e).__name__}: {str(e)[:150]}")
        print()


# ===========================================================================
# 5. L3：scripts 执行 / references 按需读
# ===========================================================================
def demo_5_level3_resources() -> None:
    section("5. L3 资源：脚本执行 vs 文档按需读")

    print("  标准规定 skill 可以带三类附加资源，加载时机各不相同：\n")
    print("    scripts/     被执行，源码**不进上下文**（0 token，只有 stdout 回来）")
    print("    references/  按需 read_file 读入（读了才占上下文）")
    print("    assets/      模板/素材，按需取\n")

    import subprocess
    import sys

    script = HERE / "skills" / "order-service" / "scripts" / "quote.py"
    print(f"  实测执行脚本: {script.relative_to(HERE.parent)}")
    r = subprocess.run(
        [sys.executable, str(script), "1.2", "800"],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    print(f"    stdout: {r.stdout.strip()}")
    print(f"    → 模型只拿到这一行输出，脚本源码 100 多行一个 token 都没进上下文\n")

    ref = HERE / "skills" / "product-service" / "references" / "spec-api.md"
    print(f"  references 文件: {ref.relative_to(HERE.parent)}")
    print(f"    大小 {len(ref.read_text(encoding='utf-8'))} 字符")
    print("    → 平时不在上下文里，只有 SKILL.md 指路、模型主动读时才加载")

    print("\n  >> 为什么脚本要「执行」而不是「读」：")
    print("     ① 省 token：读进来几百 token，执行只要几十 token 的输出")
    print("     ② 稳：计算是确定性的，模型心算每次可能不一样")
    print("  【Java 对照】把易错算式固化成工具类方法让模型调，而不是让它每次自己算")


# ===========================================================================
# 6. @skill 点名：pinned_skills
# ===========================================================================
def demo_6_pinned() -> None:
    section("6. 用户点名 @skill：pinned_skills 预加载")

    print("  场景：用户已经知道要用哪个 skill，比如输入「@order-service 帮我查 SO001」。")
    print("  如果走常规流程，agent 要先看到描述、再判断、再 read_file —— 多一轮调用。\n")

    print("  官方做法：应用侧自己解析消息里的 @xxx / /xxx，把名字传 pinned_skills：\n")
    print("    agent.invoke({")
    print("        'messages': [{'role': 'user', 'content': '帮我查 SO001'}],")
    print("        'pinned_skills': ['order-service'],   # ← 首轮就塞进上下文")
    print("    }, config)")
    print()
    print("  效果：下一次模型调用前，该 SKILL.md 会作为独立的 HumanMessage 追加进对话，")
    print("        additional_kwargs 里带 lc_source='pinned_skill'。\n")

    print("  ⚠️ 注意：**语法由应用自己解析**，deepagents 不负责识别消息里的 @ 或 /。")
    print("     你在客户端看到的 @skill 就是这一层在干的事。\n")

    def extract_pinned(text: str) -> list[str]:
        """从用户输入里提取 @skill / /skill 点名（演示用，应用侧自己实现）。"""
        names = re.findall(r"[@/]+([a-zA-Z0-9_-]+)", text)
        return [n for n in names]

    for text in ["@order-service 帮我查 SO001", "/after-sale 能退吗", "订单到哪了"]:
        print(f"    {text!r:<40} → pinned_skills={extract_pinned(text)}")

    print("\n  实测调用（点名 order-service）：")
    agent = build_skill_agent()
    try:
        res = agent.invoke({
            "messages": [{"role": "user", "content": "帮我算 2kg 寄 300km 的运费"}],
            "pinned_skills": ["order-service"],
        })
        msgs = res.get("messages", [])
        pinned = [
            m for m in msgs
            if getattr(m, "additional_kwargs", {}).get("lc_source") == "pinned_skill"
        ]
        print(f"    注入的 pinned 消息数: {len(pinned)}")
        if pinned:
            print(f"    内容前 80 字: {str(pinned[0].content)[:80]}")
        print(f"    最终回答: {str(msgs[-1].content)[:100] if msgs else ''}")
    except Exception as e:
        print(f"    ❌ {type(e).__name__}: {str(e)[:200]}")


# ===========================================================================
# 7. 工具绑定
# ===========================================================================
def bound_tools_of(meta: dict) -> list[str]:
    """从解析出的 metadata 里取绑定的工具名。

    ⚠️ 实测坑：deepagents 要求 include_tools 是**空格分隔的字符串**，
       不是 YAML 列表。写成列表会告警并被忽略：
       "should be a space-separated string of tool names"
    """
    raw = (meta.get("metadata") or {}).get("include_tools", "")
    if isinstance(raw, list):          # 兼容万一有人写成列表
        return raw
    return str(raw).split()


def demo_7_tool_binding() -> None:
    section("7. 工具跟着 skill 一起加载（include_tools）")

    print("  在 SKILL.md 的 frontmatter 里声明：\n")
    print("    metadata:")
    print("      include_tools: logistics_track calc_shipping_fee\n")

    print("  ⚠️ 必须是**空格分隔的字符串**。我第一版写成了 YAML 列表：\n")
    print("      include_tools:")
    print("        - logistics_track      ❌ 会告警：")
    print("        - calc_shipping_fee       should be a space-separated string of tool names\n")

    print("  效果：")
    print("    · 这些工具**不在** agent 的初始工具列表里")
    print("    · agent 读完本 SKILL.md 之后，工具才进入上下文")
    print("    · 在那之前调用 → 按 unknown tool 失败\n")

    print("  >> 这解决了文件 5/6 里没解决的问题：")
    print("     工具和「教你怎么用它的说明书」是绑定的，")
    print("     不会出现「工具被调了但说明书没读」的尴尬。\n")

    print("  各 skill 的工具绑定情况（从 frontmatter 解析）：")
    for d in sorted((HERE / "skills").iterdir()):
        f = d / "SKILL.md"
        if not f.exists():
            continue
        meta, _ = parse_frontmatter(f)
        bound = bound_tools_of(meta)
        print(f"    {meta.get('name', d.name):<16} → {bound or '（不绑定工具，纯知识型）'}")

    # ---- 实测：工具只能来自 skill ----
    print("\n  ⚠️ 关键：**绑定的工具要传给 SkillsMiddleware，不是传给 agent**")
    print("     官方原话：Pass those tools to SkillsMiddleware instead of the agent")
    print("     （我第一版就是传给 agent 的，结果工具根本没跟着 skill 出现）\n")

    print("  实测：agent 本身一个工具都不给，工具只从 skill 绑定里来")
    try:
        backend = FilesystemBackend(root_dir=HERE, virtual_mode=True)
        mw = SkillsMiddleware(
            backend=backend,
            sources=["skills"],     # SkillSource = str | tuple[str, str]
            tools=ALL_TOOLS,        # ← 工具传这里，才会跟着 skill 一起出现
        )
        agent = create_deep_agent(
            model=build_llm(),
            tools=[],                    # ← agent 自己不带工具
            middleware=[mw],
            backend=backend,
            system_prompt="你是电商客服助手。需要查数据时用 skill 提供的工具。",
        )
        res = agent.invoke(
            {"messages": [{"role": "user", "content": "订单 SO001 到哪了"}]}
        )
        msgs = res.get("messages", [])
        used = [
            c["name"] for m in msgs if isinstance(m, AIMessage)
            for c in (m.tool_calls or [])
        ]
        print(f"    实际调用过的工具: {used}")
        print(f"    击中 Skill: {hits_from_messages(msgs) or '无'}")
        print(f"    回答: {str(msgs[-1].content)[:110] if msgs else ''}")
        if "logistics_track" in used:
            print("\n    → ✅ 工具确实是从 skill 绑定里拿到的（agent 本身没带任何工具）")
        else:
            print("\n    → ⚠️ 本次没调到 logistics_track，可能模型没选择用工具")
    except Exception as e:
        print(f"    ❌ {type(e).__name__}: {str(e)[:250]}")


# ===========================================================================
# 8. 总结
# ===========================================================================
def demo_8_summary() -> None:
    section("8. 总结：什么时候用哪种方案")

    print("  【Skill 的三种形态，按复杂度选】")
    print("    纯知识/流程    → 只有 SKILL.md，不绑工具（本文件的 after-sale）")
    print("    知识 + 工具    → SKILL.md + include_tools（order-service / product-service）")
    print("    知识 + 长文档  → SKILL.md + references/（规格文档按需读）")
    print("    知识 + 确定性计算 → SKILL.md + scripts/（执行不读入）\n")

    print("  【和文件 5/6 的关系】")
    print("    文件 5/6 讲的「判断击中哪个 Skill」的 6 种方法**依然有效**，")
    print("    但它们是在「没有标准」时自己搭的方案。")
    print("    有了标准之后：")
    print("      · Skill 从目录加载，不再写死字典")
    print("      · 判断击中 = 看 agent 读了哪个 SKILL.md（最本质）")
    print("      · 回调/事件流那些方法仍然可以用来做埋点和进度提示\n")

    print("  【写 SKILL.md 的三条硬规则】")
    print("    ① description 必须写清「做什么 + 什么时候用」，这是命中的唯一依据")
    print("    ② 正文控制在 500 行 / 5000 tokens 内，长了拆到 references/")
    print("    ③ 引用层级只做一层，别 SKILL.md → a.md → b.md 套娃\n")

    print("  【本机可以直接看的实例】")
    print("    ~/.workbuddy/skills/java_init/SKILL.md")
    print("    ~/.workbuddy/skills/pink-crystal-workbuddy-skin/SKILL.md")


def main() -> None:
    print("7. Skill 标准规范与渐进式加载（Agent Skills 开放标准 + DeepSeek）")

    demo_1_what_is_standard()
    demo_2_level1_metadata()

    if not os.getenv("DEEPSEEK_API_KEY"):
        print("\n⚠️ 没读到 DEEPSEEK_API_KEY，跳过需要调模型的演示。.env 路径：", _ENV_PATH)
        return

    demo_3_create_agent()
    demo_4_level2_and_hit()
    demo_5_level3_resources()
    demo_6_pinned()
    demo_7_tool_binding()
    demo_8_summary()

    print("\n" + "=" * 62)
    print("执行完毕。本组顺序：1 定义 → 2 公式 → 3 远程 → 4 绑定")
    print("                  → 5 路由判断(旧方案) → 6 Agent → 7 标准 Skill")


if __name__ == "__main__":
    main()
