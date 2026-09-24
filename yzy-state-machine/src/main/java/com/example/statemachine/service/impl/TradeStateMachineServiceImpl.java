package com.example.statemachine.service.impl;

import com.example.common.enums.TradeEventEnum;
import com.example.common.enums.TradeStateEnum;
import com.example.statemachine.dto.TradeStateMessage;
import com.example.statemachine.entity.MqConsumeRecord;
import com.example.statemachine.entity.MqPendingEvent;
import com.example.statemachine.entity.TradeOrderState;
import com.example.statemachine.exception.DuplicateMessageException;
import com.example.statemachine.mapper.MqConsumeRecordMapper;
import com.example.statemachine.mapper.MqPendingEventMapper;
import com.example.statemachine.mapper.TradeOrderStateMapper;
import com.example.statemachine.service.TradeStateMachineService;
import lombok.extern.slf4j.Slf4j;
import org.springframework.dao.DuplicateKeyException;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import javax.annotation.Resource;
import java.util.Date;
import java.util.List;

/**
 * 订单状态机服务实现
 *
 * <p><b>消息顺序性设计（三层保证 + 乱序治理）：</b></p>
 * <ol>
 *   <li>生产端：yzy-demo 以 bizNo 作为 hashKey 发送顺序消息，
 *       同一 bizNo 的消息路由到同一 MessageQueue；</li>
 *   <li>消费端：@RocketMQMessageListener(consumeMode = ConsumeMode.ORDERLY)
 *       队列内单线程顺序消费——注意 ORDERLY 只保证「按入队顺序消费」，
 *       入队顺序本身可能因并发请求/网络延迟/发送重试与业务真实顺序不符；</li>
 *   <li>DB 兜底：状态流转使用条件更新（CAS 语义），乱序消息永远无法破坏状态。</li>
 * </ol>
 *
 * <p><b>乱序治理（超前暂存 + 过期丢弃 + 回放补齐）：</b></p>
 * <p>当事件与当前状态不匹配（非法流转）时，按事件合法前置状态（event.from）
 * 与当前状态的链路序号（order）分三类处理：</p>
 * <table border="1">
 *   <tr><th>情形</th><th>判定</th><th>处理</th></tr>
 *   <tr><td>from == current</td><td>正常流转</td><td>CAS 流转 + 回放 pending</td></tr>
 *   <tr><td>from.order &gt; current.order</td><td>超前事件（如 PAY 在路上，FINISH 先到）</td><td>暂存 mq_pending_event + ACK，状态追上后回放</td></tr>
 *   <tr><td>from.order &lt; current.order</td><td>过期事件（历史流转已完成，典型于重放）</td><td>warn 日志 + ACK 丢弃</td></tr>
 * </table>
 *
 * <p><b>消息级防重复设计（mq_consume_record）：</b>RocketMQ 是 at-least-once 投递，
 * 消费完成但 ACK 前宕机/超时会导致消息重投。本服务在状态流转<b>同一事务内</b>
 * 先登记消费记录（uk_flow_id 唯一索引）：重复投递命中索引 → 明确判定为
 * 【重复消息】跳过；处理失败回滚 → 登记一并回滚 → 重试时不会误判。</p>
 *
 * <p><b>状态记录懒创建：</b>首条消息到达时插入 INIT 状态记录（uk_biz_no 唯一索引），
 * 并发场景下插入冲突（DuplicateKeyException）视为记录已存在，回读后继续流转。</p>
 *
 * @author yzy
 * @version 1.1
 */
@Slf4j
@Service
public class TradeStateMachineServiceImpl implements TradeStateMachineService {

    @Resource
    private TradeOrderStateMapper tradeOrderStateMapper;

    /** 消费去重表 Mapper（消息级幂等，与状态流转同事务登记） */
    @Resource
    private MqConsumeRecordMapper mqConsumeRecordMapper;

    /** 乱序超前事件暂存表 Mapper */
    @Resource
    private MqPendingEventMapper mqPendingEventMapper;

