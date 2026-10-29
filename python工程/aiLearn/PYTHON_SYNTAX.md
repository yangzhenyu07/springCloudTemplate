# Python 语法速查（写给有 Java 背景的人）

看 LangChain 代码时会被一些 Python 写法卡住，这里集中解释。
每条都给 Java 对照——你熟 Java，对照着看会快很多。

> **一句话总览**：Python 是「动态类型 + 鸭子类型 + 一等函数」的语言。
> 你在 Java 里用**接口 + 实现类**表达的东西，Python 里往往直接用一个函数（lambda）就完了；
> 你在 Java 里靠**编译器**兜住的东西，Python 里全靠运行时和约定。

---

## 0. 先记住这 5 个「Java 里没有」的差异

这是最容易被绕进去的地方，先打个预防针：

| 差异 | Java | Python |
|---|---|---|
| **运算符重载** | 只有 `String +`，其余不支持 | **任何类都能重载**。`\|` 被 LangChain 重载成「管道」，LCEL 全靠它 |
| **真值判断** | 必须写 `x != null && !x.isEmpty()` | **`if not x:` 一把梭**，None / 空串 / 空列表 / 0 全是 False |
| **类型检查** | 编译期强校验 | 注解只是注释，**运行时不校验**，写错不报错 |
| **函数是一等公民** | 得套 `Function<T,R>` 接口 | 函数本身就是对象，能当参数传、能放字典里 |
| **集合类型** | `List/Map/Set` 是接口，实现要选 | `list/dict/set` 直接是内置类型，`dict` ≈ `LinkedHashMap`（保序） |

---

## 1. 闭包 / 工厂函数（**最重要的一个**）

你举的例子：

```python
def fake_vector_search(source: str):      # 外层：接收配置
    def search(x):                        # 内层：真正的逻辑
        q = x["query"]
        return f"[{source}命中] 关于「{q}」的资料"
    return RunnableLambda(search)         # 把内层函数「包成 Runnable」返回
```

**这是「返回函数的函数」。** 调用 `fake_vector_search("产品文档库")` **不会执行检索**，
只是造出一个检索器。真正执行发生在后面 `chain.invoke()` 时。

内层 `search` 用到了外层的 `source`，这叫**闭包**——变量被内层函数"记住"了。
所以调用三次会造出三个不同的检索器，各自记得自己的数据源名。

Java 对照（结构完全一致，只是 Java 必须有**函数式接口**这个载体）：

```java
// Java 8+：lambda 捕获的局部变量必须是 effectively final（事实不可变）
static Function<Map<String, Object>, String> fakeVectorSearch(String source) {
    return x -> "[" + source + "命中] 关于「" + x.get("query") + "」的资料";
}
```

**两个关键对照：**

| 概念 | Java | Python |
|---|---|---|
| 返回函数 | 返回类型是 `Function<T,R>` / `Supplier<T>` 等**函数式接口** | 直接返回函数对象，没有类型约束 |
| 捕获外部变量 | **必须是 effectively final**（不能再赋值） | 随便，甚至能在内层改（要 `nonlocal`） |

> 顺带一提：Java 里 `source` 如果被重新赋值就编译不过；Python 里能改，但也容易踩坑
> （循环里造闭包捕获循环变量是经典 Bug）。

**为什么 LangChain 里到处是这个写法？**
因为 `RunnableParallel(a=..., b=...)` 的每个分支需要的是一个"可执行单元"，
而"可执行单元"往往需要参数化（不同的数据源、不同的名字），
所以就用一个外层函数接收参数、造出内层的执行逻辑。
**等价于 Java 里的工厂方法返回 `Function`**（比如 `Retryer.of(config)` 返回策略对象）。

---

## 2. lambda（匿名函数）

```python
lambda x: x              # 等价于 def fn(x): return x
lambda x: x["query"]     # 等价于 def fn(x): return x["query"]
lambda: 1 + 1            # 冒号前【没有参数】，零参数匿名函数
lambda d: {"a": d["b"]}  # 返回字典
```

