package com.example.service.impl;

import com.example.common.enums.TradeEventEnum;
import com.example.common.enums.TradeStateEnum;
import com.example.common.trace.TraceIdUtil;
import com.example.dto.TradeStateMessage;
import com.example.dto.TradeSubmitDTO;
import com.example.entity.TradeMessageFlow;
import com.example.mapper.TradeMessageFlowMapper;
import com.example.service.IdempotentService;
import com.example.service.SubmitResult;
import com.example.service.TradeService;
import lombok.extern.slf4j.Slf4j;
import org.apache.rocketmq.spring.core.RocketMQTemplate;
import org.apache.rocketmq.spring.support.RocketMQHeaders;
import org.springframework.dao.DuplicateKeyException;
import org.springframework.messaging.Message;
import org.springframework.messaging.support.MessageBuilder;
import org.springframework.stereotype.Service;
import org.springframework.transaction.PlatformTransactionManager;
import org.springframework.transaction.support.TransactionTemplate;

import javax.annotation.PostConstruct;
import javax.annotation.Resource;
import java.util.Date;

/**
 * 交易中心交易服务实现（幂等防线 + 乱序入口预检 + 顺序消息生产者）
 *
 * <p><b>幂等防线：</b></p>
 * <ol>
 *   <li>Redis 原子命令 {@code SET 幂等key 1 EX 259200 NX}——拦截绝大多数重复请求；</li>
 *   <li>DB 事务插入报文流水表（uk_idem_key 唯一索引）——拦截并发穿透
 *       （DuplicateKeyException 判定为重复请求）；</li>
 *   <li>状态机端 biz_no 唯一 + 条件更新——拦截消息重复/乱序对状态的破坏。</li>
 * </ol>
 *
 * <p><b>乱序入口预检（防线A）：</b>顺序消息只保证"按入队顺序消费"，但并发请求/
 * 网络延迟/发送重试会导致入队顺序与业务真实顺序不符。本服务在受理时先校验
 * 「事件与订单当前状态是否匹配」（规则与状态机共用 common 中的
 * {@link TradeEventEnum}，单一事实来源），乱序请求直接返回状态冲突、不进 MQ——
 * 把乱序治理前移到入口。残留的"预检通过到消费前"竞态窗口由状态机端的
 * 超前暂存 + 回放（防线B，mq_pending_event）兜底。</p>
 *
 * <p><b>异常约定（与需求 2.3 对齐）：</b>事务回滚后【不主动删除 Redis 幂等 key】，
 * 等待 3 天自动过期——失败重试窗口内同一幂等 key 的请求会被直接判重，防止异常
 * 场景下重复请求反复冲击下游。</p>
 *
 * <p><b>顺序消息设计：</b>以 bizNo 作为 hashKey，RocketMQ 将同一 bizNo 的消息
 * 路由到同一 MessageQueue；发送动作放在事务提交之后（避免事务回滚产生脏消息）。
 * 后续可升级为 RocketMQ 事务消息（half message + 本地事务回查）进一步保证
 * “DB 落库”与“消息发送”的最终一致性。</p>
 *
 * @author yzy
 * @version 1.1
 */
@Slf4j
@Service
public class TradeServiceImpl implements TradeService {

    /** MQ 目标 topic（与消费端 yzy-state-machine 保持一致） */
    private static final String TRADE_STATE_TOPIC = "yzy-trade-topic";

    @Resource
    private IdempotentService idempotentService;

    @Resource
    private TradeMessageFlowMapper tradeMessageFlowMapper;

    @Resource
    private RocketMQTemplate rocketMQTemplate;

    /** Spring 事务管理器（MyBatis-Plus + MySQL 自动装配 DataSourceTransactionManager） */
    @Resource
    private PlatformTransactionManager transactionManager;

    /** 编程式事务模板：显式控制事务边界，避免 @Transactional 自调用代理失效问题 */
    private TransactionTemplate transactionTemplate;

