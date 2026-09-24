-- ============================================================
-- 乱序治理（防线B）- 增量 DDL：超前事件暂存表
-- 已执行过 increment_v2.sql 的环境执行本脚本即可
-- ============================================================

USE YZY_DB;

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
