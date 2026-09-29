package com.example.bdemo.flow.cache;

import com.example.bdemo.flow.common.flow.TradeFlowConfig;
import org.springframework.stereotype.Component;

import java.util.concurrent.atomic.AtomicReference;

/**
 * @author yangzhenyu
 * @version 1.0
 * @description:
 * @date 2026/9/28 20:15
 */
@Component
public class TradeFlowConfigCache {

    private final AtomicReference<TradeFlowConfig> ref = new AtomicReference<>(TradeFlowConfig.empty());

    public TradeFlowConfig get() {
        return ref.get();
    }

    public void refresh(TradeFlowConfig newConfig){
        if(newConfig == null) throw new IllegalArgumentException("config must not be null");
        ref.set(newConfig);
    }
}