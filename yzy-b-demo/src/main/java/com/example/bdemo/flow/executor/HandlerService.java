package com.example.bdemo.flow.executor;

import com.example.bdemo.flow.common.TradeFlowContext;
import com.example.bdemo.flow.common.flow.NodeDefinition;
import com.example.bdemo.flow.handler.Handler;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Slf4j
@Service
public class HandlerService {

    @Transactional
    public void transactionalHandler(Handler handler, TradeFlowContext context, NodeDefinition node){
        log.info("{} 事务执行...", node.getHandlerBeanName());
        handler.handle(context, node);
    }
}