# aiLearn：langchain_core.prompts / messages 入门

> 环境：**Python 3.11.9**（2026-10 从 3.10.9 升级）/ langchain-core **1.7.0** / deepagents 0.7.32
> 项目自带 venv `yzy/`，依赖见根目录 `requirements.in` → `requirements.txt`
>
> **为什么要升到 3.11**：Agent Skills 的官方实现 `deepagents` 要求 Python>=3.11，
> 3.10.9 上 pip 直接报「找不到匹配的发行版」。升级后同时解开了两条 3.10 时代的版本锁：
> `SQLAlchemy <2.1` → 2.1.6、`WTForms 3.2.2` → 3.3.1。
>
> **回归状态**：36 个 demo 在 3.11.9 上**全部通过**（34 个跑于升级后首轮回归，耗时 7m57s，
> 0 失败；另 2 个为之后新增）。详见文末「回归结果」。

## 文件清单与建议学习顺序

### 第一部分：prompts / messages（不需要 API key，零配置可跑）

```bash
./yzy/Scripts/python.exe aiLearn/prompts/messages_demo.py
./yzy/Scripts/python.exe aiLearn/prompts/prompts_demo.py
./yzy/Scripts/python.exe aiLearn/prompts/message_prompt_templates_demo.py
```

| 顺序 | 文件 | 讲什么 | 重点看 |
|---|---|---|---|
| ① | `prompts/messages_demo.py` | messages 是什么、四大作用 | 先搞懂"消息"这个数据形态 |
| ② | `prompts/prompts_demo.py` | prompts 七种用法 | 第 2 节 ChatPromptTemplate、第 6 节 LCEL |
| ③ | `prompts/message_prompt_templates_demo.py` | 三个 XxxMessagePromptTemplate + 综合实战 | 第 6 节多轮客服机器人 |

> 为什么先看 messages：prompts 的产出物就是 messages。
> 不先认识"消息"，看 prompts 会觉得它只是个花哨的字符串拼接。

### 第二部分：model（真实调用 DeepSeek，需要 API key）

```bash
./yzy/Scripts/python.exe "aiLearn/model/1.LLM与ChatModel使用技巧.py"
./yzy/Scripts/python.exe "aiLearn/model/2.Model批处理.py"
./yzy/Scripts/python.exe "aiLearn/model/3.Model流式输出.py"
```

| 顺序 | 文件 | 讲什么 | 原教材（已归档） |
|---|---|---|---|
| ④ | `model/1.LLM与ChatModel使用技巧.py` | LCEL 管道、AIMessage 结构、参数、解析器 | `old/1.*` |
| ⑤ | `model/2.Model批处理.py` | batch 并发、限流、容错、成本 | `old/2.*` |
| ⑥ | `model/3.Model流式输出.py` | stream 打字机、chunk 累积、TTFT、异步 | `old/3.*` |

> 这三个文件都真实调用 DeepSeek，key 从 `.env` 的 `DEEPSEEK_API_KEY` 读取，
> **不硬编码在代码里**（避免你以后分享代码时泄露）。
> 教材里的对应文件是 2024 年的分步调用写法（手动 `prompt.invoke()` 再喂给 `llm.invoke()`），
> 这里统一改成 LCEL 管道。

### 第三部分：outputParser（真实调用 DeepSeek，需要 API key）

```bash
./yzy/Scripts/python.exe "aiLearn/outputParser/1.StrOutputParser使用技巧.py"
./yzy/Scripts/python.exe "aiLearn/outputParser/2.JsonOutputParser使用技巧.py"
./yzy/Scripts/python.exe "aiLearn/outputParser/3.with_structured_output结构化输出.py"
```

| 顺序 | 文件 | 讲什么 | 原教材（已归档） |
|---|---|---|---|
| ⑦ | `outputParser/1.StrOutputParser使用技巧.py` | 三层套娃 → 管道、流式为何必须加解析器 | `old/1.*` |
| ⑧ | `outputParser/2.JsonOutputParser使用技巧.py` | pydantic v2、Json/Pydantic 解析器、嵌套结构、重试兜底 | `old/2.*` |
| ⑨ | `outputParser/3.with_structured_output结构化输出.py` | **最新最推荐**的方案，三种 method 实测对比 | 教材没有 |

> ⚠️ 教材里的 `old/2.*` 用了 `from langchain_core.pydantic_v1 import BaseModel`，
> 在 langchain-core 1.7.0 上**已经跑不起来了**（模块被彻底移除），改成 `from pydantic import` 即可。
> 第 ⑨ 个文件是新增的，`with_structured_output` 是现在做结构化输出的首选方案。

### 第四部分：runnable（真实调用 DeepSeek，需要 API key）

```bash
./yzy/Scripts/python.exe "aiLearn/runnable/1.RunnableParallel使用技巧.py"
./yzy/Scripts/python.exe "aiLearn/runnable/2.RunnableParallel模拟检索.py"
./yzy/Scripts/python.exe "aiLearn/runnable/3.RunnablePassthrough使用技巧.py"
```

| 顺序 | 文件 | 讲什么 | 原教材（已归档） |
|---|---|---|---|
| ⑩ | `runnable/1.RunnableParallel使用技巧.py` | 并行多路、真并发实测、max_concurrency、异步 | `old/1.*` |
| ⑪ | `runnable/2.RunnableParallel模拟检索.py` | RAG 最小链路、dict 为何能变 RunnableParallel、多路检索 | `old/2.*` |
| ⑫ | `runnable/3.RunnablePassthrough使用技巧.py` | assign 语义、链式叠加、RunnableAssign | `old/3.*` |

> 这一组教材原文件本身已经在用 LCEL 管道了，所以改动主要是"写法规范化 + 补充新版 API"，
> 不像前两组有破坏性变更。最大的认知更新在第 ⑩ 个文件：**dict 何时等价、何时不等价**。

### 第五部分：callable（真实调用 DeepSeek，需要 API key）

```bash
./yzy/Scripts/python.exe "aiLearn/callable/1.回调功能使用技巧.py"
./yzy/Scripts/python.exe "aiLearn/callable/2.流式回调与用量统计.py"
./yzy/Scripts/python.exe "aiLearn/callable/3.astream_events事件流.py"
```

| 顺序 | 文件 | 讲什么 | 原教材（已归档） |
|---|---|---|---|
| ⑬ | `callable/回调功能使用技巧.py` | `BaseCallbackHandler` 全套钩子、三种绑定方式、`on_chat_model_end` 陷阱 | `old/1.*` |
| ⑭ | `callable/流式回调与用量统计.py` | `on_llm_new_token` 打字机、token 用量统计、**invoke 不触发流式** | 新增 |
| ⑮ | `callable/astream_events事件流.py` | `astream_events(v2)` 事件流、`run_name` / `parent_ids` 区分组件 | 新增 |

> 关键认知：回调和事件流是**两条并行的观测方案**，不是新旧替代关系（选型见 ⑮ 结尾的对照表）。
> 注：这一组的 `old/` 教材文件已经清理，示例平铺在 `callable/` 下。

### 第六部分：memory（真实调用 DeepSeek，需要 API key）

```bash
./yzy/Scripts/python.exe "aiLearn/memory/1.ChatMessageHistory基础.py"          # 无需 key
./yzy/Scripts/python.exe "aiLearn/memory/2.持久化历史存储.py"                  # 无需 key
./yzy/Scripts/python.exe "aiLearn/memory/3.RunnableWithMessageHistory.py"
./yzy/Scripts/python.exe "aiLearn/memory/4.上下文裁剪trim_messages.py"
./yzy/Scripts/python.exe "aiLearn/memory/5.摘要记忆.py"
./yzy/Scripts/python.exe "aiLearn/memory/6.实体记忆.py"
./yzy/Scripts/python.exe "aiLearn/memory/7.记忆选型与LangGraph方案.py"
```

| 顺序 | 文件 | 讲什么 | 原教材（已归档） |
|---|---|---|---|
| ⑯ | `memory/1.ChatMessageHistory基础.py` | 历史接口、自实现历史类、序列化、**实测废弃告警** | `old/ChatMessageHistory组件上手与源码解析/1.*` |
| ⑰ | `memory/2.持久化历史存储.py` | 自实现 JSON 文件持久化、多会话隔离、生产选型 | `old/.../2.文件对话消息历史组件实现记忆.py` |
| ⑱ | `memory/3.RunnableWithMessageHistory.py` | **本组核心**：**已改用 checkpointer 主线**（thread_id 隔离、流式、两个坑），末尾附废弃写法迁移对照 | `old/RunnableWithMessageHistory简化代码与使用/1.*` |
| ⑲ | `memory/4.上下文裁剪trim_messages.py` | `trim_messages` 替代 `ConversationTokenBufferMemory`；第 6 节已改用 `create_agent` + 裁剪中间件 | `old/LangChain缓冲记忆组件/1.*` |
| ⑳ | `memory/5.摘要记忆.py` | 用 LCEL 自建「摘要 + 缓冲」混合记忆 | `old/LangChain摘要记忆组件/1.*` |
| ㉑ | `memory/6.实体记忆.py` | `with_structured_output` 抽实体、固定字段 schema | `old/LangChain实体记忆组件/1.*` |
| ㉒ | `memory/7.记忆选型与LangGraph方案.py` | **本组总结**：三层架构（上下文管理 / 短期 checkpointer / 长期 Store）、`ToolRuntime` 注入、namespace 设计、选型与迁移对照表 | `old/Memory组件运行流程/*`、`old/内置 Chain 组件/*` |

