package com.example.bdemo.flow.executor;

import com.alibaba.fastjson2.JSON;
import com.example.bdemo.common.dto.*;
import com.example.bdemo.flow.common.TradeFlowContext;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Component;
@Slf4j
@Component
@RequiredArgsConstructor
public class HandlerExecutorVersion {

    private final SceneExecutorVersion sceneExecutor;

    public <REQ, RESP> RESP execute(String sceneCode, REQ request, TradeFlowContext<REQ, RESP> context, Class<RESP> responseType){
        context.setSceneId(sceneCode);
        // 放请求
        if((request instanceof BaseRequest<?>)){
            BaseRequest<?> requestTemp = (BaseRequest<?>) request;
            KfhlReqHead kfhlReqHead = requestTemp.getHead();
            context.setKfhlReqHead(kfhlReqHead);
            BaseReqData<?> baseReqData = requestTemp.getData();
            if (null == baseReqData) {return null;}

            UwapHeader msgHeader = baseReqData.getMsgHeader();
            if (null != msgHeader){
                context.setUwapHeader(msgHeader);
            }
        }

        // 创建响应实例
        RESP response = null;
        try {
            response = responseType.newInstance();
        } catch (InstantiationException | IllegalAccessException e) {
            throw new RuntimeException("无法创建响应实例: " + responseType.getName(), e);
        }
        context.setOrgResponseContext(response); // 放入响应参数
        this.setCondition(context, request); // 放入conditon条件参数
        log.info("HandlerExecutor execute context:{}", JSON.toJSONString(context));
        sceneExecutor.executeScene(sceneCode, context);
        return context.getOrgResponseContext();
    }

    /**
     * 放入条件参数
     * @param context
     * @param request
     * @param <REQ>
     * @param <RESP>
     */
    private <REQ, RESP> void setCondition(TradeFlowContext<REQ, RESP> context, REQ request) {
        FlowCondition flowCondition = new FlowCondition();
        context.setFlowCondition(flowCondition);
    }
}