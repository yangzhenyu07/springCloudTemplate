"""
三个 XxxMessagePromptTemplate 详解 + 综合实战
=============================================

本文件回答一个问题：教材里的 SystemMessagePromptTemplate /
HumanMessagePromptTemplate / AIMessagePromptTemplate 这三个类，到底该怎么用？

先建立一个核心认知（非常重要）：

    ChatPromptTemplate.from_messages([...]) 接收的其实是一个"元素列表"，
    列表里每个元素可以是三种形态之一：
        1. 元组        ("system", "你是{role}")     ← 现代主流写法
        2. 字符串      "{q}"                        ← 默认当成 human
        3. 模板类实例  SystemMessagePromptTemplate(...)  ← 教材写法

    而形态 1 和 2 会在内部自动被转换成形态 3。
    也就是说：元组写法是"语法糖"，这三个类才是底层实现。

    上一份文件里验证过这个等价关系，本文件会再演示一次。

那什么时候该手写这三个类，而不是用元组？
    - 用元组就够了：99% 的日常场景（写 system / human / ai 提示词）
    - 必须手写类：需要给消息加"非文本属性"时，比如
        · AIMessagePromptTemplate 想带 tool_calls / 角色名
        · 需要复用同一个消息模板对象（把模板存成变量到处引用）
        · 需要动态指定 role（用 ChatMessagePromptTemplate）

运行：
    ./yzy/Scripts/python.exe aiLearn/message_prompt_templates_demo.py
"""

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_core.prompts import (
    AIMessagePromptTemplate,
    ChatMessagePromptTemplate,
    ChatPromptTemplate,
    HumanMessagePromptTemplate,
    MessagesPlaceholder,
    SystemMessagePromptTemplate,
)
from langchain_core.language_models.fake_chat_models import FakeListChatModel


def section(title: str) -> None:
    print("\n" + "=" * 62)
    print(title)
    print("=" * 62)


def dump(messages, indent: str = "  ") -> None:
    """打印消息数组，带角色和内容。"""
    for i, m in enumerate(messages, 1):
        extra = ""
        if getattr(m, "tool_calls", None):
            extra = f"  tool_calls={m.tool_calls}"
        print(f"{indent}[{i}] {type(m).__name__:<14} | {m.content!r}{extra}")


# ---------------------------------------------------------------------------
# 1. SystemMessagePromptTemplate —— 系统提示词模板
# ---------------------------------------------------------------------------
def demo_1_system() -> None:
    section("1. SystemMessagePromptTemplate —— 系统指令模板")

    # 作用：定义"模型是谁、该遵守什么规则"。角色是 system，优先级最高。
    # 什么时候用：设定人设、输出格式约束、安全边界。
    sys_tpl = SystemMessagePromptTemplate.from_template(
        "你是一名{domain}专家。回答要求：\n"
        "1. 只输出结论，不要解释过程\n"
        "2. 不超过{max_len}个字"
    )
    print("模板变量:", sys_tpl.input_variables)
    print("渲染结果:")
    dump(sys_tpl.format_messages(domain="PostgreSQL", max_len="50"))

    # 等价的元组写法：("system", "...")
    # 建议：日常就写元组，from_messages 内部帮你转成本类实例
    sugar = ChatPromptTemplate.from_messages([("system", "你是一名{domain}专家")])
    print("\n元组写法底层生成的类:", type(sugar.messages[0]).__name__)
    print(">> 两种写法完全等价，元组更简洁。")

    # ⚠️ 注意：system 消息通常放在列表最前面。
    # 放在中间虽然不报错，但模型对 system 的遵循度会下降。


