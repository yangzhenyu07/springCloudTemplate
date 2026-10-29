#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
2. 持久化历史存储（最新 API 版）
===============================

【Python 语法看不懂？】闭包、lambda、** 解包、推导式等见 ../PYTHON_SYNTAX.md


    自己继承 BaseChatMessageHistory 实现一个文件版，代码不到 40 行。
    这样做的好处：
        ① 零额外依赖
        ② 把「持久化」这件事的原理彻底搞明白（就是读写 JSON）
        ③ 换成 Redis / MySQL 只是把读写换掉，接口一模一样



【运行】
    ./yzy/Scripts/python.exe "aiLearn/memory/new/2.持久化历史存储.py"

    本文件**不需要 API key**。会在脚本所在目录写一个 _history_demo/ 目录做演示。
"""

import json
from pathlib import Path
from typing import Sequence

from langchain_core.chat_history import BaseChatMessageHistory
from langchain_core.messages import (
    AIMessage,
    BaseMessage,
    HumanMessage,
    message_to_dict,
    messages_from_dict,
)

# 演示文件放在脚本同目录下，方便你看一眼长什么样
STORE_DIR = Path(__file__).resolve().parent / "_history_demo"


def section(title: str) -> None:
    """打印分节标题，纯排版用。"""
    print("\n" + "=" * 62)
    print(title)
    print("=" * 62)


# ---------------------------------------------------------------------------
# 核心：自己实现一个文件版历史
# ---------------------------------------------------------------------------
class JsonFileChatMessageHistory(BaseChatMessageHistory):
    """把对话历史存成 JSON 文件，一个会话一个文件。

    【接口契约】和第 1 个文件里的 SimpleListHistory 完全一样，只是存储换了：
        读 messages  → 从文件 json.load
        写 add_messages → 先读出来、追加、再整体写回
        清 clear     → 删文件

    【Java 对照】
        public class JsonFileChatMessageHistory implements ChatMessageHistory {
            private final Path file;
            public List<BaseMessage> getMessages() { ... }   // ObjectMapper.readValue
            public void addMessages(List<BaseMessage> ms) { ... }  // read + addAll + write
            public void clear() { Files.deleteIfExists(file); }
        }

    ⚠️ 这个实现是**教学版**：整体读写，没有加锁、没有原子写。
       生产环境请用 Redis / Postgres，或 LangGraph 的 checkpointer。
    """

    def __init__(self, file_path: str | Path) -> None:
        # 【注意】不能把字段命名为 messages —— 基类要求 messages 是 property，
        # 这里换了个名字存消息，真正的 messages 在下面用 @property 暴露。
        self.file_path = Path(file_path)
        # parent.mkdir：父目录不存在就创建，exist_ok=True 表示已存在也不报错
        self.file_path.parent.mkdir(parents=True, exist_ok=True)

    @property
    def messages(self) -> list[BaseMessage]:
        """读：文件不存在就返回空列表（第一次对话时必然走到这个分支）。"""
        if not self.file_path.exists():
            return []
        try:
            data = json.loads(self.file_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            # 文件被写坏了不要整个应用崩掉，退化成空历史更安全
            return []
        return messages_from_dict(data)

    def add_messages(self, messages: Sequence[BaseMessage]) -> None:
        """写：读出旧的全部 → 追加新的 → 整体写回。"""
        all_messages = list(self.messages)                              # 1. 读旧
        all_messages.extend(messages)                                   # 2. 追加
        serialized = [message_to_dict(m) for m in all_messages]         # 3. 转字典
        self.file_path.write_text(
            json.dumps(serialized, ensure_ascii=False, indent=2),       # ensure_ascii=False 保证中文可读
            encoding="utf-8",
        )

    def clear(self) -> None:
        """清空：直接删文件。"""
        if self.file_path.exists():
            self.file_path.unlink()


# ---------------------------------------------------------------------------
# 1. 基本读写 + 落盘文件长什么样
# ---------------------------------------------------------------------------
def demo_1_basic_persist() -> None:
    section("1. 写进文件，再读出来")

    file_path = STORE_DIR / "muxiaoke.json"
    history = JsonFileChatMessageHistory(file_path)

    history.add_messages([
        HumanMessage("你好，我是yangzhenyu，你是谁？"),
        AIMessage("你好yangzhenyu，我是智能助手！"),
        HumanMessage("我住在广州"),
    ])

    print(f"文件位置: {file_path}")
    print(f"文件是否存在: {file_path.exists()}")
    print("\n文件内容（这就是持久化的真面目，就是个 JSON 数组）：")
    content = file_path.read_text(encoding="utf-8")
    for line in content.splitlines()[:12]:
        print("  " + line)
    print("  ...")

    print("\n重新读出来（模拟程序重启）：")
    reloaded = JsonFileChatMessageHistory(file_path)
    for m in reloaded.messages:
        print(f"  [{type(m).__name__}] {m.content}")

    print("\n>> 关键点：重新 new 一个对象，数据还在——这就是持久化的意义。")


# ---------------------------------------------------------------------------
# 2. 多会话隔离：一个会话一个文件
# ---------------------------------------------------------------------------
def demo_2_multi_session() -> None:
    section("2. 多会话隔离：一个 session 一个文件")

    # 【这是个「闭包工厂」，看不懂先看 ../PYTHON_SYNTAX.md 第 1 节】
    # 外层接收「存储目录」，内层接收 session_id 返回对应的历史对象。
    def get_history(session_id: str) -> JsonFileChatMessageHistory:
        return JsonFileChatMessageHistory(STORE_DIR / f"{session_id}.json")

    # 用户 A 聊了自己的事
    get_history("user_a").add_messages([
        HumanMessage("我叫yangzhenyu，我喜欢打篮球"),
    ])
    # 用户 B 聊了别的
    get_history("user_b").add_messages([
        HumanMessage("我叫taoyutian，我喜欢游泳"),
    ])

    # 各自加一条，互不影响
    get_history("user_a").add_messages([AIMessage("好的，记住你喜欢篮球")])
    get_history("user_b").add_messages([AIMessage("好的，记住你喜欢游泳")])

    for sid in ("user_a", "user_b"):
        print(f"\n  [{sid}] 的历史：")
        for m in get_history(sid).messages:
            print(f"    [{type(m).__name__}] {m.content}")

    print("\n  磁盘上的文件：", sorted(p.name for p in STORE_DIR.glob("*.json")))
    print("\n>> 多会话隔离的本质：**给每个会话一个独立的 key**（这里是文件名）。")
    print("   换成 Redis 就是 key = chat:{session_id}；换成 MySQL 就是 where session_id = ?")


# ---------------------------------------------------------------------------
# 3. 生产环境该用什么：现成实现 vs 自己写
# ---------------------------------------------------------------------------
def demo_3_production_options() -> None:
    section("3. 生产环境有哪些现成实现")


    print("\n  选型建议（按场景）：")
    print("   · 纯 LCEL 链、简单项目     → 自己实现（本文件这样）或 RedisChatMessageHistory")
    print("   · 用 agent                 → LangGraph checkpointer（见第 7 个文件，官方推荐）")
    print("   · 要跨会话的长期记忆        → LangGraph Store（langgraph.store）")

    print("\n  ⚠️ 生产必做的三件事（教学版没做）：")
    print("   ① 加锁 / 原子写：并发下「读-改-写」会丢消息")
    print("   ② 设过期：Redis 用 TTL，别让历史无限增长")
    print("   ③ 裁剪上限：历史太长要 trim（见第 4 个文件）")


# ---------------------------------------------------------------------------
# 4. 踩坑：文件损坏时会怎样
# ---------------------------------------------------------------------------
def demo_4_corrupted_file() -> None:
    section("4. 实测：文件写坏了会怎样")

    bad = STORE_DIR / "corrupted.json"
    bad.write_text("{ 这不是合法 JSON", encoding="utf-8")

    history = JsonFileChatMessageHistory(bad)
    print("  故意写入非法 JSON，然后读 messages：")
    print("   读到:", history.messages)
    print("   是否正常返回:", isinstance(history.messages, list))

    print("\n  >> 因为 messages 里做了 try/except JSONDecodeError 兜底，")
    print("     损坏时退化成空历史，不会让整个服务崩掉。")
    print("     这是**防御性编程**：宁可丢历史，也不要 500。")

    # 清理演示文件
    bad.unlink(missing_ok=True)


def main() -> None:
    print("2. 持久化历史存储（最新 API，无需 API key）")
    print("   教材：old/ChatMessageHistory组件上手与源码解析/2.*")

    demo_1_basic_persist()
    demo_2_multi_session()
    demo_3_production_options()
    demo_4_corrupted_file()

    print("\n" + "=" * 62)
    print("全部示例执行完毕。演示文件留在:", STORE_DIR)
    print("下一个：3.RunnableWithMessageHistory.py（这组最核心的一个）")


if __name__ == "__main__":
    main()