> ⚠️ **这一组是变化最大的一组**：教材里 `langchain.memory` 和 `langchain.chains` 两个模块
> 在 langchain 1.x **已被彻底移除**，`ConversationXxxMemory`、`LLMChain`、`ConversationChain`
> 全都没了。所以这组的写法不是「改个 API」，而是**用 LCEL 自己把记忆搭出来**。
> 好处是搭完你就彻底明白记忆在干什么了。
>
> 注：这一组的 `old/` 教材文件也已清理，示例平铺在 `memory/` 下。

### 第七部分：runnableModule（真实调用 DeepSeek，需要 API key）

```bash
./yzy/Scripts/python.exe "aiLearn/runnableModule/1.bind绑定默认参数.py"
./yzy/Scripts/python.exe "aiLearn/runnableModule/2.configurable_fields运行时改字段.py"
./yzy/Scripts/python.exe "aiLearn/runnableModule/3.configurable_alternatives动态替换组件.py"
./yzy/Scripts/python.exe "aiLearn/runnableModule/4.重试与回退机制.py"
./yzy/Scripts/python.exe "aiLearn/runnableModule/5.生命周期监听器with_listeners.py"
./yzy/Scripts/python.exe "aiLearn/runnableModule/6.RunnableWithMessageHistory回顾.py"
```

| 顺序 | 文件 | 讲什么 | 原教材（已归档） |
|---|---|---|---|
| ㉓ | `runnableModule/1.bind绑定默认参数.py` | bind 预置参数、**多参函数进管道**、不校验的坑 | `old/Runnable组件动态添加默认调用参数/*` |
| ㉔ | `runnableModule/2.configurable_fields运行时改字段.py` | 运行时改 temperature、换提示词、**教材字段名笔误实测** | `old/Runnable组件配置运行时链内部/*` |
| ㉕ | `runnableModule/3.configurable_alternatives动态替换组件.py` | 换模型/换组件、懒加载、**RunnableLambda 不支持** | `old/Runnable组件动态替换运行组件/1.*` |
| ㉖ | `runnableModule/4.重试与回退机制.py` | `with_retry` / `with_fallbacks`、限定异常类型 | `old/Runnable组件重试与回退机制降低程序错误率/*` |
| ㉗ | `runnableModule/5.生命周期监听器with_listeners.py` | `with_listeners`、**和回调的作用范围区别** | `old/Runnable组件生命周期监听器与使用场景/1.*` |
| ㉘ | `runnableModule/6.RunnableWithMessageHistory回顾.py` | 文件名是历史遗留，**内容已全切 checkpointer**：`with_xxx` 在 agent 上照旧可用（实测）、记忆从包装变内建、`{query}` 老签名的适配层迁移技巧 | `old/RunnableWithMessageHistory简化代码与使用/1.*` |

> 这一组的核心是**「怎么包装一个 Runnable」**：改参数、能动态、能容错、能观测、能记事儿。
>
> ⚠️ 其中最后一项「能记事儿」现在**不再是包装**了：`RunnableWithMessageHistory` 已废弃，
> 改用 `create_agent(checkpointer=...)`，记忆由框架托管。见文件 6 的对照表。
> 共同点是**都返回新的 Runnable，不改原对象**（Java 视角：装饰器模式，和 `BufferedInputStream` 一个路子）。

### 第八部分：tool（真实调用 DeepSeek，需要 API key）

```bash
./yzy/Scripts/python.exe "aiLearn/tool/1.工具定义三种方式.py"        # 无需 key
./yzy/Scripts/python.exe "aiLearn/tool/2.逻辑公式类工具.py"
./yzy/Scripts/python.exe "aiLearn/tool/3.远程调用类工具.py"
./yzy/Scripts/python.exe "aiLearn/tool/4.工具绑定与执行闭环.py"
./yzy/Scripts/python.exe "aiLearn/tool/5.工具分组与路由判断.py"
./yzy/Scripts/python.exe "aiLearn/tool/6.Agent与工具实战.py"
./yzy/Scripts/python.exe "aiLearn/tool/7.Skill标准规范与渐进式加载.py"
```

| 顺序 | 文件 | 讲什么 |
|---|---|---|
| ㉙ | `tool/1.工具定义三种方式.py` | `@tool` / `StructuredTool` / `BaseTool` 子类、`ToolException`、描述四要素 |
| ㉚ | `tool/2.逻辑公式类工具.py` | 纯计算类工具（月供 / 日期差 / 温度 / 运费）、并行调用、`eval` 安全 |
| ㉛ | `tool/3.远程调用类工具.py` | 超时 / 重试 / 4xx 不重试 5xx 重试 / 凭证不放 schema / 结果裁剪 |
| ㉜ | `tool/4.工具绑定与执行闭环.py` | `bind_tools`、手写四步闭环、并行执行、`tool_choice` 四档实测 |
| ㉝ | `tool/5.工具分组与路由判断.py` | **能力域分组**（≠ Skill）+ 判断击中哪个域的 6 种方法 + 两级路由 + `LLMToolSelectorMiddleware` |
| ㉞ | `tool/6.Agent与工具实战.py` | `create_agent`、多轮记忆、中间件（工具筛选含 DeepSeek 绕过 / 工具重试）、完整客服 Agent |
| ㉟ | `tool/7.Skill标准规范与渐进式加载.py` | **Skill 开放标准**：`deepagents`、三级渐进式披露、`pinned_skills`、`include_tools` |

> 这一组回答三个问题：**工具怎么造（1-3）→ 怎么让模型用（4）→ 用了之后怎么知道（5-7）**。
>
> ⚠️ **术语已统一**：文件 5 原来叫「Skill 集成」，名字是错的，已改名为「工具分组与路由判断」。
> 把工具按业务域塞进一个字典，这个分组叫**能力域 / 工具域**（domain），**不是 Skill**。
> Skill 是另一套东西：**开放标准**（Anthropic 发起，2025-12-18 发布为 open standard，规范站
> https://skill.md），格式是目录 + `SKILL.md` + `scripts/references/assets`，官方实现在 `deepagents`。
>
> 最容易混的一点——两者判断「命中」的方式完全不同：
>
> | | 文件 5 的能力域 | 文件 7 的 Skill |
> |---|---|---|
> | 是什么 | 工具的分组（Python 字典） | 独立目录 + `SKILL.md` + 脚本/资料 |
> | 谁加载 | 手动 `create_agent(tools=...)` | `deepagents` 按需读取 |
> | 怎么判断命中 | 看 `tool_calls` 里的**工具名** | 看 `read_file` 读了哪个 **`SKILL.md`** |
> | 适合 | 工具 10~50 个，要管住选择范围 | 能力需要配套说明文档/脚本/参考资料 |
>
> 一句话：**文件 5 管「发给模型哪些工具」，文件 7 管「怎么把知识按需喂给模型」。**
> 两者可以叠加：用能力域管工具选择范围，用 Skill 加载业务知识。
> 建议先看 5 理解「工具选择」这个问题，再看 7 看标准答案。

---

## 零、目录结构与 .env 加载方式

```
aiLearn/
├── prompts/      零依赖可跑（messages / prompts / 模板类）
├── model/        真实调 DeepSeek（基础调用 / 批处理 / 流式）
├── outputParser/ 真实调 DeepSeek（Str / Json / 结构化输出）
├── runnable/     真实调 DeepSeek（并行 / RAG / assign）
├── callable/    最新 API（回调 / 流式 / 事件流）
├── memory/         最新 API（历史 / 持久化 / 裁剪 / 摘要 / 实体 / LangGraph）
├── runnableModule/  最新 API（bind / 动态配置 / 容错 / 监听 / 记忆接入方式）
├── tool/          最新 API（工具定义 / 公式类 / 远程类 / bind_tools / 分组路由 / Agent / 标准 Skill）
│   └── skills/    按 Agent Skills 开放标准写的 3 个 skill（order / product / after-sale）
├── PYTHON_SYNTAX.md   ← Python 语法速查（闭包 / lambda / **解包，带 Java 对照）
└── README.md
```