# ---------------------------------------------------------------------------
# 2. HumanMessagePromptTemplate —— 用户消息模板
# ---------------------------------------------------------------------------
def demo_2_human() -> None:
    section("2. HumanMessagePromptTemplate —— 用户消息模板")

    # 作用：表达"用户说了什么"。角色是 human（API 里叫 user）。
    # 这是最常用的一类，也是唯一可以省略成裸字符串的形态。
    human_tpl = HumanMessagePromptTemplate.from_template("请解释一下{concept}")
    dump(human_tpl.format_messages(concept="分布式锁"))

    print("\n>> from_messages 里的字符串会被自动当成 human 消息：")
    p = ChatPromptTemplate.from_messages([
        ("system", "你是助手"),
        "{question}",          # 裸字符串 == HumanMessagePromptTemplate
    ])
    print("   底层类:", [type(m).__name__ for m in p.messages])
    dump(p.invoke({"question": "什么是幂等性？"}).to_messages())

    # 多模态场景：content 是列表而不是字符串时，就必须显式构造
    print("\n>> 需要传图片等非文本内容时，就得手写模板类了：")
    mm = HumanMessagePromptTemplate.from_template([
        {"type": "text", "text": "描述这张图：{hint}"},
    ])
    dump(mm.format_messages(hint="注意看左下角"))


# ---------------------------------------------------------------------------
# 3. AIMessagePromptTemplate —— AI 消息模板
# ---------------------------------------------------------------------------
def demo_3_ai() -> None:
    section("3. AIMessagePromptTemplate —— 模型消息模板")

    print("作用一：构造 few-shot 示例里的「标准答案」")
    # 这是它最主要的用途：告诉模型"遇到这类问题，应该这样回答"
    ai_tpl = AIMessagePromptTemplate.from_template("{{ 结果：{answer} }}")
    dump(ai_tpl.format_messages(answer="4"))

    # 注意上面用了双大括号 {{ }} —— 这是转义，表示原文输出一个 {
    # 因为单大括号会被当成模板变量解析

    print("\n作用二：预填充（prefill），强制模型按指定格式续写")
    # 技巧：预先塞一条只写了一半的 AIMessage，模型会接着往下补全。
    # 这在要求稳定输出 JSON / 代码块时非常好用。
    prefill = ChatPromptTemplate.from_messages([
        ("human", "用 JSON 返回杭州的天气，字段：city, temp"),
        AIMessagePromptTemplate.from_template("{prefix}"),
    ])
    dump(prefill.invoke({"prefix": '{"city": "杭州", "temp": '}).to_messages())
    print(">> 模型会从这个半截 JSON 继续写，不容易跑偏。")

    print("\n作用三：拼接历史对话里模型之前说过的话")
    history = [
        HumanMessage("Redis 分布式锁怎么防死锁？"),
        AIMessage("加过期时间，并用看门狗自动续期。"),
    ]
    dump(history)


# ---------------------------------------------------------------------------
# 4. ChatMessagePromptTemplate —— 自定义角色（补充）
# ---------------------------------------------------------------------------
def demo_4_custom_role() -> None:
    section("4. ChatMessagePromptTemplate —— 自定义角色（教材没提但有用）")

    # 前面三个类的 role 是固定的（system / human / ai）。
    # 如果你的模型支持自定义角色名（比如某些开源模型的 "tool" / "observation"），
    # 就用 ChatMessagePromptTemplate 动态指定 role。
    tpl = ChatMessagePromptTemplate.from_template(
        template="{content}",
        role="{role_name}",     # role 也是模板变量，运行时决定
    )
    dump(tpl.format_messages(role_name="observer", content="监控到一次超时"))
    print(">> 主流 OpenAI 兼容模型一般只用 system/human/ai/tool，这个类较少用到。")