    /**
     * 初始化编程式事务模板
     */
    @PostConstruct
    public void init() {
        this.transactionTemplate = new TransactionTemplate(transactionManager);
    }

    /**
     * 交易报文提交主流程
     *
     * <p>流程：① 参数校验（Controller @Valid）→ ② Redis SET NX 幂等校验
     * → ③ 入口状态预检（乱序拦截，防线A）→ ④ 事务插入报文流水（唯一索引兜底）
     * → ⑤ 事务提交后按 bizNo 发送顺序消息。</p>
     *
     * @param dto 交易报文提交请求
     * @return 受理结果（见 {@link SubmitResult}）
     */
    @Override
    public SubmitResult submit(TradeSubmitDTO dto) {
        // ---------- 第 1 步：Redis 原子幂等校验 ----------
        // SET idem:trade:{idemKey} 1 EX 259200 NX
        // 返回 false（key 已存在）→ 直接判定重复请求，终止流程
        if (!idempotentService.tryAcquire(dto.getIdemKey())) {
            log.warn("[交易中心] 重复请求（Redis幂等拦截），idemKey={}, bizNo={}", dto.getIdemKey(), dto.getBizNo());
            return SubmitResult.DUPLICATE;
        }

        // ---------- 第 2 步：入口状态预检（乱序拦截，防线A） ----------
        SubmitResult precheck = checkStateConflict(dto);
        if (precheck != null) {
            return precheck;
        }

        // ---------- 第 3 步：DB 事务插入报文流水表 ----------
        TradeMessageFlow flow = buildFlow(dto);
        try {
            // 编程式事务：插入成功则提交；抛异常则回滚
            transactionTemplate.executeWithoutResult(status -> tradeMessageFlowMapper.insert(flow));
            log.info("[交易中心] 报文流水落库成功，flowId={}, idemKey={}, bizNo={}, event={}",
                    flow.getId(), dto.getIdemKey(), dto.getBizNo(), dto.getEvent());
        } catch (DuplicateKeyException e) {
            // ---------- 并发穿透兜底：uk_idem_key 唯一索引冲突 ----------
            // 典型场景：Redis 幂等 key 恰好过期/被删除后，同一幂等 key 的两个请求并发进来，
            // 双双通过 Redis 校验，由 DB 唯一索引完成最后拦截
            log.warn("[交易中心] 重复请求（DB唯一索引拦截并发穿透），idemKey={}, bizNo={}", dto.getIdemKey(), dto.getBizNo());
            return SubmitResult.DUPLICATE;
        } catch (Exception e) {
            // ---------- 其他异常：事务回滚；不删除 Redis 幂等 key，等待 3 天自动过期 ----------
            log.error("[交易中心] 报文流水落库失败，事务已回滚（不删除Redis幂等key，等待3天过期），idemKey={}, bizNo={}",
                    dto.getIdemKey(), dto.getBizNo(), e);
            throw e;
        }

        // ---------- 第 4 步：事务提交成功后，发送顺序消息（hashKey = bizNo） ----------
        sendOrderlyMessage(flow);
        return SubmitResult.ACCEPTED;
    }

