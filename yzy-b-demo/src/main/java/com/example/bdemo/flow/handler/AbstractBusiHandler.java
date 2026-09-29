package com.example.bdemo.flow.handler;


import com.example.bdemo.flow.common.TradeFlowContext;
import com.example.bdemo.flow.common.flow.NodeDefinition;
import lombok.extern.slf4j.Slf4j;

/**
 * Busi处理器抽象父类: 所有Busi类型处理器继承此类
 * 封装Busi处理器通用逻辑，统一业务处理规范
 */
@Slf4j
public abstract class AbstractBusiHandler implements Handler {


    @Override
    public final void handle(TradeFlowContext context, NodeDefinition node) {
        before(context, node);
        if(!node.getNodeEnable()){
            log.info("node is disabled, continue nodeCode: {}", node.getNodeCode());
            node.setNodeEnable(true);
            return;
        }
        executor(context, node);
        after(context, node);
    }

    /**
     * 前置处理（可选重写）
     */
    public void before(TradeFlowContext context, NodeDefinition node){

    }

    /**
     * 核心业务逻辑（必须重写）
     */
    protected abstract void executor(TradeFlowContext context, NodeDefinition node);

    /**
     * 后置处理（可选重写）
     */
    public void after(TradeFlowContext context, NodeDefinition node){

    }
}
