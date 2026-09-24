package com.example.statemachine.exception;

/**
 * 重复消息异常（消费端消息级幂等的内部控制流信号）
 *
 * <p>触发场景：RocketMQ at-least-once 重投的消息命中 mq_consume_record
 * 的 uk_flow_id 唯一索引。该异常从 {@code apply()}（@Transactional）抛出：</p>
 * <ul>
 *   <li>事务回滚——重复消息本就没有任何状态变更需要提交；</li>
 *   <li>由监听器捕获后记录 info 日志并正常 ACK（不重试、不进死信表）。</li>
 * </ul>
 *
 * <p>设计意图：把"重复消息"与"非法流转"（warn 日志）从日志语义上彻底分开，
 * 前者是 MQ 机制的正常现象，后者才是需要告警关注的异常信号。</p>
 *
 * @author yzy
 * @version 1.0
 */
public class DuplicateMessageException extends RuntimeException {

    private static final long serialVersionUID = 1L;

    /** 业务单号 */
    private final String bizNo;

    /** 报文流水ID */
    private final Long flowId;

    /**
     * 构造重复消息异常
     *
     * @param bizNo  业务单号
     * @param flowId 报文流水ID
     */
    public DuplicateMessageException(String bizNo, Long flowId) {
        super("duplicate message, bizNo=" + bizNo + ", flowId=" + flowId);
        this.bizNo = bizNo;
        this.flowId = flowId;
    }

    public String getBizNo() {
        return bizNo;
    }

    public Long getFlowId() {
        return flowId;
    }
}
