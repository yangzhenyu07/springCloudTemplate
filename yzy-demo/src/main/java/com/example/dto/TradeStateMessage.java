package com.example.dto;

import lombok.Data;

import java.io.Serializable;

/**
 * RocketMQ 状态机消息体（yzy-demo → yzy-state-machine）
 *
 * <p>顺序性设计：消费端以 bizNo 作为顺序消息的 hashKey（sharding key），
 * RocketMQ 保证同一 hashKey 的消息按发送顺序落在同一 MessageQueue，
 * 配合消费端 ConsumeMode.ORDERLY（队列内单线程顺序消费），
 * 实现“同一业务单号的消息严格有序、不同单号之间并行”。 </p>
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

    /** RocketMQ 原生消息ID（由消费端回填，写入消费去重表对账用；生产端不填） */
    private String msgId;

    /** 消息产生时间戳（毫秒） */
    private Long occurredAt;
}
