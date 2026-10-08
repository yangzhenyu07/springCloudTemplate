package com.example.bdemo.controller;

import com.example.bdemo.common.dto.BaseReqData;
import com.example.bdemo.common.dto.KfhlReqHead;
import com.example.bdemo.dto.*;
import com.example.bdemo.flow.common.TradeFlowContext;
import com.example.bdemo.flow.common.dto.ConditionCheck;
import com.example.bdemo.flow.executor.HandlerExecutorVersion;
import com.example.common.result.Result;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.util.Map;

/**
 * <p>
 * 流程表 前端控制器
 * </p>
 *
 * @author yzy
 * @since 2026-09-28 17:45:25
 */
@Slf4j
@RestController
@RequestMapping("/api/flowInfo")
public class FlowController {

    @Autowired
    private HandlerExecutorVersion handlerExecutorVersion;
    @GetMapping("/test")
    public void test() {

        FlowDto flowDto = new FlowDto();
        KfhlReqHead kfhlReqHead = new KfhlReqHead();
        kfhlReqHead.setAPPID("III");
        flowDto.setHead(kfhlReqHead);
        BaseReqData<FlowVo> baseReqData = new BaseReqData<>();
        FlowVo flowVo = new FlowVo();
        flowVo.setId("45");
        baseReqData.setBody(flowVo);
        flowDto.setData(baseReqData);
        TradeFlowContext tradeFlowContext = new TradeFlowContext();
        ConditionCheck conditionCheck = new ConditionCheck();
        conditionCheck.setVersionId("v2");
        conditionCheck.setId("2");
        tradeFlowContext.setConditionCheck(conditionCheck);
        handlerExecutorVersion.execute("yzv_test",flowDto,tradeFlowContext,OrderPaymentRequest.class);
    }
}
