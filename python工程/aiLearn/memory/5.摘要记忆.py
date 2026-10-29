#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
5. 摘要记忆：用 LCEL 自己搭（最新 API 版）
========================================

【Python 语法看不懂？】闭包、lambda、** 解包、推导式等见 ../PYTHON_SYNTAX.md

【摘要记忆解决什么问题】
    上一节的 trim_messages 是「直接扔掉老的对话」——扔了就真没了。
    但有些信息是早期说的、后面还要用（比如「我叫yangzhenyu」「我有 9 年 Java 经验」）。

    摘要记忆的思路：
        老的对话 → 让模型压缩成一段话（摘要） → 摘要 + 最近 N 条原始对话 一起送给模型

    这就是教材里 ConversationSummaryBufferMemory 干的事：
    summary（摘要）+ buffer（最近缓冲）混合。

【现在怎么办】
    ConversationSummaryBufferMemory 住在 langchain.memory 里，**已经没了**（见第 4 个文件实测）。
    好消息是这个组件本来就没多少代码，用 LCEL 30 行就能自己搭出来，
    而且搭完你会彻底明白它到底在干什么。

【新旧对比】


    新版：自己写一个 summarize_if_needed() 函数 + 一条 LCEL 链
          # 白盒：摘要 prompt 你能改、阈值你能调、存哪你能定

【运行】
    ./yzy/Scripts/python.exe "aiLearn/memory/new/5.摘要记忆.py"
