# 交易中心幂等校验 + 状态机服务 整体架构设计

> 版本：v1.3（2026-09-15）｜ 项目：springCloudTemplate ｜ 集成测试：16/16 PASS
>
> 变更记录：v1.1 消息可靠性增强（消费去重/死信/发送状态）→ v1.2 代码走查优化 → v1.3 乱序治理（防线A+B）

## 1. 需求背景

交易中心场景下的幂等校验设计，核心诉求：

1. **请求幂等**：`SET 幂等key 1 EX 259200 NX`，false 直接返回【重复请求】终止；true 继续执行业务；
2. **DB 兜底**：事务插入报文流水表（幂等 key 唯一索引），`DuplicateKeyException` = 并发穿透判重；其他异常回滚且**不删除 Redis key**，等待 3 天自动过期；
3. **状态机**：独立新服务，消费顺序消息驱动订单状态流转，设计上考虑消息顺序性；
4. **消息防重复**：覆盖 RocketMQ at-least-once 重投、ORDERLY 重试阻塞、生产端发送失败丢失等问题；
5. **乱序治理**：并发请求/网络延迟导致"入队顺序 ≠ 业务真实顺序"时，事件不丢、状态不坏。

## 2. 总体架构

```
┌──────────┐   POST /api/trade/submit    ┌──────────────────────────────────┐
│  客户端   │ ──────────────────────────▶ │  yzy-demo : 8088（交易中心/生产者）│
└──────────┘                             │  · TradeController（统一响应）    │
                                         │  · IdempotentService    → L1     │
                                         │  · checkStateConflict   → 防线A  │
                                         │  · TradeServiceImpl(Tx) → L2     │
                                         │  · sendOrderlyMessage（状态回写） │
                                         └──────┬───────┬───────┬───────────┘
                                                │       │       │
                          ┌─────────────────────┘       │       └──────────────────┐
                          ▼                             ▼                          ▼
                  ┌──────────────┐            ┌───────────────┐          ┌──────────────────┐
                  │ MySQL YZY_DB │            │ Redis         │          │ RocketMQ         │
                  │ trade_       │            │ idem:trade:*  │          │ yzy-trade-topic  │
                  │ message_flow │            │ (SET NX EX    │          │ (顺序消息,        │
                  │ (流水+发送状态)│           │  259200s)     │          │  hashKey=bizNo)  │
                  └──────────────┘            └───────────────┘          └────────┬─────────┘
                                                                                  │ ORDERLY 消费
                                                                                  ▼
                                                                  ┌──────────────────────────────┐
                                                                  │ yzy-state-machine : 8090     │
                                                                  │ · TradeOrderlyListener(死信) │
                                                                  │ · 消费去重        → L3        │
                                                                  │ · 三类流转判定    → 防线B     │
                                                                  │ · pending 暂存回放 + CAS → L4 │
                                                                  │ GET  /api/state/order/{bizNo}│
                                                                  │ POST /api/state/debug/apply  │
                                                                  └──────────────┬───────────────┘
                                                                                 ▼
                                                        MySQL YZY_DB（trade_order_state /
                                                        mq_consume_record / mq_pending_event /
                                                        mq_dead_message）
```

**技术栈**：Spring Boot 2.6.15 / Spring Cloud 2021.0.9（Nacos 注册+配置）/ MyBatis-Plus 3.5.2 / Redis(Jedis) / RocketMQ（rocketmq-spring-boot-starter 2.2.2，nameserver 127.0.0.1:9876）。

> 依赖说明：需求原定 `bes-cloudmq-h-clernt-all`（宝兰德私有客户端）本地仓库不存在，经确认改用 Apache 官方 starter。生产端仅 `TradeServiceImpl.sendOrderlyMessage` 一处触碰 RocketMQ API，后续替换 bes 客户端时只需改此方法。

## 3. 防线全景（六层）

| 层 | 位置 | 机制 | 拦截什么 |
|----|------|------|----------|
| L1 Redis SET NX | 生产端 | `SET idem:trade:{key} 1 EX 259200 NX` | 重复请求（3 天窗口） |
| L2 流水唯一索引 | 生产端 | `trade_message_flow.uk_idem_key`，事务内 insert | Redis 失效后的并发穿透 |
| **A 入口预检** | 生产端 | 查流水表推导"在途状态"，事件不匹配 → 409 | **乱序操作（不进 MQ）** |
| L3 消费去重表 | 消费端 | `mq_consume_record.uk_flow_id`，与流转**同事务** | MQ at-least-once 重投 |
| **B 暂存回放** | 消费端 | 超前事件暂存 `mq_pending_event`，状态追上后回放 | **入队序 ≠ 业务序（事件不丢）** |
| L4 状态 CAS | 消费端 | `trade_order_state` 条件更新 + `uk_biz_no` | 一切乱序/重复对状态的破坏（正确性最后兜底） |

