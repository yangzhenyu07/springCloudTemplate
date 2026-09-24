package com.example.common.enums;

/**
 * 订单状态机 - 交易事件枚举（yzy-demo 入口预检与 yzy-state-machine 消费流转共用）
 *
 * <p>定义每个事件唯一合法的「前置状态 → 目标状态」迁移规则。
 * <b>规则单一事实来源</b>：入口预检（yzy-demo）与状态机流转（yzy-state-machine）
 * 共用本枚举，避免两套规则漂移导致"入口放行、消费端拒绝"或反之。</p>
 *
 * @author yzy
 * @version 1.0
 */
public enum TradeEventEnum {

    /** 交易创建：INIT → CREATED */
    TRADE_CREATE(TradeStateEnum.INIT, TradeStateEnum.CREATED),

    /** 交易支付：CREATED → PAID */
    TRADE_PAY(TradeStateEnum.CREATED, TradeStateEnum.PAID),

    /** 交易完成：PAID → FINISHED */
    TRADE_FINISH(TradeStateEnum.PAID, TradeStateEnum.FINISHED);

    /** 允许触发本事件的前置状态 */
    private final TradeStateEnum from;

    /** 本事件触发的目标状态 */
    private final TradeStateEnum to;

    TradeEventEnum(TradeStateEnum from, TradeStateEnum to) {
        this.from = from;
        this.to = to;
    }

    public TradeStateEnum getFrom() {
        return from;
    }

    public TradeStateEnum getTo() {
        return to;
    }

    /**
     * 判断「当前状态 + 事件」是否为一次合法流转
     *
     * @param current 当前状态
     * @return true = 合法流转
     */
    public boolean matches(TradeStateEnum current) {
        return this.from == current;
    }

    /**
     * 按名称解析事件（容错：null / 非法名称返回 null）
     *
     * @param name 事件名称
     * @return 对应枚举，未匹配返回 null
     */
    public static TradeEventEnum of(String name) {
        if (name == null || name.isEmpty()) {
            return null;
        }
        for (TradeEventEnum event : values()) {
            if (event.name().equals(name)) {
                return event;
            }
        }
        return null;
    }
}