    /**
     * 入口状态预检（乱序拦截，防线A）
     *
     * <p>数据源选择（关键设计）：查<b>流水表</b>该单号最新已受理事件，推导"在途状态"
     * （最新事件的 to 状态）——而非查 trade_order_state（消费后状态）。原因：
     * 消息消费存在延迟（秒级到分钟级），若预检读消费后状态，"连续快速提交同一单号
     * 的多个事件"（上一事件尚未消费）会被误判乱序拒绝，这属于正常业务不能拒。
     * 流水表是受理视角，落库即生效，在途状态永远不落后于受理进度，
     * 也天然单调（每受理一个合法事件，在途状态前移一格）。</p>
     *
     * <p>规则来源：与状态机共用 common 中的 {@link TradeEventEnum}（单一事实来源），
     * 不会出现"入口放行、消费端拒绝"的规则漂移。</p>
     *
     * <p>竞态窗口说明：预检通过到消息被消费之间仍可能发生并发受理（两个请求同时
     * 通过预检），该窗口由消费端防线B（超前暂存 + 回放）与流水表 uk_idem_key 兜底。</p>
     *
     * @param dto 交易报文提交请求
     * @return null = 预检通过；STATE_CONFLICT = 乱序拒绝
     */
    private SubmitResult checkStateConflict(TradeSubmitDTO dto) {
        TradeEventEnum event = TradeEventEnum.of(dto.getEvent());
        if (event == null) {
            // 未知事件：参数错误语义，按状态冲突拒绝（参数校验层只校验了非空）
            log.warn("[交易中心] 未知事件被拒绝，bizNo={}, event={}", dto.getBizNo(), dto.getEvent());
            return SubmitResult.STATE_CONFLICT;
        }
        String latestEvent = tradeMessageFlowMapper.selectLatestEventByBizNo(dto.getBizNo());
        if (latestEvent == null) {
            // 该单号尚无任何已受理事件（首笔）：仅允许 CREATE 进入
            if (event != TradeEventEnum.TRADE_CREATE) {
                log.warn("[交易中心] 乱序拒绝（订单尚未创建），bizNo={}, event={}", dto.getBizNo(), dto.getEvent());
                return SubmitResult.STATE_CONFLICT;
            }
            return null;
        }
        // 在途状态 = 最新已受理事件的目标状态
        TradeEventEnum latest = TradeEventEnum.of(latestEvent);
        if (latest == null) {
            log.error("[交易中心] 流水表事件脏数据，拒绝受理，bizNo={}, latestEvent={}", dto.getBizNo(), latestEvent);
            return SubmitResult.STATE_CONFLICT;
        }
        TradeStateEnum current = latest.getTo();
        if (!event.matches(current)) {
            log.warn("[交易中心] 乱序拒绝（状态冲突），bizNo={}, 在途状态={}, 事件={}, 事件合法前置状态={}",
                    dto.getBizNo(), current, event, event.getFrom());
            return SubmitResult.STATE_CONFLICT;
        }
        return null;
    }

    /**
     * 构建报文流水记录
     *
     * <p>send_status 初始为 SENDING：落库成功即代表"待发送"，
     * 发送结果由 {@link #sendOrderlyMessage} 回写为 SENT / SEND_FAILED。</p>
     *
     * @param dto 交易报文提交请求
     * @return 报文流水实体
     */
    private TradeMessageFlow buildFlow(TradeSubmitDTO dto) {
        TradeMessageFlow flow = new TradeMessageFlow();
        flow.setIdemKey(dto.getIdemKey());
        flow.setBizNo(dto.getBizNo());
        flow.setEvent(dto.getEvent());
        flow.setMessageBody(dto.getMessageBody());
        flow.setTraceId(TraceIdUtil.getTraceId());
        flow.setSendStatus(TradeMessageFlow.SEND_STATUS_SENDING);
        flow.setCreateTime(new Date());
        return flow;
    }

