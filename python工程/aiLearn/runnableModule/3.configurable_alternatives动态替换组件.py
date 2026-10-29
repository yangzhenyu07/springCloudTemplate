#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
3. configurable_alternatives：运行时换掉整个组件（最新 API 版）
============================================================

【Python 语法看不懂？】闭包、lambda、** 解包、推导式等见 ../PYTHON_SYNTAX.md

【它和 configurable_fields 的区别】
    configurable_fields      改的是**字段值**（temperature 从 1 改成 0）
    configurable_alternatives 换的是**整个组件**（把模型 A 换成模型 B）

    【Java 对照】
        configurable_fields       ≈ 改一个对象的属性（setTemperature(0)）
        configurable_alternatives ≈ 换一个实现类（strategy.setImpl(new BImpl())）
                                    典型的**策略模式 / Strategy Pattern**

【典型用途】
    · 一套代码支持多个模型厂商，运行时按客户/场景切换
    · 大模型降级：贵模型挂了自动切便宜的
    · 灰度：部分流量走新模型
    · 多租户：不同租户用不同模型

【⚠️ 教材这行有个 bug】
    llm = ChatOpenAI(...).configurable_alternatives(
        ConfigurableField(id="llm"),
        default_key="gpt-3.5",
        gpt4=ChatOpenAI(model="gpt-4o"),
        ...
    )
    chain.invoke(..., config={"configurable": {"llm": "gpt4o"}})   # ← 这里

    注意 default_key 写的是 "gpt-3.5"，但备选的 key 叫 "gpt4"（不是 gpt4o），
    调用时却传了 "gpt4o" —— 名字对不上，运行时会报错。本文件实测给你看。

【运行】
    ./yzy/Scripts/python.exe "aiLearn/runnableModule/new/3.configurable_alternatives动态替换组件.py"
