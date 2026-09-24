package com.example.statemachine.entity;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import lombok.Data;

import java.io.Serializable;
import java.util.Date;

/**
 * 乱序超前事件暂存表实体（mq_pending_event）
 *
 * <p><b>为什么需要暂存：</b>RocketMQ 顺序消息只保证"按入队顺序消费"，
 * 但并发请求 + 网络延迟/发送重试会导致<b>入队顺序本身与业务真实顺序不符</b>
 * （如真实序 PAY→FINISH，FINISH 先入队）。此时消费端遇到"超前事件"
 * （事件合法前置状态在当前状态之后）：丢弃则事件永久丢失（订单卡中间态），
 * 重试则阻塞队列（ORDERLY 语义）死锁。唯一正确解法：<b>暂存 + ACK 放行，
 * 待状态追上后回放</b>。</p>
 *
 * <p>与消费去重表的事务关系：暂存与去重登记、状态流转同事务——
 * 一起提交或一起回滚，重投消息不会重复暂存（uk_flow_id 兜底）。</p>
 *
 * @author yzy
 * @version 1.0
 */
@Data
@TableName("mq_pending_event")
public class MqPendingEvent implements Serializable {

    private static final long serialVersionUID = 1L;

    /** 主键（数据库自增） */
    @TableId(value = "id", type = IdType.AUTO)
    private Long id;

    /** 业务单号 */
    private String bizNo;

    /** 报文流水ID（唯一索引 uk_flow_id，防止重复暂存） */
    private Long flowId;

    /** 交易事件 */
    private String event;

    /** 交易报文原文（回放时使用） */
    private String messageBody;

    /** 全链路追踪ID */
    private String traceId;

    /** RocketMQ 原生消息ID */
    private String msgId;

    /** 暂存时间 */
    private Date createTime;
}
