package com.example.bdemo.hanlder.transaction.business;

import com.example.bdemo.flow.common.TradeFlowContext;
import com.example.bdemo.flow.common.flow.NodeDefinition;
import com.example.bdemo.flow.handler.AbstractBusiHandler;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Component;

/**
 * @author yangzhenyu
 * @version 1.0
 * @description:
 * @date 2026/9/30 09:59
 */
@Slf4j
@Component
public class TestTransactionBusHandler extends AbstractBusiHandler {
    @Override
    protected void executor(TradeFlowContext context, NodeDefinition node) {
        log.info("--------------------TestTransactionBusHandler-------------------------");

    }
}