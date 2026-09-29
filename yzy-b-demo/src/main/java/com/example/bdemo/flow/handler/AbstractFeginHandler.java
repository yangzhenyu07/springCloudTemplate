package com.example.bdemo.flow.handler;

import com.example.bdemo.flow.common.FeignNodeConfig;
import com.example.bdemo.flow.common.FlowNodeTypeEnum;
import com.example.bdemo.flow.common.TradeFlowContext;
import com.example.bdemo.flow.common.flow.NodeDefinition;
import com.example.bdemo.flow.feign.FeignInvoker;
import com.example.bdemo.flow.feign.RemoteInvokeConfig;
import com.fasterxml.jackson.databind.ObjectMapper;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Component;

/**
 * Fegin处理器抽象父类: 所有Fegin类型处理器继承此类
 * 封装Fegin处理器通用逻辑, 统一远程调用规范
 */
@Slf4j
@Component
@RequiredArgsConstructor
public abstract class AbstractFeginHandler<REQ, RESP> implements Handler {

    private final FeignInvoker feignInvoker;
    private final ObjectMapper objectMapper;

    @Override
    public final void handle(TradeFlowContext context, NodeDefinition node) {
        before(context, node);
        if(!node.getNodeEnable()){
            log.info("node is disabled, continue nodeCode: {}", node.getNodeCode());
            node.setNodeEnable(true);
            return;
        }
        FeignNodeConfig config = parseFeignConfig(node);
        REQ request = buildRequest(context, node);
        RESP response = null;
        if(node.getNodeType().equals(FlowNodeTypeEnum.FEIGN.getCode())){
            response = doFeignCall(config, request);
        } else {
            response = doMockCall(config, request);
        };
        handleResponse(context, response);
        after(context, node);
    }

    protected RESP doMockCall(FeignNodeConfig config, REQ request){
        return null;
    };

    protected FeignNodeConfig parseFeignConfig(NodeDefinition node){
        String nodeConfig = node.getNodeConfig();
        FeignNodeConfig config;
        try {
            config = objectMapper.readValue(nodeConfig, FeignNodeConfig.class);
        } catch (Exception e) {
            throw new IllegalArgumentException("invaild json object");
        }
        return config;
    }

    protected abstract REQ buildRequest(TradeFlowContext context, NodeDefinition node);

    protected RESP doFeignCall(FeignNodeConfig config, REQ request) {
        RemoteInvokeConfig remoteInvokeConfig = toRemoteInvokeConfig(config);
        return (RESP) feignInvoker.invoke(remoteInvokeConfig, request, responseClass());
    }

    protected abstract Class<RESP> responseClass();

    protected RemoteInvokeConfig toRemoteInvokeConfig(FeignNodeConfig node){
        RemoteInvokeConfig c = new RemoteInvokeConfig();
        c.setServiceName(node.getServerId());
        c.setPath(node.getApiPatch());
        c.setMethod(node.getMethod());
        c.setCharset(node.getCharset());
        c.setHeaders(node.getHeaders());
        String timeoutMs = node.getTimeoutMs();
        if(timeoutMs != null){
            Integer t = Integer.valueOf(node.getTimeoutMs());
            c.setConnectTimeoutMillis(t);
            c.setReadTimeoutMillis(t);
        }
        return c;
    }

    protected abstract void handleResponse(TradeFlowContext context, RESP response);

    /**
     * 前置处理（可选重写）
     */
    public void before(TradeFlowContext context, NodeDefinition node){

    }

    /**
     * 后置处理（可选重写）
     */
    public void after(TradeFlowContext context, NodeDefinition node){

    }
}