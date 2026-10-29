"""
langchain_core.prompts 使用示例（详细注释版）
=============================================

【核心认知，先记住这三点】
    1. ChatPromptTemplate 是「纯本地的模板渲染器」——不连模型、不发请求、不耗 token。
       它做的只是：变量字典 → 消息数组。你完全可以渲染完直接打印，跟模型无关。
    2. 它常被类比成"字符串拼接"，但产出物不是 str，而是 List[BaseMessage]。
       每条消息自带角色（system/human/ai/tool），这才是模型 API 真正要的格式。
    3. prompts 和 messages 是一件事的两面：
       prompts 负责"怎么拼出请求"，messages 是"请求长什么样"。

【学习顺序建议】
    本文件按使用频率从高到低排列，建议按 2 → 3 → 6 的顺序重点看：
        2. ChatPromptTemplate   （90% 的场景都是它）
        3. MessagesPlaceholder  （多轮对话的关键）
        6. LCEL 管道            （把模板、模型、解析器串成链路）

【运行】
    ./yzy/Scripts/python.exe aiLearn/prompts_demo.py
    （注意：用项目 venv 的 Python 3.10，不要用系统 Python 3.13）
"""

import os
from typing import List

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import (
    ChatPromptTemplate,
    FewShotChatMessagePromptTemplate,
    MessagesPlaceholder,
    PromptTemplate,
)
from langchain_core.language_models.fake_chat_models import FakeListChatModel


# ===========================================================================
# 模型层：可插拔设计
# ---------------------------------------------------------------------------
# 本文件演示的是 prompts，跟用哪个模型无关——这一点很重要，
# 说明 prompts 是"与模型解耦"的独立抽象层。
#
# 下面做了自适应：配了 DEEPSEEK_API_KEY 且装了 langchain-openai 就走真实 DeepSeek，
# 否则回退到 langchain_core 自带的假模型，保证示例零配置就能跑通。
# ===========================================================================
def build_model():
    """构造一个聊天模型。

    DeepSeek 用的是 OpenAI 兼容协议，所以不需要专门的包，
    用 ChatOpenAI 换掉 base_url 就能指向 DeepSeek。
    """
    api_key = os.getenv("DEEPSEEK_API_KEY")
    if api_key:
        try:
            from langchain_openai import ChatOpenAI

            return ChatOpenAI(
                model="deepseek-chat",
                api_key=api_key,
                base_url="https://api.deepseek.com",  # DeepSeek 的 OpenAI 兼容端点
                temperature=0,
            )
        except ImportError:
            print("  [提示] 未安装 langchain-openai，回退到假模型\n")

    # 假模型：按列表顺序依次返回预设回复。
    # 用途：在没有 API key 的情况下验证链路是否通畅，也是写单测的常用手法。
    return FakeListChatModel(responses=["【假模型回复】我已收到你的问题。"])


def section(title: str) -> None:
    print("\n" + "=" * 62)
    print(title)
    print("=" * 62)


def dump_messages(messages: List[BaseMessage]) -> None:
    """把消息数组按角色打印出来。

    这样打印是为了让你直观看到"带角色"长什么样——
    这是 ChatPromptTemplate 和普通字符串拼接最本质的区别。
    """
    for i, m in enumerate(messages, 1):
        print(f"  [{i}] {type(m).__name__:<14} | {m.content}")


# ===========================================================================
# 1. PromptTemplate —— 最基础的字符串模板
# ---------------------------------------------------------------------------
# 是什么：处理「纯文本模板」，变量用 {xxx} 占位，渲染结果是 str。
# 何时用：只在对接老式"文本补全模型"时才需要。
#         现在主流都是聊天模型，所以这个类用得越来越少。
# 注意  ：聊天场景一律用 ChatPromptTemplate，别用它。
# ===========================================================================
def demo_1_prompt_template() -> None:
    section("1. PromptTemplate —— 最基础的字符串模板")

    # from_template 默认按 f-string 语法解析 {变量}
    tpl = PromptTemplate.from_template("请把「{text}」翻译成{lang}，只输出译文。")
    print("模板变量:", tpl.input_variables)
    print("渲染结果:", tpl.format(text="分布式锁", lang="English"))

    # 比裸 f-string 强的地方：变量校验。
    # 裸 f-string 少传变量会静默拼出 "{lang}" 这种怪东西，这里会直接报错。
    try:
        tpl.format(text="分布式锁")
    except KeyError as e:
        print("少传变量时:", f"KeyError {e}  <-- 提前暴露问题，而非静默出错")


