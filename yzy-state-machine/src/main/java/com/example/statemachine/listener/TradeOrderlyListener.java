package com.example.statemachine.listener;

import com.example.statemachine.dto.TradeStateMessage;
import com.example.statemachine.entity.MqDeadMessage;
import com.example.statemachine.exception.DuplicateMessageException;
import com.example.statemachine.mapper.MqDeadMessageMapper;
import com.example.statemachine.service.TradeStateMachineService;
import com.fasterxml.jackson.databind.ObjectMapper;
import lombok.extern.slf4j.Slf4j;
import org.apache.rocketmq.common.message.MessageExt;
import org.apache.rocketmq.spring.annotation.ConsumeMode;
import org.apache.rocketmq.spring.annotation.RocketMQMessageListener;
import org.apache.rocketmq.spring.core.RocketMQListener;
import org.slf4j.MDC;
import org.springframework.stereotype.Component;

import javax.annotation.Resource;
import java.nio.charset.StandardCharsets;
import java.util.Date;

/**
 * 交易中心状态消息顺序消费者（消息级防重复 + 死信兜底）
 *
 * <p><b>顺序性核心配置：{@code consumeMode = ConsumeMode.ORDERLY}</b></p>
 * <p>RocketMQ 顺序消费语义：同一 MessageQueue 内的消息由单线程按存入顺序依次回调本监听器；
 * 配合生产端以 bizNo 为 hashKey，实现「同一业务单号严格有序、不同单号并行」。</p>
 *
 * <p><b>本监听器的异常/重试/死信约定：</b></p>
 * <table border="1">
 *   <tr><th>场景</th><th>处理方式</th><th>是否重试</th></tr>
 *   <tr><td>重复消息（去重表命中）</td><td>捕获 {@link DuplicateMessageException}，info 日志</td><td>否，正常 ACK</td></tr>
 *   <tr><td>业务性拒绝（非法流转/未知事件）</td><td>状态机内部 warn 日志后返回</td><td>否，正常 ACK</td></tr>
 *   <tr><td>基础设施异常，重试次数 &lt; 上限</td><td>向上抛出</td><td>是，ORDERLY 原地重试（阻塞当前队列，不乱序）</td></tr>
 *   <tr><td>基础设施异常，重试次数 ≥ 上限</td><td>落死信表 mq_dead_message 后 ACK</td><td>否，解除队列阻塞，人工介入</td></tr>
 *   <tr><td>消息体解析失败（毒消息）</td><td>直接落死信表后 ACK</td><td>否（重试也不可能成功）</td></tr>
 * </table>
 *
 * <p><b>为什么用 MessageExt 而不是直接反序列化：</b>死信判定需要读取
 * {@code reconsumeTimes}（已重试次数），这是 RocketMQ 原生消息元数据，
 * 必须监听 MessageExt 后自行反序列化消息体。</p>
 *
 * @author yzy
 * @version 1.0
 */
@Slf4j
@Component
@RocketMQMessageListener(
        topic = "yzy-trade-topic",
        consumerGroup = "yzy-state-machine-consumer",
        consumeMode = ConsumeMode.ORDERLY
)
public class TradeOrderlyListener implements RocketMQListener<MessageExt> {

    /** 基础设施异常最大重试次数：超过后消息进死信表并 ACK，防止队列无限阻塞 */
    private static final int MAX_RECONSUME_TIMES = 3;

    private static final String TRACE_ID_KEY = "traceId";

    @Resource
    private TradeStateMachineService tradeStateMachineService;

    @Resource
    private MqDeadMessageMapper mqDeadMessageMapper;

    /** JSON 反序列化器（消息体 → TradeStateMessage） */
    private final ObjectMapper objectMapper = new ObjectMapper();

    /**
     * 顺序消费入口
     *
     * @param ext RocketMQ 原生消息（含 msgId、reconsumeTimes 等元数据）
     */
    @Override
    public void onMessage(MessageExt ext) {
        // 1. 反序列化消息体（失败 = 毒消息：已落死信表，直接 ACK 返回，避免重投循环）
        TradeStateMessage message = parsePayload(ext);
        if (message == null) {
            return;
        }

        // 2. traceId 回填 MDC，使消费端日志与生产端日志链路连续
        String traceId = message.getTraceId();
        if (traceId != null && !traceId.isEmpty()) {
            MDC.put(TRACE_ID_KEY, traceId);
        }
        try {
            log.info("[消费者] 收到顺序消息，bizNo={}, event={}, flowId={}, msgId={}, reconsumeTimes={}, traceId={}",
                    message.getBizNo(), message.getEvent(), message.getFlowId(),
                    ext.getMsgId(), ext.getReconsumeTimes(), traceId);

            // 消费端回填 broker 消息ID，随消息体写入消费去重表（对账用）
            message.setMsgId(ext.getMsgId());

            tradeStateMachineService.apply(message);
        } catch (DuplicateMessageException e) {
            // 重复消息（at-least-once 重投）：去重表已拦截，正常 ACK 跳过
            log.info("[消费者] 重复消息已跳过（去重命中），bizNo={}, flowId={}, msgId={}",
                    e.getBizNo(), e.getFlowId(), ext.getMsgId());
        } catch (Exception e) {
            // 基础设施异常：按重试次数决定「继续原地重试」或「落死信表后 ACK」
            handleConsumeFailure(ext, message, e);
        } finally {
            MDC.remove(TRACE_ID_KEY);
        }
    }

