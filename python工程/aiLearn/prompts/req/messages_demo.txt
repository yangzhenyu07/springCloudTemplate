"""
langchain_core.messages 是什么、有什么作用（详细注释版）
========================================================

【一句话定义】
    messages 是 LangChain 对「大模型对话输入输出」的统一抽象：
        一条消息 = 角色(role) + 内容(content) + 元数据(metadata)

【为什么需要它，而不是直接用字符串？】
    1. 大模型 API 的入参本质就是「带角色的消息数组」，不是一整段文本。
    2. 角色决定模型如何理解这句话：
           system → 系统指令（优先级最高）
           human  → 用户说的话
           ai     → 模型自己说过的
           tool   → 工具返回的结果
       如果把所有话混成一串字符串，模型就分不清哪句是谁说的了。
    3. 只有做成了统一对象，才能对对话做「上下文工程」：
       裁剪(trim)、过滤(filter)、合并(merge)、序列化、流式拼接。

【四大作用（本文件按这个顺序演示）】
    作用一：承载多轮对话历史
    作用二：工具调用（Function Calling）链路
    作用三：多模态内容块
    作用四：上下文工程 —— 这才是 messages 最大的价值

【运行】
    ./yzy/Scripts/python.exe aiLearn/messages_demo.py
"""

from langchain_core.messages import (
    AIMessage,
    AIMessageChunk,
    BaseMessage,
    ChatMessage,
    HumanMessage,
    SystemMessage,
    ToolMessage,
    convert_to_messages,
    convert_to_openai_messages,
    filter_messages,
    get_buffer_string,
    merge_message_runs,
    messages_from_dict,
    messages_to_dict,
    trim_messages,
)


def section(title: str) -> None:
    print("\n" + "=" * 62)
    print(title)
    print("=" * 62)


def dump(messages, indent: str = "  ") -> None:
    """打印消息数组。AI 消息带 tool_calls、ToolMessage 带 id 时额外标注。"""
    for i, m in enumerate(messages, 1):
        extra = ""
        if isinstance(m, AIMessage) and m.tool_calls:
            extra = f"  tool_calls={m.tool_calls}"
        if isinstance(m, ToolMessage):
            extra = f"  tool_call_id={m.tool_call_id}"
        print(f"{indent}[{i}] {type(m).__name__:<14} | {m.content!r}{extra}")


# ===========================================================================
# 1. 一条消息到底长什么样
# ---------------------------------------------------------------------------
# 核心字段：
#   type    → 角色，对应 API 里的 role（system/human/ai/tool）
#   content → 内容，可以是 str，也可以是内容块 list（多模态时用）
#   id      → 消息唯一标识，用于追踪（可为空）
# 其他：response_metadata（模型返回的元信息）、usage_metadata（token 消耗）
# ===========================================================================
def demo_1_what_is_message() -> None:
    section("1. 一条消息到底是什么")

    msg = HumanMessage(content="帮我看下订单状态")
    print("类型      :", type(msg).__name__)
    print("角色 role :", msg.type, " <-- 这就是 OpenAI API 里的 role 字段")
    print("内容      :", msg.content)
    print("id        :", msg.id, "(可为空，用于追踪)")
    print("转字典    :", msg.model_dump())

    print("\n>> 转成模型 API 真正认识的格式（OpenAI messages 数组）：")
    print("  ", convert_to_openai_messages([msg]))
    print(">> 看到了吗：所谓调模型，就是把这样的数组 POST 过去。")


# ===========================================================================
# 2. 五种核心消息类型
# ---------------------------------------------------------------------------
# 记忆要点：
#   SystemMessage → 定规矩，人设/格式/边界
#   HumanMessage  → 用户说的话
#   AIMessage     → 模型说的（回复、历史、预填充）
#   ToolMessage   → 工具结果，靠 tool_call_id 回关联
#   ChatMessage   → 自定义角色，非主流模型才用
# ===========================================================================
def demo_2_message_types() -> None:
    section("2. 五种核心消息类型（对应不同 role）")

    table = [
        (SystemMessage("你是资深 DBA"), "system", "系统指令，设定人设/规则/约束，优先级最高"),
        (HumanMessage("怎么优化慢查询？"), "human", "用户说的话（API 里叫 user）"),
        (AIMessage("先看执行计划。"), "ai", "模型的回复，也用于拼接历史/预填充"),
        (ToolMessage(content="rows=10", tool_call_id="call_1"), "tool", "工具执行结果，靠 tool_call_id 回关联"),
        (ChatMessage(content="自定义", role="custom_role"), "custom_role", "自定义角色，非主流模型可能用到"),
    ]
    for msg, role, desc in table:
        print(f"  {type(msg).__name__:<14} role={role:<12} {desc}")

    print("\n>> 也可以用 dict 直接构造 —— 从数据库/前端拿到 JSON 时很有用：")
    dump(convert_to_messages([
        {"role": "system", "content": "你是助手"},
        {"role": "user", "content": "你好"},
        {"role": "assistant", "content": "你好，有什么可以帮你？"},
    ]))