# ===========================================================================
# 2. ChatPromptTemplate.from_messages —— 主力写法（最重要的一节）
# ---------------------------------------------------------------------------
# 是什么：把变量渲染成「带角色的消息数组」List[BaseMessage]。
# 何时用：几乎所有聊天场景。业界 90% 的代码都是这个写法。
# 输入  ：from_messages 接收一个列表，元素可以是
#           · 元组   ("system", "你是{role}")
#           · 字符串 "{q}"（默认当 human）
#           · 模板类 SystemMessagePromptTemplate(...)
# 注意  ：invoke() 返回的是 ChatPromptValue 包装对象，
#         要 .to_messages() 才拿到真正的消息列表。
# ===========================================================================
def demo_2_chat_prompt_template() -> None:
    section("2. ChatPromptTemplate.from_messages —— 主力写法（90% 场景用它）")

    prompt = ChatPromptTemplate.from_messages([
        ("system", "你是一名{domain}专家，回答要简洁，不超过{max_len}字。"),
        ("human", "{question}"),
    ])
    # input_variables 是模板自动解析出来的必填变量清单
    print("模板变量:", prompt.input_variables)

    # invoke 返回 ChatPromptValue，调用 .to_messages() 才能得到消息列表
    messages = prompt.invoke({
        "domain": "PostgreSQL",
        "max_len": "50",
        "question": "连接池大小该怎么设置？",
    }).to_messages()
    dump_messages(messages)

    # 对比：同样的话如果用裸 f-string 拼接会怎样
    print("\n>> 关键：产出的是「带角色的消息数组」，不是一整段字符串。")
    print(">> 看裸拼接的结果——模型分不清哪句是指令、哪句是提问：")
    raw = f"你是一名PostgreSQL专家，回答要简洁，不超过50字。连接池大小该怎么设置？"
    print("   裸拼接:", raw)

    # 只用一条消息时的简写：from_template 会自动包成 HumanMessage
    print("\n>> 简写：from_template 会把整个模板当成一条 human 消息")
    p2 = ChatPromptTemplate.from_template("解释一下{concept}")
    dump_messages(p2.invoke({"concept": "幂等性"}).to_messages())


# ===========================================================================
# 3. MessagesPlaceholder —— 多轮对话的历史占位符
# ---------------------------------------------------------------------------
# 是什么：在模板里"挖个坑"，运行时把一整段历史消息列表插进去。
# 何时用：只要是多轮对话（聊天机器人、客服），就必须有它。
# 注意  ：· history 传空列表也不会报错，占位符会被直接跳过
#         · 它插的是"消息列表"，不是字符串，所以不能写成 ("history", "{history}")
# ===========================================================================
def demo_3_messages_placeholder() -> None:
    section("3. MessagesPlaceholder —— 多轮对话的历史消息占位符")

    prompt = ChatPromptTemplate.from_messages([
        ("system", "你是客服助手，语气友好。"),
        MessagesPlaceholder("history"),   # 运行时整段插入历史消息列表
        ("human", "{question}"),
    ])
    print("模板变量:", prompt.input_variables, " <-- history 是一个变量")

    # 历史消息通常来自数据库或会话缓存（Redis / PostgreSQL）
    history = [
        HumanMessage("我上周下的订单还没发货"),
        AIMessage("您好，已帮您查询到订单已打包，预计明天发出。"),
    ]
    messages = prompt.invoke({
        "history": history,
        "question": "能改成后天送吗？",
    }).to_messages()
    dump_messages(messages)

    print("\n>> 第一轮对话时历史为空，也不会报错，占位符直接被跳过：")
    dump_messages(prompt.invoke({"history": [], "question": "你好"}).to_messages())


# ===========================================================================
# 4. partial —— 预绑定部分变量
# ---------------------------------------------------------------------------
# 是什么：提前把某些变量的值固定住，调用时就不用再传了。
# 何时用：注入那些"每次都一样"的信息——当前日期、租户 ID、用户等级、环境标识。
# 好处  ：调用方只关心业务变量，公共信息由框架统一注入，不会漏传。
# ===========================================================================
def demo_4_partial() -> None:
    section("4. partial —— 预绑定变量，调用方就不用传了")

    prompt = ChatPromptTemplate.from_messages([
        ("system", "今天是 {date}，用户等级：{level}。"),
        ("human", "{question}"),
    ]).partial(date="2026-10-26", level="VIP")

    # date 和 level 已被固定，只剩 question 需要传
    print("预绑定后剩余变量:", prompt.input_variables, " <-- date/level 已固定")
    dump_messages(prompt.invoke({"question": "我的优惠券什么时候过期？"}).to_messages())


