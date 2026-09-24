package com.example.statemachine.dto;

import lombok.Data;

import java.io.Serializable;

/**
 * RocketMQ 状态机消息体（与 yzy-demo 发送端字段一一对应）
 *
 * <p>顺序性说明：消费端 ConsumeMode.ORDERLY + 生产端以 bizNo 为 hashKey，
 * 保证同一 bizNo 的消息严格按发送顺序到达本服务。</p>
 *
 * @author yzy
 * @version 1.0
 */
@Data
public class TradeStateMessage implements Serializable {

    private static final long serialVersionUID = 1L;

    /** 业务单号（顺序 hashKey） */
    private String bizNo;

    /** 交易事件：TRADE_CREATE / TRADE_PAY / TRADE_FINISH */
    private String event;

    /** 交易报文原文 */
    private String messageBody;

    /** 全链路追踪ID（消费端回填 MDC，保持日志链路连续） */
    private String traceId;

    /** 报文流水ID（trade_message_flow.id，便于两端对账） */
    private Long flowId;

    /** RocketMQ 原生消息ID（由消费端回填，写入消费去重表对账用） */
    private String msgId;

    /** 消息产生时间戳（毫秒） */
    private Long occurredAt;
}
