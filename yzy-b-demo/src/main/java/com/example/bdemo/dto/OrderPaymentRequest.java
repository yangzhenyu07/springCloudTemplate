package com.example.bdemo.dto;

import com.alibaba.fastjson2.annotation.JSONField;
import lombok.Data;

@Data
public class OrderPaymentRequest {
    /**
     * 付款钱包ID
     */
    @JSONField(name = "walletId")
    private String walletId;

    /**
     * 支付方式
     */
    @JSONField(name = "mergeType")
    private String mergeType;
}