> **看不懂某个 Python 写法先看 `PYTHON_SYNTAX.md`**。
> 比如"返回函数的函数"（闭包工厂）、`lambda x: ...`、`**{...}` 这些，
> 都配了 Java 对照写法，一看就懂。代码里同类写法只在首次出现处详细注释。

> 示例代码不从 `aiLearn/` 这一层算固定的 `parents[N]` 去找 `.env`，
> 而是**从文件所在目录向上逐层查找**（见每个文件顶部的 `_find_env()`）。
> 之前写成 `parents[3]` 时，目录层级一调整就找不到了，直接报
> `Missing credentials`。改成向上查找后，文件怎么挪都不会失效。

## 一、先建立一张心智地图

```
                      你的业务数据
                          │
                          ▼
   ┌──────────────────────────────────────────┐
   │  prompts（模板层）                        │
   │  ChatPromptTemplate 把变量渲染成消息数组  │  ← 纯本地，不联网
   └──────────────────────────────────────────┘
                          │  产出 List[BaseMessage]
                          ▼
   ┌──────────────────────────────────────────┐
   │  messages（数据层）                       │
   │  角色 + 内容，是模型 API 的真实入参格式   │
   └──────────────────────────────────────────┘
                          │
                          ▼
                    ChatModel（DeepSeek / OpenAI ...）
                          │
                          ▼
                    AIMessage → 解析器 → str
```

**一句话区分**：
- `prompts` 是**怎么拼出请求**（模板、变量、占位符）
- `messages` 是**请求长什么样**（带角色的消息数组）

---

## 二、ChatPromptTemplate 是不是"字符串拼接"？

**一半对。** 它做的是模板渲染，但产出物不一样：

| | 裸字符串拼接 | ChatPromptTemplate |
|---|---|---|
| 产出 | 一个 `str` | `List[BaseMessage]`，每条带 role |
| 角色区分 | ❌ 模型分不清哪句是谁说的 | ✅ system / human / ai / tool |
| 少传变量 | 静默拼出 `{x}` | ✅ 提前报错 |
| 历史消息 | 手写循环 | ✅ `MessagesPlaceholder` |
| 复用/组合 | 复制粘贴 | ✅ `partial` / `|` 管道 |

> 大模型 API 的入参**本来就不是字符串**，而是带角色的消息数组。这就是需要 messages 的根本原因。

---

## 三、prompts 速查（按使用频率排序）

| 用法 | 代码示例 | 场景 |
|---|---|---|
| `ChatPromptTemplate.from_messages` | `[("system","你是{role}"),("human","{q}")]` | **90% 场景**，主力写法 |
| `MessagesPlaceholder` | `MessagesPlaceholder("history")` | 多轮对话注入历史 |
| `.partial(date=...)` | 预绑定变量 | 注入日期/租户/用户画像 |
| `FewShotChatMessagePromptTemplate` | 传 `examples` + `example_prompt` | few-shot 示例 |
| `PromptTemplate.from_template` | `"翻译成{lang}"` | 纯文本模板（老式补全模型） |
| `prompt \| model \| StrOutputParser()` | LCEL 管道 | 组合成可执行链路 |

---

## 四、messages 速查

### 五种核心类型

| 类型 | role | 用途 |
|---|---|---|
| `SystemMessage` | system | 系统指令、人设、规则（优先级最高） |
| `HumanMessage` | human/user | 用户说的话 |
| `AIMessage` | ai/assistant | 模型回复、历史、预填充 |
| `ToolMessage` | tool | 工具结果，靠 `tool_call_id` 关联 |
| `ChatMessage` | 自定义 | 非主流模型可能用到 |

### 四大作用

1. **承载多轮历史** —— 不断往列表追加，整段发给模型
2. **工具调用链路** —— `AIMessage.tool_calls` → 执行 → `ToolMessage(tool_call_id=...)` 回填
3. **多模态内容块** —— `content` 可以是 `[{"type":"text",...},{"type":"image_url",...}]`
4. **上下文工程** —— `trim_messages` / `filter_messages` / `merge_message_runs`

### 上下文工程三件套

```python
merge_message_runs(msgs)                        # 合并连续同类消息，省 token
filter_messages(msgs, include_types=["human"])  # 按角色过滤
trim_messages(msgs, max_tokens=2000,            # 按预算裁剪（生产必备）
              token_counter=counter,
              strategy="last",
              include_system=True)              # ⚠️ 默认 False 会裁掉系统提示词
```

### 序列化与流式

```python
messages_to_dict(msgs)      # → 存 Redis / PostgreSQL
messages_from_dict(data)    # ← 读回来
chunk_a + chunk_b           # 流式 AIMessageChunk 可直接相加
```

---

## 五、怎么接 DeepSeek

DeepSeek 用的是 **OpenAI 兼容协议**，所以换 `base_url` 即可：

```python
# pip install langchain-openai
from langchain_openai import ChatOpenAI

model = ChatOpenAI(
    model="deepseek-flash",
    api_key=os.environ["DEEPSEEK_API_KEY"],
    base_url="https://api.deepseek.com",
)
```

> ⚠️ **模型名实测（2026-10-26）**：调 `/models` 接口查到 DeepSeek 当前只有
> `deepseek-flash` 和 `deepseek-v4-pro` 两个模型，**没有 `deepseek-chat`**。
> 网上教程清一色写 `deepseek-chat`，传它会被服务端静默映射到 `deepseek-flash`——
> 能跑通，但你以为在用的模型和你实际用的不是同一个。建议显式写 `deepseek-flash`。

> `prompts/prompts_demo.py` 里的 `build_model()` 已经写好了这个自适应逻辑：
> 配了 `DEEPSEEK_API_KEY` 且装了 `langchain-openai` 就走真模型，否则自动回退到假模型。

**为什么社区都在聊 `langchain_openai`**：官方包 `langchain-deepseek` 的依赖里就含
`langchain-openai>=1.3.1`，底层就是它。而 `langchain-openai` 一个包能通吃所有
OpenAI 兼容厂商（DeepSeek / 通义 / Kimi / 智谱 / vLLM / Ollama），换模型只改 `base_url`。

---

## 五点五、model 部分的实测数据

都是在本项目 venv + 真实 DeepSeek 上跑出来的，不是估算：

| 指标 | 实测结果 | 出处 |
|---|---|---|
| 串行 invoke vs 并发 batch（4 条请求） | 5.75s → 1.75s，**提速 3.29x** | `2.Model批处理.py` 第 2 节 |
| 首个 chunk 到达 vs 首个真实文字 | 0.28s（空） vs **1.75s** | `3.Model流式输出.py` 第 4 节 |
| 非流式拿全部内容 | 2.40s | 同上 |
| 流式 chunk 分布 | 65 个 chunk 里**前 43 个是空的**（思考阶段） | `3.Model流式输出.py` 第 2 节 |
| `temperature=0` 稳定性 | **两次输出不一致**，并非完全确定 | `1.LLM与ChatModel使用技巧.py` 第 3 节 |

两点提醒：
- **别把"首个 chunk"当 TTFT**。DeepSeek 是带思考的模型，前面会吐一堆空 chunk，
  真实首字延迟是首个非空内容的到达时间（实测差 6 倍）。
- **`temperature=0` 不保证逐字一致**。要严格稳定输出，得靠
  `JsonOutputParser` / `with_structured_output()` 在格式层面兜底。

---

## 五点六、outputParser 部分的实测结论

### `with_structured_output` 三种 method 在 DeepSeek 上的表现

| method | 实测结果 | 原因 |
|---|---|---|
| `json_schema`（默认） | ❌ 400 | `This response_format type is unavailable now`，DeepSeek 不支持 |
| `json_mode` | ❌ 400 / 解析失败 | prompt 必须含 `json` 字样；且只保证输出 JSON 对象，**不保证 schema**，实测多吐了 `type` 字段 |
| `function_calling` | ✅ **可用** | 但要先关掉思考模式，否则报 `Thinking mode does not support this tool_choice` |

### DeepSeek 结构化输出的正确姿势

```python
llm = ChatOpenAI(
    model="deepseek-flash",
    api_key=..., base_url="https://api.deepseek.com",
    extra_body={"thinking": {"type": "disabled"}},   # ← 关键：关掉思考模式
)
chain = prompt | llm.with_structured_output(MySchema, method="function_calling")
```

思考模式与 function calling 互斥，这是 DeepSeek 特有的坑，不关就永远 400。

### 选型建议

| 场景 | 用什么 |
|---|---|
| 只要一段纯文本 | `StrOutputParser` |
| 1-3 个简单字段 | `JsonOutputParser` / `PydanticOutputParser` |
| 嵌套结构、列表、可选字段 | `with_structured_output` |
| 要接数据库/下游接口 | `with_structured_output`（格式由 API 层保证） |

---

