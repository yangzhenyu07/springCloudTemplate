# 交易中心幂等 + 状态机 表设计

> 版本：v1.2（2026-09-15）｜ 目标库：YZY_DB（MySQL 8.x / InnoDB / utf8mb4）
> 脚本：全量 `sql/trade_idempotent.sql`，增量 `sql/increment_v2.sql`

## 0. 表清单总览

| 表名 | 所属服务 | 防线角色 | 核心索引 |
|------|----------|----------|----------|
| `trade_message_flow` | yzy-demo（写）/ 两端对账 | L2 请求幂等 + 生产端发送状态追踪 + 防线A预检数据源 | `uk_idem_key` |
| `trade_order_state` | yzy-state-machine | L4 状态正确性（CAS 流转） | `uk_biz_no` |
| `mq_consume_record` | yzy-state-machine | L3 消息级去重（at-least-once） | `uk_flow_id` |
| `mq_dead_message` | yzy-state-machine | 死信兜底（重试耗尽/毒消息） | `idx_flow_id` |
| `mq_pending_event` | yzy-state-machine | 防线B：乱序超前事件暂存（暂存+回放） | `uk_flow_id` |

六层防线闭环：请求幂等（L1 Redis + L2 流水唯一索引）+ 乱序治理（防线A 入口预检 + 防线B 暂存回放）+ 消息幂等（L3 消费去重 + L4 状态 CAS）。

---

## 1. trade_message_flow 报文流水表

**职责**：交易中心每笔受理报文的唯一登记处。既是 L2 幂等防线（idem_key 唯一），也是消息发送状态追踪与两端对账的依据。

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | BIGINT | PK, AUTO_INCREMENT | 主键，即 flowId（消费端去重键） |
| idem_key | VARCHAR(64) | NOT NULL, **UNIQUE(uk_idem_key)** | 幂等 key（客户端每次请求唯一） |
| biz_no | VARCHAR(64) | NOT NULL, KEY(idx_biz_no) | 业务单号（顺序消息 hashKey） |
| event | VARCHAR(32) | NOT NULL | 交易事件：TRADE_CREATE/TRADE_PAY/TRADE_FINISH |
| message_body | VARCHAR(1024) | NULL | 交易报文原文（业务长度约束在 DB 层兜底） |
| trace_id | VARCHAR(64) | NULL | 全链路追踪ID |
| send_status | VARCHAR(16) | NOT NULL DEFAULT 'SENDING', KEY(idx_send_status) | SENDING/SENT/SEND_FAILED |
| create_time | DATETIME | NOT NULL DEFAULT CURRENT_TIMESTAMP | 创建时间 |

**索引设计理由**：

- `uk_idem_key`（唯一）：L2 防线本体。并发穿透场景下两个请求同时通过 Redis 校验，唯一索引保证只有一个 insert 成功，另一个拿到 `DuplicateKeyException` 判重；
- `idx_biz_no`：按单号查流水（对账高频路径），与唯一索引分开避免把业务单号误当幂等键；同时是**防线A入口预检**的数据源查询路径——`selectLatestEventByBizNo` 取最新已受理事件推导"在途状态"（受理视角，无消费延迟，见 trade_order_state 一节的对比说明）；
- `idx_send_status`：补偿任务扫描 `SEND_FAILED` 的低频路径，普通索引即可。

**send_status 状态机**：

```
落库(SENDING) ──发送成功──▶ SENT
      └─────重试2次耗尽────▶ SEND_FAILED ──补偿任务顺序重发──▶ SENT
```

---

## 2. trade_order_state 订单状态机表

**职责**：L4 防线。每个业务单号一条记录，状态流转通过**条件更新（CAS）**完成，保证消息乱序/重复时状态不被破坏。

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | BIGINT | PK, AUTO_INCREMENT | 主键 |
| biz_no | VARCHAR(64) | NOT NULL, **UNIQUE(uk_biz_no)** | 业务单号（一单一状态） |
| state | VARCHAR(32) | NOT NULL DEFAULT 'INIT' | 当前状态：INIT/CREATED/PAID/FINISHED |
| pre_state | VARCHAR(32) | NULL | 流转前状态（排查用） |
| version | INT | NOT NULL DEFAULT 0 | 流转次数（合法流转 +1，观测/对账） |
| create_time | DATETIME | NOT NULL DEFAULT CURRENT_TIMESTAMP | 创建时间 |
| update_time | DATETIME | NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE | 更新时间 |

**CAS 流转 SQL**（正确性核心）：

```sql
UPDATE trade_order_state
SET state = #{to}, pre_state = #{from}, version = version + 1
WHERE biz_no = #{bizNo} AND state = #{from}
```

影响行数 = 0 即"当前状态与预期前置状态不符"（并发修改或乱序），上层记录告警。即使去重表数据被人工误修，这张表的 CAS 仍是状态正确性的最后防线。

**为什么不用 version 做乐观锁 WHERE 条件**：`state` 本身就是业务版本——状态机流转天然由"前置状态"定义合法性，用 state 做 WHERE 比 version 更直接表达业务语义（version 保留作流转计数）。

---

## 3. mq_consume_record 消费去重表

