package com.example.statemachine.service;

import com.example.statemachine.dto.TradeStateMessage;

/**
 * 订单状态机服务接口
 *
 * @author yzy
 * @version 1.0
 */
public interface TradeStateMachineService {

    /**
     * 处理状态消息：懒创建 INIT 状态记录 → 状态机规则校验 → 条件更新流转
     *
     * @param message 状态机消息
     */
    void apply(TradeStateMessage message);
}