### 3.1 主流程（yzy-demo `TradeServiceImpl.submit`）

```
① 参数校验（@NotBlank + @Valid，缺失 → 400 fail-fast）
② Redis SET NX EX 259200 ──false──▶ 返回【重复请求】(500) 终止
③ 入口预检（防线A）：查流水表最新已受理事件推导"在途状态"
   └─ 事件与在途状态不匹配 ──▶ 返回 409【当前状态不允许该操作】，不落流水不发消息
④ 事务(TransactionTemplate)插入 trade_message_flow（send_status=SENDING）
   ├─ DuplicateKeyException ──▶ 并发穿透，返回【重复请求】
   └─ 其他异常 ──▶ 事务回滚；【不删 Redis key】，等 3 天过期   ← 需求 2.3
⑤ 事务提交后 syncSendOrderly(topic, msg, hashKey=bizNo)
   ├─ 成功 → 回写 send_status=SENT
   └─ 重试 2 次仍失败 → 回写 SEND_FAILED + ERROR 日志（等对账补偿）
```

**关键设计决策**：

- **预检数据源是流水表而非状态表**：状态表是"消费后视角"，有消费延迟（秒~分钟级），
  连续快速提交同一单号的多个事件（上一事件尚未消费）会被误拒；流水表是"受理视角"，
  落库即生效，在途状态 = 最新已受理事件的 to 状态，天然单调、永不落后于受理进度；
- **异常不删 key（需求 2.3）**：业务失败后重试窗口内，同 idemKey 请求一律判重拒绝。代价是"真需要重试的业务"被挡住 3 天，收益是异常场景下重复请求无法反复冲击下游——交易中心场景宁可保守；
- **Redis 不可用时 fail-closed**：`setIfAbsent` 抛异常 → 请求失败（不降级放行）。幂等是交易正确性组件，不能因组件故障退化为"无幂等"；
- **发送状态回写在事务外**：仅影响对账效率，不影响正确性（消费端有 L3/L4 兜底）；回写失败只告警不抛出。

### 3.2 消费流程（yzy-state-machine `TradeOrderlyListener` + `apply`）

```
① MessageExt 反序列化（失败=毒消息 → 落死信表 + ACK，不抛异常防重投循环）
② MDC 回填 traceId（全链路日志连续）
③ apply()【单事务】：
   ├─ 必填字段防御校验（flowId/bizNo/event 缺失 → error 日志 + ACK 丢弃）
   ├─ 插入 mq_consume_record ──DuplicateKey──▶ 重复消息，info 日志 + ACK 跳过
   ├─ 懒创建状态记录（uk_biz_no 并发冲突 → 回读）
   └─ 三类流转判定（防线B）：
      ├─ 正常（from == current）        → CAS 流转 + 回放 pending
      ├─ 超前（from.order > current）   → 暂存 mq_pending_event + ACK，状态追上后回放
      └─ 过期（from.order < current）   → warn 日志 + ACK 丢弃（历史已发生，典型于重放）
```

**事务边界要点**：消费去重登记、暂存、状态流转、回放全部在**同一事务**内提交/回滚——
处理失败时登记一并消失，消息重试时不会被误判为重复；这是"去重表方案"正确性的关键。

## 4. 顺序性设计与乱序治理

### 4.1 顺序性保证（正常运行时）

同一 bizNo 的消息严格有序，跨 bizNo 并行：

| 环节 | 机制 |
|------|------|
| 生产端 | `syncSendOrderly(topic, msg, hashKey=bizNo)`：`Math.abs(bizNo.hashCode()) % 队列数` 选队列（HashMap 分桶语义，队列数固定少量、单号数无限），同单号恒定同队列 |
| Broker | 同一 MessageQueue 内消息天然有序（FIFO 日志） |
| 消费端 | `consumeMode = ConsumeMode.ORDERLY`：队列内单线程顺序消费（每队列同时只被一个消费线程持有） |
| DB 兜底 | CAS 条件流转，极端乱序也无法破坏状态 |

**消息 KEY**：`KEYS = idemKey`，broker 端可按 key 检索消息轨迹，与流水表对账。

### 4.2 关键认知：MQ 保序 ≠ 保业务序

ORDERLY 只保证「按**入队顺序**消费」。并发请求（同单号两个操作打到不同线程/实例）、
网络延迟、发送重试都会导致**入队顺序本身与业务真实顺序不符**（如真实序 PAY→FINISH，
FINISH 先入队）。此时消费端单独无解：

