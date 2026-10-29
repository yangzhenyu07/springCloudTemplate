#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
1. ChatMessageHistory 基础（最新 API 版）
=======================================

【Python 语法看不懂？】闭包、lambda、** 解包、推导式等见 ../PYTHON_SYNTAX.md

【记忆（Memory）到底解决什么问题】
    LLM 的 API 是**无状态**的：你第二次调 invoke()，它完全不记得你第一次说了什么。
    所谓「记忆」，本质是：
        ① 把历史对话**存起来**（存内存 / 存文件 / 存数据库）
        ② 每次调用前把历史**读出来塞进 prompt**
        ③ 调用完把这一轮的问答**再写回去**

    所以「记忆」= 存储 + 拼装，没有魔法。理解这点，后面所有组件都好懂。

【⚠️ 这一组是 aiLearn 里变化最大的一组，先说结论】
    在 langchain-core 1.7.0 上实测：



【运行】
    ./yzy/Scripts/python.exe "aiLearn/memory/new/1.ChatMessageHistory基础.py"

    本文件**不需要 API key**，纯粹讲数据结构和接口。
"""

import subprocess
import sys
from pathlib import Path

from langchain_core.chat_history import BaseChatMessageHistory, InMemoryChatMessageHistory
from langchain_core.messages import (
    AIMessage,
    BaseMessage,
    HumanMessage,
    SystemMessage,
    get_buffer_string,
    message_to_dict,
    messages_from_dict,
)


def section(title: str) -> None:
    """打印分节标题，纯排版用。"""
    print("\n" + "=" * 62)
    print(title)
    print("=" * 62)


# ---------------------------------------------------------------------------
# 1. 最基础的用法：往里加消息、读出来
# ---------------------------------------------------------------------------
def demo_1_basic_usage() -> None:
    section("1. InMemoryChatMessageHistory：最基础的存取")

    history = InMemoryChatMessageHistory()

    # 两条便捷方法（教材里就是这两行）
    history.add_user_message("你好，我是慕小课，你是谁？")
    history.add_ai_message("你好，我是智能助手，有什么可以帮到您的？")

    print("读出来的消息列表：")
    for i, msg in enumerate(history.messages, 1):
        # type(m).__name__ 拿到类名，Java 里是 obj.getClass().getSimpleName()
        print(f"  {i}. [{type(msg).__name__}] {msg.content}")

    # ---------------------------------------------------------------
    # 【Java 对照】
    #   class ChatHistory {
    #       private final List<BaseMessage> messages = new ArrayList<>();
    #       public void addUserMessage(String s) { messages.add(new HumanMessage(s)); }
    #       public List<BaseMessage> getMessages() { return messages; }
    #   }
    # 结构一模一样，只是 Python 这边自带好几个便捷方法。
    # ---------------------------------------------------------------

    print("\n清空前条数:", len(history.messages))
    history.clear()
    print("clear() 之后条数:", len(history.messages))


# ---------------------------------------------------------------------------
# 2. 完整接口：不只有 add_user_message / add_ai_message
# ---------------------------------------------------------------------------
def demo_2_full_interface() -> None:
    section("2. 完整接口一览")

    history = InMemoryChatMessageHistory()

    # ① 一次性加多条（推荐！少一次 IO 往返）
    history.add_messages([
        SystemMessage("你是一个乐于助人的助手。"),
        HumanMessage("我叫yangzhenyu"),
        AIMessage("你好yangzhenyu，很高兴认识你！"),
    ])
    print("add_messages() 批量加 3 条 →", len(history.messages), "条")

    # ② 单条加（内部就是循环调 add_messages 里的逻辑）
    history.add_message(HumanMessage("我住在广州"))
    print("add_message() 再加 1 条 →", len(history.messages), "条")

    # ③ 系统消息也能存（很多人不知道）
    #    注意：老教材的 ConversationBufferMemory 默认**不存** system 消息
    print("\n第 1 条是:", type(history.messages[0]).__name__, "→", history.messages[0].content)

    print("\n接口方法小结：")
    print("  .messages            读（property，不是方法，别加括号）")
    print("  .add_messages(list)  批量写【推荐】")
    print("  .add_message(msg)    单条写")
    print("  .add_user_message(s) / .add_ai_message(s)   便捷写法")
    print("  .clear()             清空")
    print("  .aadd_messages / .aget_messages / .aclear   异步版本（默认内部转同步）")

    print("\n>> 官方建议：更新历史时优先用 add_messages()，")
    print("   别用 add_user_message + add_ai_message 各调一次——")
    print("   如果底层是数据库，那就变成两次 IO 往返了。")


# ---------------------------------------------------------------------------
# 3. 自己实现一个历史类（理解接口契约，为第 2 个文件的持久化做准备）
# ---------------------------------------------------------------------------
class SimpleListHistory(BaseChatMessageHistory):
    """最小可用的历史实现：内部就是一个 list。

    【为什么要自己写】
        因为 langchain_community 这个包**当前项目没装**，
        想持久化（文件 / Redis / MySQL）就得自己继承 BaseChatMessageHistory 实现。
        而且这也是理解「记忆」最好的方式：它真的只是个存取容器。

    【接口契约】只需要实现 3 个东西：
        ① messages      property，读
        ② add_messages  写
        ③ clear         清空
    异步方法（aadd_messages / aget_messages / aclear）有默认实现，
    内部会转调同步版本，不用重写。
    """

    def __init__(self) -> None:
        # 注意：不要在这里声明 messages 字段，因为基类要求它是 property
        self._store: list[BaseMessage] = []

    @property
    def messages(self) -> list[BaseMessage]:
        """读：返回全部消息。

        【Java 对照】这就是个 getter：
            public List<BaseMessage> getMessages() { return store; }
        Python 的 @property 让你能写 history.messages 而不是 history.messages()。
        """
        return self._store

    def add_messages(self, messages) -> None:
        """写：追加一批消息。"""
        self._store.extend(messages)

    def clear(self) -> None:
        """清空。基类里这是唯一的抽象方法，必须实现。"""
        self._store = []


def demo_3_custom_history() -> None:
    section("3. 自己实现一个历史类（理解接口契约）")

    history = SimpleListHistory()
    history.add_messages([
        HumanMessage("我叫yangzhenyu"),
        AIMessage("你好！"),
    ])
    print("自实现的 history：", [m.content for m in history.messages])
    history.clear()
    print("clear() 之后：", history.messages)

    print("\n>> 关键认知：所谓「记忆组件」，本质就是")
    print("   【一个能读能写的消息列表 + 约定好的接口】。")
    print("   换成文件存储 = 把 list 换成读写文件（第 2 个文件）")
    print("   换成 Redis   = 把 list 换成 redis.lpush / lrange")
    print("   换成 MySQL   = 把 list 换成 INSERT / SELECT")


# ---------------------------------------------------------------------------
# 4. 序列化：持久化必须会的两对函数
# ---------------------------------------------------------------------------
def demo_4_serialize() -> None:
    section("4. 序列化：怎么把消息存进文件/数据库")

    messages = [
        SystemMessage("你是助手"),
        HumanMessage("我叫yangzhenyu"),
        AIMessage("你好yangzhenyu！"),
    ]

    # ① 消息 → 字典（能 json.dumps）
    dicts = [message_to_dict(m) for m in messages]
    print("message_to_dict 之后（这就是存文件的格式）：")
    for d in dicts:
        print("  ", d)

    # ② 字典 → 消息（读文件时用）
    restored = messages_from_dict(dicts)
    print("\nmessages_from_dict 还原：", [type(m).__name__ for m in restored])
    print("  内容是否一致:", [m.content for m in restored] == [m.content for m in messages])

    # ③ 拼成一整段文本（有些场景要把历史塞进 prompt 字符串里）
    text = get_buffer_string(messages)
    print("\nget_buffer_string() 拼成文本（老教材的 FileChatMessageHistory 就是这么塞进 prompt 的）：")
    print("  " + text.replace("\n", "\n  "))

    print("\n>> 用哪个？")
    print("   · 结构化存储（文件/DB）→ message_to_dict / messages_from_dict")
    print("   · 直接拼进 prompt 文本 → get_buffer_string")
    print("   · 正常使用（塞 MessagesPlaceholder）→ 都不用，直接传 messages 列表")



def main() -> None:
    print("1. ChatMessageHistory 基础（最新 API，无需 API key）")
    print("   教材：old/ChatMessageHistory组件上手与源码解析/1.*")

    demo_1_basic_usage()
    demo_2_full_interface()
    demo_3_custom_history()
    demo_4_serialize()

    print("\n" + "=" * 62)
    print("全部示例执行完毕。下一个：2.持久化历史存储.py")


if __name__ == "__main__":
    main()
