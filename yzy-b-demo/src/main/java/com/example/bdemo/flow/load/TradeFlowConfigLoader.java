package com.example.bdemo.flow.load;

import com.example.bdemo.flow.raw.TradeFlowRawConfig;
import com.example.bdemo.service.*;
import lombok.RequiredArgsConstructor;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Component;

/**
 * @author yangzhenyu
 * @version 1.0
 * @description:
 * @date 2026/9/28 19:57
 */
@Component
@RequiredArgsConstructor
public class TradeFlowConfigLoader {

    @Autowired
    public SceneInfoService tradeSceneService;

    @Autowired
    public FlowInfoService tradeFlowService;

    @Autowired
    public SceneFlowRelationService tradeSceneFlowRelService;

    @Autowired
    public FlowNodeService tradeNodeService;

    @Autowired
    public FlowNodeRelationService tradeFlowNodeRelService;

    public TradeFlowRawConfig loadAll(){
        TradeFlowRawConfig config = new TradeFlowRawConfig();
        config.setScenes(tradeSceneService.list());
        config.setFlows(tradeFlowService.list());
        config.setSceneFlowRels(tradeSceneFlowRelService.list());
        config.setNodes(tradeNodeService.list());
        config.setFlowNodeRels(tradeFlowNodeRelService.list());
        return config;
    }
}