| 消费端策略 | 结局 |
|-----------|------|
| 拒绝 + ACK（丢事件） | FINISH 被丢弃 → 订单卡在 PAID，事件永久丢失 |
| 抛异常重试 | FINISH 在队列头部原地重试，堵死后面的 PAY → **死锁** |

### 4.3 乱序治理：防线A + 防线B 协作

```
用户操作 ──▶ 防线A 入口预检 ──▶ MQ ──▶ 防线B 消费端
              │                        │
              │ 查流水表最新已受理事件    │ 超前事件：暂存 mq_pending_event + ACK
              │ 推导"在途状态"，          │ 过期事件：丢弃告警
              │ 事件不匹配 → 409 拒绝，   │ 正常流转后回放 pending，应用即删除
              │ 乱序请求不进 MQ          │ （防线A漏掉的竞态窗口由此兜底）
```

- **防线A 拦截绝大多数乱序**（如订单还在 CREATED 就提交 FINISH），根本不进 MQ；
- **防线B 兜住"A 预检通过到消费前"的竞态窗口**：预检时合法、消费时状态已被并发推进的超前事件，
  暂存不丢，状态追上后由回放补齐；
- **回放算法**：每次正常流转后按 flow_id 升序遍历该单号 pending，前置状态匹配即 CAS 应用并删除，
  循环直到无进展（剩余事件仍超前，等后续事件推进）；回放与触发流转同事务；
- **巡检口径**：单号 pending 挂起超过 N 分钟 → 告警（前置事件疑似丢失，需人工/补偿介入）。
  pending 不做自动清理——事件不丢是硬承诺。

## 5. 消息可靠性：异常 → 处理约定矩阵

| 场景 | 处理方式 | 重试 |
|------|----------|------|
| 重复消息（去重表命中） | info 日志 + ACK 跳过 | 否 |
| 乱序操作（入口预检命中，防线A） | 409 返回调用方，不进 MQ | 否（调用方按需修正后重新提交） |
| 超前事件（消费端判定，防线B） | 暂存 pending + ACK，状态追上后回放 | 否（回放机制补齐） |
| 过期事件 / 未知事件 / 畸形消息 | warn/error 日志 + ACK 丢弃 | 否 |
| 毒消息（JSON 解析失败） | 落死信表 + ACK（**不能抛异常**，否则重投循环） | 否 |
| 基础设施异常（重试 < 3） | 抛出 → ORDERLY 原地重试（阻塞本队列，不乱序） | 是 |
| 基础设施异常（重试 ≥ 3） | 落死信表 + ACK，解除队列阻塞 | 否 |
| 生产端发送失败（重试 2 次耗尽） | 流水标记 SEND_FAILED，等对账补偿 | 否（人工/任务） |

**三个容易踩的坑（已在代码中处理并注释）**：

1. rocketmq-spring 对自定义类型走消息转换器会丢失原生元数据，死信判定需要 `reconsumeTimes`，因此监听器必须用 `RocketMQListener<MessageExt>` 自行反序列化；
2. 任何从 `onMessage` 抛出的异常都会被判定消费失败触发重投——毒消息路径必须 ACK 返回，否则形成"重投 → 再失败 → 死信表重复插入"循环；
3. 入口预检若读状态表（消费后视角）而非流水表（受理视角），消费延迟窗口内连续提交同单号多事件会被误拒。

## 6. 状态机模型

```
INIT ──TRADE_CREATE──▶ CREATED ──TRADE_PAY──▶ PAID ──TRADE_FINISH──▶ FINISHED
(0)                    (1)                    (2)                    (3)
```

- 规则集中在 common-module-v1 的 `TradeEventEnum`（from → to 映射）+ `TradeStateEnum`
  （含链路序号 order，供超前/过期判定）——入口预检与状态机**共用同一规则源**，不会漂移；
  新增事件只改枚举；
- 状态表 `trade_order_state`：`uk_biz_no` 唯一 + `version` 流转计数 + `pre_state` 上一状态；
- 日志语义分层：重复消息 info / 过期事件 warn / 超前暂存 info / 回放成功 info / CAS 冲突 warn，
  告警规则可按级别直接配置。

## 7. 接口清单

| 路径 | Method | 服务 | 说明 |
|------|--------|------|------|
| `/api/trade/submit` | POST | yzy-demo:8088 | 报文提交（body: bizNo/event/idemKey/messageBody） |
| `/api/state/order/{bizNo}` | GET | yzy-state-machine:8090 | 查询状态机当前状态 |
| `/api/state/debug/apply` | POST | yzy-state-machine:8090 | 调试：绕过 MQ 直调状态机（乱序模拟/运维重放，生产需网关屏蔽） |
| `/doc.html` | GET | yzy-demo:8088 | Knife4j 接口文档 |