## 五点七、runnable 部分的实测结论

### RunnableParallel 是真并发

实测两个各阻塞 1.5s 的分支：

| 方式 | 耗时 |
|---|---|
| 串行预期 | 3.00s |
| `RunnableParallel.invoke()` **实测** | **1.51s** |

两个分支跑在 `ThreadPoolExecutor-1_0` / `_1` 两个不同线程上。
`invoke()` 内部用线程池跑各个分支，IO 密集场景（调模型、查库）收益很大。

### 三个易混淆的概念

| 组件 | 语义 | 什么时候用 |
|---|---|---|
| `RunnableParallel({...})` | 明确列出要哪些字段，**丢弃未列出的** | 只要少数几个字段 |
| `{字典字面量}` | 同上，是它的语法糖 | 管道里追求简洁 |
| `RunnablePassthrough.assign(...)` | **保留全部原字段 + 追加新的** | 字段多、想保留大部分 |

`assign` 内部等价于 `RunnableAssign(RunnableParallel(...))`，所以**也是并发的**
（实测两个各 1.2s 的字段总耗时 1.21s，串行应为 2.40s）。

### dict 字面量为什么能接 `|`

```
{"a": fn} | prompt
   ↑ dict 没有 __or__
        ↓ Python 改调用右边 prompt 的 __ror__
             ↓ langchain 在里面把 dict 转成 RunnableParallel
```

由此推导出的坑：**`|` 要求两边至少一边是 Runnable**。

| 写法 | 结果 |
|---|---|
| `dict \| Runnable` | ✅ |
| `RunnableParallel \| fn` | ✅ |
| `dict \| fn`（两边都不是 Runnable） | ❌ TypeError |

---

## 五点八、callable 部分的实测结论

### 回调：20 个 on_* 钩子，但只有用的那几个会触发

`BaseCallbackHandler` 里能拿到 20 个 `on_*` 方法，全部是**空实现**（默认什么都不做）。
你重写哪个，哪个才生效；其余的不会有任何输出——所以"我明明加了 handler 怎么没反应"
通常不是没绑上，而是**重写的方法名写错了**。

⚠️ **实测踩坑：`on_chat_model_end` 根本不存在**（正确名是 `on_llm_end`）。
写了它不会报错、不会警告，就是永远不触发——这是静默失败，最难查。
第 ⑬ 个文件里专门做了这个演示。

### `invoke()` 不触发 `on_llm_new_token`

| 调用方式 | 实测 `on_llm_new_token` 次数 |
|---|---|
| `chain.invoke(...)` | **0 次** |
| `chain.stream(...)` | **130 次** |

回调里只有 `stream()` / `astream()` 才会一个 chunk 一个 chunk 地回调。
想做打字机效果就必须用 `stream()`，这一点在第 ⑭ 个文件里做了对照实验。

### 事件流：`astream_events(version="v2")`

一次 `prompt | llm | parser` 调用实测吐出的事件（v2 必须显式指定，v1 已过时）：

| 事件 | 次数 | 说明 |
|---|---|---|
| `on_chain_start` / `on_chain_end` | 1 / 1 | 整条链 |
| `on_prompt_start` / `on_prompt_end` | 1 / 1 | 模板渲染 |
| `on_chat_model_start` / `on_chat_model_end` | 1 / 1 | 模型调用 |
| `on_chat_model_stream` | **82** | 模型逐个吐字 |
| `on_parser_start` / `on_parser_end` | 1 / 1 | 解析器 |
| `on_chain_stream` / `on_parser_stream` | 82 / 82 | 跟着模型流式走 |

事件名规律：`on_<组件>_<阶段>`，组件是 `chain / prompt / chat_model / parser / tool / retriever`，
阶段是 `start / stream / end / error`——记住规律就不用背方法名了。

### 嵌套链路怎么区分每一步（⑮ 的核心）

**坑**：`step1`、`step2`、整条链都叫 `RunnableSequence`，光看 `name` 分不清谁是谁。

两种解法，实测都有效：

1. **`.with_config(run_name="① 翻译")`** —— 给组件起名字（推荐）。只是加标签，不改任何逻辑，
   但在事件流和 LangSmith 追踪里能救命。
2. **判断 `not event["parent_ids"]`** —— 根链没有父节点，`parent_ids` 是空列表 `[]`，
   越外层越短，可以直接判定"这是最终结果"。

### 回调 vs 事件流：怎么选

| 维度 | 回调 `BaseCallbackHandler` | 事件流 `astream_events` |
|---|---|---|
| 写法 | 继承类 + 重写方法 | `async for` 遍历 + `if` 判断 |
| 适用链路 | 同步 / 异步都行 | **仅异步** |
| 拿中间结果 | 比较绕 | 直接取 `event["data"]` |
| 嵌套链路 | 靠 `run_id` 自己串 | `parent_ids` 自动关联 |
| 对接监控平台 | LangSmith 就用这个 | 常用于前端推送 |

- 日志 / 监控 / 计费这类「旁路」需求 → **回调**（更轻，同步异步都能用）
- 流式 UI、进度条、要中间结果 → **事件流**（信息最全）
- 要接入 LangSmith 做追踪 → **回调**（官方集成方式）

---

## 五点九、memory 部分的实测结论

### 老 API 现状（逐个 import 实测，不是猜的）

| 组件 | 现状 |
|---|---|
| `langchain.memory`（整个模块） | ❌ **已移除** —— `BaseChatMemory` / `ConversationBufferMemory` / `ConversationTokenBufferMemory` / `ConversationSummaryBufferMemory` / `ConversationEntityMemory` 全没了 |
| `langchain.chains`（整个模块） | ❌ **已移除** —— `LLMChain` / `ConversationChain` / `create_stuff_documents_chain` 全没了 |
| `InMemoryChatMessageHistory` / `BaseChatMessageHistory` | ⚠️ **已废弃**（1.6.4 起，2.0.0 移除），能用但抛 `LangChainDeprecationWarning` |
| `RunnableWithMessageHistory` | ⚠️ **已废弃**（1.3.3 起，2.0.0 移除），能用但会告警，官方让改用 LangGraph 持久化 |
| LangGraph `checkpointer` + `thread_id` | ✅ **官方推荐方向** |

### ⚠️ 废弃告警抓不到？

`InMemoryChatMessageHistory` 的废弃告警**每个进程只报一次**（Python 警告去重），
所以在同一个脚本里第二次实例化是抓不到警告的——想实测必须开一个干净的子进程。
第 ⑯ 个文件里就是这么做的。

### 会话记忆的两个坑（老 API 和 checkpointer 都有，只是 key 名换了）

> ⚠️ **2026-10 更新**：`memory/3` 已把主线从废弃的 `RunnableWithMessageHistory`
> 改成官方推荐的 **LangGraph checkpointer**，`session_id` → `thread_id`。
> 两个坑的性质完全一样，只是报错信息换了：

1. **它会自动写历史**，别自己再拼一遍——实测消息会翻倍（老 API 是手动 `add_*`，
   checkpointer 是手动把历史塞进 `messages`，都会翻倍）。
2. **会话标识必传**，不传直接 `ValueError`：
   - 老 API：`Missing keys ['session_id'] in config['configurable']`
   - checkpointer：`Checkpointer requires one or more of the following 'configurable' keys: thread_id, checkpoint_ns, checkpoint_id`

**两维度定位**（某用户的某会话）：checkpointer 只有一个 `thread_id`，
实用做法是拼字符串 `thread_id = f'{user_id}:{session_id}'`，
再用 `agent.checkpointer.list(None)` 枚举按前缀过滤（实测可行）。

### 持久化：InMemorySaver 重启就丢，生产必须落盘

`memory/3` 的第 7 节专门讲这个，四项实测：

1. 写入 sqlite → 关连接（模拟服务停）
2. 重开连接再问 → 答得出「你叫老王」，4 条消息
3. sqlite 里有 `checkpoints` / `writes` 两张表，对话是**序列化**存在 `checkpoint` 字段里
4. **起一个全新的 python 进程**读同一个库 → 仍答「你叫老王」（6 条）✅ 真·重启验证

正确写法：

```python
import sqlite3
from langgraph.checkpoint.sqlite import SqliteSaver

conn = sqlite3.connect("checkpoints.db", check_same_thread=False)
checkpointer = SqliteSaver(conn)          # ← 不是 from_conn_string(...)
agent = create_agent(model=llm, checkpointer=checkpointer)
```

⚠️ **`from_conn_string` 在 3.x 是 `@contextmanager`**，直接赋值会拿到上下文管理器：

```
checkpointer = SqliteSaver.from_conn_string("checkpoints.db")   # ❌
→ TypeError: Invalid checkpointer provided...Received _GeneratorContextManager
```

