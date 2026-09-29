package com.example.bdemo.flow.handler;


import com.example.bdemo.flow.common.TradeFlowContext;
import com.example.bdemo.flow.common.flow.NodeDefinition;

public interface Handler {
    void handle(TradeFlowContext context, NodeDefinition node);
}