`lambda 参数: 返回值`，**只能写一个表达式**，不能写多行语句。
要写多行就必须用 `def` 定义具名函数。

Java 对照：

| Python | Java |
|---|---|
| `lambda x: x` | `x -> x`，或直接 `Function.identity()` |
| `lambda x: x["query"]` | `x -> x.get("query")` |
| `lambda: 1 + 1` | `() -> 1 + 1`（`Supplier<Integer>`） |
| `lambda d: {"a": d["b"]}` | `d -> Map.of("a", d.get("b"))` |

⚠️ **Java 同学最容易懵的一点**：Python 的 lambda **不需要声明类型、不需要接口**。
Java 里 `x -> x` 必须挂在 `Function<T,R>` 上，Python 里它就是个裸函数对象。
LangChain 拿到后会自己包一层 `RunnableLambda` 适配成 Runnable。

**延迟执行的技巧**：`lambda: d | fn` 这种零参数 lambda 常常是用来
"把一段会报错的代码包起来，先不执行"，等后面再调用。
≈ Java 里 `() -> doSomething()` 的 `Supplier`，**调用 `get()` 时才真正执行**。

---

## 3. `**` 和 `*` 解包

```python
def f(a, b, **kwargs):   # **kwargs 收集多余的「关键字参数」成字典
    print(kwargs)        # {'c': 3}

f(a=1, b=2, c=3)

d = {"a": 1, "b": 2}
g(**d)                   # **d 把字典「拆成」关键字参数：g(a=1, b=2)
```

- `*列表`：把列表拆成**位置参数**
- `**字典`：把字典拆成**关键字参数**

Java 对照：**基本没有直接对应**，这是 Python 独有的动态特性。

| Python | Java 最接近的写法 |
|---|---|
| `*args`（收集） | `void f(T... args)` 变长参数 |
| `**kwargs`（收集） | Java 没有。最接近的是 `Map<String, Object> params`，或 Java 9+ 的 `Map.of(...)` |
| `f(*list)`（拆开） | 数组可以传给 varargs，仅此而已 |
| `f(**map)`（拆开） | **完全没有**。Java 只能靠反射 `Method.invoke(obj, args)` 或 Builder 模式 |

**最接近 Java 直觉的类比**：把一个 `Map<String, Object>` 在调用时自动展开成具名参数
（有点像 MyBatis 的 `@Param` + 反射注入，只是 Python 在语法层面就支持）。

本项目里的用法：
```python
RunnableParallel(**{f"t{i}": slow_with_tag(i) for i in range(8)})
# 等价于手写 RunnableParallel(t0=..., t1=..., ... t7=...)
```
≈ Java 里 `new RunnableParallel(Map.of("t0", ..., "t1", ...))`，只是 Python 把它写成了
「看起来像具名参数」的形式。

---

## 4. 推导式（Comprehension）

```python
{f"t{i}": slow_with_tag(i) for i in range(8)}
# 生成 {"t0": Runnable, "t1": Runnable, ..., "t7": Runnable}
```

Java 对照（Stream API，一眼就懂）：

```java
IntStream.range(0, 8).boxed()
    .collect(Collectors.toMap(i -> "t" + i, i -> slowWithTag(i)));
```

列表推导式同理：

```python
[x * 2 for x in range(5)]              # [0, 2, 4, 6, 8]
[x for x in items if x > 0]            # 带过滤条件
```

```java
IntStream.range(0, 5).map(x -> x * 2).boxed().toList();          // [0,2,4,6,8]
items.stream().filter(x -> x > 0).toList();                       // 带过滤
```

> 推导式读法：**从右往左读**——先 `for`，再 `if`，最后看左边的表达式。
> 和 SQL 的 `SELECT ... FROM ... WHERE` 顺序刚好反过来，但和 Java Stream 的
> `.filter().map()` 链条顺序一致（filter 在前、map 在后）。