# ===========================================================================
# 3. 作用一：承载多轮对话历史
# ---------------------------------------------------------------------------
# 这是 messages 最基础的用途。
# "多轮对话"的本质就是：不断往这个列表末尾追加消息，再整段发给模型。
# 模型能记住前面说了什么，靠的就是这个列表，而不是模型本身有记忆。
# ===========================================================================
def demo_3_history() -> None:
    section("3. 作用一：承载多轮对话历史")

    history = [
        SystemMessage("你是 PostgreSQL 专家。"),
        HumanMessage("怎么定位慢查询？"),
        AIMessage("用 EXPLAIN ANALYZE 看执行计划。"),
        HumanMessage("那索引该怎么建？"),
    ]
    dump(history)
    print("\n>> 多轮对话靠的就是不断追加这个列表，再整段发给模型。")
    print(">> 模型本身是无状态的，它「记住」的东西全在这个数组里。")

    print("\n>> get_buffer_string(): 把消息压成纯文本")
    print("   常用于打日志、调试，或喂给老式文本模型：")
    print("  ", repr(get_buffer_string(history)))


# ===========================================================================
# 4. 作用二：工具调用（Function Calling）链路
# ---------------------------------------------------------------------------
# 完整链路（三步）：
#   ① 模型返回 AIMessage，content 为空，但带 tool_calls（想调哪个工具、参数是什么）
#   ② 你的代码执行工具，把结果包成 ToolMessage，用 tool_call_id 关联回去
#   ③ 把「原始问题 + AI 的调用意图 + 工具结果」整段再发给模型，让它总结
#
# ⚠️ 最常见的坑：tool_call_id 必须和 tool_calls[].id 一字不差，否则模型 API 直接报错。
# ===========================================================================
def demo_4_tool_calling() -> None:
    section("4. 作用二：工具调用链路 AIMessage.tool_calls -> ToolMessage")

    # 第 1 步：模型决定要调工具
    ai = AIMessage(
        content="",
        tool_calls=[{
            "name": "query_weather",
            "args": {"city": "杭州"},
            "id": "call_abc123",
            "type": "tool_call",
        }],
    )
    print("① 模型返回（它想调工具，所以 content 是空的）:")
    dump([ai])

    # 第 2 步：执行工具，把结果用 ToolMessage 回填
    tool_result = ToolMessage(content="杭州 晴 25℃", tool_call_id="call_abc123")
    print("\n② 工具执行结果回填:")
    dump([tool_result])

    # 第 3 步：把完整链路再发给模型做总结
    full = [HumanMessage("杭州天气怎么样？"), ai, tool_result]
    print("\n③ 第 3 次请求时发给模型的完整消息链路:")
    dump(full)
    print("\n>> tool_call_id 必须和 tool_calls 里的 id 对上，否则模型 API 会报错。")


# ===========================================================================
# 5. 作用三：多模态内容块（content blocks）
# ---------------------------------------------------------------------------
# 关键点：content 不只能是字符串，还可以是「内容块列表」。
# 这是 langchain-core 1.x 的标准化做法，用来承载图片/音频/视频/文件。
#
# 便利属性 .text：不管 content 是 str 还是 list，都能直接取到纯文本，
# 不用自己判断类型。
# ===========================================================================
def demo_5_multimodal() -> None:
    section("5. 作用三：多模态内容块（content 可以是 list）")

    msg = HumanMessage(content=[
        {"type": "text", "text": "这两张图有什么区别？"},
        {"type": "image_url", "image_url": {"url": "https://example.com/a.png"}},
        {"type": "image_url", "image_url": {"url": "https://example.com/b.png"}},
    ])
    print("content 类型:", type(msg.content).__name__)
    for block in msg.content:
        print("   block:", block)

    print("\n>> 纯文本消息也能用 .text 直接取字符串，不用管是不是 list:")
    print("   HumanMessage('你好').text =", HumanMessage("你好").text)


