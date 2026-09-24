package com.example.statemachine.entity;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import lombok.Data;

import java.io.Serializable;
import java.util.Date;

/**
 * MQ 死信记录表实体（mq_dead_message）
 *
 * <p><b>为什么需要本地死信表：</b>ORDERLY 顺序消费中，消息处理抛出异常会在当前队列
 * 原地重试并阻塞后续消息（保证不乱序）。若基础设施异常（如 DB 宕机）长时间不恢复，
 * 无限重试会让整个队列永久卡死。因此消费端设置重试上限：达到上限仍失败的消息，
 * 落入本表并正常 ACK（不抛异常），解除队列阻塞；后续由人工或补偿任务处理。</p>
 *
 * <p>注意：业务性拒绝（非法流转、重复消息、未知事件）不属于死信——
 * 它们在去重表/状态机处已被正常"处理"并 ACK。</p>
 *
 * @author yzy
 * @version 1.0
 */
@Data
@TableName("mq_dead_message")
public class MqDeadMessage implements Serializable {

    private static final long serialVersionUID = 1L;

    /** 主键（数据库自增） */
    @TableId(value = "id", type = IdType.AUTO)
    private Long id;

    /** RocketMQ 原生消息ID */
    private String msgId;

    /** 报文流水ID（消息体解析失败时可能为空） */
    private Long flowId;

    /** 业务单号（消息体解析失败时可能为空） */
    private String bizNo;

    /** 已重试次数 */
    private Integer reconsumeTimes;

    /** 原始消息体（JSON，用于补偿重放） */
    private String messageBody;

    /** 最后一次异常信息 */
    private String errorMsg;

    /** 入死信时间 */
    private Date createTime;
}