---

## 5. f-string（字符串插值）

```python
name = "Redis"
f"介绍一下{name}"                    # '介绍一下Redis'
f"{cost:.2f}s"                      # 保留 2 位小数
f"{msg!r}"                          # !r 表示用 repr()，会带引号，调试常用
f"{d['docs']}\n{d['faq']}"          # 里面可以取字典、可以换行
```

Java 对照：

| Python | Java |
|---|---|
| `f"介绍{name}"` | `String.format("介绍%s", name)`，或 Java 15+ `"介绍%s".formatted(name)` |
| `f"{cost:.2f}s"` | `String.format("%.2fs", cost)`（`%.2f` 和 C/Java 一样） |
| `f"{msg!r}"` | 类似 `Objects.toString(msg)` 的调试输出，会带类型信息/引号 |
| 多行 f-string | Java 15+ 文本块 `"""` + Java 21+ `STR."...\{name}"`（字符串模板） |

> 注意：f-string 是**运行时**求值，和 Java 编译期常量拼接（`final String` 常量折叠）不同。
> 所以 f-string 里能写任意表达式，甚至可以调方法。

---

## 6. 类型注解（只作提示，运行时不强制）

```python
def build_llm() -> ChatOpenAI:        # -> 表示返回类型
def slow(name: str, sec: float):      # 参数类型
def _find_env() -> Path:
```

Python 的类型注解**不会**在运行时校验，写错了也不会报错（除非用 mypy / pyright 检查）。
主要作用是让 IDE 能补全、让代码更好读。

**Java 同学请注意**：别把它当成 Java 的强类型。

```python
def f(x: int) -> str:
    return 123        # 声明返回 str 却返回 int —— 运行时照样跑，不报错
```

≈ Java 里的 `@Nullable` / `@NonNull` 这类**注解只是给 IDE 和静态检查工具看的**，
JVM 本身不管。Python 的注解比这个还宽松一点：完全不做运行期校验。

另外几个常见泛型注解（≈ Java 泛型）：

| Python（typing） | Java |
|---|---|
| `List[str]` | `List<String>` |
| `Dict[str, Any]` | `Map<String, Object>` |
| `Optional[str]` | `Optional<String>` / `@Nullable String` |
| `Callable[[str], int]` | `Function<String, Integer>` |
| `Union[str, int]` | 无直接对应（Java 没有联合类型） |

---

## 7. 其他零碎点

| 写法 | 含义 | Java 对照 |
|---|---|---|
| `def f(_x):` | 参数名以 `_` 开头 = 约定"这个参数我不用"，避免 lint 警告 | 类似 Java 里用 `@SuppressWarnings` 压制未使用警告 |
| `enumerate(items, 1)` | 遍历时带序号，从 1 开始 | `IntStream.range(0,n).mapToObj(i -> new Indexed(i+1, items.get(i)))`，Java 没内置 |
| `isinstance(x, str)` | 判断类型 | `x instanceof String` |
| `hasattr(obj, "invoke")` | 判断对象有没有这个方法 | 反射：`clazz.getMethod("invoke") != null` |
| `getattr(obj, "a", None)` | 取属性，没有则返回默认值 | `map.getOrDefault("a", null)` |
| `if not hits:` | 空列表/空字符串/None 都算 False | ⚠️ Java 没有真值短路，必须显式 `hits == null \|\| hits.isEmpty()` |
| `async def` / `await` | 协程 | `CompletableFuture` + `thenCompose`（语义接近，机制不同） |
| `asyncio.run(main())` | 启动事件循环（脚本入口用） | `ExecutorService` 提交任务 + `shutdown()`（≈ 主线程等线程池跑完） |
| `if __name__ == "__main__":` | 脚本入口 | `public static void main(String[] args)` |
| `with open(...) as f:` | 上下文管理器 | try-with-resources |
| `try / except X as e` | 异常处理 | `try / catch (Xxx e)` |
| `class A(B):` | 继承 | `class A extends B` |
| `@decorator` | 装饰器 | ⚠️ **不是** Java 注解。是「函数包装」≈ AOP 的环绕通知 / 装饰者模式 |

