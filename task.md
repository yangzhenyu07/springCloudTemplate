# task.md — 交易中心幂等校验 + 状态机服务 + RocketMQ 顺序消息

- 生成时间：2026-09-15
- 需求来源：用户需求（交易中心场景）
- 技术栈摘要（提取自 yzy.md + 工作记忆）：Java 8 编译目标 / Spring Boot 2.6.15 / Spring Cloud 2021.0.9 / MyBatis-Plus 3.5.2 / MySQL(YZY_DB) / Redis / Nacos / RocketMQ(官方 starter 2.2.2，nameserver 127.0.0.1:9876)
- 决策记录：`bes-cloudmq-h-clernt-all` 本地仓库不存在（宝兰德私有依赖），经用户确认改用 `rocketmq-spring-boot-starter 2.2.2`，生产者侧 API 做薄封装，后续可替换 bes 客户端

## 数据库设计

| 表名 | 所属库 | 说明 |
|------|--------|------|
| trade_message_flow | YZY_DB | 报文流水表，幂等 key 唯一索引（第二层 DB 幂等） |
| trade_order_state  | YZY_DB | 状态机状态表，biz_no 唯一，条件更新保证流转合法 |

### 建表 SQL

见 `sql/trade_idempotent.sql`（T001 生成）

## 开发任务

### 阶段一：依赖与配置

- [x] T001 生成建表 SQL `sql/trade_idempotent.sql`
  - trade_message_flow：id, idem_key(UK), biz_no, event, message_body, trace_id, create_time
  - trade_order_state：id, biz_no(UK), state, pre_state, version, create_time, update_time
- [x] T002 BOM `yzy-dependencies-bom/pom.xml` 增加 rocketmq-spring-boot-starter 2.2.2 版本管理
- [x] T003 root `pom.xml` 增加 yzy-state-machine 模块

### 阶段二：交易中心（yzy-demo，幂等 + 生产者）

- [x] T004 `TradeMessageFlow` 实体 + `TradeMessageFlowMapper`
- [x] T005 `IdempotentService`：Redis `SET key 1 EX 259200 NX` 原子命令获取幂等标记
  - 返回 false → 重复请求，终止
  - 返回 true → 放行；业务异常**不删除** key，等待 3 天自动过期
- [x] T006 `TradeSubmitDTO` / `TradeStateMessage`（MQ 消息体，含 traceId 透传）
- [x] T007 `TradeService`（@Transactional）：
  - 事务内插入 trade_message_flow（uk_idem_key）
  - DuplicateKeyException → 并发穿透，返回重复请求
  - 其他异常 → 回滚，不删 Redis key
  - 事务提交后 `rocketMQTemplate.syncSendOrderly(topic, msg, hashKey=bizNo)` 顺序消息
- [x] T008 `TradeController`：POST /api/trade/submit
- [x] T009 yzy-demo `bootstrap.yml` 增加 rocketmq name-server/producer-group 配置

### 阶段三：状态机服务（新模块 yzy-state-machine，端口 8090）

- [x] T010 模块骨架：pom.xml（rocketmq starter + web + mybatis-plus + mysql + springCloud-module/common-module-v1）、`StateMachineApplication`、bootstrap.yml
- [x] T011 `TradeStateEnum` / `TradeEventEnum` + 合法流转规则表
  - INIT --CREATE--> CREATED --PAY--> PAID --FINISH--> FINISHED
- [x] T012 `TradeOrderState` 实体 + `TradeOrderStateMapper`
- [x] T013 `TradeStateMachineService`：
  - 首条消息懒建 INIT 状态记录（biz_no 唯一）
  - 条件更新 `UPDATE ... SET state=to WHERE biz_no=? AND state=from`（乐观锁式，杜绝乱序/重复消息破坏状态）
  - 非法流转拒绝并告警日志
- [x] T014 `TradeOrderlyListener`：`@RocketMQMessageListener(consumeMode = ConsumeMode.ORDERLY)` 顺序消费，MDC 透传 traceId
- [x] T015 `TradeStateQueryController`：GET /api/state/order/{bizNo} 状态查询

### 阶段四：构建与集成测试

- [x] T016 全量构建 `mvn clean install -DskipTests`（先下载 rocketmq 依赖）
- [x] T017 执行建表 SQL（pymysql，复用 setup_db.py 方式）
- [x] T018 集成测试：启动 yzy-state-machine(8090)、yzy-demo(8088)，curl 验证
  - 场景1：同 idemKey 重复提交 → 第二次返回【重复请求】（Redis 层）
  - 场景2：同 bizNo 不同 idemKey 重复事件 → 流水表可插但状态机拒绝非法流转
  - 场景3：完整流转链 CREATE→PAY→FINISH → 状态机依次流转到 FINISHED
  - 场景4：并发穿透模拟：绕过 Redis 直插同 idemKey → DB 唯一索引拦截返回重复请求
- [x] T019 集成测试通过后补全详细注释（设计意图 / 顺序性说明 / 幂等三层防线）

### 阶段五：消息级防重复与可靠性增强（T020-T024）

- [x] T020 消费去重表 `mq_consume_record`（uk_flow_id）：RocketMQ at-least-once 重投显式判重；
  去重登记与状态流转**同事务**，处理失败一起回滚（重试不误判重复）；
  重复消息与非法流转日志语义分离（info vs warn）