# ---------------------------------------------------------------------------
# 5. 三种形态混用 + 等价性验证
# ---------------------------------------------------------------------------
def demo_5_mixed() -> None:
    section("5. 三种形态可以在同一个列表里混用")

    prompt = ChatPromptTemplate.from_messages([
        SystemMessagePromptTemplate.from_template("你是{role}"),   # 形态 3：显式类
        ("human", "{history_hint}"),                               # 形态 1：元组
        MessagesPlaceholder("history"),
        "{question}",                                              # 形态 2：裸字符串
    ])
    print("底层实际类型:")
    for m in prompt.messages:
        print("   ", type(m).__name__)

    print("\n渲染结果:")
    dump(prompt.invoke({
        "role": "DBA",
        "history_hint": "以下是之前的对话",
        "history": [HumanMessage("慢查询怎么查？"), AIMessage("用 EXPLAIN ANALYZE。")],
        "question": "索引该怎么建？",
    }).to_messages())


# ---------------------------------------------------------------------------
# 6. 综合实战：把三个类 + MessagesPlaceholder 串成一个多轮客服机器人
# ---------------------------------------------------------------------------
def demo_6_real_world() -> None:
    section("6. 综合实战：多轮客服机器人（串起全部知识点）")

    # 第 1 步：把 system 提示单独抽成一个可复用对象。
    # 这样做的好处：同一个 system 模板可以在多个 prompt 之间复用，
    # 而不是每个 prompt 里复制一遍字符串。
    SYSTEM = SystemMessagePromptTemplate.from_template(
        "你是{brand}的客服助手。规则：\n"
        "- 语气友好，用「您」称呼用户\n"
        "- 不知道就说不知道，不许编造\n"
        "- 回答控制在 {max_len} 字以内"
    )

    # 第 2 步：组装完整 prompt
    #   system   → 人设规则
    #   history  → 历史对话（运行时注入，可为空）
    #   human    → 本轮用户问题
    prompt = ChatPromptTemplate.from_messages([
        SYSTEM,
        MessagesPlaceholder("history"),
        HumanMessagePromptTemplate.from_template("{question}"),
    ])

    # 第 3 步：接模型（没配 key 就用假模型，保证能跑）
    model = FakeListChatModel(responses=[
        "您好，已为您查询到订单已打包，预计明天发出。",
        "好的，已帮您改成后天配送。",
    ])
    chain = prompt | model

    # 第 4 步：模拟一个真实的多轮会话
    # 关键点：history 列表随着对话推进不断追加，这就是"记忆"的本质
    history = []
    rounds = [
        {"brand": "小米", "max_len": "100", "question": "我的订单怎么还没发货？"},
        {"brand": "小米", "max_len": "100", "question": "能改成后天送吗？"},
    ]

    for turn, r in enumerate(rounds, 1):
        print(f"\n--- 第 {turn} 轮 ---")
        print(f"用户: {r['question']}")

        # 渲染出本轮要发给模型的完整消息
        messages = prompt.invoke({
            "brand": r["brand"],
            "max_len": r["max_len"],
            "history": history,
            "question": r["question"],
        }).to_messages()
        dump(messages)

        # 调用模型
        reply = chain.invoke({
            "brand": r["brand"],
            "max_len": r["max_len"],
            "history": history,
            "question": r["question"],
        })
        print(f"助手: {reply.content}")

        # 把本轮的「用户问题」和「模型回复」追加进历史，供下一轮使用
        history.append(HumanMessage(r["question"]))
        history.append(reply)
        print(f">> 历史条数: {len(history)}")

    print("\n>> 这就是 messages 最核心的作用：它是会话记忆的载体。")
    print(">> 生产环境里，history 一般来自 Redis / PostgreSQL，")
    print("   用 messages_to_dict() 存、messages_from_dict() 取（见 messages_demo.py）。")


def main() -> None:
    print("三个 XxxMessagePromptTemplate 详解（langchain-core 1.7.0 实测）")
    demo_1_system()
    demo_2_human()
    demo_3_ai()
    demo_4_custom_role()
    demo_5_mixed()
    demo_6_real_world()
    print("\n" + "=" * 62)
    print("全部示例执行完毕。")


if __name__ == "__main__":
    main()
