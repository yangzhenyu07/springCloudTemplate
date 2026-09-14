package com.example.flow.cache;

import com.example.flow.raw.TestConfig;
import org.springframework.stereotype.Component;

import java.util.concurrent.atomic.AtomicReference;

/**
 * @author yangzhenyu
 * @version 1.0
 * @description:
 * @date 2026/8/31 19:23
 */
@Component
public class TestConfigCache {

    private final AtomicReference<TestConfig> ref = new AtomicReference<>();

    public TestConfig get(){
        return ref.get();
    }

    public void refresh(TestConfig newConfig){
        if (newConfig == null){
            throw new IllegalArgumentException("config must not be null");
        }
        ref.set(newConfig);
    }
}
