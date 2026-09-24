package com.example.service;

/**
 * 交易报文提交结果枚举
 *
 * <p>三种受理结局的语义严格区分，Controller 据此映射不同的响应码与提示：</p>
 * <ul>
 *   <li>{@link #ACCEPTED}：受理成功，流水落库、消息已发；</li>
 *   <li>{@link #DUPLICATE}：重复请求（Redis 幂等层或 DB 唯一索引拦截）；</li>
 *   <li>{@link #STATE_CONFLICT}：状态冲突——事件与订单当前状态不匹配
 *       （乱序操作，防线A拦截），乱序请求不进 MQ。</li>
 * </ul>
 *
 * @author yzy
 * @version 1.0
 */
public enum SubmitResult {

    /** 受理成功 */
    ACCEPTED,

    /** 重复请求（幂等拦截） */
    DUPLICATE,

    /** 状态冲突（乱序操作被入口预检拒绝，未进 MQ） */
    STATE_CONFLICT
}
