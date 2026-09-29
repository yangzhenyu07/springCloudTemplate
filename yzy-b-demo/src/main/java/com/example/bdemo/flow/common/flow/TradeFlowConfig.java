package com.example.bdemo.flow.common.flow;

import lombok.Data;

import java.util.Collections;
import java.util.Map;

/**
 * @author yangzhenyu
 * @version 1.0
 * @description:
 * @date 2026/9/29 14:03
 */
@Data
public class TradeFlowConfig {

    public Map<String, SceneDefinition> sceneMap;

    public Map<String, FlowDefinition> flowMap;

    public Map<String, NodeDefinition> nodeMap;

    public static TradeFlowConfig empty() {
        TradeFlowConfig config = new TradeFlowConfig();
        config.setSceneMap(Collections.emptyMap());
        config.setFlowMap(Collections.emptyMap());
        config.setNodeMap(Collections.emptyMap());
        return config;
    }

}