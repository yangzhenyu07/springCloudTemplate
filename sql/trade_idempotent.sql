-- ============================================================
-- 交易中心幂等校验 + 状态机 + 消息可靠性 建表脚本
-- 目标库：YZY_DB（MySQL 127.0.0.1:3306）
-- 说明：
--   1. trade_message_flow 报文流水表：幂等第二道防线，
--      idem_key 唯一索引拦截并发穿透（Redis 幂等 key 过期/删除后的兜底）；
--      send_status 记录消息发送状态，发送失败可对账补偿（防止消息丢失无人知晓）
--   2. trade_order_state 状态机状态表：biz_no 唯一，
--      状态流转通过条件更新（乐观锁思想）保证消息乱序/重复时不破坏状态一致性
--   3. mq_consume_record 消费去重表：RocketMQ at-least-once 语义下，
--      消费端按 flow_id 唯一索引显式判重（重复消息跳过，与非法流转明确区分）；
--      去重记录与状态流转同事务，处理失败一起回滚，保证重试时仍可正常处理
--   4. mq_dead_message 死信记录表：ORDERLY 消费基础设施异常达到重试上限后，
--      消息落此表并 ACK，解除队列阻塞，由人工/对账任务介入
-- ============================================================

USE YZY_DB;

-- ----------------------------
-- 1. 报文流水表
-- ----------------------------
CREATE TABLE IF NOT EXISTS trade_message_flow (
    id           BIGINT       NOT NULL AUTO_INCREMENT COMMENT '主键',
    idem_key     VARCHAR(64)  NOT NULL                COMMENT '幂等key（客户端每次请求唯一，如 UUID）',
    biz_no       VARCHAR(64)  NOT NULL                COMMENT '业务单号（顺序消息 hashKey，同一单号顺序消费）',
    event        VARCHAR(32)  NOT NULL                COMMENT '交易事件：TRADE_CREATE/TRADE_PAY/TRADE_FINISH',
    message_body VARCHAR(1024)         DEFAULT NULL   COMMENT '交易报文原文',
    trace_id     VARCHAR(64)           DEFAULT NULL   COMMENT '全链路追踪ID',
    send_status  VARCHAR(16)  NOT NULL DEFAULT 'SENDING' COMMENT '消息发送状态：SENDING/SENT/SEND_FAILED',
    create_time  DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    PRIMARY KEY (id),
    UNIQUE KEY uk_idem_key (idem_key),
    KEY idx_biz_no (biz_no),
    KEY idx_send_status (send_status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='交易中心报文流水表';

-- ----------------------------
-- 2. 状态机状态表
-- ----------------------------
CREATE TABLE IF NOT EXISTS trade_order_state (
    id         BIGINT      NOT NULL AUTO_INCREMENT COMMENT '主键',
    biz_no     VARCHAR(64) NOT NULL                COMMENT '业务单号（唯一）',
    state      VARCHAR(32) NOT NULL DEFAULT 'INIT' COMMENT '当前状态：INIT/CREATED/PAID/FINISHED',
    pre_state  VARCHAR(32)          DEFAULT NULL   COMMENT '流转前状态',
    version    INT         NOT NULL DEFAULT 0      COMMENT '流转次数（每次合法流转+1）',
    create_time DATETIME   NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    update_time DATETIME   NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    PRIMARY KEY (id),
    UNIQUE KEY uk_biz_no (biz_no)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='交易中心订单状态机表';

-- ----------------------------
-- 3. 消费去重表（消息级幂等）
--    设计要点：
--    a) uk_flow_id 唯一索引：同一报文流水（flow_id）只允许登记一次消费记录，
--       重复投递的消息 DuplicateKeyException → 明确判定为重复消息并跳过；
--    b) 去重登记与状态流转在同一 DB 事务内：处理失败一起回滚，
--       消息重试时去重记录不存在，不会误跳过未成功处理的消息；
--    c) msg_id 保留 RocketMQ 原生消息ID，便于与 broker 侧日志对账。
-- ----------------------------
CREATE TABLE IF NOT EXISTS mq_consume_record (
    id          BIGINT      NOT NULL AUTO_INCREMENT COMMENT '主键',
    flow_id     BIGINT      NOT NULL                COMMENT '报文流水ID（trade_message_flow.id，消息级去重依据）',
    biz_no      VARCHAR(64) NOT NULL                COMMENT '业务单号',
    event       VARCHAR(32) NOT NULL                COMMENT '交易事件',
    msg_id      VARCHAR(64)          DEFAULT NULL   COMMENT 'RocketMQ 原生消息ID（对账用）',
    consume_time DATETIME   NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '消费时间',
    PRIMARY KEY (id),
    UNIQUE KEY uk_flow_id (flow_id),
    KEY idx_biz_no (biz_no)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='MQ消费去重表';

-- ----------------------------
-- 4. 死信记录表
--    设计要点：
--    a) ORDERLY 顺序消费中基础设施异常（DB 不可用等）会原地重试并阻塞当前队列，
--       达到重试上限（默认 3 次）仍失败的消息落此表并正常 ACK，解除阻塞；
--    b) 落表内容包含完整消息体与异常信息，供人工排查或补偿任务重放；
--    c) 业务性拒绝（非法流转/重复消息）不进死信表——它们在去重表/状态机处被正常处理。
-- ----------------------------
CREATE TABLE IF NOT EXISTS mq_dead_message (
    id             BIGINT       NOT NULL AUTO_INCREMENT COMMENT '主键',
    msg_id         VARCHAR(64)           DEFAULT NULL   COMMENT 'RocketMQ 原生消息ID',
    flow_id        BIGINT                DEFAULT NULL   COMMENT '报文流水ID（解析失败时可能为空）',
    biz_no         VARCHAR(64)           DEFAULT NULL   COMMENT '业务单号（解析失败时可能为空）',
    reconsume_times INT         NOT NULL DEFAULT 0       COMMENT '已重试次数',
    message_body   TEXT                  DEFAULT NULL   COMMENT '原始消息体（JSON，用于补偿重放）',
    error_msg      VARCHAR(1024)         DEFAULT NULL   COMMENT '最后一次异常信息',
    create_time    DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '入死信时间',
    PRIMARY KEY (id),
    KEY idx_flow_id (flow_id),
    KEY idx_create_time (create_time)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='MQ死信记录表';

-- ----------------------------
-- 5. 乱序超前事件暂存表（乱序治理防线B）
--    设计要点：
--    a) 顺序消息只保证"按入队顺序消费"，并发请求/网络延迟/发送重试会导致
--       入队顺序与业务真实顺序不符（如 FINISH 先于 PAY 入队）；
--    b) 消费端遇到"超前事件"（事件合法前置状态的链路序号 > 当前状态序号）：
--       丢弃则丢单、重试则阻塞队列死锁，唯一正确解法是暂存 + ACK，
--       状态追上后由回放逻辑补齐（应用成功即删除本表记录）；
--    c) uk_flow_id 防止重复暂存；暂存与消费去重登记、状态流转同事务；
--    d) 巡检建议：单号暂存超过 N 分钟仍存在 → 告警（说明前置事件疑似丢失）。
-- ----------------------------
CREATE TABLE IF NOT EXISTS mq_pending_event (
    id           BIGINT        NOT NULL AUTO_INCREMENT COMMENT '主键',
    biz_no       VARCHAR(64)   NOT NULL                COMMENT '业务单号',
    flow_id      BIGINT        NOT NULL                COMMENT '报文流水ID（唯一，防重复暂存）',
    event        VARCHAR(32)   NOT NULL                COMMENT '交易事件',
    message_body VARCHAR(1024)          DEFAULT NULL   COMMENT '交易报文原文（回放时使用）',
    trace_id     VARCHAR(64)            DEFAULT NULL   COMMENT '全链路追踪ID',
    msg_id       VARCHAR(64)            DEFAULT NULL   COMMENT 'RocketMQ 原生消息ID',
    create_time  DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '暂存时间',
    PRIMARY KEY (id),
    UNIQUE KEY uk_flow_id (flow_id),
    KEY idx_biz_no (biz_no),
    KEY idx_create_time (create_time)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='乱序超前事件暂存表';