    /**
     * 发送顺序消息到状态机服务（含防丢失处理）
     *
     * <p><b>顺序性保证：</b>syncSendOrderly 的第三个参数 hashKey = bizNo，
     * RocketMQ 对 hashKey 取模选择 MessageQueue，同一 bizNo 的消息必然进入同一队列，
     * 由消费端 ConsumeMode.ORDERLY 保证队列内严格按发送顺序消费。</p>
     *
     * <p><b>消息 KEY 设置：</b>将消息 KEYS 设为幂等 key，broker 端可按 key
     * 快速检索消息轨迹，便于与流水表对账。</p>
     *
     * <p><b>防丢失设计（重要）：</b>发送动作在事务提交之后，任何重试都无法做到
     * 100% 可靠（进程崩溃即丢失）。因此采用"状态回写 + 对账补偿"模式：</p>
     * <ol>
     *   <li>发送前流水已带 send_status=SENDING 落库；</li>
     *   <li>发送成功 → 回写 SENT；</li>
     *   <li>重试 2 次仍失败 → 回写 SEND_FAILED 并打 ERROR 日志，
     *       由对账任务扫描 SEND_FAILED 流水人工/自动补偿；
     *       注意补偿必须按 flowId 顺序重发同一 bizNo 的消息，否则会破坏顺序性。</li>
     * </ol>
     *
     * @param flow 报文流水记录（已落库）
     */
    private void sendOrderlyMessage(TradeMessageFlow flow) {
        TradeStateMessage message = buildStateMessage(flow);
        Message<TradeStateMessage> msg =
                MessageBuilder.withPayload(message)
                        // 消息 KEYS = 幂等 key：broker 端可按 key 查询消息轨迹，便于对账
                        .setHeader(RocketMQHeaders.KEYS, flow.getIdemKey())
                        .build();

        // 最多尝试 2 次：syncSendOrderly 内部已有 broker 级重试，此处仅补偿瞬时网络抖动
        for (int attempt = 1; attempt <= 2; attempt++) {
            try {
                rocketMQTemplate.syncSendOrderly(TRADE_STATE_TOPIC, msg, flow.getBizNo());
                updateSendStatus(flow.getId(), TradeMessageFlow.SEND_STATUS_SENT);
                log.info("[交易中心] 顺序消息发送成功，topic={}, hashKey={}, flowId={}, event={}, attempt={}",
                        TRADE_STATE_TOPIC, flow.getBizNo(), flow.getId(), flow.getEvent(), attempt);
                return;
            } catch (Exception e) {
                log.error("[交易中心] 顺序消息发送失败，topic={}, flowId={}, attempt={}",
                        TRADE_STATE_TOPIC, flow.getId(), attempt, e);
            }
        }
        // 重试耗尽：回写 SEND_FAILED 供对账补偿。此时流水已落库、Redis key 已存在，
        // 同 idemKey 的后续请求会被判重——必须由补偿流程重发，不能放行新请求
        updateSendStatus(flow.getId(), TradeMessageFlow.SEND_STATUS_FAILED);
        log.error("[交易中心] 顺序消息重试耗尽，流水标记 SEND_FAILED 等待对账补偿，flowId={}, bizNo={}, idemKey={}",
                flow.getId(), flow.getBizNo(), flow.getIdemKey());
    }

    /**
     * 构建状态机消息体
     *
     * @param flow 报文流水记录（已落库）
     * @return MQ 消息体
     */
    private TradeStateMessage buildStateMessage(TradeMessageFlow flow) {
        TradeStateMessage message = new TradeStateMessage();
        message.setBizNo(flow.getBizNo());
        message.setEvent(flow.getEvent());
        message.setMessageBody(flow.getMessageBody());
        message.setTraceId(flow.getTraceId());
        message.setFlowId(flow.getId());
        message.setOccurredAt(System.currentTimeMillis());
        return message;
    }

    /**
     * 回写消息发送状态
     *
     * <p>注意：此更新在原事务之外（发送发生在事务提交后），失败仅记录告警——
     * 状态不准只影响对账效率，不影响幂等与顺序性正确性（消费端还有去重与 CAS 兜底）。</p>
     *
     * @param flowId 报文流水ID
     * @param status 目标发送状态
     */
    private void updateSendStatus(Long flowId, String status) {
        try {
            TradeMessageFlow update = new TradeMessageFlow();
            update.setId(flowId);
            update.setSendStatus(status);
            tradeMessageFlowMapper.updateById(update);
        } catch (Exception e) {
            log.error("[交易中心] 发送状态回写失败（不影响业务正确性，仅影响对账），flowId={}, status={}", flowId, status, e);
        }
    }
}