    /**
     * 处理状态消息（事务内完成：消费去重登记 + 懒建记录 + 流转判定 + 回放）
     *
     * <p>异常约定：业务性处理（重复/超前/过期/未知事件）记录日志后正常 ACK；
     * 基础设施异常（DB 不可用等）向上抛出，交由监听器的重试/死信机制处理。</p>
     *
     * @param message 状态机消息
     */
    @Override
    @Transactional(rollbackFor = Exception.class)
    public void apply(TradeStateMessage message) {
        // ---------- 0. 必填字段防御性校验 ----------
        // flowId/bizNo/event 缺失的消息无法去重、无法定位业务单号，属于畸形消息：
        // 直接 ACK 丢弃（error 日志），不能抛异常——否则会撞 mq_consume_record 的
        // NOT NULL 约束，被误判为基础设施异常白白重试 3 次后才进死信表
        if (message.getFlowId() == null || isBlank(message.getBizNo()) || isBlank(message.getEvent())) {
            log.error("[状态机] 畸形消息（必填字段缺失），丢弃，flowId={}, bizNo={}, event={}",
                    message.getFlowId(), message.getBizNo(), message.getEvent());
            return;
        }

        // ---------- 1. 消息级去重登记（与状态流转同事务） ----------
        registerConsumeRecord(message);

        // ---------- 2. 事件解析 ----------
        TradeEventEnum event = TradeEventEnum.of(message.getEvent());
        if (event == null) {
            log.warn("[状态机] 未知事件，消息丢弃，bizNo={}, event={}", message.getBizNo(), message.getEvent());
            return;
        }

        // ---------- 3. 懒创建状态记录（首条消息） ----------
        TradeOrderState state = ensureStateRecord(message.getBizNo());
        TradeStateEnum current = TradeStateEnum.of(state.getState());
        if (current == null) {
            log.error("[状态机] 状态记录脏数据，无法解析，bizNo={}, state={}", message.getBizNo(), state.getState());
            return;
        }

        // ---------- 4. 三类流转判定（正常 / 超前 / 过期） ----------
        if (event.matches(current)) {
            // 4a. 正常流转：CAS 条件更新 + 流转后回放暂存的超前事件
            casTransition(message.getBizNo(), current, event.getTo(), message.getFlowId());
            replayPendingEvents(message.getBizNo());
        } else if (event.getFrom().isAfter(current)) {
            // 4b. 超前事件：状态还没走到本事件的前置状态（如 FINISH 先于 PAY 入队）。
            // 丢弃会丢单、重试会阻塞队列死锁，唯一正确解法：暂存 + ACK，等状态追上后回放
            stashPendingEvent(message, current, event);
        } else {
            // 4c. 过期事件：事件的前置状态早于当前状态（对应流转历史上已发生过），
            // 典型于消息重放。注意与"重复消息"区分：重复已被第 1 步去重表拦截，
            // 走到这里的是不同 flowId 的同型事件重放
            log.warn("[状态机] 过期事件丢弃，bizNo={}, 当前状态={}, 事件={}, 事件合法前置状态={}, flowId={}",
                    message.getBizNo(), current, event, event.getFrom(), message.getFlowId());
        }
    }

    /**
     * CAS 条件流转：仅当当前状态等于预期前置状态时更新
     *
     * @param bizNo  业务单号
     * @param from   预期前置状态
     * @param to     目标状态
     * @param flowId 触发本次流转的报文流水ID（日志追踪）
     */
    private void casTransition(String bizNo, TradeStateEnum from, TradeStateEnum to, Long flowId) {
        int rows = tradeOrderStateMapper.casUpdateState(bizNo, from.name(), to.name());
        if (rows == 0) {
            // 理论上顺序消费 + 去重后不会走到这里；走到说明发生了并发修改，记录告警便于排查
            log.warn("[状态机] 条件更新影响 0 行（并发修改），bizNo={}, 预期前置状态={}, 目标状态={}, flowId={}",
                    bizNo, from, to, flowId);
            return;
        }
        log.info("[状态机] 状态流转成功，bizNo={}, {} --> {}, flowId={}", bizNo, from, to, flowId);
    }

    /**
     * 暂存超前事件到 mq_pending_event
     *
     * <p>uk_flow_id 唯一索引防止重复暂存（at-least-once 重投的同一消息
     * 会在去重表被拦截，此处兜底防御人工/补偿重放场景）。
     * 暂存后正常返回（ACK），不阻塞队列。</p>
     *
     * @param message 超前事件消息
     * @param current 当前状态（超前：event.from 在 current 之后）
     * @param event   事件枚举
     */
    private void stashPendingEvent(TradeStateMessage message, TradeStateEnum current, TradeEventEnum event) {
        MqPendingEvent pending = new MqPendingEvent();
        pending.setBizNo(message.getBizNo());
        pending.setFlowId(message.getFlowId());
        pending.setEvent(message.getEvent());
        pending.setMessageBody(message.getMessageBody());
        pending.setTraceId(message.getTraceId());
        pending.setMsgId(message.getMsgId());
        pending.setCreateTime(new Date());
        try {
            mqPendingEventMapper.insert(pending);
            log.info("[状态机] 超前事件暂存（等待状态追上后回放），bizNo={}, 当前状态={}, 事件={}, 前置状态={}, flowId={}",
                    message.getBizNo(), current, event, event.getFrom(), message.getFlowId());
        } catch (DuplicateKeyException e) {
            log.info("[状态机] 超前事件重复暂存被忽略（uk_flow_id），bizNo={}, flowId={}",
                    message.getBizNo(), message.getFlowId());
        }
    }

