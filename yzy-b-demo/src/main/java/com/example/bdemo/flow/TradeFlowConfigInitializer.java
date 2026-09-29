package com.example.bdemo.flow;

import com.example.bdemo.flow.assembler.TradeFlowConfigAssembler;
import com.example.bdemo.flow.cache.TradeFlowConfigCache;
import com.example.bdemo.flow.common.flow.TradeFlowConfig;
import com.example.bdemo.flow.factory.TradeFlowFactory;
import com.example.bdemo.flow.load.TradeFlowConfigLoader;
import com.example.bdemo.flow.raw.TradeFlowRawConfig;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.boot.ApplicationArguments;
import org.springframework.boot.ApplicationRunner;
import org.springframework.core.annotation.Order;
import org.springframework.stereotype.Component;

@Order(1)
@Slf4j
@Component
@RequiredArgsConstructor
public class TradeFlowConfigInitializer implements ApplicationRunner {

    private final TradeFlowConfigLoader configLoader;
    private final TradeFlowConfigAssembler configAssembler;
    private final TradeFlowConfigCache configCache;
    private final TradeFlowFactory tradeFlowFactory;


    @Override
    public void run(ApplicationArguments args) {
        TradeFlowRawConfig rawConfig = configLoader.loadAll();
        TradeFlowConfig config = configAssembler.assemble(rawConfig);
        configCache.refresh(config);
    }
}