"""

import os
from pathlib import Path
from typing import Any

import dotenv
from langchain_core.callbacks import BaseCallbackHandler
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import ConfigurableField, RunnableLambda
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


def build_llm(model: str = "deepseek-flash", **kwargs) -> ChatOpenAI:
    """构造 DeepSeek 模型。DeepSeek 实际只有两个模型可用（实测 /models 接口）：
    deepseek-flash（快、便宜）和 deepseek-v4-pro（强、贵）。
    """
    base = dict(
        model=model,
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


class ModelCapture(BaseCallbackHandler):
    """回调处理器：抓取每次模型调用**实际**用的模型名和温度。

    用途：验证「运行时到底切到哪个模型了」。
    比让模型自报身份可靠得多（模型会瞎编自己的身份）。
    """

    def __init__(self) -> None:
        self.used: list[str] = []      # 模型名
        self.temps: list = []          # 对应的 temperature

    def on_chat_model_start(self, serialized, messages, **kwargs) -> None:
        kw = serialized.get("kwargs", {})
        self.used.append(str(kw.get("model_name") or kw.get("model")))
        self.temps.append(kw.get("temperature"))


# ---------------------------------------------------------------------------
# 1. 基本用法：在两个模型之间切换
# ---------------------------------------------------------------------------
def demo_1_basic_switch() -> None:
    section("1. 基本用法：运行时在两个模型间切换")

    # 【关键】default_key 指定默认用哪个；其余 kwargs 是「备选组件」
    llm = build_llm().configurable_alternatives(
        ConfigurableField(id="llm"),
        default_key="flash",                       # 默认用 flash
        pro=build_llm("deepseek-v4-pro"),          # 备选：pro
    )

    prompt = ChatPromptTemplate.from_template("{query}")
    chain = prompt | llm | StrOutputParser()

    # ---------------------------------------------------------------
    # 怎么证明「真的换了模型」？
    #   问模型「你是什么模型」是**不可靠的**——它会瞎编（实测一会儿说
    #   「聊天GPT」一会儿说「深度求索」，同一个模型两次回答都不一样）。
    #   可靠办法：用回调抓取**实际发出请求时用的 model_name**。
    # ---------------------------------------------------------------
    print("  用回调抓取「实际请求的 model_name」（比问模型自己是谁可靠）：\n")

    for label, cfg in [
        ("【默认】不传配置", {}),
        ("【显式传 flash】", {"configurable": {"llm": "flash"}}),
        ("【传 pro】", {"configurable": {"llm": "pro"}}),
    ]:
        cap = ModelCapture()
        chain.invoke({"query": "1+1=?"}, config={**cfg, "callbacks": [cap]})
        print(f"    {label:<18} → 实际模型: {cap.used}")

    print("\n  >> config 里传的值要和**备选的 key 名**一致（这里是 pro），")
    print("     不是模型名，也不是 default_key。")


# ---------------------------------------------------------------------------
# 2. ⚠️ 坑：key 名对不上会怎样（教材就踩了这个）
# ---------------------------------------------------------------------------
def demo_2_pitfall_wrong_key() -> None:
    section("2. ⚠️ 坑：key 名对不上会怎样（教材就踩了）")

    llm = build_llm().configurable_alternatives(
        ConfigurableField(id="llm"),
        default_key="flash",
        pro=build_llm("deepseek-v4-pro"),
    )
    chain = ChatPromptTemplate.from_template("{query}") | llm | StrOutputParser()

    print("  教材的毛病：注册时叫 gpt4，调用时传 gpt4o（差一个字母）")
    print("  复现一下：注册 pro，调用时故意传 pro_max\n")
    try:
        chain.invoke({"query": "1+1=?"}, config={"configurable": {"llm": "pro_max"}})
        print("    ✅ 没报错（版本行为可能变了，请自行确认）")
    except Exception as e:
        print(f"    ❌ {type(e).__name__}: {str(e)[:180]}")

    print("\n  >> 传了不存在的 key 会直接报错（这点比静默降级好）。")
    print("     教材里 gpt4 / gpt4o 那个不一致，在新版本上是会炸的。")

    print("\n  另外实测：default_key 如果写了一个不存在的 key 会怎样？")
    try:
        bad = build_llm().configurable_alternatives(
            ConfigurableField(id="llm2"),
            default_key="not_exist",          # 没注册这个 key
            pro=build_llm("deepseek-v4-pro"),
        )
        (ChatPromptTemplate.from_template("{query}") | bad | StrOutputParser()).invoke({"query": "1+1=?"})
        print("    ✅ 不存在的 default_key 也能跑（会退化成基础组件）")
    except Exception as e:
        print(f"    ❌ {type(e).__name__}: {str(e)[:120]}")
    print("     → default_key 不存在时不报错，会用**基础组件**（构造时的那个）兜底。")


# ---------------------------------------------------------------------------
# 3. 懒加载：用 lambda 延迟创建（省资源）
# ---------------------------------------------------------------------------
def demo_3_lazy_loading() -> None:
    section("3. 进阶：用 lambda 懒加载备选组件")

    print("  上面那种写法有个问题：**所有备选模型在链组装时就全被创建了**。")
    print("  如果备选是个很重的对象（要连数据库、要加载模型），白浪费资源。")

    print("\n  解法：传一个 **lambda（零参数函数）**，用到时才创建：\n")

    create_count = {"flash": 0, "pro": 0}

    def make_flash():
        create_count["flash"] += 1
        return build_llm("deepseek-flash")

    def make_pro():
        create_count["pro"] += 1
        return build_llm("deepseek-v4-pro")

    llm = build_llm().configurable_alternatives(
        ConfigurableField(id="llm"),
        default_key="flash",
        pro=make_pro,        # ← 注意：传的是函数本身，不是 make_pro()
    )
    chain = ChatPromptTemplate.from_template("{query}") | llm | StrOutputParser()

    print("  组装完链，此时创建次数:", create_count)
    chain.invoke({"query": "1+1=?"})
    print("  用默认(flash)调一次后:", create_count, "（pro 没被创建）")
    chain.invoke({"query": "1+1=?"}, config={"configurable": {"llm": "pro"}})
    print("  切到 pro 调一次后:", create_count, "（pro 这时才创建）")

    print("\n  >> 懒加载的价值：")
    print("     · 备选组件很重时（连接、加载模型）能省启动开销")
    print("     · 备选组件依赖运行时才能拿到的配置时，只能懒加载")


# ---------------------------------------------------------------------------
# 4. 不止能换模型：任何 Runnable 都能换
# ---------------------------------------------------------------------------
def demo_4_swap_any_runnable() -> None:
    section("4. ⚠️ 限制：不是所有 Runnable 都能用（实测）")

    print("  【先踩坑】想给 RunnableLambda 加 configurable_alternatives：\n")
    try:
        RunnableLambda(lambda x: x).configurable_alternatives(
            ConfigurableField(id="r"), default_key="a", b=RunnableLambda(lambda x: x)
        )
        print("    ✅ 能用")
    except AttributeError as e:
        print(f"    ❌ AttributeError: {e}")

    print("\n  实测哪些类有这两个方法：\n")
    from langchain_core.runnables import RunnableParallel, RunnablePassthrough
    from langchain_core.prompts import PromptTemplate

    targets = [
        ("ChatOpenAI", build_llm()),
        ("PromptTemplate", PromptTemplate.from_template("{a}")),
        ("RunnableParallel", RunnableParallel(a=lambda x: x)),
        ("RunnablePassthrough", RunnablePassthrough()),
        ("RunnableLambda", RunnableLambda(lambda x: x)),
    ]
    print(f"    {'类':<24}{'configurable_fields':<24}{'configurable_alternatives'}")
    print("    " + "-" * 66)
    for name, obj in targets:
        f1 = hasattr(obj, "configurable_fields")
        f2 = hasattr(obj, "configurable_alternatives")
        print(f"    {name:<24}{str(f1):<24}{f2}")

    print("\n  ⚠️ 结论：这两个方法只挂在 **RunnableSerializable**（pydantic 模型类）上，")
    print("     而 RunnableLambda 是纯函数包装，**没有**这两个方法。")
    print("     原因：它们靠 pydantic 的字段系统实现，函数没有字段可言。")

    print("\n  【替代方案】RunnableLambda 可以直接接收第二个参数 config：\n")

    def search_doc(x):
        return "[产品文档] 重置密码：登录页点「忘记密码」"

    def search_faq(x):
        return "[FAQ] 重置密码：在设置-安全里操作"

    def search_ticket(x):
        return "[工单] 历史上有人问过：需要管理员协助"

    REGISTRY = {"doc": search_doc, "faq": search_faq, "ticket": search_ticket}

    def dispatch(x, config):
        """按 config 里指定的 key 选一个检索函数。

        ⚠️ 关键：第二个参数名必须叫 config，LangChain 才会把 RunnableConfig 传进来。
        """
        key = config.get("configurable", {}).get("retriever", "doc")
        return REGISTRY.get(key, search_doc)(x)

    retriever = RunnableLambda(dispatch)

    prompt = ChatPromptTemplate.from_template(
        "根据资料回答问题，不超过 30 字。\n资料：{docs}\n问题：{query}"
    )
    chain = (
        {"docs": retriever, "query": lambda x: x["query"]}
        | prompt
        | build_llm()
        | StrOutputParser()
    )

    for key in ("doc", "faq", "ticket"):
        answer = chain.invoke(
            {"query": "怎么重置密码"},
            config={"configurable": {"retriever": key}},
        )
        print(f"    retriever={key:<8} → {answer}")

    print("\n  >> 所以「换组件」的本质是**策略模式**：")
    print("     注册多个实现，运行时选一个。")
    print("     · pydantic 系组件（模型/提示词）→ 直接用 configurable_alternatives")
    print("     · 普通函数                      → 用 RunnableLambda + config 自己分派")


# ---------------------------------------------------------------------------
# 5. prefix_keys：给 key 加前缀（嵌套场景用）
# ---------------------------------------------------------------------------
def demo_5_prefix_keys() -> None:
    section("5. prefix_keys：给「备选组件自己的字段」加命名空间")

    print("  先说清楚它**不是**什么：")
    print("    ❌ 不是让你把选择 key 写成 'llm/pro'（实测这样写会 ValueError）")
    print("    ✅ 选择 key 永远还是 'pro'，和 prefix_keys 无关\n")

    print("  它真正的作用：当**备选组件自己也有 configurable_fields** 时，")
    print("  多个备选的字段 id 会撞车（都叫 t），一个 config 会同时改掉所有备选。")
    print("  开了 prefix_keys 之后，就能用 '<id>==<key>/<field_id>' 精确指定某一个。\n")

    # 两个备选，各自都把 temperature 声明成可配（id 都叫 t）
    a = build_llm().configurable_fields(temperature=ConfigurableField(id="t"))
    b = build_llm("deepseek-v4-pro").configurable_fields(temperature=ConfigurableField(id="t"))

    for prefix in (False, True):
        alt = a.configurable_alternatives(
            ConfigurableField(id="llm"), default_key="flash", pro=b, prefix_keys=prefix
        )
        print(f"  【prefix_keys={prefix}】")
        for cfg in ({"llm": "pro"}, {"llm": "pro", "t": 0.1}, {"llm": "pro", "llm==pro/t": 0.1}):
            cap = ModelCapture()
            alt.invoke("hi", config={"configurable": cfg, "callbacks": [cap]})
            print(f"    {str(cfg):<38} → 模型 {cap.used} / temperature {cap.temps}")
        print()

    print("  实测结论：")
    print("    · prefix_keys=False：只有通用的 't' 生效（所有备选共享）")
    print("    · prefix_keys=True ：'t' 和 'llm==pro/t' **都能**生效")
    print("      → 想「只给 pro 配温度、不改 flash」就用 'llm==pro/t'")
    print("\n  ⚠️ 什么时候才需要它：只有当你**给备选组件本身也加了 configurable_fields**")
    print("     时才用得上。普通换模型场景不用开，开了反而容易记混。")


# ---------------------------------------------------------------------------
# 6. 选型对比
# ---------------------------------------------------------------------------
def demo_6_summary() -> None:
    section("6. 三个「动态」API 怎么选")

    rows = [
        ("bind", "预置固定参数", "❌", "参数永远不变"),
        ("configurable_fields", "改字段值", "✅", "调温度 / 换提示词模板"),
        ("configurable_alternatives", "换整个组件", "✅", "换模型 / 换检索器"),
        ("with_fallbacks", "出错才换", "自动", "降级容灾（第 4 个文件）"),
    ]
    print(f"  {'API':<30}{'干什么':<18}{'运行时':<10}{'用途'}")
    print("  " + "-" * 82)
    for a, b, c, d in rows:
        print(f"  {a:<30}{b:<18}{c:<10}{d}")

    print("\n  判断口诀：")
    print("     想改一个值          → configurable_fields")
    print("     想换一个东西        → configurable_alternatives")
    print("     想出错才换          → with_fallbacks")
    print("     值永远不变          → bind")

    print("\n  ⚠️ 生产提醒：")
    print("     · alternatives 的 key 建议集中定义成常量，别散落在字符串里")
    print("     · 换模型要考虑 prompt 兼容性（不同模型对指令的服从度不同）")
    print("     · 计费模型切换要有日志，否则成本对不上账")


def main() -> None:
    print("3. configurable_alternatives 动态替换组件（DeepSeek + 最新 API）")
    print("   教材：old/Runnable组件动态替换运行组件/1.*")

    demo_3_lazy_loading()      # 不需要 API 也能跑（会调一次，所以放后面）
    demo_4_swap_any_runnable()

    if not os.getenv("DEEPSEEK_API_KEY"):
        print("\n⚠️ 没读到 DEEPSEEK_API_KEY，跳过部分演示。.env 路径：", _ENV_PATH)
        return

    demo_1_basic_switch()
    demo_2_pitfall_wrong_key()
    demo_5_prefix_keys()
    demo_6_summary()

    print("\n" + "=" * 62)
    print("全部示例执行完毕。下一个：4.重试与回退机制.py")


if __name__ == "__main__":
    main()
