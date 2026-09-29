package com.example.bdemo.flow.factory.impl;

import com.example.bdemo.flow.cache.TradeFlowConfigCache;
import com.example.bdemo.flow.common.flow.FlowDefinition;
import com.example.bdemo.flow.common.flow.NodeDefinition;
import com.example.bdemo.flow.common.flow.SceneDefinition;
import com.example.bdemo.flow.common.flow.TradeFlowConfig;
import com.example.bdemo.flow.factory.TradeFlowFactory;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Component;

@Component
@RequiredArgsConstructor
public class DefaultTradeFlowFactory implements TradeFlowFactory {

    private final TradeFlowConfigCache configCache;

    @Override
    public SceneDefinition getScene(String sceneCode) {
        TradeFlowConfig config = configCache.get();
        SceneDefinition sceneDefinition = config.getSceneMap().get(sceneCode);
        if(sceneDefinition == null){
            throw new IllegalArgumentException("scene not found");
        }
        return sceneDefinition;
    }

    @Override
    public FlowDefinition getFlow(String flowCode) {
        TradeFlowConfig config = configCache.get();
        FlowDefinition flowDefinition = config.getFlowMap().get(flowCode);
        if(flowDefinition == null){
            throw new IllegalArgumentException(flowCode + " flow not found");
        }
        return flowDefinition;
    }

    @Override
    public NodeDefinition getNode(String nodeCode) {
        TradeFlowConfig config = configCache.get();
        NodeDefinition nodeDefinition = config.getNodeMap().get(nodeCode);
        if(nodeDefinition == null){
            throw new IllegalArgumentException("scene not found");
        }
        return nodeDefinition;
    }

}