# ===========================================================================
# 5. FewShotChatMessagePromptTemplate —— 少样本示例注入
# ---------------------------------------------------------------------------
# 是什么：把若干"问题-标准答案"示例自动展开成一串 Human/AI 交替的消息。
# 何时用：模型输出格式不稳定、或需要它模仿特定风格时。
# 好处  ：比把示例塞进 system 里更贴近真实对话结构，效果通常更好。
# 注意  ：示例会占用 token，别放太多，一般 2~5 个足够。
# ===========================================================================
def demo_5_few_shot() -> None:
    section("5. FewShotChatMessagePromptTemplate —— few-shot 示例注入")

    examples = [
        {"input": "这个需求做不了", "output": "负面"},
        {"input": "你们响应真快", "output": "正面"},
    ]
    # 先定义"单个示例长什么样"：一条人问 + 一条 AI 答
    example_prompt = ChatPromptTemplate.from_messages([
        ("human", "{input}"),
        ("ai", "{output}"),
    ])
    few_shot = FewShotChatMessagePromptTemplate(
        examples=examples,
        example_prompt=example_prompt,
    )

    final = ChatPromptTemplate.from_messages([
        ("system", "你是一个情感分类器，只输出「正面」或「负面」。"),
        few_shot,
        ("human", "{input}"),
    ])
    dump_messages(final.invoke({"input": "价格有点贵但能用"}).to_messages())
    print(">> 示例被展开成多条 Human/AI 交替的消息，模型更容易照着学。")


# ===========================================================================
# 6. LCEL 管道 —— 业界事实标准（第二重要的一节）
# ---------------------------------------------------------------------------
# 是什么：用 | 把「模板 → 模型 → 解析器」串成一条可执行的链路。
# 何时用：几乎所有正式项目。这是 LangChain 推荐的组合方式。
# 好处  ：· 链路本身就是 Runnable 对象，天然支持 invoke / batch / stream
#         · 加了 StrOutputParser 之后直接拿到字符串，不用每次 .content
# 注意  ：教材里的 PipelinePromptTemplate 就是被这套管道取代的（已移除）。
# ===========================================================================
def demo_6_lcel_chain() -> None:
    section("6. LCEL 管道：prompt | model | parser")

    prompt = ChatPromptTemplate.from_messages([
        ("system", "你是一名资深 Java 工程师。"),
        ("human", "{question}"),
    ])
    model = build_model()
    # 三个 Runnable 用 | 串起来，数据从左往右流
    chain = prompt | model | StrOutputParser()

    print("链路对象:", type(chain).__name__, " <-- RunnableSequence")
    result = chain.invoke({"question": "分布式锁的看门狗续期是怎么实现的？"})
    # 注意：langchain-core 1.7 里 StrOutputParser 返回的是 TextAccessor（str 的子类），
    # 打印和字符串操作都跟 str 一样，直接当 str 用即可
    print("返回值类型:", type(result).__name__, "| isinstance(str):", isinstance(result, str))
    print("返回值:", result)

    print("\n>> 去掉 StrOutputParser，拿到的就是原始的 AIMessage：")
    print("  ", type((prompt | model).invoke({"question": "hi"})).__name__)


# ===========================================================================
# 7. batch —— LCEL 自带的工程能力
# ---------------------------------------------------------------------------
# 是什么：一次并发处理多组输入。
# 何时用：批量标注、批量翻译、离线跑数据。
# 好处  ：不用自己写 asyncio.gather，LCEL 内部帮你并发。
# 延伸  ：同样还有 .stream()（流式）和 .astream()（异步流式）。
# ===========================================================================
def demo_7_batch_and_stream() -> None:
    section("7. LCEL 附带的批量与流式能力")

    prompt = ChatPromptTemplate.from_template("用一句话解释 {topic}")
    model = build_model()
    chain = prompt | model | StrOutputParser()

    print("批量调用 batch():")
    for r in chain.batch([{"topic": "幂等性"}, {"topic": "分布式锁"}]):
        print("  -", r)


def main() -> None:
    print("langchain_core.prompts 示例（无需连接真实模型即可运行）")
    demo_1_prompt_template()
    demo_2_chat_prompt_template()
    demo_3_messages_placeholder()
    demo_4_partial()
    demo_5_few_shot()
    demo_6_lcel_chain()
    demo_7_batch_and_stream()
    print("\n" + "=" * 62)
    print("全部示例执行完毕。")


if __name__ == "__main__":
    main()
