package com.example.entity;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import lombok.Data;

import java.io.Serializable;
import java.util.Date;

/**
 * 交易中心报文流水表实体（trade_message_flow）
 *
 * <p>幂等设计的第二道防线：idem_key 上建立唯一索引（uk_idem_key），
 * 当 Redis 幂等 key 已过期/被删除后，仍可通过 DB 唯一索引拦截并发穿透的重复请求。</p>
 *
 * <p>消息可靠性：send_status 记录"事务提交后发送顺序消息"的结果
 * （SENDING → SENT / SEND_FAILED）。发送动作在事务提交之后执行，存在失败可能；
 * SEND_FAILED 的流水由对账/补偿任务扫描重发（本服务不自动重发，避免顺序被打乱）。</p>
 *
 * @author yzy
 * @version 1.0
 */
@Data
@TableName("trade_message_flow")
public class TradeMessageFlow implements Serializable {

    private static final long serialVersionUID = 1L;

    /** 消息发送状态：已落库待发送 */
    public static final String SEND_STATUS_SENDING = "SENDING";

    /** 消息发送状态：发送成功 */
    public static final String SEND_STATUS_SENT = "SENT";

    /** 消息发送状态：发送失败（等待对账补偿） */
    public static final String SEND_STATUS_FAILED = "SEND_FAILED";

    /** 主键（数据库自增） */
    @TableId(value = "id", type = IdType.AUTO)
    private Long id;

    /** 幂等key（客户端每次请求唯一，如 UUID），对应唯一索引 uk_idem_key；同时作为 MQ 消息 KEYS 便于 broker 端检索 */
    private String idemKey;

    /** 业务单号（作为顺序消息的 hashKey，同一单号路由到同一队列保证顺序） */
    private String bizNo;

    /** 交易事件：TRADE_CREATE / TRADE_PAY / TRADE_FINISH */
    private String event;

    /** 交易报文原文 */
    private String messageBody;

    /** 全链路追踪ID（透传到 MQ 消费端，保持链路可追踪） */
    private String traceId;

    /** 消息发送状态：SENDING / SENT / SEND_FAILED */
    private String sendStatus;

    /** 创建时间 */
    private Date createTime;
}