要嘛 `with SqliteSaver.from_conn_string(...) as cp:`，要嘛自己建连接（服务用后者）。
`check_same_thread=False` 必须写，否则多线程服务报错。

选型：demo/单测 → `InMemorySaver`；单机 → `langgraph-checkpoint-sqlite`；
多实例/分布式 → `langgraph-checkpoint-postgres`。

### trim_messages 的三个坑

1. **`include_system` 默认 False**，不写就把系统提示词裁掉了（人设丢失，且不报错）。
2. **`include_system` 不能配 `strategy='first'`**，直接 `ValueError: include_system parameter is only valid with strategy='last'`。
3. **`allow_partial=True` 单独写没效果**，必须同时给 `text_splitter`；且只对「边界那条消息」生效。
   实测：`max_tokens=40` 下 strict 得 1 条 `[4]`，加 `allow_partial + text_splitter` 得 2 条 `[4, 97]`。

### 实体记忆：自由 key 下「同名覆盖」根本不生效

我原本以为「广州」会被「深圳」覆盖，实测结果是**两个都在**——
模型把搬家抽成了新实体「深圳」，而不是更新「广州」的值。
原因是实体名（dict 的 key）由模型自由发挥，每次都可能不同。

**解法（实测有效）**：别用 `Dict[str, str]`，改成**固定 pydantic 字段**
（`name` / `city` / `main_language`），key 由你定，更新一定生效。
实测三次调用后 `city` 从「广州」正确变成「深圳」。

### DeepSeek 结构化输出必须关思考

实体抽取要用 `with_structured_output(method="function_calling")`，
而 DeepSeek 的思考模式和 function calling 互斥，必须：
`ChatOpenAI(..., extra_body={"thinking": {"type": "disabled"}})`。
建议**单独建一个抽取用的模型实例**，普通对话保留思考（质量更好）。

### 官方推荐方案（实测跑通）

```python
agent = create_agent(model=llm, system_prompt="...", checkpointer=InMemorySaver())
agent.invoke({"messages": [{"role": "user", "content": "..."}]},
             {"configurable": {"thread_id": "thread_001"}})
```

实测：同一 `thread_id` 连聊三轮，第三轮能答出「你叫慕小课，住在广州」；
换 `thread_id` 立刻答不出来（记忆隔离正确）。
**`thread_id` 就是 `session_id` 的马甲，语义完全一样。**

### 长期记忆：Store + ToolRuntime（实测跑通）

短期记忆只能活在一次会话里。「这个用户是谁」这类事实要跨会话记住，
就得用 Store。给工具用的正确注解是 `ToolRuntime`，**不是** `Runtime`：

```python
from langgraph.prebuilt import ToolRuntime   # ← 工具用这个
from langgraph.store.memory import InMemoryStore
from langchain_core.tools import tool

@tool
def save_fact(fact: str, runtime: ToolRuntime) -> str:
    """把一条关于用户的事实保存进长期记忆。"""
    items = runtime.store.search(("facts",))
    runtime.store.put(("facts",), f"f{len(items)}", {"fact": fact})
    return f"已记住：{fact}"

agent = create_agent(model=llm, tools=[save_fact, read_facts],
                     checkpointer=InMemorySaver(),   # 短期：本会话历史
                     store=InMemoryStore())          # 长期：跨会话事实
```

实测：`thread_A` 里存了 3 条事实，换 `thread_B`（全新会话）去问
「你还记得我的什么信息？」——照样答得出来。**短期隔离、长期共享，同时成立。**

#### 三个要点

1. **注解写错会直接崩**：写 `runtime: Runtime` 会抛
   `PydanticInvalidForJsonSchema: Cannot generate a JsonSchema for ... IsInstanceSchema(BaseStore)`。
   原因：工具每个参数都要生成 JSON Schema 给模型看，`Runtime`/`BaseStore` 不是模型该填的参数。
   `ToolRuntime` 继承 `_DirectlyInjectedToolArg`，框架会把它从 Schema 里摘掉，所以**不用 `Annotated` 包一层**。
2. **namespace 必须带 user_id**：`("facts", user_id)`。
   两条键：`namespace`（元组，可前缀匹配）+ `key`（字符串）。
   `search(("facts",))` 是前缀匹配（≈ SQL 的 `LIKE 'facts%'`），`get(ns, key)` 是单条精确读。
   不按用户分 namespace 会串号——这是最常见的越权 bug。
3. **Store 也有持久化实现**：`SqliteStore.from_conn_string(path)`。
   注意它**是**上下文管理器（要 `with`），跟 `SqliteSaver` 我们绕开 `from_conn_string` 的写法不一致，历史遗留。

#### 短期 vs 长期的分工

| | 短期记忆 | 长期记忆 |
|---|---|---|
| 存什么 | 全量对话流水 | 抽取出来的结论（画像、偏好） |
| 怎么区分 | `thread_id` | `namespace` |
| 换会话 | 读不到 | 读得到 |
| 实现 | `checkpointer` | `store` |

> 别把原始对话流水往 Store 里塞——那是短期记忆的活。

### 官方上下文管理中间件（实测 import 探活）

| 中间件 | 策略 | 代价 | 什么时候用 |
|---|---|---|---|
| `TrimMessagesMiddleware` | 硬裁剪，砍最早的 | 丢信息 | 最省事、最可控 |
| `SummarizationMiddleware` | 超阈值压成摘要 | 多花一次调用 | 不想丢信息 |
| `ContextEditingMiddleware` | 按规则改写/删除 | 要配规则 | 精细控制 |

> `wrap_model_call` 只改「发给模型的那一批」（存储不变）；
> `before_model` 返回状态更新（**存储真的被改**）。
> 想省钱又不丢历史 → `wrap_model_call`；想给存储瘦身 → `before_model` / `SummarizationMiddleware`。

### 一句话记住

> 老思路：LangChain 给你一堆 Memory 类，帮你把存取历史全包了。
> 新思路：记忆不是一个组件，是**三层架构**——
> 短期记忆交给 checkpointer（按 `thread_id`），长期记忆交给 Store（按 `namespace`），
> 上下文管理（裁剪/摘要/抽取）是**独立的纯函数**，跟存储解耦、随便换。

---

## 五点十、runnableModule 部分的实测结论

### ⚠️ 重要更正：`RunnableWithMessageHistory` 也是废弃的

之前我判断它「未废弃」，**错了**。实测构造时就抛：

```
LangChainDeprecationWarning: RunnableWithMessageHistory is deprecated.
Use LangGraph's built-in persistence instead.        (since 1.3.3, removal 2.0.0)
```

我第一次只看了类源码的开头（docstring 区），没看到 `__init__` 里的 `warn_deprecated` 调用——
**教训：判断一个 API 是否废弃，要看运行时警告，不能只看源码开头。**

连同 `ChatMessageHistory` 接口（1.6.4 起废弃），官方的方向很明确：
**统一改用 LangGraph checkpointer（`memory/7` 有实测）**。

### bind

- **不校验参数**：`bind(model="gpt-4o")` 在 DeepSeek 上要到发请求时才报 400，
  错误信息里会把支持的模型名列出来（`deepseek-flash, deepseek-v4-pro`）。
- **是覆盖不是合并**：后 bind 的覆盖先 bind 的。
- **⚠️ DeepSeek 上 `max_tokens` 不生效**：实测同一 prompt 用 None / 60 / 20 各跑一次，
  输出长度和设置值毫无相关性（几百到一千字不等）。想限长只能在提示词里写「不超过 N 字」。

### configurable_fields

- **会校验字段名**（比 bind 安全）：写错立刻 `ValueError`，且报错信息会列出所有可用字段。
- **教材笔误**：`template_demo` 是错的，正确是 `template`。
- **ChatOpenAI 上模型名字段是 `model_name` 不是 `model`**（`model` 只是别名，不认真名）。

### configurable_alternatives

- **只在 pydantic 系 Runnable 上有**：`ChatOpenAI` / `PromptTemplate` / `RunnableParallel` /
  `RunnablePassthrough` ✅；**`RunnableLambda` 没有**这两个方法（AttributeError）。
  替代方案：`RunnableLambda` 的函数可以声明第二个参数 `config`，自己读 config 分派。
- **选择 key 要和注册时的 key 一致**：传不存在的 key → `ValueError: Unknown alternative`。
  教材里注册 `gpt4` 却传 `gpt4o`，在新版本上会炸。
- **`default_key` 不存在不报错**，会退化成基础组件。
- **`prefix_keys` 不是给选择 key 加前缀**（实测传 `'llm/pro'` 会 ValueError）。
  它真正的作用是给**备选组件自己的 configurable_fields** 加命名空间 `llm==pro/t`，
  用于「只给某一个备wahl组件配字段」。

### with_retry / with_fallbacks

