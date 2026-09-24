package com.example.statemachine.controller;

import com.example.common.result.Result;
import com.example.common.trace.TraceIdUtil;
import com.example.statemachine.dto.TradeStateMessage;
import com.example.statemachine.service.TradeStateMachineService;
import lombok.extern.slf4j.Slf4j;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import javax.annotation.Resource;

/**
 * 状态机调试接口（仅测试/运维使用）
 *
 * <p>用途：绕过 MQ 直接调用状态机 apply，用于</p>
 * <ul>
 *   <li>集成测试模拟「乱序消息」（真实 MQ 无法从外部控制入队顺序）；</li>
 *   <li>线上问题排查时手工重放某条消息验证状态机行为。</li>
 * </ul>
 *
 * <p>注意：本接口等价于一次 MQ 消费，会走去重登记、暂存、回放全流程；
 * 生产环境应通过网关鉴权屏蔽外部访问。</p>
 *
 * @author yzy
 * @version 1.0
 */
@Slf4j
@RestController
@RequestMapping("api/state/debug")
public class TradeStateDebugController {

    @Resource
    private TradeStateMachineService tradeStateMachineService;

    /**
     * 模拟一次状态机消费（绕过 MQ）
     *
     * @param message 状态机消息体（bizNo/event/flowId 必填）
     * @return 处理结果
     */
    @PostMapping("/apply")
    public Result<String> apply(@RequestBody TradeStateMessage message) {
        String traceId = TraceIdUtil.getTraceId();
        message.setTraceId(traceId);
        log.info("[调试] 直调状态机 apply，bizNo={}, event={}, flowId={}",
                message.getBizNo(), message.getEvent(), message.getFlowId());
        try {
            tradeStateMachineService.apply(message);
            Result<String> r = Result.success("处理完成");
            r.setTraceId(traceId);
            return r;
        } catch (Exception e) {
            // 重复消息会以 DuplicateMessageException 抛出（属正常业务信号，非错误）
            log.warn("[调试] apply 抛出异常（重复消息属正常信号），bizNo={}, event={}, msg={}",
                    message.getBizNo(), message.getEvent(), e.getMessage());
            Result<String> r = Result.failed("处理信号: " + e.getMessage());
            r.setTraceId(traceId);
            return r;
        }
    }
}
