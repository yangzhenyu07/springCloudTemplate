package com.example.statemachine.controller;

import com.example.common.result.Result;
import com.example.common.trace.TraceIdUtil;
import com.example.statemachine.entity.TradeOrderState;
import com.example.statemachine.mapper.TradeOrderStateMapper;
import lombok.extern.slf4j.Slf4j;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import javax.annotation.Resource;

/**
 * 订单状态查询接口（供集成测试与对账使用）
 *
 * @author yzy
 * @version 1.0
 */
@Slf4j
@RestController
@RequestMapping("api/state")
public class TradeStateQueryController {

    @Resource
    private TradeOrderStateMapper tradeOrderStateMapper;

    /**
     * 按业务单号查询状态机当前状态
     *
     * @param bizNo 业务单号
     * @return 状态记录（不存在时返回失败提示）
     */
    @GetMapping("/order/{bizNo}")
    public Result<TradeOrderState> queryState(@PathVariable("bizNo") String bizNo) {
        String traceId = TraceIdUtil.getTraceId();
        TradeOrderState state = tradeOrderStateMapper.selectByBizNo(bizNo);
        if (state == null) {
            Result<TradeOrderState> r = Result.failed("订单状态不存在，bizNo=" + bizNo);
            r.setTraceId(traceId);
            return r;
        }
        Result<TradeOrderState> r = Result.success(state);
        r.setTraceId(traceId);
        return r;
    }
}