- `stop_after_attempt` = **总尝试次数**（含第一次），不是「额外重试几次」。
- **必须配 `retry_if_exception_type`**：默认任何异常都重试，参数错误（400）也重试 3 次纯属浪费钱。
  实测限定后 ValueError 只跑 1 次，ConnectionError 才跑满 3 次。
- 默认开了**指数退避 + 抖动**，实测失败 2 次后成功的调用总耗时约 3.5s（大部分是等待）。
- **`exception_key` 的两个坑**：① 开了它输入**必须是 dict**，传字符串直接 ValueError；
  ② 兜底函数收到的是「原始输入 + exception 键」组成的 dict，**不是**单独的异常对象。

### with_listeners vs 回调

| 维度 | with_listeners | BaseCallbackHandler |
|---|---|---|
| 作用范围 | 某一个 Runnable | 整条链 + 所有子链 |
| 传递性 | ❌ 不传递 | ✅ 自动传给子链 |
| 典型用途 | 盯某一步的耗时/审计 | 全链路日志/追踪/计费 |

实测：把 listener 挂在 `(a | b)` 这条链上只触发 1 次；挂在里面的 `a` 上也只触发 1 次——**不会扩散到子链**。

### 这一组学到的 with_xxx，在 agent 上照样能用（实测）

`create_agent(model=...)` 收的就是一个 Runnable，所以这一组的东西一个都没过时：

```python
llm = ChatOpenAI(...)
llm = llm.with_retry(stop_after_attempt=3, retry_if_exception_type=(APIError,))
llm = llm.with_fallbacks([备用模型])
llm = llm.with_listeners(on_end=记耗时)

agent = create_agent(model=llm, checkpointer=InMemorySaver())
```

实测：`with_retry` 失败 2 次后成功（共调用 3 次）、`with_fallbacks` 主组件挂了切备用、
`with_listeners` 挂模型上调用一次 agent 触发 `on_end` 1 次。
`create_agent` 返回的 `CompiledStateGraph` 自己也还是 Runnable，
同样有 `invoke` / `stream` / `batch` / `with_retry`。

**组合顺序的约束消失了**：老写法要纠结「历史包装放最外层、重试放内层，否则重试会重复写历史」，
新写法里 checkpointer 是框架托管的内建能力，跟 `with_xxx` 不在同一维度，不存在谁包谁的问题。

### 老代码 `{query}` 签名的平滑迁移（实测有效）

老代码到处是 `chain.invoke({"query": "..."}, config={"configurable": {"session_id": "x"}})`，
全改造成 `{"messages": [...]}` 成本高。加一层适配即可，且 **config 自动透传**，`thread_id` 照样能用：

```python
def to_state(x: dict) -> dict:
    return {"messages": [{"role": "user", "content": x["query"]}]}

adapted = RunnableLambda(to_state) | agent
adapted.invoke({"query": "我叫慕小课"}, {"configurable": {"thread_id": "u1"}})
```

实测：连续两次用老签名调用，第二次能正确答出「你叫慕小课」——记忆生效。
（Java 视角：这就是适配器模式，调用方无感。）

### 这一组的记忆口诀

```
改参数 → bind
要动态 → configurable_fields / configurable_alternatives
要容错 → with_retry / with_fallbacks
要观测 → with_listeners / callbacks
要记忆 → create_agent + checkpointer（不再是包装，框架托管）
```

---

## 五点十一、tool 部分的实测结论

### 先分清两个东西：能力域（文件 5）vs Skill（文件 7）

这是我改过一次名的地方，值得单独说清楚。

**⚠️ 2026-10 更正**：我一开始只在 langchain 1.4.7 包里搜 `Skill` 类名，没搜到就写
「Skill 是我们自己组织工具的方式」——**这是错的**。

**Agent Skills 是开放标准**（Anthropic 发起，2025-12-18 发布为 open standard，规范站 https://skill.md）。
Skill 不是一个类，但它是**标准格式**（目录 + SKILL.md + scripts/references/assets），
不是各人自创的组织方式。LangChain 官方实现在 `deepagents` 包（要求 Python>=3.11）。

修正之后又发现了第二个问题：**文件 5 把「工具分组字典」叫 Skill 也是错的**，
已改名为 `5.工具分组与路由判断.py`，里面那个字典改叫**能力域**（domain）。

| | 能力域（文件 5） | Skill（文件 7） |
|---|---|---|
| 是什么 | 工具的分组（一个 Python 字典） | 独立目录 + `SKILL.md` + 脚本/资料 |
| 谁加载 | 手动 `create_agent(tools=...)` | `deepagents` 按需读取 |
| 怎么判断命中 | 看 `tool_calls` 里的**工具名** | 看 `read_file` 读了哪个 **`SKILL.md`** |
| 适合 | 工具 10~50 个，要管住选择范围 | 能力需要配套说明文档/脚本/参考资料 |

一句话：**文件 5 管「发给模型哪些工具」，文件 7 管「怎么把知识按需喂给模型」。**
两者不冲突，可以叠加用。

### 能力域怎么落地（文件 5）

自建方式落地成三件事：

1. 用字典把工具按业务域分组：`DOMAINS = {"订单": [...], "商品": [...]}`
2. 官方的 `BaseToolkit` 抽象（实现 `get_tools()`）
3. 一张反查表：`TOOL_TO_DOMAIN = {工具名: 域名}`

判断「击中哪个域」的本质全是这一行：**工具名 → 反查表 → 域名**。六种方法只是「在哪里拿到工具名」的区别。

> 这个反查表是手工维护的，容易漏。用标准 Skill 就不需要它——
> 工具归属写在 `SKILL.md` 的 `include_tools` 里。

### 判断击中哪个能力域：六种方法怎么选

| 方式 | 成本 | 可控性 | 什么时候用 |
|---|---|---|---|
| ① 看 `AIMessage.tool_calls` | 零 | 低 | 调试、简单场景（最常用） |
| ② 回调 `on_tool_start` | 零 | 中 | 全链路埋点、计费、统计次数 |
| ③ `astream_events` | 零 | 中 | 前端流式显示「正在查询...」 |
| ④ 工具内部埋点 | 改代码 | 高 | 需要业务字段（用户 ID、耗时、结果码） |
| ⑤ `tool_choice` 强制 | 零 | 最高 | 确定这一步必须调某个工具 / 做结构化抽取 |
| ⑥ 两级意图路由 | 多一次调用 | 最高 | 工具 > 20 个 |

实测路由准确率：8 个工具 / 3 个域，4 个问题（订单 / 商品 / 售后 / 闲聊）**全部命中正确域**，
闲聊句正确返回空 `tool_calls`。

### ⚠️ 方法③最大的坑：bind_tools 不产生工具事件

```python
async for e in llm.bind_tools(tools).astream_events(q, version="v2"):
    ...  # 只有 on_chat_model_*，永远等不到 on_tool_start
```

`bind_tools` 只让模型「说出想调谁」，**工具压根没执行**。必须把执行那一步接进链：

```python
async def run_tools(ai, config: RunnableConfig):   # ← 第二个参数 config 必须声明
    return [await TOOLS[c["name"]].ainvoke(c["args"], config=config) for c in ai.tool_calls]

chain = llm.bind_tools(tools) | RunnableLambda(run_tools)   # 这样才有 on_tool_*
```

关键是 **`config` 要透传给 `tool.ainvoke(...)`**，否则回调链断掉，事件照样不触发。
（Java 视角：和方法签名里声明了 `ProceedingJoinPoint` 框架才把上下文递给你，是一个道理。）

### `tool_choice` 四档在 DeepSeek 上的实测矩阵

| 思考模式 | `tool_choice` | 结果 |
|---|---|---|
| 开 | `auto` | ✅ 正常，`tool_calls` 正常返回 |
| 开 | `any` | ❌ `OpenAIInvalidRequestError`（思考模式不支持强制 tool_choice） |
| 关 | `auto` | ✅ 正常 |
| 关 | `any` | ✅ 返回了 2 个工具调用 |
| 关 | 指定工具名 | ✅ 只返回指定那个 |

**结论**：`bind_tools` + 默认 `auto` 可以开思考，两者不冲突；一旦要**强制**指定，必须关思考。

### DeepSeek 结构化输出的死规矩（本组又踩了一次）

```
with_structured_output(Schema)                     → 400 This response_format type is unavailable now
with_structured_output(Schema, method="function_calling")  ← 必须这样
# 且 function_calling 与思考模式冲突，还要：
extra_body={"thinking": {"type": "disabled"}}
```

### ⚠️ `LLMToolSelectorMiddleware` 在 DeepSeek 上直接 400

中间件内部硬编码了 `model.with_structured_output(schema)`（默认 json_schema），
DeepSeek 不支持，且**没有参数让你改 method**。绕过方案是装饰器模式包一层子类：

