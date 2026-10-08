package com.example.bdemo.flow.executor;

import com.alibaba.nacos.common.utils.CollectionUtils;
import com.alibaba.nacos.shaded.com.google.common.collect.Lists;
import com.example.bdemo.flow.common.FlowHistory;
import com.example.bdemo.flow.common.TradeFlowContext;
import com.example.bdemo.flow.common.flow.ConditionBranchDefinition;
import com.example.bdemo.flow.common.flow.FlowDefinition;
import com.example.bdemo.flow.common.flow.NodeDefinition;
import com.example.bdemo.flow.common.flow.SceneFlowDefinition;
import com.example.bdemo.flow.condition.SpelConditionEvaluator;
import com.example.bdemo.flow.factory.TradeFlowFactory;
import lombok.RequiredArgsConstructor;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Component;

import java.text.MessageFormat;
import java.util.List;

/**
 * 统一入口执行器: 初始化上下文，为处理器注入上下文，关联整个流程
 */
@Component
@RequiredArgsConstructor
public class FlowExecutorVersion {

    private final TradeFlowFactory tradeFlowFactory;
    private final NodeExecutorVersion nodeExecutor;
    private final SpelConditionEvaluator conditionEvaluator;
    @Autowired
    private SceneExecutorVersion sceneExecutor;

    public void executeFlow(String flowCode, TradeFlowContext context) {
        FlowDefinition flow = tradeFlowFactory.getFlow(flowCode);
        executeSerialFlow(flow, context);
    }

    public void executePreFlow(String flowCode, TradeFlowContext context) {
        FlowDefinition flow = tradeFlowFactory.getFlow(flowCode);
        executePreSerialFlow(flow, context);
    }

    public void executePreSceneFlow(SceneFlowDefinition sceneFlow, TradeFlowContext context){
        FlowDefinition flow = tradeFlowFactory.getFlow(sceneFlow.getFlowCode());
        if(FlowDefinition.FLOW_TYPE_SERIAL.equals(flow.getFlowType())){
            executePreSerialFlow(flow, context);
            return;
        }
        if(FlowDefinition.FLOW_TYPE_CONDITION.equals(flow.getFlowType())){
            executePreConditionFlow(sceneFlow, context);
            return;
        }
        throw new IllegalArgumentException("unsupported type");
    }

    public void executeSceneFlow(SceneFlowDefinition sceneFlow, TradeFlowContext context){
        FlowDefinition flow = tradeFlowFactory.getFlow(sceneFlow.getFlowCode());
        if(FlowDefinition.FLOW_TYPE_SERIAL.equals(flow.getFlowType())){
            executeSerialFlow(flow, context);
            return;
        }
        if(FlowDefinition.FLOW_TYPE_CONDITION.equals(flow.getFlowType())){
            executeConditionFlow(sceneFlow, context);
            return;
        }
        throw new IllegalArgumentException("unsupported type");
    }

    public void executeSerialFlow(FlowDefinition flow, TradeFlowContext context){
        if(flow.getNodeCodes() == null){
            return;
        }
        for (String nodeCode: flow.getNodeCodes()) {
            // TODO 判断流程停止，叫停循环
            if(context.isStopChain()){
                break;
            }
            List<FlowHistory> flowHistoryList = context.getFlowHistoryList();
            long start = System.currentTimeMillis();
            if (CollectionUtils.isNotEmpty(flowHistoryList)){
                FlowHistory flowHistory = flowHistoryList.get(flowHistoryList.size() -1);
                start = flowHistory.getNodeTimeStamp();
            }else{
                flowHistoryList = Lists.newArrayList();
            }
            NodeDefinition node = tradeFlowFactory.getNode(nodeCode);
            node.setFlowCode(flow.getFlowCode());
            nodeExecutor.execute(node, context);
            long end = System.currentTimeMillis();
            FlowHistory flowHistory = new FlowHistory();
            flowHistory.setNodeCode(node.getNodeCode());
            flowHistory.setNodeDesc(node.getNodeDesc());
            flowHistory.setNodeTimeStamp(end);
            flowHistory.setConsumingTime(end - start);
            flowHistoryList.add(flowHistory);
            context.setFlowHistoryList(flowHistoryList);
        }
    }

    public void executePreSerialFlow(FlowDefinition flow, TradeFlowContext context) {
        String msg = "【{0}】-【{1}】";
        if(flow.getNodeCodes() == null) {
            return;
        }
        for (String nodeCode: flow.getNodeCodes()) {
            // TODO 判断流程停止，叫停循环
            if(context.isStopChain()){
                break;
            }
            List<String> pre = context.getPre();
            if (CollectionUtils.isEmpty(pre)){
                pre = Lists.newArrayList();
            }
            NodeDefinition node = tradeFlowFactory.getNode(nodeCode);
            pre.add(MessageFormat.format(msg,node.getNodeCode(),node.getNodeDesc()));
            context.setPre(pre);
        }
    }

    public void executePreConditionFlow(SceneFlowDefinition sceneFlow, TradeFlowContext context) {
        if(sceneFlow.getConditionBranches() == null){
            return;
        }
        for(ConditionBranchDefinition branch : sceneFlow.getConditionBranches()){
            if(conditionEvaluator.evaluatePre(branch.getCondition(),branch.getCompiledExpression(), context)){
                if(branch.getSubFlowCode() != null){
                    executePreFlow(branch.getSubFlowCode(), context);
                }
                if(branch.getSubSceneCode() != null && !sceneFlow.getSceneCode().equals(branch.getSubSceneCode())){
                    sceneExecutor.executePreScene(sceneFlow.getSceneCode(), context);
                }
                return;
            }
        }
    }

    public void executeConditionFlow(SceneFlowDefinition sceneFlow, TradeFlowContext context) {
        if(sceneFlow.getConditionBranches() == null){
            return;
        }
        for(ConditionBranchDefinition branch : sceneFlow.getConditionBranches()){
            if(conditionEvaluator.evaluate(branch.getCondition(),branch.getCompiledExpression(), context)){
                if(branch.getSubFlowCode() != null){
                    executeFlow(branch.getSubFlowCode(), context);
                }
                if(branch.getSubSceneCode() != null && !sceneFlow.getSceneCode().equals(branch.getSubSceneCode())){
                    sceneExecutor.executeScene(sceneFlow.getSceneCode(), context);
                }
                return;
            }
        }
    }
}