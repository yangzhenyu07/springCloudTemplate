package com.example.bdemo.hanlder.business;

import com.example.bdemo.common.dto.BaseReqData;
import com.example.bdemo.common.dto.KfhlReqHead;
import com.example.bdemo.dto.FlowDto;
import com.example.bdemo.dto.FlowVo;
import com.example.bdemo.dto.OrderPaymentRequest;
import com.example.bdemo.flow.common.TradeFlowContext;
import com.example.bdemo.flow.common.dto.ConditionCheck;
import com.example.bdemo.flow.common.flow.NodeDefinition;
import com.example.bdemo.flow.executor.HandlerExecutorVersion;
import com.example.bdemo.flow.handler.AbstractBusiHandler;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Component;

/**
 * @author yangzhenyu
 * @version 1.0
 * @description:
 * @date 2026/9/30 09:55
 */
@Slf4j
@Component
public class TestV2BusiHandler extends AbstractBusiHandler {

    @Autowired
    private HandlerExecutorVersion handlerExecutorVersion;

    @Override
    protected void executor(TradeFlowContext context, NodeDefinition node) {


        log.info("--------------------TestV2BusiHandler-------------------------");

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
        conditionCheck.setVersionId("v1");
        conditionCheck.setId("1");
        tradeFlowContext.setConditionCheck(conditionCheck);
        handlerExecutorVersion.execute("yzv_test",flowDto,tradeFlowContext, OrderPaymentRequest.class);
    }
}