#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
6. 实体记忆：抽取结构化事实（最新 API 版）
========================================

【Python 语法看不懂？】闭包、lambda、** 解包、推导式等见 ../PYTHON_SYNTAX.md

【实体记忆是什么】
    前面两种记忆存的是「对话原文」或「一段摘要」，都是**文本**。
    实体记忆存的是**结构化的事实**，比如：

        {
            "yangzhenyu": "人名；住在广州；9 年 Java 经验",
            "广州":   "用户所在城市",
            "Java":   "用户最熟悉的语言，9 年经验"
        }

    好处：
        · 精确：不会因为摘要而失真
        · 可查询：能直接问「yangzhenyu是谁」
        · 可更新：新事实覆盖旧事实，不会无限膨胀
        · 省 token：比塞几十轮原文便宜得多

    坏处：
        · 每轮都要多调一次模型做抽取（贵、慢）
        · 抽取可能漏、可能错



【新版怎么做】
    ① 用 with_structured_output 让模型按 schema 抽实体（见 outputParser/3）
    ② 自己维护一个 dict 当实体库
    ③ 每轮结束后更新，调用前渲染进 prompt

【DeepSeek 特别注意】
    结构化输出必须关掉思考模式，否则报：
    "Thinking mode does not support this tool_choice"
    写法：ChatOpenAI(..., extra_body={"thinking": {"type": "disabled"}})

【运行】
    ./yzy/Scripts/python.exe "aiLearn/memory/new/6.实体记忆.py"