    /**
     * 消息体反序列化
     *
     * <p>解析失败视为毒消息（格式损坏，重试也不可能成功）：落死信表后返回 null，
     * 监听器据此直接 ACK。注意：任何从 onMessage 抛出的异常都会被 rocketmq-spring
     * 判定为消费失败并触发重投，因此毒消息路径【不能抛异常】，否则会形成
     * "重投 → 再解析失败 → 死信表重复插入"的循环。</p>
     *
     * @param ext 原生消息
     * @return 反序列化后的消息体；解析失败返回 null（消息已落死信表）
     */
    private TradeStateMessage parsePayload(MessageExt ext) {
        String body = new String(ext.getBody(), StandardCharsets.UTF_8);
        try {
            return objectMapper.readValue(body, TradeStateMessage.class);
        } catch (Exception e) {
            log.error("[消费者] 消息体解析失败（毒消息），已进入死信表并 ACK，msgId={}, body={}", ext.getMsgId(), body, e);
            saveDeadMessage(ext, null, body, "payload parse error: " + e.getMessage());
            return null;
        }
    }

    /**
     * 消费失败处理：重试次数未达上限则抛出异常触发 ORDERLY 原地重试；
     * 达到上限则落死信表并正常返回（ACK），解除队列阻塞
     *
     * <p>重试期间注意：apply 的事务已回滚（消费去重登记一并回滚），
     * 因此重试时消息不会被误判为重复。</p>
     *
     * @param ext     原生消息
     * @param message 消息体（可能为 null，见 parsePayload）
     * @param e       消费异常
     */
    private void handleConsumeFailure(MessageExt ext, TradeStateMessage message, Exception e) {
        int reconsumeTimes = ext.getReconsumeTimes();
        if (reconsumeTimes < MAX_RECONSUME_TIMES) {
            // 向上抛出 → ORDERLY 消费在当前队列内原地重试（阻塞后续消息，保证不乱序）
            log.warn("[消费者] 消息处理失败，第 {} 次重试（上限 {}），msgId={}, flowId={}",
                    reconsumeTimes + 1, MAX_RECONSUME_TIMES, ext.getMsgId(),
                    message == null ? null : message.getFlowId(), e);
            throw e instanceof RuntimeException ? (RuntimeException) e : new IllegalStateException(e);
        }
        // 重试耗尽：落死信表并 ACK，解除当前队列阻塞，等待人工/补偿任务处理
        String body = new String(ext.getBody(), StandardCharsets.UTF_8);
        saveDeadMessage(ext, message, body, "max reconsume exceeded, last error: " + e.getMessage());
        log.error("[消费者] 重试耗尽（{} 次），消息进入死信表并 ACK，flowId={}, bizNo={}, msgId={}",
                MAX_RECONSUME_TIMES,
                message == null ? null : message.getFlowId(),
                message == null ? null : message.getBizNo(),
                ext.getMsgId(), e);
    }

    /**
     * 保存死信记录
     *
     * <p>落表失败仅记录 ERROR 日志（此时消息已无法重试成功，
     * 只能依赖消费端日志排查），避免死信表故障反过来阻塞消费。</p>
     *
     * @param ext     原生消息
     * @param message 消息体（可能为 null）
     * @param body    原始消息体 JSON
     * @param errMsg  异常描述
     */
    private void saveDeadMessage(MessageExt ext, TradeStateMessage message, String body, String errMsg) {
        try {
            MqDeadMessage dead = new MqDeadMessage();
            dead.setMsgId(ext.getMsgId());
            dead.setFlowId(message == null ? null : message.getFlowId());
            dead.setBizNo(message == null ? null : message.getBizNo());
            dead.setReconsumeTimes(ext.getReconsumeTimes());
            dead.setMessageBody(body);
            // 截断异常信息，避免超出 VARCHAR(1024) 导致落表本身失败
            dead.setErrorMsg(errMsg.length() > 1000 ? errMsg.substring(0, 1000) : errMsg);
            dead.setCreateTime(new Date());
            mqDeadMessageMapper.insert(dead);
        } catch (Exception ex) {
            log.error("[消费者] 死信记录落表失败（消息仅存在于本日志中，需人工介入），msgId={}", ext.getMsgId(), ex);
        }
    }
}
