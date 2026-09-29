package com.example.bdemo.flow.executor;


import com.alibaba.nacos.common.utils.StringUtils;
import com.example.bdemo.flow.common.NodeCommon;
import com.example.bdemo.flow.common.TradeFlowContext;
import com.example.bdemo.flow.common.flow.NodeDefinition;
import com.example.bdemo.flow.handler.Handler;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Component;

import java.util.Map;

/**
 * 统一入口执行器: 初始化上下文，为处理器注入上下文，关联整个流程
 */
@Component
@RequiredArgsConstructor
@Slf4j
public class NodeExecutorVersion implements NodeCommon {

    private final Map<String, Handler> handlerMap;
    @Autowired
    private HandlerService handlerService;

    public void execute(NodeDefinition node, TradeFlowContext context) {
        if(node == null){
            throw new IllegalArgumentException("node is null");
        }
        String errorMsg = "通用节点校验失败, sceneId: {0}, flowCode: {1}, nodeCode: {2}, nodeName: {3},handlerBeanName: {4}, nodeType:{5}, "+
                "check:{6}";
        Handler handler = handlerMap.get(node.getHandlerBeanName());
        if(handler == null){
            throw new IllegalArgumentException("handler is null");
        }
        String nodeType = node.getNodeType();
        if(log.isInfoEnabled()){
            log.info("开始执行【handle】, sceneId: {}, flowCode: {}, nodeCode: {}, handlerBeanName: {}, nodeType:{}",
                    context.getSceneId(), node.getFlowCode(), node.getNodeCode(), node.getHandlerBeanName(),nodeType);
        }
        String type = "NO";
        if (StringUtils.isNotBlank(nodeType)){
            String[] nodeTypes = nodeType.split("_");
            if (nodeTypes.length == 2) {
                type = nodeTypes[1];
            }
        }
        if ("T".equals(type)){
            handlerService.transactionalHandler(handler, context, node);
        }else {
            handler.handle(context, node);
        }
    }
}