```python
class DeepSeekForStructured(ChatOpenAI):
    def with_structured_output(self, schema, **kwargs):
        kwargs.setdefault("method", "function_calling")   # 强制改默认方法
        return super().with_structured_output(schema, **kwargs)

selector = DeepSeekForStructured(..., extra_body={"thinking": {"type": "disabled"}})
agent = create_agent(model=主模型, tools=..., middleware=[LLMToolSelectorMiddleware(model=selector, max_tools=2)])
```

实测：直接跑报 400，换成包装类后成功，实际只从筛完的 2 个工具里选出了 `logistics_track`。

### Agent 里判断击中哪个能力域：别把历史算进去

`agent.invoke()` 返回的 `messages` 是**全量历史**，不是本轮增量。要统计本轮，必须自己切片：

```python
seen = 0
for q in dialog:
    r = agent.invoke({...}, config=cfg)
    new = r["messages"][seen:]      # ← 只取本轮新增
    seen = len(r["messages"])
```

实测前没切片时，第二轮会打出 `['售后', '订单']`（把上一轮也算进去了），切片后正确为 `['订单']`。

### 其他实测结论

- `create_agent` + DeepSeek：✅ 完全正常，多工具**一次性并行**发起（单次返回 2 个 tool_call）
- `ToolRetryMiddleware`：✅ 生效。造了个「前 2 次必抛异常」的工具，最终第 3 次成功拿到结果
- 多轮记忆：同一 `thread_id` 能记住「我叫张三 / 订单 SO001」；换 `thread_id` 同样的提问答「看不到」

---

## 五点十二、Skill 开放标准（文件 7，Skill 这件事的标准答案）

### 先更正：我前面的结论是错的

文件 5 里我写过「langchain 1.4.7 没有 Skill 类 → Skill 是我们自己组织工具的方式」。
**这个结论错了**，错在我只搜了 langchain 包里的**类名**，没去查生态有没有**开放标准**。

（顺带第二个错：文件 5 后来把「工具分组字典」也叫 Skill，名字已改成**能力域**，
文件也改名为 `5.工具分组与路由判断.py`。见「五点十一」开头的对照表。）

真实情况：

- **Agent Skills 是开放标准**，Anthropic 发起，**2025-12-18 发布为 open standard**（跨产品可移植）
- 规范站：<https://skill.md>
- 已被 LangChain(Deep Agents)、Claude Code、Codex 等几十家产品支持
- 本机 `~/.workbuddy/skills/` 下就是这套标准的实例（`java_init/SKILL.md` 等）
- LangChain 官方实现：**`deepagents` 包**（Python>=3.11）

所以：**Skill 不是一个类，但它是一套标准格式**，不是各人自创的组织方式。
文件 5 的价值在于「没有标准时怎么自己搭」，文件 7 才是标准做法。

### 标准格式

```
my-skill/
├── SKILL.md        # 必需：YAML frontmatter + Markdown 正文
├── scripts/        # 可选：可执行代码
├── references/     # 可选：文档
└── assets/         # 可选：模板/素材
```

`SKILL.md` 必须以 `---` 开头的 YAML frontmatter 开始，**只有两个必需字段**：

| 字段 | 限制 | 说明 |
|---|---|---|
| `name` | ≤64 字符 | 小写字母/数字/连字符 |
| `description` | ≤1024 字符 | **必须同时写清「做什么」和「什么时候用」**——这是模型判断是否加载的**唯一依据** |

### 核心机制：渐进式披露

| 级别 | 何时加载 | 内容 | 上下文代价 |
|---|---|---|---|
| L1 元数据 | 启动时 | 只有 name + description 进系统提示 | ~100 tokens/skill |
| L2 指令 | 命中才加载 | 用 `read_file` 读完整 SKILL.md | <5k tokens |
| L3 资源 | 需要才加载 | scripts 执行 / references 读 | **脚本 0 token**（源码不进上下文，只有 stdout 回来） |

本文件实测：3 个 skill，L1 元数据合计 302 字符，L2 正文合计 1637 字符
→ 启动时只花 302 的开销，1637 的内容**一个字都不进上下文**。

### 「判断击中哪个 Skill」——标准答案（和能力域的判断不是一回事）

| | 文件 5（自建方案） | 文件 7（标准方案） |
|---|---|---|
| 做法 | 查自己维护的 `TOOL_TO_DOMAIN` 反查表 | **看 agent 读了哪个 SKILL.md** |
| 实现 | 字典写死 | 扫 `tool_calls` 里的 `read_file`，从路径提取 skill 名 |

标准方案里更本质：命中某个 skill 的标志就是**它去读了那个 SKILL.md**。

实测三个问题全部正确命中：

| 问题 | read_file | 击中 |
|---|---|---|
| 我的订单 SO001 到哪了？ | `/skills/order-service/SKILL.md` | order-service |
| 商品 P100 还有多少库存？ | `/skills/product-service/SKILL.md` | product-service |
| 买了三天能退货吗？ | `/skills/after-sale/SKILL.md` | after-sale |

### deepagents 用法

```python
from deepagents import create_deep_agent
from deepagents.backends import FilesystemBackend
from deepagents.middleware import SkillsMiddleware

backend = FilesystemBackend(root_dir=HERE, virtual_mode=True)
mw = SkillsMiddleware(backend=backend, sources=["skills"], tools=ALL_TOOLS)  # ← 工具传这里
agent = create_deep_agent(model=llm, tools=[], middleware=[mw], backend=backend)
```

简化写法（`create_deep_agent(skills=["skills"])` 会自动建中间件），
但**要绑定工具就必须显式构造 SkillsMiddleware**。

### `@skill` 点名 = pinned_skills

```python
agent.invoke({
    "messages": [{"role": "user", "content": "帮我查 SO001"}],
    "pinned_skills": ["order-service"],   # 首轮就塞进上下文，省一轮 read_file
}, config)
```

实测：注入 1 条 pinned 消息，内容以 `<skill name="order-service" path="...">` 开头。

**⚠️ 语法由应用自己解析**（`@xxx` / `/xxx`），deepagents 不负责识别消息内容。
你在各种 AI 客户端看到的 `@某个skill` 就是这一层在干的事。

---

## 六、几个已实测的坑

