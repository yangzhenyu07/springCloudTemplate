package com.example.bdemo.flow.factory;


import com.example.bdemo.flow.common.flow.FlowDefinition;
import com.example.bdemo.flow.common.flow.NodeDefinition;
import com.example.bdemo.flow.common.flow.SceneDefinition;

/**
 * @author yangzhenyu
 * @version 1.0
 * @description:
 * @date 2026/9/28 20:04
 */

public interface TradeFlowFactory {
    SceneDefinition getScene(String sceneCode);

    FlowDefinition getFlow(String flowCode);

    NodeDefinition getNode(String nodeCode);
}