    /**
     * 回放暂存的超前事件：每次正常流转后调用
     *
     * <p>算法：按 flow_id 升序取出该单号的全部暂存事件，循环尝试应用——
     * 事件的合法前置状态等于当前状态则 CAS 流转并删除暂存记录，
     * 状态前移后继续下一轮，直到一轮内无任何进展（剩余事件仍是超前的，
     * 等待后续事件推进状态）。单号暂存事件通常 0-2 条，循环开销可忽略。</p>
     *
     * <p>幂等性：CAS 条件更新保证重复回放不会破坏状态；回放与触发它的
     * 正常流转在同一事务内，失败一起回滚。</p>
     *
     * @param bizNo 业务单号
     */
    private void replayPendingEvents(String bizNo) {
        boolean progressed = true;
        while (progressed) {
            progressed = false;
            List<MqPendingEvent> pendings = mqPendingEventMapper.selectByBizNo(bizNo);
            if (pendings.isEmpty()) {
                return;
            }
            TradeOrderState state = tradeOrderStateMapper.selectByBizNo(bizNo);
            TradeStateEnum current = TradeStateEnum.of(state.getState());
            if (current == null) {
                log.error("[状态机] 回放时状态解析失败，暂停回放，bizNo={}", bizNo);
                return;
            }
            for (MqPendingEvent pending : pendings) {
                TradeEventEnum event = TradeEventEnum.of(pending.getEvent());
                if (event == null || !event.matches(current)) {
                    continue;
                }
                int rows = tradeOrderStateMapper.casUpdateState(bizNo, current.name(), event.getTo().name());
                if (rows > 0) {
                    mqPendingEventMapper.deleteById(pending.getId());
                    log.info("[状态机] 暂存事件回放成功，bizNo={}, {} --{}--> {}, flowId={}",
                            bizNo, current, event, event.getTo(), pending.getFlowId());
                    current = event.getTo();
                    progressed = true;
                }
            }
        }
    }

    /**
     * 消费去重登记：mq_consume_record 插入成功 = 首次消费；唯一索引冲突 = 重复消息
     *
     * <p>关键点：本方法在 apply 的事务内执行——
     * 状态流转失败 → 事务回滚 → 登记记录一并回滚 → 消息重试时不会被误判为重复。</p>
     *
     * @param message 状态机消息
     */
    private void registerConsumeRecord(TradeStateMessage message) {
        MqConsumeRecord record = new MqConsumeRecord();
        record.setFlowId(message.getFlowId());
        record.setBizNo(message.getBizNo());
        record.setEvent(message.getEvent());
        record.setMsgId(message.getMsgId());
        record.setConsumeTime(new Date());
        try {
            mqConsumeRecordMapper.insert(record);
        } catch (DuplicateKeyException e) {
            // 重复消息：典型于"处理成功但 ACK 前宕机/超时"导致的 at-least-once 重投
            log.info("[状态机] 重复消息判定（消费去重命中 uk_flow_id），跳过处理，bizNo={}, flowId={}, msgId={}",
                    message.getBizNo(), message.getFlowId(), record.getMsgId());
            throw new DuplicateMessageException(message.getBizNo(), message.getFlowId());
        }
    }

    /**
     * 判空工具（避免引入额外依赖）
     *
     * @param s 字符串
     * @return true = null 或空串
     */
    private boolean isBlank(String s) {
        return s == null || s.isEmpty();
    }

    /**
     * 确保状态记录存在：不存在则插入 INIT 记录，存在则直接返回
     *
     * <p>并发兜底：uk_biz_no 唯一索引保证同一 bizNo 只有一条状态记录，
     * DuplicateKeyException 说明记录已被并发请求创建，回读即可。</p>
     *
     * @param bizNo 业务单号
     * @return 状态记录
     */
    private TradeOrderState ensureStateRecord(String bizNo) {
        TradeOrderState state = tradeOrderStateMapper.selectByBizNo(bizNo);
        if (state != null) {
            return state;
        }
        TradeOrderState created = new TradeOrderState();
        created.setBizNo(bizNo);
        created.setState(TradeStateEnum.INIT.name());
        created.setVersion(0);
        created.setCreateTime(new Date());
        created.setUpdateTime(new Date());
        try {
            tradeOrderStateMapper.insert(created);
            log.info("[状态机] 状态记录懒创建成功，bizNo={}, state=INIT", bizNo);
            return created;
        } catch (DuplicateKeyException e) {
            // 并发创建冲突：记录已存在，回读
            log.info("[状态机] 状态记录并发创建冲突，回读已有记录，bizNo={}", bizNo);
            return tradeOrderStateMapper.selectByBizNo(bizNo);
        }
    }
}