- [x] T021 死信记录表 `mq_dead_message`：ORDERLY 基础设施异常重试上限（3 次）后
  落表并 ACK 解除队列阻塞；毒消息（解析失败）直接落表 ACK，防止重投循环
- [x] T022 生产端防丢失：trade_message_flow 增加 send_status（SENDING/SENT/SEND_FAILED），
  发送重试 2 次，结果回写流水表供对账补偿（补偿需按 flowId 顺序重发，否则破坏顺序性）；
  消息 KEYS = idemKey，broker 端可按 key 检索轨迹
- [x] T023 增量 DDL `sql/increment_v2.sql` 执行 + 全量脚本 `sql/trade_idempotent.sql` 更新
- [x] T024 回归测试 10/10 通过 + 数据对账验证：
  8 条消息全部 SENT；mq_consume_record 8 条与流水表 JOIN 完全一致；死信 0 条；msg_id 全部回填

### 阶段六：代码走查与优化（T025-T027）

- [x] T025 走查发现并修复 5 项问题：
  ① TradeSubmitDTO 补 @NotBlank/@Size 参数校验（原 @Valid 形同虚设，空 idemKey 会共享幂等锁）；
  ② yzy-demo 新增 GlobalExceptionHandler 统一异常响应格式（400 参数校验/500 系统异常，带 traceId）；
  ③ DuplicateMessageException 从 impl 内部类抽取为独立异常类（解除监听器对实现类的耦合）；
  ④ 状态机 apply 增加必填字段防御校验（畸形消息 ACK 丢弃，避免撞 NOT NULL 约束被误判为基础设施异常空耗 3 次重试）；
  ⑤ TradeServiceImpl 内联全限定类名改 import
- [x] T026 messageBody 入口校验取 4096 上限（防恶意超大报文 fail-fast），业务长度 1024 仍由 DB 列兜底，
  保留需求 2.3"DB 异常回滚不删 key"链路可达
- [x] T027 优化后回归测试 11/11 PASS（新增场景0 参数校验拦截；场景6 响应统一为 Result 格式）+ 对账一致
- [x] T028 输出文档：docs/architecture-design.md（整体架构设计）、docs/table-design.md（表设计）

### 阶段七：乱序治理（防线A入口预检 + 防线B消费端暂存回放）

- [x] T029 问题定位：MQ ORDERLY 只保证"按入队顺序消费"，并发请求/网络延迟/发送重试会导致
  入队顺序与业务真实顺序不符；消费端单独无解（丢弃丢单/重试死锁）
- [x] T030 规则枚举下沉 common-module-v1（TradeStateEnum 加 order 序号、TradeEventEnum），
  两端单一事实来源；ResultCode 新增 CONFLICT(409)
- [x] T031 防线A：yzy-demo 入口预检 checkStateConflict——查流水表最新已受理事件推导
  "在途状态"（不查状态表，规避消费延迟误拒连续提交），乱序请求 409 不进 MQ
- [x] T032 防线B：yzy-state-machine 三类流转判定（正常 CAS/超前暂存 mq_pending_event/
  过期丢弃）+ 流转后 pending 回放（同事务，应用即删除）
- [x] T033 debug 接口 /api/state/debug/apply（模拟乱序消息直调状态机，测试/运维用）
- [x] T034 修复实现过程中发现的两个问题：
  ① 预检初版查状态表导致"连续快速提交同单号多事件"被消费延迟误拒 → 改查流水表（场景7 暴露）
  ② 测试脚本 debug flowId 复用历史轮次撞消费去重表 → 随机化
- [x] T035 回归测试 16/16 PASS（13 大场景，含防线A 409/防线B 暂存回放/过期丢弃/消费去重）
  + 对账一致（28 SENT、pending 0 残留、死信 0）
- [x] T036 文档同步：架构文档 4.2-4.4 节（MQ 保序≠保业务序、乱序治理、六层防线全景）、
  表设计文档 mq_pending_event 章节；SQL 全量脚本 + increment_v3.sql

## 接口清单

| 路径 | Method | 服务 | 说明 | 请求参数 | 响应 |
|------|--------|------|------|----------|------|
| /api/trade/submit | POST | yzy-demo(8088) | 交易报文提交（幂等校验+流水+发顺序消息） | body: bizNo, event, idemKey, messageBody | Result |
| /api/state/order/{bizNo} | GET | yzy-state-machine(8090) | 查询状态机当前状态 | path: bizNo | Result<TradeOrderState> |

## 注意事项

- Redis 幂等 key 统一前缀 `idem:trade:`，过期 259200 秒（3 天）
- 顺序消息保证：同一 bizNo 作为 hashKey 路由到同一 MessageQueue；消费端 ConsumeMode.ORDERLY 单线程顺序消费
- 顺序消息只在事务提交后发送（TransactionSynchronization afterCommit），避免事务回滚后脏消息
- 状态流转用 DB 条件更新兜底，即使消息重复/乱序也不会破坏状态一致性
- RocketMQ nameserver：127.0.0.1:9876；topic：yzy-trade-topic；producer group：yzy-demo-trade-producer；consumer group：yzy-state-machine-consumer