"""

import os
from pathlib import Path

import dotenv
from langchain_core.chat_history import BaseChatMessageHistory, InMemoryChatMessageHistory
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.runnables import RunnableLambda, RunnablePassthrough
from langchain_core.runnables.history import RunnableWithMessageHistory
from langchain_openai import ChatOpenAI


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
    """构造 DeepSeek 模型。"""
    return ChatOpenAI(
        model="deepseek-flash",
        api_key=os.getenv("DEEPSEEK_API_KEY"),
        base_url=os.getenv("DEEPSEEK_API_BASE"),
        temperature=0.3,
    )


def section(title: str) -> None:
    """打印分节标题，纯排版用。"""
    print("\n" + "=" * 62)
    print(title)
    print("=" * 62)


# ---------------------------------------------------------------------------
# 核心 1：把「旧对话 + 旧摘要」压缩成「新摘要」
# ---------------------------------------------------------------------------
SUMMARY_PROMPT = ChatPromptTemplate.from_messages([
    ("system",
     "你是一个对话摘要助手。请把【已有摘要】和【新增对话】合并成一份新的摘要。\n"
     "要求：\n"
     "1. 保留所有关键事实（人名、数字、偏好、结论），不要丢失\n"
     "2. 用中文，控制在 200 字以内\n"
     "3. 只输出摘要本身，不要任何解释"),
    MessagesPlaceholder("new_messages"),
    ("human", "已有摘要（可能是空的）：\n{existing_summary}\n\n请输出合并后的新摘要："),
])


def build_summarizer():
    """造一个「摘要器」：输入 (已有摘要, 新增消息) → 输出 新摘要。

    【这是个闭包工厂，看不懂先看 ../PYTHON_SYNTAX.md 第 1 节】
    外层不接参数也写成函数，是为了把「链的组装」和「链的使用」分开，
    换个模型只要改这里。
    """
    return SUMMARY_PROMPT | build_llm() | StrOutputParser()


def summarize(existing_summary: str, new_messages: list[BaseMessage]) -> str:
    """把已有摘要和新增消息合并成一份新摘要。

    这就是老组件里「自动调模型做摘要」的那一步，拆出来就 4 行。
    """
    summarizer = build_summarizer()
    return summarizer.invoke({
        "existing_summary": existing_summary or "（暂无）",
        "new_messages": new_messages,
    })


# ---------------------------------------------------------------------------
# 1. 先看摘要本身好不好用
# ---------------------------------------------------------------------------
def demo_1_summarize_once() -> None:
    section("1. 摘要函数单独跑一次")

    conversation = [
        HumanMessage("我叫yangzhenyu，今年 31 岁"),
        AIMessage("你好yangzhenyu！"),
        HumanMessage("我有 9 年 Java 开发经验，主要在腾讯做后端"),
        AIMessage("厉害，Java 后端经验很扎实。"),
        HumanMessage("我住在广州，平时喜欢打篮球"),
        AIMessage("广州是个好地方，篮球也是很好的运动。"),
    ]

    print("  原始对话（6 条）：")
    for m in conversation:
        print(f"    [{type(m).__name__}] {m.content}")

    result = summarize("", conversation)
    print("\n  生成的摘要：")
    print("   ", result)

    print(f"\n  压缩比：原文 {sum(len(m.content) for m in conversation)} 字 → 摘要 {len(result)} 字")

    # 增量摘要：再来一轮对话，合并进已有摘要
    more = [
        HumanMessage("我最喜欢的框架是 Spring Boot"),
        AIMessage("Spring Boot 确实是 Java 后端的主流选择。"),
    ]
    result2 = summarize(result, more)
    print("\n  追加两轮后再摘要（增量更新，旧信息没丢）：")
    print("   ", result2)
    print("\n  >> 关键：摘要是**增量**的——把旧摘要和新对话一起喂给模型，")
    print("     而不是只喂新对话（否则旧信息会丢）。")


# ---------------------------------------------------------------------------
# 核心 2：完整的「摘要 + 缓冲」策略
# ---------------------------------------------------------------------------
class SummaryBufferMemory:
    """自己实现的「摘要 + 缓冲」混合记忆。

    策略（这就是 ConversationSummaryBufferMemory 的全部逻辑）：
        · 历史总长度 < max_recent 条  → 原样全送
        · 超过                        → 老的部分压成摘要，只保留最近 keep_recent 条原文

    【Java 对照】
        public class SummaryBufferMemory {
            private String summary = "";
            private final List<BaseMessage> buffer = new ArrayList<>();
            private final int maxRecent, keepRecent;
            public List<BaseMessage> getMessagesForPrompt() { ... }
            public void addTurn(BaseMessage user, BaseMessage ai) { ... }
        }
    """

    def __init__(self, max_recent: int = 6, keep_recent: int = 4) -> None:
        self.summary: str = ""                 # 累积摘要
        self.buffer: list[BaseMessage] = []    # 最近的原始消息
        self.max_recent = max_recent           # 超过这个条数就触发摘要
        self.keep_recent = keep_recent         # 摘要后保留多少条原文
        self.summary_count = 0                 # 统计用：做过几次摘要

    def add_turn(self, user_msg: BaseMessage, ai_msg: BaseMessage) -> None:
        """每轮对话结束后调用：先入 buffer，再判断要不要压缩。"""
        self.buffer.extend([user_msg, ai_msg])

        if len(self.buffer) > self.max_recent:
            # 要被挤掉的是 buffer 里「最早的那部分」
            to_summarize = self.buffer[:-self.keep_recent]
            self.summary = summarize(self.summary, to_summarize)
            self.summary_count += 1
            # 只保留最近 keep_recent 条原文
            self.buffer = self.buffer[-self.keep_recent:]

    def messages_for_prompt(self) -> list[BaseMessage]:
        """给 prompt 用的消息列表：摘要（如有）+ 最近原文。"""
        result: list[BaseMessage] = []
        if self.summary:
            # 用 SystemMessage 承载摘要，模型会把它当背景信息
            result.append(SystemMessage(f"【之前对话的摘要】\n{self.summary}"))
        result.extend(self.buffer)
        return result

    def stats(self) -> str:
        """给 demo 打印用的状态摘要。"""
        return (f"摘要 {self.summary_count} 次 / 摘要文本 {len(self.summary)} 字 / "
                f"原始缓冲 {len(self.buffer)} 条")


# ---------------------------------------------------------------------------
# 2. 观察压缩是怎么一步步发生的
# ---------------------------------------------------------------------------
def demo_2_buffer_grows() -> None:
    section("2. 实测：历史增长时，摘要是怎么触发的")

    memory = SummaryBufferMemory(max_recent=6, keep_recent=4)

    # 【这是个闭包工厂】外层捕获 i，内层是真正的问题生成逻辑
    # 这里用普通循环更简单，闭包工厂的例子见 runnable/2
    rounds = [
        ("我叫yangzhenyu，今年 31 岁", "你好yangzhenyu！"),
        ("我有 9 年 Java 开发经验", "很扎实的经验。"),
        ("我住在广州", "广州是个好城市。"),
        ("我喜欢打篮球和游泳", "运动习惯很好。"),
        ("我最喜欢的框架是 Spring Boot", "Java 后端主流选择。"),
        ("我正在学习 LangChain", "很好的方向！"),
    ]

    for i, (q, a) in enumerate(rounds, 1):
        memory.add_turn(HumanMessage(q), AIMessage(a))
        print(f"  第 {i} 轮后 → {memory.stats()}")
        if memory.summary:
            print(f"           摘要内容: {memory.summary[:56]}...")

    print("\n  最终送给 prompt 的内容：")
    for m in memory.messages_for_prompt():
        print(f"    [{type(m).__name__}] {str(m.content)[:60]}")

    print("\n  >> 观察点：缓冲超过 6 条就压一次，压完只留 4 条原文。")
    print("     所以无论聊多少轮，送给模型的长度是**有上界**的——这就是摘要记忆的意义。")


# ---------------------------------------------------------------------------
# 3. 挂到完整链上（配合 RunnableWithMessageHistory）
# ---------------------------------------------------------------------------
def demo_3_full_chain() -> None:
    section("3. 实战：摘要记忆 + 完整对话链")

    # ① 每个 session 一份 memory（真实项目里存 Redis，这里存内存 dict）
    memories: dict[str, SummaryBufferMemory] = {}

    def get_memory(session_id: str) -> SummaryBufferMemory:
        if session_id not in memories:
            memories[session_id] = SummaryBufferMemory(max_recent=6, keep_recent=4)
        return memories[session_id]

    # ② prompt：历史占位符 + 本轮问题
    prompt = ChatPromptTemplate.from_messages([
        ("system", "你是助手，回答用中文，尽量简短（30 字以内）。"),
        MessagesPlaceholder("history"),
        ("human", "{query}"),
    ])

    llm = build_llm()

    # ③ 每轮结束后手动把这一轮写进 memory
    #    （用 RunnableWithMessageHistory 的自动写入 + 这里自己做摘要，会重复，
    #     所以这个 demo 用普通链 + 手动管理，逻辑更清楚）
    session_id = "summary_demo"
    questions = [
        "我叫yangzhenyu，记住这个名字",
        "我有 9 年 Java 经验，现在在学 LangChain",
        "我住在广州，喜欢打篮球",
        "我最喜欢的框架是 Spring Boot",
        "我的幸运数字是 7",
    ]

    for i, q in enumerate(questions, 1):
        memory = get_memory(session_id)
        history = memory.messages_for_prompt()

        answer = (prompt | llm | StrOutputParser()).invoke({
            "history": history,
            "query": q,
        })

        memory.add_turn(HumanMessage(q), AIMessage(answer))
        print(f"  第 {i} 轮  Q: {q}")
        print(f"          A: {answer[:40]}")
        print(f"          状态: {memory.stats()}")

    # ④ 关键验证：问一个「最早说的、已经被摘掉」的信息
    memory = get_memory(session_id)
    print("\n  【关键验证】问一个第 1 轮说的、早就不在原文缓冲里的信息：")
    final = (prompt | llm | StrOutputParser()).invoke({
        "history": memory.messages_for_prompt(),
        "query": "我叫什么名字？我的幸运数字是多少？",
    })
    print("   A:", final)

    print("\n  >> 如果摘要做得好，这里应该能答出「yangzhenyu」和「7」。")
    print("     这就是摘要记忆比纯裁剪强的地方：**老信息没丢，只是被压缩了**。")


# ---------------------------------------------------------------------------
# 4. 什么时候该用摘要，什么时候该裁剪
# ---------------------------------------------------------------------------
def demo_4_when_to_use() -> None:
    section("4. 裁剪 vs 摘要，怎么选")

    rows = [
        ("实现方式", "trim_messages 纯函数", "要调一次模型做摘要"),
        ("成本", "零成本", "每次压缩多一次 LLM 调用（要花钱）"),
        ("延迟", "无", "压缩那一轮会多等 1~2 秒"),
        ("老信息", "直接丢弃", "压缩保留（可能失真）"),
        ("信息保真", "保留的部分 100% 准确", "摘要可能丢失细节或产生幻觉"),
        ("适合场景", "闲聊、问答，前文不太重要", "长对话、关键信息在开头"),
    ]
    print(f"  {'维度':<12}{'裁剪（第 4 个文件）':<28}{'摘要（本文件）'}")
    print("  " + "-" * 74)
    for a, b, c in rows:
        print(f"  {a:<12}{b:<28}{c}")

    print("\n  生产上的常见组合（也是最实用的）：")
    print("   ① 用 trim_messages 做**硬上限**（保命，防止超窗口报错）")
    print("   ② 超过阈值时才做摘要（控制成本）")
    print("   ③ 摘要也设长度上限（否则摘要自己会越来越长）")

    print("\n  ⚠️ 摘要的两个坑：")
    print("   ① 摘要会**累积误差**：每次压缩都可能丢一点信息，10 次之后就可能失真")
    print("   ② 摘要本身也要设上限，否则「摘要的摘要」会越来越抽象")
    print("      （老组件的 max_token_limit 就是管这个的）")


def main() -> None:
    print("5. 摘要记忆：用 LCEL 自己搭（DeepSeek + 最新 API）")
    print("   教材：old/LangChain摘要记忆组件的使用与解析/1.*")

    if not os.getenv("DEEPSEEK_API_KEY"):
        print("\n❌ 没读到 DEEPSEEK_API_KEY，请检查 .env：", _ENV_PATH)
        return

    demo_1_summarize_once()
    demo_2_buffer_grows()
    demo_3_full_chain()
    demo_4_when_to_use()

    print("\n" + "=" * 62)
    print("全部示例执行完毕。下一个：6.实体记忆.py")


if __name__ == "__main__":
    main()