响应统一 `Result{code, message, data, traceId}`；全局异常处理器保证所有异常路径响应格式一致
（400 参数校验 / 409 状态冲突 / 500 系统异常）。

## 8. 已知边界与后续优化

| 项 | 现状 | 建议 |
|----|------|------|
| 落库与发消息的原子性 | "本地事务 + afterCommit 发送 + send_status 对账"，进程在提交后崩溃仍可能丢消息 | 升级 RocketMQ 事务消息（half message + 本地事务回查） |
| SEND_FAILED 补偿 | 状态已落库，无自动重发 | 补偿任务扫描 SEND_FAILED，**按 flowId 顺序重发同一 bizNo**（乱序重发会破坏顺序性） |
| pending 巡检 | 超前事件暂存后无自动告警 | 巡检任务：单号 pending 挂起超 N 分钟 → 告警（前置事件疑似丢失） |
| 预检的并发受理竞态 | 预检通过到消费前两个并发请求可能同时放行 | 已由防线B暂存回放 + 流水 uk 兜底，正确性无损；如需更强可加 bizNo 级分布式锁（代价吞吐） |
| topic 消费延迟 | 本地 WSL 环境观察：topic 自动创建后消费者 rebalance 约 90s，首条消息消费延迟 | 预创建 topic；测试轮询窗口 ≥ 2min |
| 幂等 key 3 天窗口 | 期间业务失败不可重试（by design，需求 2.3） | 如需"失败可重试"，改为"成功才设 key"或缩短 TTL——但会削弱防重能力，需权衡 |
| 顺序消费吞吐 | ORDERLY 单线程/队列 | 按 bizNo 分片已天然并行；如需更高吞吐增大队列数 |
| debug 接口暴露 | /api/state/debug/apply 可直接驱动状态机 | 生产环境网关鉴权屏蔽外部访问 |

## 9. 本地运行与测试

```bash
# 构建（common-module-v1 含规则枚举，改动后需全量）
E:/apache-maven-3.6.3/bin/mvn.cmd clean install -DskipTests

# 建表（首次全量 / 已有库按版本递增）
python sql/run_ddl.py          # 或手工执行 sql/trade_idempotent.sql
                                # 增量：sql/increment_v2.sql → sql/increment_v3.sql

# 启动（端口必须命令行传入）
java -jar yzy-state-machine/target/yzy-state-machine-1.0-SNAPSHOT.jar --server.port=8090
java -jar yzy-demo/target/yzy-demo-1.0-SNAPSHOT.jar --server.port=8088

# 集成测试（13 大场景 16 项断言：参数校验/幂等/穿透/回滚/顺序流转/乱序治理/对账）
python sql/integration_test.py
```

依赖基础设施：MySQL(3306/YZY_DB)、Redis(6379)、Nacos(8848)、RocketMQ(9876)。

## 10. 模块与代码索引

| 文件 | 职责 |
|------|------|
| `yzy-demo/.../controller/TradeController.java` | 交易提交入口（三态响应映射：受理/重复/409） |
| `yzy-demo/.../dto/TradeSubmitDTO.java` | 提交请求 + 参数校验注解 |
| `yzy-demo/.../service/IdempotentService.java` | L1 Redis 幂等（SET NX EX） |
| `yzy-demo/.../service/SubmitResult.java` | 受理结果三态枚举 |
| `yzy-demo/.../service/impl/TradeServiceImpl.java` | 主流程：L1 + 防线A预检 + L2 事务 + 顺序消息 + 发送状态 |
| `yzy-demo/.../mapper/TradeMessageFlowMapper.java` | 流水 Mapper + 最新事件查询（预检数据源） |
| `yzy-demo/.../config/GlobalExceptionHandler.java` | 统一异常响应（400/500） |
| `common-module-v1/.../enums/TradeEventEnum.java` | 流转规则表（两端共用，单一事实来源） |
| `common-module-v1/.../enums/TradeStateEnum.java` | 状态枚举（含 order 序号，超前/过期判定依据） |
| `yzy-state-machine/.../listener/TradeOrderlyListener.java` | ORDERLY 消费 + 死信兜底 |
| `yzy-state-machine/.../service/impl/TradeStateMachineServiceImpl.java` | L3 去重 + 防线B 三类判定 + L4 CAS + pending 回放 |
| `yzy-state-machine/.../controller/TradeStateDebugController.java` | debug 直调状态机（乱序模拟/运维重放） |
| `sql/trade_idempotent.sql` | 全量建表脚本（5 张表） |
| `sql/increment_v2.sql` / `sql/increment_v3.sql` | 增量 DDL（消息可靠性 / 乱序治理） |
| `sql/integration_test.py` | 集成测试脚本（13 场景 16 断言） |