# ===========================================================================
# 6. 作用四：上下文工程 —— messages 最大的价值所在
# ---------------------------------------------------------------------------
# 为什么重要：上下文窗口有限且按 token 收费。
# 对话轮数一多，就必须对历史做"裁剪和整理"，否则要么超窗口报错，要么成本爆炸。
#
# 三件套：
#   merge_message_runs → 合并连续同类消息（省 token）
#   filter_messages    → 按角色过滤（只留需要的）
#   trim_messages      → 按 token 预算截断（生产必备）
# ===========================================================================
def demo_6_context_engineering() -> None:
    section("6. 作用四：上下文工程 —— 裁剪 / 过滤 / 合并")

    # 6.1 合并连续的同类消息
    # 场景：用户连发好几条消息，合并成一条能省token，也更符合模型预期
    print("6.1 merge_message_runs()  合并连续同类消息")
    msgs = [
        HumanMessage("在吗"),
        HumanMessage("我想问个问题"),
        SystemMessage("你是助手"),
        HumanMessage("问题是什么"),
    ]
    print("  合并前:", [m.content for m in msgs])
    print("  合并后:", [m.content for m in merge_message_runs(msgs)])
    print("  >> 中间被 SystemMessage 打断，所以后面那条没被合并进去。")

    # 6.2 过滤：只保留某些角色
    print("\n6.2 filter_messages()  按角色过滤")
    conv = [
        SystemMessage("你是助手"),
        HumanMessage("q1"), AIMessage("a1"),
        HumanMessage("q2"), AIMessage("a2"),
    ]
    print("  只要 human      :", [m.content for m in filter_messages(conv, include_types=["human"])])
    print("  排除 system     :", [m.content for m in filter_messages(conv, exclude_types="system")])

    # 6.3 裁剪：对话太长时按 token 预算截断
    print("\n6.3 trim_messages()  按 token 预算裁剪（生产必备）")
    long_conv = [SystemMessage("你是助手")] + [
        HumanMessage(f"历史问题{i}") for i in range(1, 6)
    ]
    # token_counter 这里用 len 演示，生产应换成真实的 tokenizer
    # （比如 tiktoken，或模型厂商提供的计数接口）
    trimmed = trim_messages(
        long_conv,
        max_tokens=4,
        token_counter=len,
        strategy="last",        # 保留最近的消息
        allow_partial=False,    # 不允许把单条消息截一半
    )
    print("  裁剪前:", [m.content for m in long_conv])
    print("  裁剪后:", [m.content for m in trimmed])

    # ⚠️ 生产上最容易踩的坑：include_system 默认是 False，系统提示词会被裁掉！
    print("\n  ⚠️ 注意上面的系统消息「你是助手」被裁掉了 —— include_system 默认 False。")
    print("     人设/规则丢了模型就变傻，生产环境务必显式打开：")
    kept = trim_messages(
        long_conv,
        max_tokens=4,
        token_counter=len,
        strategy="last",
        include_system=True,    # 永远保留 system 消息
    )
    print("     include_system=True 后:", [m.content for m in kept])


# ===========================================================================
# 7. 序列化持久化 & 流式输出
# ---------------------------------------------------------------------------
# 序列化：会话历史要存 Redis / PostgreSQL，就得能转成可 JSON 化的结构。
# 流式  ：模型逐字返回时，每个字是一个 AIMessageChunk，可以直接相加合并。
# ===========================================================================
def demo_7_serialize_and_stream() -> None:
    section("7. 序列化持久化 & 流式输出拼接")

    # 7.1 存库：消息 ↔ 字典
    conv = [HumanMessage("你好"), AIMessage("你好，请问需要什么帮助？")]
    data = messages_to_dict(conv)
    print("7.1 messages_to_dict():", data)
    restored = messages_from_dict(data)
    print("    messages_from_dict():", [(type(m).__name__, m.content) for m in restored])
    print("    >> 会话历史存 Redis/PostgreSQL 就靠这一对函数")

    # 7.2 流式：chunk 可以直接相加，LangChain 重载了 + 运算符
    print("\n7.2 AIMessageChunk 流式拼接")
    chunks = [AIMessageChunk(content=c) for c in ["分", "布", "式", "锁"]]
    acc = None
    for c in chunks:
        acc = c if acc is None else acc + c
        print(f"   收到 chunk={c.content!r}  累计={acc.content!r}")
    print("   >> 流式最终类型:", type(acc).__name__)
    print("   >> 真实流式场景见 chain.stream()，返回的就是一串 chunk。")


def main() -> None:
    print("langchain_core.messages 是什么 / 有什么作用")
    demo_1_what_is_message()
    demo_2_message_types()
    demo_3_history()
    demo_4_tool_calling()
    demo_5_multimodal()
    demo_6_context_engineering()
    demo_7_serialize_and_stream()
    print("\n" + "=" * 62)
    print("全部示例执行完毕。")


if __name__ == "__main__":
    main()