"""

import os
from pathlib import Path
from typing import Dict

import dotenv
from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
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


def build_llm() -> ChatOpenAI:
    """普通对话用的模型。"""
    return ChatOpenAI(
        model="deepseek-flash",
        api_key=os.getenv("DEEPSEEK_API_KEY"),
        base_url=os.getenv("DEEPSEEK_API_BASE"),
        temperature=0.3,
    )


def build_extract_llm() -> ChatOpenAI:
    """【专门用来抽实体的模型】必须关掉思考模式。

    为什么单独建一个：
        DeepSeek 的思考模式和 function calling 互斥，关掉思考才能用结构化输出。
        而普通对话我们希望它保留思考（质量更好），所以两个模型实例分开。
    """
    return ChatOpenAI(
        model="deepseek-flash",
        api_key=os.getenv("DEEPSEEK_API_KEY"),
        base_url=os.getenv("DEEPSEEK_API_BASE"),
        temperature=0,
        extra_body={"thinking": {"type": "disabled"}},   # ⚠️ 关键
    )


def section(title: str) -> None:
    """打印分节标题，纯排版用。"""
    print("\n" + "=" * 62)
    print(title)
    print("=" * 62)


# ---------------------------------------------------------------------------
# 定义「抽取结果」的结构
# ---------------------------------------------------------------------------
class EntityFacts(BaseModel):
    """模型抽取实体后要按这个格式返回。

    【Java 对照】这就是个 record / DTO：
        public record EntityFacts(Map<String, String> entities) {}
    pydantic 会自动校验类型，不合格就抛 ValidationError。
    """

    entities: Dict[str, str] = Field(
        description="实体名 -> 关于这个实体的关键事实。只抽对话里明确提到的，不要猜。"
    )


EXTRACT_PROMPT = ChatPromptTemplate.from_messages([
    ("system",
     "你是一个信息抽取助手。从下面这段对话里抽取所有【实体】及其【关键事实】。\n"
     "规则：\n"
     "1. 实体可以是人名、地名、技术名词、产品名等\n"
     "2. 只抽明确提到的信息，不要推测、不要编造\n"
     "3. 事实要简短，用分号分隔多个事实\n"
     "4. 如果对话里没有实体，返回空对象"),
    ("human", "{conversation}"),
])


class EntityStore:
    """实体库：一个 dict，key 是实体名，value 是事实。

    【Java 对照】
        public class EntityStore {
            private final Map<String, String> store = new LinkedHashMap<>();
            public void merge(Map<String, String> newFacts) { store.putAll(newFacts); }
            public String render() { ... }
        }
    """

    def __init__(self) -> None:
        self.store: Dict[str, str] = {}

    def merge(self, new_facts: Dict[str, str]) -> None:
        """合并新抽出来的事实（同名实体直接覆盖）。"""
        self.store.update(new_facts)

    def render(self) -> str:
        """渲染成给 prompt 用的文本。"""
        if not self.store:
            return "（暂无实体信息）"
        return "\n".join(f"- {k}: {v}" for k, v in self.store.items())

    def __len__(self) -> int:
        return len(self.store)


def build_extractor():
    """造「抽取器」：输入一段对话文本 → 输出 EntityFacts 对象。

    【这是闭包工厂，看不懂先看 ../PYTHON_SYNTAX.md 第 1 节】
    with_structured_output 会返回一个「新的链」，直接 invoke 就拿到 pydantic 对象，
    不用自己解析 JSON。
    """
    return EXTRACT_PROMPT | build_extract_llm().with_structured_output(
        EntityFacts, method="function_calling"
    )


# ---------------------------------------------------------------------------
# 1. 先单独看抽取效果
# ---------------------------------------------------------------------------
def demo_1_extract_once() -> None:
    section("1. 单独跑一次实体抽取")

    conversation = (
        "User: 我叫yangzhenyu，今年 31 岁\n"
        "AI: 你好yangzhenyu！\n"
        "User: 我有 9 年 Java 开发经验，主要在腾讯做后端\n"
        "AI: 经验很扎实。\n"
        "User: 我现在住在广州，平时喜欢打篮球"
    )

    print("  输入对话：")
    for line in conversation.split("\n"):
        print("   ", line)

    result = build_extractor().invoke({"conversation": conversation})

    print(f"\n  抽取结果（类型是 {type(result).__name__}，不是字符串！）：")
    for name, fact in result.entities.items():
        print(f"    {name:<10} → {fact}")

    print("\n  >> 注意：拿到的是 pydantic 对象，可以直接 .entities 取字典，")
    print("     不用 json.loads，也不用担心模型多输出了别的话。")
    print("     这就是 with_structured_output 的价值（详见 outputParser/3）。")


# ---------------------------------------------------------------------------
# 2. 增量更新：新事实覆盖旧事实
# ---------------------------------------------------------------------------
def demo_2_incremental() -> None:
    section("2. ⚠️ 增量更新的坑：自由 key 下同覆盖根本不生效")

    store = EntityStore()
    extractor = build_extractor()

    rounds = [
        ("User: 我叫yangzhenyu，住在广州", "AI: 你好！"),
        ("User: 我有 9 年 Java 经验，最喜欢的框架是 Spring Boot", "AI: 很厉害。"),
        ("User: 我搬家了，现在住在深圳", "AI: 深圳也不错。"),   # 覆盖广州
    ]

    for i, (u, a) in enumerate(rounds, 1):
        facts = extractor.invoke({"conversation": f"{u}\n{a}"})
        store.merge(facts.entities)
        print(f"  第 {i} 轮抽到: {list(facts.entities.keys())}")
        print(f"          实体库现在 {len(store)} 个:")
        for k, v in store.store.items():
            print(f"            {k}: {v}")

    print("\n  ⚠️ 实测发现的坑：我原本以为「广州」会被「深圳」覆盖，")
    print("     但结果是**两个都在**——模型把「搬家」抽成了新实体「深圳」，")
    print("     而不是把「广州」的值更新掉。")

    print("\n  原因：实体名（dict 的 key）是**模型自由发挥**的，")
    print("     它可能写「居住地」「城市」「广州」「深圳」…… 每次都不一样。")
    print("     所以「同名覆盖」这个机制在自由 key 下**经常失效**。")

    print("\n  怎么修（三种办法，按推荐度排序）：")
    print("   ① 【最推荐】固定字段：别用 Dict[str,str]，改成固定的 pydantic 字段")
    print("      class Profile(BaseModel):")
    print("          name: str | None")
    print("          city: str | None")
    print("          years_of_java: int | None")
    print("      → key 由你定，更新一定生效")
    print("   ② 给抽取 prompt 明确列出「允许的实体名清单」")
    print("   ③ 抽完做一次归一化/实体链接（把「广州」「深圳」都归到 city 字段）")

    # 演示办法①：固定字段，更新一定生效
    print("\n  【用办法①实测一次】固定字段 schema：")

    class Profile(BaseModel):
        """固定字段的画像 schema——key 由我们定，不由模型定。"""

        name: str = Field(default="", description="用户姓名，没提到就留空")
        city: str = Field(default="", description="用户所在城市，没提到就留空")
        main_language: str = Field(default="", description="用户主语言，没提到就留空")

    extractor2 = EXTRACT_PROMPT | build_extract_llm().with_structured_output(
        Profile, method="function_calling"
    )
    profile = Profile()
    for text in ["我叫yangzhenyu，住在广州", "我有 9 年 Java 经验", "我搬家了，现在住在深圳"]:
        got = extractor2.invoke({"conversation": text})
        # 只覆盖「这次抽到了的」字段，空值不覆盖（否则会清空已有信息）
        profile = Profile(
            name=got.name or profile.name,
            city=got.city or profile.city,
            main_language=got.main_language or profile.main_language,
        )
        print(f"    「{text}」 → {profile.model_dump()}")

    print("\n  >> 看最后的 city：广州 → 深圳，**真的更新了**。")
    print("     这就是固定字段比自由 Dict 可靠的原因：key 由你控制。")


# ---------------------------------------------------------------------------
# 3. 完整链路：抽取 → 存 → 渲染进 prompt
# ---------------------------------------------------------------------------
def demo_3_full_chain() -> None:
    section("3. 实战：实体记忆 + 对话链")

    store = EntityStore()
    extractor = build_extractor()
    llm = build_llm()

    # prompt 里除了历史，再加一块「已知实体信息」
    prompt = ChatPromptTemplate.from_messages([
        ("system",
         "你是助手，回答用中文，尽量简短（30 字以内）。\n\n"
         "【关于用户的已知事实】\n{entities}\n"),
        MessagesPlaceholder("history"),
        ("human", "{query}"),
    ])
    chain = prompt | llm | StrOutputParser()

    history: list = []
    questions = [
        "我叫yangzhenyu，住在广州",
        "我有 9 年 Java 经验，最喜欢的框架是 Spring Boot",
        "我最近在学 LangChain",
    ]

    for i, q in enumerate(questions, 1):
        answer = chain.invoke({
            "entities": store.render(),
            "history": history,
            "query": q,
        })
        print(f"  第 {i} 轮  Q: {q}")
        print(f"          A: {answer[:40]}")

        # 每轮结束后抽取 + 入库 + 记入历史
        facts = extractor.invoke({"conversation": f"User: {q}\nAI: {answer}"})
        store.merge(facts.entities)
        history.extend([HumanMessage(q), AIMessage(answer)])
        print(f"          实体库: {len(store)} 个 → {list(store.store.keys())}")

    print("\n  最终实体库：")
    print("   " + store.render().replace("\n", "\n   "))

    # 关键验证：新起一段对话（不带 history），只看实体库能不能答对
    print("\n  【关键验证】清空对话历史，只靠实体库回答：")
    answer = chain.invoke({
        "entities": store.render(),
        "history": [],                       # 历史是空的！
        "query": "我叫什么？住在哪里？有多少年 Java 经验？",
    })
    print("   A:", answer)

    print("\n  >> 即使历史全清空，只要实体库在，模型依然答得出来。")
    print("     这就是实体记忆最强的地方：**记忆独立于对话历史**，")
    print("     换会话、换设备、跨天，实体库还在（只要持久化了）。")


# ---------------------------------------------------------------------------
# 4. 三种记忆横向对比 + 什么时候用实体记忆
# ---------------------------------------------------------------------------
def demo_4_compare() -> None:
    section("4. 三种记忆横向对比")

    rows = [
        ("存什么", "对话原文", "一段摘要文本", "结构化 KV"),
        ("额外成本", "无", "压缩时 1 次调用", "每轮 1 次调用"),
        ("老信息", "超限就丢", "保留但可能失真", "精确保留"),
        ("可查询", "❌", "❌", "✅ 直接查 key"),
        ("省 token", "最费", "中等", "最省"),
        ("实现复杂度", "最简单", "中等", "最复杂"),
    ]
    print(f"  {'维度':<10}{'缓冲/裁剪':<18}{'摘要记忆':<18}{'实体记忆'}")
    print("  " + "-" * 62)
    for a, b, c, d in rows:
        print(f"  {a:<10}{b:<18}{c:<18}{d}")

    print("\n  什么时候用实体记忆：")
    print("   ✅ 客服/陪聊：要记住用户的姓名、偏好、订单号")
    print("   ✅ 长期陪伴类产品：跨会话记住用户画像")
    print("   ✅ 信息密度高、且需要精确查询的场景")

    print("\n  什么时候别用：")
    print("   ❌ 闲聊（没实体可抽，白花钱）")
    print("   ❌ 对成本敏感（每轮多一次调用，token 翻倍）")
    print("   ❌ 对话逻辑本身很重要（实体存不下「怎么说的」）")

    print("\n  生产建议：")
    print("   · 抽取和对话**并行**做，别串行等（用 RunnableParallel，见 runnable/1）")
    print("   · 实体库持久化到 Redis/DB，key 带上 user_id")
    print("   · 给实体数量设上限，防止有人恶意刷")
    print("   · 敏感信息（手机号、身份证）**不要**存进实体库")


def main() -> None:
    print("6. 实体记忆：抽取结构化事实（DeepSeek + 最新 API）")
    print("   教材：old/LangChain实体记忆组件的使用与解析/1.*")

    if not os.getenv("DEEPSEEK_API_KEY"):
        print("\n❌ 没读到 DEEPSEEK_API_KEY，请检查 .env：", _ENV_PATH)
        return

    demo_1_extract_once()
    demo_2_incremental()
    demo_3_full_chain()
    demo_4_compare()

    print("\n" + "=" * 62)
    print("全部示例执行完毕。下一个：7.记忆选型与LangGraph方案.py")


if __name__ == "__main__":
    main()
