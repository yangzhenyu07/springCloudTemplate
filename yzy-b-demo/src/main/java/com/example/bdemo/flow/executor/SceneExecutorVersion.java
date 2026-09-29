package com.example.bdemo.flow.executor;


import com.alibaba.nacos.shaded.com.google.common.collect.Lists;
import com.example.bdemo.flow.common.FlowHistory;
import com.example.bdemo.flow.common.TradeFlowContext;
import com.example.bdemo.flow.common.dto.CommonParam;
import com.example.bdemo.flow.common.dto.WalletPayBaseInfo;
import com.example.bdemo.flow.common.flow.SceneDefinition;
import com.example.bdemo.flow.common.flow.SceneFlowDefinition;
import com.example.bdemo.flow.factory.TradeFlowFactory;
import com.example.common.tag.TagUtils;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Component;

import java.util.List;

@Slf4j
@Component
@RequiredArgsConstructor
public class SceneExecutorVersion {

    private final TradeFlowFactory tradeFlowFactory;
    @Autowired
    private FlowExecutorVersion flowExecutor;

    public void executeScene(String sceneCode, TradeFlowContext context) {
        init(context);
        executePreScene(sceneCode, context);
        List<String> pre = context.getPre();
        log.info("【】-编排-预编译:\n{}", sceneCode,String.join("\n",pre));
        SceneDefinition scene = tradeFlowFactory.getScene(sceneCode);
        List<String> history = Lists.newArrayList();
        if(scene.getSceneFlows() == null){
            return;
        }
        boolean flag = Boolean.TRUE;
        for (SceneFlowDefinition sceneFlow : scene.getSceneFlows()) {
            flowExecutor.executeSceneFlow(sceneFlow, context);
            // TODO 判断流程停止，叫停循环
            if(context.isStopChain()){
                break;
            }
        }
        if (flag){
            List<FlowHistory> flowHistoryList = context.getFlowHistoryList();
            for (FlowHistory flowHistory : flowHistoryList){
                history.add(flowHistory.toString());
            }
            String channelTag = TagUtils.getChannelTag();
            log.info("中心:{},执行链路:\n{}", channelTag,String.join("\n", history));
        }
    }

    public void executePreScene(String sceneCode, TradeFlowContext context) {
        SceneDefinition scene = tradeFlowFactory.getScene(sceneCode);
        if(scene.getSceneFlows() == null){
            return;
        }
        for (SceneFlowDefinition sceneFlow : scene.getSceneFlows()) {
            flowExecutor.executePreSceneFlow(sceneFlow, context);
        }
    }

    public void init(TradeFlowContext context) {
        if(context.getWalletPayBaseInfo() == null) {
            context.setWalletPayBaseInfo(new WalletPayBaseInfo());
        }

        if(context.getCommonParam() == null) {
            context.setCommonParam(new CommonParam());
        }

    }
}