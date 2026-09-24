package com.example.service;

import com.example.dto.TradeSubmitDTO;

/**
 * 交易中心交易服务接口
 *
 * @author yzy
 * @version 1.1
 */
public interface TradeService {

    /**
     * 交易报文提交：幂等校验 → 入口状态预检 → 事务插入报文流水 → 事务提交后发送顺序消息
     *
     * @param dto 交易报文提交请求
     * @return 受理结果（ACCEPTED 受理成功 / DUPLICATE 重复请求 /
     *         STATE_CONFLICT 状态冲突即乱序操作被入口预检拒绝）
     */
    SubmitResult submit(TradeSubmitDTO dto);
}