| 坑 | 现象 | 处理 |
|---|---|---|
| `trim_messages` 裁掉系统提示词 | 人设丢失、模型变傻 | 显式 `include_system=True` |
| `StrOutputParser` 返回不是 `str` | 类型是 `TextAccessor` | 它是 `str` 子类，直接用即可 |
| 少传模板变量 | `KeyError` | 这是好事，提前暴露问题 |
| `tool_call_id` 对不上 | 模型 API 报错 | 必须和 `tool_calls[].id` 一致 |
| **裸 dict 当 RunnableParallel 用** | `AttributeError: 'dict' object has no attribute 'invoke'` | dict 只有参与 `\|` 组合才自动转换；单独用要 `RunnableParallel(...)` 或 `coerce_to_runnable(dict)` |
| `.env` 用固定 `parents[N]` 定位 | 目录一调整就 `Missing credentials` | 改成向上逐层查找（见各文件 `_find_env()`） |
| **回调方法名写错** | 完全没反应，不报错不警告 | 默认全是空实现，写错名就是静默失败。尤其注意没有 `on_chat_model_end`，只有 `on_llm_end` |
| **用 `invoke()` 等流式回调** | `on_llm_new_token` 一次都不触发 | 必须用 `stream()` / `astream()` |
| **嵌套链路靠 `name` 区分** | 全是 `RunnableSequence`，分不清 | `.with_config(run_name=...)` 起名，或判断 `parent_ids` 是否为空 |
| **用了 RWMH 还手动写历史** | 消息翻倍，模型看到两遍同样的问题 | RWMH 会自动写入，别自己再 add |
| **忘记传 `session_id`** | `ValueError: Missing keys ['session_id']` | config 里必传 `{"configurable": {"session_id": ...}}` |
| **`trim_messages` 不写 `include_system`** | 系统提示词被裁掉，人设丢失且不报错 | 显式写 `include_system=True` |
| **`allow_partial=True` 没效果** | 裁剪结果和不写一样 | 必须同时传 `text_splitter` |
| **实体记忆用自由 `Dict` key** | 更新不生效（广州/深圳变两个实体） | 改成固定 pydantic 字段 |
| **prompt 带 `MessagesPlaceholder` 却不传 history** | `KeyError: missing variables {'history'}` | 不带历史的链要用独立的、无占位符的 prompt |
| **`bind` 参数名写错** | bind 时不报错，调用时才 400 | bind 不做校验，对着文档写参数名 |
| **指望 `max_tokens` 限长** | DeepSeek 上完全不生效 | 在提示词里写「不超过 N 字」 |
| **`configurable_fields` 字段名写错** | 立刻 `ValueError`（会列出可用字段） | 看报错信息里的 available keys |
| **给 `RunnableLambda` 用 `configurable_alternatives`** | `AttributeError`，没这个方法 | 只在 pydantic 系 Runnable 上有；改用 `RunnableLambda` + config 参数 |
| **`alternatives` 的 key 对不上** | `ValueError: Unknown alternative` | 传注册时的 key，不是模型名 |
| **`with_retry` 不限制异常类型** | 参数错误也重试 3 次，白花钱 | 配 `retry_if_exception_type` |
| **组合时顺序搞反** | 重试时把历史重复写一遍 | 重试/回退/监听包内层，历史包最外层 |
| **`with_structured_output` 不写 method** | DeepSeek 上 400 `response_format type is unavailable` | 必须 `method="function_calling"` + 关思考 |
| **开思考时用强制 `tool_choice`** | 400 `Thinking mode does not support this tool_choice` | 强制指定必须 `extra_body={"thinking": {"type": "disabled"}}` |
| **指望 `bind_tools().astream_events()` 出工具事件** | 只有 `on_chat_model_*`，等不到 `on_tool_start` | 把执行工具接进链，并把 `config` 透传给 `tool.ainvoke` |
| **直接上 `LLMToolSelectorMiddleware`** | DeepSeek 400（内部用 json_schema） | 传自定义 `ChatOpenAI` 子类强制 function_calling |
| **统计 Agent 本轮击中 Skill** | 把历史也算进去，数字越滚越大 | 记住上一轮长度，用 `messages[seen:]` 切片 |
| **工具描述写得太笼统** | 模型乱调 / 不调 | 描述写四要素：干什么、何时用、何时别用、参数怎么给 |
| **`include_tools` 写成 YAML 列表** | 告警 `should be a space-separated string of tool names`，绑定被忽略 | 必须是**空格分隔字符串**：`include_tools: a b c` |
| **绑定的工具传给 agent 而不是中间件** | 工具不跟着 skill 出现，模型说「工具没接进来」 | 传给 `SkillsMiddleware(tools=...)`，agent 那边 `tools=[]` |
| **手写正则解析 SKILL.md frontmatter** | `description: >` 折叠标记被当内容、注释被吞进值 | frontmatter 是标准 YAML，直接用 `yaml.safe_load` |
| **`skills=` 指向 skill 目录本身** | 一个 skill 都加载不出来 | 要指向**包含** skill 目录的父目录；路径用 forward slash |
| **把 `LangChainDeprecationWarning` 当报错** | 满屏红字以为脚本崩了，其实退出码是 0 | 那是**废弃预告**（`since x, removal y`），不是错误。要么按提示迁移到新 API，要么用 `warnings.filterwarnings("ignore", LangChainDeprecationWarning)` 收掉 |
| **`SqliteSaver.from_conn_string()` 直接赋值** | `TypeError: ...Received _GeneratorContextManager` | 3.x 起它是 `@contextmanager`。用 `with ... as cp`，或 `SqliteSaver(sqlite3.connect(...))` |
| **sqlite 连接不加 `check_same_thread=False`** | 多线程服务下报错 | 服务里必须加这个参数 |
| **生产用 `InMemorySaver`** | 服务重启，用户历史全没 | 换 `langgraph-checkpoint-sqlite`（单机）或 postgres 版（分布式） |
| **配了 checkpointer 却不传 `thread_id`** | `ValueError: Checkpointer requires one or more of the following 'configurable' keys: thread_id, checkpoint_ns, checkpoint_id` | 每次 `invoke` / `stream` 都带 `config={"configurable": {"thread_id": ...}}`（比老 API 静默不记历史友好） |
| **`request.messages = xxx` 直接赋值** | `DeprecationWarning` | 用 `request.override(messages=...)` |
| **用 `before_model` 做上下文裁剪** | 存储被真的改小，历史丢失 | 它返回的是 state 更新会写回 checkpointer。裁剪要用 `wrap_model_call`（只改本次发给模型的消息） |
| **`from langgraph.prebuilt import create_react_agent`** | `LangGraphDeprecatedSinceV10` 告警 | 改用 `from langchain.agents import create_agent` |
| **工具参数注解成 `runtime: Runtime`** | `PydanticInvalidForJsonSchema: Cannot generate a JsonSchema for ... IsInstanceSchema(BaseStore)` | 工具要用子类 `ToolRuntime`（带 `_DirectlyInjectedToolArg` 标记，会被摘出 Schema）；`Runtime` 只给图节点/中间件用 |
| **Store 的 namespace 不带 user_id** | A 用户读到 B 用户的事实（越权） | 用户相关的必须写成 `("facts", user_id)` |
| **`get_state` 拿不到东西** | 忘了传带 `thread_id` 的 config | `agent.get_state({"configurable": {"thread_id": ...}})`；`get_state_history` 可「时间旅行」回滚 |

### 裁剪怎么挂到最新 API 上（memory/4 第 6 节）

老写法 `RunnableWithMessageHistory + RunnablePassthrough.assign` 已废弃，现在是：

```python
class TrimMessagesMiddleware(AgentMiddleware):
    def wrap_model_call(self, request, handler):
        trimmed = trim_messages(request.messages, max_tokens=60,
                                token_counter="approximate", strategy="last",
                                include_system=True, end_on=HumanMessage)
        return handler(request.override(messages=trimmed))   # ← override，不是直接赋值

agent = create_agent(model=llm, checkpointer=InMemorySaver(),
                     middleware=[TrimMessagesMiddleware(60)])
```

实测 5 轮：**存储涨到 10 条不动，送进模型稳定 5 条** —— 裁剪只影响送给模型的内容。

⚠️ 别用 `before_model` 做这件事：它返回的是 **state 更新**，会写回 checkpointer 把存储真的改小，
那就不是裁剪而是删历史了。
（Java 视角：`before_model` ≈ 改数据库；`wrap_model_call` ≈ 只改这次请求的 body。）

---

## 七、老教材清单 vs langchain-core 1.7.0 实测对照

在当前 1.7.0 上逐个验证过（`python -c "import langchain_core.prompts; ..."`）：

| 教材条目 | 现状 | 说明 |
|---|---|---|
| `PromptTemplate` | ✅ 还在 | 定位变成"纯文本模板"，场景少了 |
| `ChatPromptTemplate` | ✅ 还在 | 依然是主力 |
| `MessagePlaceholder` | ✅ 还在 | 教材类名少了个 s，实际是 **`MessagesPlaceholder`** |
| `SystemMessagePromptTemplate` | ✅ 还在 | 但日常不用手写，见下方说明 |
| `HumanMessagePromptTemplate` | ✅ 还在 | 同上 |
| `AIMessagePromptTemplate` | ✅ 还在 | 同上 |
| `PipelinePromptTemplate` | ❌ **已移除** | 被 LCEL 管道 `prompt \| model` 取代 |

方法清单 `partial / format / invoke / to_string / to_messages` **5 个全部还在**。
注意 `invoke()` 的返回值是个包装对象：`ChatPromptTemplate` 返回 `ChatPromptValue`、
`PromptTemplate` 返回 `StringPromptValue`，用 `.to_messages()` / `.to_string()` 解包。

**关于那三个 XxxMessagePromptTemplate**：它们没有消失，而是"下沉"成了底层类。
你写的元组 `("system", "你是{role}")` 会被 `from_messages` 内部转换成
`SystemMessagePromptTemplate.from_template("你是{role}")`——实测两种写法生成的类和渲染结果完全一致。
所以现代写法直接用元组，可读性更好；显式类只在需要精细控制时才用。

---

## 八、回归结果（Python 3.11.9）

升级到 3.11.9 后对 `aiLearn/` 下全部 demo 做过一轮完整回归：**36 个文件，0 失败**。
（首轮 34 个，耗时 7m57s；每个脚本单独子进程跑，超时阈值 900s）

| 分组 | 数量 | 结果 |
|---|---|---|
| prompts | 3 | ✅ 全通过（不需要 API key，各约 1s） |
| model | 3 | ✅ 全通过（16~32s，批处理最慢） |
| outputParser | 3 | ✅ 全通过 |
| runnable | 3 | ✅ 全通过 |
| callable | 3 | ✅ 全通过 |
| memory | 7 | ✅ 全通过（含 LangGraph 方案） |
| runnableModule | 6 | ✅ 全通过 |
| tool | 7 | ✅ 全通过（含 deepagents 标准 Skill） |

结论：**Python 3.11.9 + langchain-core 1.7.0 下全部兼容**，无需为升级改代码。

复跑方式：

```bash
yzy/Scripts/python.exe tmp/regress.py     # 结果写入 tmp/regress_result.md / .json
```

各脚本耗时分布：不需要调模型的（prompts / tool-1 / memory-1,2）约 1s；
单次模型调用的 8~20s；多轮的（批处理、重试回退、Agent 实战）30s 上下。