> **装饰器是 Java 同学最容易误解的一个**：Java 的 `@Override` 只是元数据（不改行为），
> Python 的 `@xxx` 会**真的把函数包一层再替换掉**，等价于：
> `fn = decorator(fn)`。≈ Spring AOP 的 `@Around` 把原方法换成了代理方法。

---

## 8. Java 工程师最容易踩的 4 个 Python 坑

**① 可变默认参数**（经典）
```python
def f(items=[]):     # ❌ 陷阱：默认列表只创建一次，跨调用共享！
    items.append(1)
    return items
```
≈ Java 里把一个 `static final List` 当默认值。正确写法是 `items=None` 再在函数里判空新建。

**② `is` vs `==`**
`is` 比较**身份**（≈ Java 的 `==` 比引用），`==` 比较**值**（≈ Java 的 `equals()`）。
判断 None 必须用 `is None`（≈ `x == null`），别写 `== None`。

**③ 缩进即作用域**
Python 没有 `{}`，**缩进就是代码块**。if / for / def 后面少一个缩进，逻辑就变了，
而且不报错。Java 同学建议 IDE 打开「显示缩进参考线」。

**④ 字典访问**
`d["k"]` key 不存在直接抛 `KeyError`（≈ Java `map.get()` 返回 null 再 NPE，但 Python 是立刻炸）。
安全写法是 `d.get("k", 默认值)`（≈ `map.getOrDefault`）。

---

## 9. 本项目统一的 .env 加载写法

每个需要 API key 的文件顶部都有：

```python
def _find_env() -> Path:
    current = Path(__file__).resolve()
    for parent in [current.parent, *current.parents]:
        candidate = parent / ".env"
        if candidate.exists():
            return candidate
    return current.parent / ".env"

_ENV_PATH = _find_env()
dotenv.load_dotenv(_ENV_PATH)
```

从文件所在目录**向上逐层查找** `.env`，而不是写死 `parents[3]`。
之前写成固定层级时，目录一挪就报 `Missing credentials`。
`*current.parents` 就是把"所有上级目录"这个序列拆开拼进列表（见第 3 节的解包）。

Java 对照（思路一样，都是「沿 ClassLoader 路径往上找配置文件」）：
```java
// 类似 Spring 的 ClassPathResource / 或向上遍历 Paths.get("").toAbsolutePath() 的父目录
for (Path p = current; p != null; p = p.getParent()) {
    if (Files.exists(p.resolve(".env"))) return p.resolve(".env");
}
```

---

## 10. LCEL 管道 `|` 到底在干什么（Java 视角）

```python
chain = prompt | llm | parser
```

Java 里**没有运算符重载**，所以只能写成：

```java
// 最接近的等价写法：函数组合
Function<Input, PromptValue>  prompt = ...;
Function<PromptValue, AIMessage> llm = ...;
Function<AIMessage, String>  parser = ...;

Function<Input, String> chain = prompt.andThen(llm).andThen(parser);
```

| Python | Java 等价物 |
|---|---|
| `a \| b` | `a.andThen(b)`（`Function` 组合） |
| `chain.invoke(x)` | `chain.apply(x)` |
| `chain.stream(x)` | 返回 `Iterator` / Stream（逐个产出） |
| `RunnableParallel({...})` | 类似 `CompletableFuture.allOf(...)` 并发跑多个分支，结果收进 Map |
| `RunnablePassthrough.assign()` | 原 Map 之上再 put 新 key（**保留原有字段**） |

> 记住一点：`|` 在 Python 里本意是**按位或**，LangChain 把它**重载**成了「前后串联」。
> 这是 Java 里做不到的事，也是 LCEL 看起来很奇怪、但很好用的原因。
