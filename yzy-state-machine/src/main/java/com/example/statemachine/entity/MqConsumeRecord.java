package com.example.statemachine.entity;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import lombok.Data;

import java.io.Serializable;
import java.util.Date;

/**
 * MQ 消费去重表实体（mq_consume_record）
 *
 * <p><b>为什么需要消息级去重：</b>RocketMQ 的投递语义是 at-least-once，
 * 以下场景消息会被重复投递：</p>
 * <ul>
 *   <li>消费端处理完成后、ACK 返回前发生 GC 停顿/网络抖动/进程重启；</li>
 *   <li>消费超时触发客户端重投；</li>
 *   <li>rebalance 期间队列迁移导致的边界重复。</li>
 * </ul>
 *
 * <p><b>设计要点：</b></p>
 * <ol>
 *   <li>以报文流水 ID（flow_id）作为去重依据，uk_flow_id 唯一索引兜底；</li>
 *   <li>去重登记必须与状态流转在<b>同一 DB 事务</b>内提交：
 *       处理失败一起回滚 → 消息重试时登记记录不存在，不会误跳过未成功处理的消息；
 *       处理成功一起提交 → 重复投递命中唯一索引，明确判定为重复消息并跳过；</li>
 *   <li>与状态机 CAS 的分工：CAS 防"状态被重复/乱序消息破坏"（正确性兜底），
 *       去重表防"重复消息被误报为非法流转"（可观测性 + 语义清晰）。</li>
 * </ol>
 *
 * @author yzy
 * @version 1.0
 */
@Data
@TableName("mq_consume_record")
public class MqConsumeRecord implements Serializable {

    private static final long serialVersionUID = 1L;

    /** 主键（数据库自增） */
    @TableId(value = "id", type = IdType.AUTO)
    private Long id;

    /** 报文流水ID（trade_message_flow.id，消息级去重依据，唯一索引 uk_flow_id） */
    private Long flowId;

    /** 业务单号 */
    private String bizNo;

    /** 交易事件 */
    private String event;

    /** RocketMQ 原生消息ID（对账用） */
    private String msgId;

    /** 消费时间 */
    private Date consumeTime;
}
