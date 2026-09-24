-- ============================================================
-- 消息可靠性增强 - 增量 DDL（针对已按旧版脚本建库的环境）
-- ============================================================

USE YZY_DB;

-- 1. 报文流水表增加消息发送状态列（存量数据默认 SENT，代表历史消息已发送）
ALTER TABLE trade_message_flow
    ADD COLUMN send_status VARCHAR(16) NOT NULL DEFAULT 'SENDING'
    COMMENT '消息发送状态：SENDING/SENT/SEND_FAILED' AFTER trace_id;

-- 2. 消费去重表（消息级幂等，与状态流转同事务登记）
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

-- 3. 死信记录表（ORDERLY 重试上限后落表 ACK，解除队列阻塞）
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
