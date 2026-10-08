package com.example.bdemo.hanlder.fegin;

import com.alibaba.fastjson.JSON;
import com.example.api.vo.ApiSdkVoRep;
import com.example.api.vo.ApiSdkVoRes;
import com.example.bdemo.flow.common.TradeFlowContext;
import com.example.bdemo.flow.common.flow.NodeDefinition;
import com.example.bdemo.flow.feign.FeignInvoker;
import com.example.bdemo.flow.handler.AbstractFeginHandler;
import com.fasterxml.jackson.databind.ObjectMapper;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Component;

/**
 * @author yangzhenyu
 * @version 1.0
 * @description:
 * @date 2026/9/30 09:56
 */
@Slf4j
@Component
public class TestFeignHandler extends AbstractFeginHandler<ApiSdkVoRes, ApiSdkVoRep> {

    public TestFeignHandler(FeignInvoker feignInvoker, ObjectMapper objectMapper){
        super(feignInvoker,objectMapper);
    }
    @Override
    protected ApiSdkVoRes buildRequest(TradeFlowContext context, NodeDefinition node) {
        ApiSdkVoRes apiSdkVoRes = new ApiSdkVoRes();
        apiSdkVoRes.setId("2");
        log.info("TestFeignHandler 传参:{}", JSON.toJSONString(apiSdkVoRes));
        return apiSdkVoRes;
    }

    @Override
    protected Class<ApiSdkVoRep> responseClass() {
        return ApiSdkVoRep.class;
    }

    @Override
    protected void handleResponse(TradeFlowContext context, ApiSdkVoRep response) {
        log.info("TestFeignHandler 返参:{}", JSON.toJSONString(response));
    }
}
