package com.example.common.enums;

/**
 * 订单状态机 - 状态枚举（yzy-demo 入口预检与 yzy-state-machine 消费流转共用）
 *
 * <p>状态流转主链路（单向、不可逆）：</p>
 * <pre>
 *   INIT ──TRADE_CREATE──▶ CREATED ──TRADE_PAY──▶ PAID ──TRADE_FINISH──▶ FINISHED
 * </pre>
 *
 * <p><b>order 序号的用途（乱序治理关键）：</b>消费端收到非法流转消息时，
 * 通过事件合法前置状态与当前状态的 order 比较区分两类乱序：</p>
 * <ul>
 *   <li>前置状态 order &gt; 当前状态 order：该事件<b>超前</b>到达（如 PAY 还在路上，
 *       FINISH 先到）→ 暂存 pending 表等状态追上后回放，事件不丢；</li>
 *   <li>前置状态 order &lt; 当前状态 order：该事件<b>过期</b>（对应流转历史上已发生过，
 *       典型于重放）→ 丢弃并告警。</li>
 * </ul>
 *
 * @author yzy
 * @version 1.0
 */
public enum TradeStateEnum {

    /** 初始状态：状态记录懒创建后的默认状态 */
    INIT(0),

    /** 已创建：TRADE_CREATE 事件流转后的状态 */
    CREATED(1),

    /** 已支付：TRADE_PAY 事件流转后的状态 */
    PAID(2),

    /** 已完成：终态，TRADE_FINISH 事件流转后的状态 */
    FINISHED(3);

    /** 状态在主链路上的序号，用于乱序场景判断事件"超前/过期" */
    private final int order;

    TradeStateEnum(int order) {
        this.order = order;
    }

    public int getOrder() {
        return order;
    }

    /**
     * 判断本状态是否位于目标状态之后（链路上更靠后）
     *
     * @param other 目标状态
     * @return true = 本状态在目标状态之后
     */
    public boolean isAfter(TradeStateEnum other) {
        return this.order > other.order;
    }

    /**
     * 按名称解析状态（容错：null / 非法名称返回 null）
     *
     * @param name 状态名称
     * @return 对应枚举，未匹配返回 null
     */
    public static TradeStateEnum of(String name) {
        if (name == null || name.isEmpty()) {
            return null;
        }
        for (TradeStateEnum state : values()) {
            if (state.name().equals(name)) {
                return state;
            }
        }
        return null;
    }
}