**职责**：L3 防线。RocketMQ 是 at-least-once 投递（处理成功但 ACK 前宕机/超时会重投），本表把"重复消息"显式识别出来，与"非法流转"告警区分。

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | BIGINT | PK, AUTO_INCREMENT | 主键 |
| flow_id | BIGINT | NOT NULL, **UNIQUE(uk_flow_id)** | 报文流水ID（去重键） |
| biz_no | VARCHAR(64) | NOT NULL, KEY(idx_biz_no) | 业务单号 |
| event | VARCHAR(32) | NOT NULL | 交易事件 |
| msg_id | VARCHAR(64) | NULL | RocketMQ 原生消息ID（与 broker 日志对账） |
| consume_time | DATETIME | NOT NULL DEFAULT CURRENT_TIMESTAMP | 消费时间 |

**正确性关键——事务边界**：去重登记与状态流转在**同一 DB 事务**内：

- 处理成功 → 登记与流转一起提交 → 重投消息命中 `uk_flow_id` → 判重跳过；
- 处理失败 → 一起回滚 → 消息重试时登记不存在 → 不会被误判为重复。

若去重与业务分两个事务，就会出现"登记了但没处理成功"的假阳性判重，消息被静默丢弃——这是该方案最常见的错误实现。

**为什么不用 Redis 做消费去重**：去重必须与状态流转同生共死（同事务），Redis 无法参与本地事务；且 Redis 判重在极端重启场景可能丢失，DB 唯一索引是确定性保证。

---

## 4. mq_dead_message 死信记录表

**职责**：消费端死信兜底。ORDERLY 顺序消费中基础设施异常会原地重试并阻塞队列，重试 3 次仍失败的消息落此表并 ACK，解除阻塞，等待人工/补偿处理。

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | BIGINT | PK, AUTO_INCREMENT | 主键 |
| msg_id | VARCHAR(64) | NULL | RocketMQ 原生消息ID |
| flow_id | BIGINT | NULL, KEY(idx_flow_id) | 报文流水ID（毒消息解析失败时为空） |
| biz_no | VARCHAR(64) | NULL | 业务单号（同上） |
| reconsume_times | INT | NOT NULL DEFAULT 0 | 入死信时的已重试次数 |
| message_body | TEXT | NULL | 原始消息体 JSON（补偿重放的输入） |
| error_msg | VARCHAR(1024) | NULL | 最后一次异常信息（超长截断） |
| create_time | DATETIME | NOT NULL DEFAULT CURRENT_TIMESTAMP, KEY | 入死信时间 |

**记录两类消息**：

1. 基础设施异常重试耗尽（DB 长时间不可用等）；
2. 毒消息（JSON 解析失败）——注意此类消息必须落表后 ACK 返回，**不能抛异常**，否则 rocketmq-spring 触发重投形成死信表重复插入循环。

`message_body` 用 TEXT 保留完整原始报文，补偿任务可据此重放；`idx_create_time` 支撑"近 N 小时死信"巡检查询。

---

## 5. mq_pending_event 乱序超前事件暂存表

**职责**：防线B。顺序消息只保证"按入队顺序消费"，但并发请求/网络延迟/发送重试会导致
入队顺序与业务真实顺序不符（如真实序 PAY→FINISH，FINISH 先入队）。消费端遇到"超前事件"
（事件合法前置状态的链路序号 > 当前状态序号）：丢弃则丢单、重试则阻塞队列死锁，
唯一正确解法是**暂存 + ACK，状态追上后回放**。

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | BIGINT | PK, AUTO_INCREMENT | 主键 |
| biz_no | VARCHAR(64) | NOT NULL, KEY(idx_biz_no) | 业务单号 |
| flow_id | BIGINT | NOT NULL, **UNIQUE(uk_flow_id)** | 报文流水ID（防重复暂存） |
| event | VARCHAR(32) | NOT NULL | 交易事件 |
| message_body | VARCHAR(1024) | NULL | 交易报文原文（回放时使用） |
| trace_id | VARCHAR(64) | NULL | 全链路追踪ID |
| msg_id | VARCHAR(64) | NULL | RocketMQ 原生消息ID |
| create_time | DATETIME | NOT NULL DEFAULT CURRENT_TIMESTAMP, KEY | 暂存时间（巡检超时告警依据） |

**事务边界**：暂存与消费去重登记、状态流转**同事务**——一起提交或一起回滚，
重投消息不会重复暂存（uk_flow_id 兜底）。

**回放语义**：每次正常流转后按 flow_id 升序遍历该单号 pending，
前置状态匹配即 CAS 应用并删除记录；循环直到无进展（剩余事件仍超前）。

**巡检口径**：单号暂存超过 N 分钟仍存在 → 告警（前置事件疑似丢失，
需人工/补偿介入——注意 pending 不做自动清理，事件不丢是硬承诺）。

---

## 6. 跨表关系（ER）

```
trade_message_flow (1) ──── flow_id ────▶ (1) mq_consume_record     一条流水最多一条消费记录（重复投递不新增）
trade_message_flow (N) ──── biz_no  ────▶ (1) trade_order_state     同一单号多条事件流水，对应一条状态记录
mq_dead_message.flow_id ─────────────────▶ trade_message_flow.id    死信回溯（可空）
```

**对账口径**（集成测试已验证）：

```sql
-- 正常情况：每个 SENT 流水恰好一条消费记录
SELECT COUNT(*) FROM trade_message_flow f
JOIN mq_consume_record c ON c.flow_id = f.id
WHERE f.send_status = 'SENT';

-- 异常巡检：发送失败未补偿 / 死信未处理
SELECT biz_no, flow_id FROM trade_message_flow WHERE send_status = 'SEND_FAILED';
SELECT biz_no, flow_id, error_msg FROM mq_dead_message WHERE create_time > NOW() - INTERVAL 1 DAY;
```
