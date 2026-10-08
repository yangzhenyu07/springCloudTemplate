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
import org.springframework.context.annotation.Lazy;
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

    /**
     * 子场景回调执行器（条件分支命中 subSceneCode 时回灌调用）。
     *
     * <p>必须 @Lazy：SceneExecutorVersion 通过构造器注入本类，而本类又依赖它，形成
     * Scene -> Flow -> Scene 的环。Spring 的三级缓存是在<b>构造器执行完之后</b>才暴露早期引用，
     * 所以构造器注入参与的环，靠 spring.main.allow-circular-references=true 也救不回来（该开关只对
     * 纯字段/setter 注入的环有效）。这里在"回调方向"加 @Lazy，让本类构造时注入的是代理，
     * 真正调用时才去容器取 bean，环被打断。
     *
     * <p>注意：加在字段上即可生效（非 final 字段注入）；不要加在 SceneExecutorVersion 侧 ——
     * 那边是 final + @RequiredArgsConstructor 的构造器注入，Lombok 默认不会把字段上的 @Lazy
     * 复制到构造器参数，加了等于没加。
     */
    @Lazy
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