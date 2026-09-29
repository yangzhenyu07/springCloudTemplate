package com.example.bdemo.dto;

import com.example.bdemo.common.dto.BaseRequest;
import lombok.Data;

@Data
public class TestRequestBO extends BaseRequest<OrderPaymentRequest> {
    //批次号
    private String batchId;
    //交易码，如验
    private String tradeCode;
}