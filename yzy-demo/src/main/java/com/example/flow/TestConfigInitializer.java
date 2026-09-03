package com.example.flow;

import com.example.flow.cache.TestConfigCache;
import com.example.flow.load.TestConfigLoader;
import com.example.flow.raw.TestConfig;
import lombok.RequiredArgsConstructor;
import org.springframework.boot.ApplicationArguments;
import org.springframework.boot.ApplicationRunner;
import org.springframework.stereotype.Component;

/**
 * @author yangzhenyu
 * @version 1.0
 * @description:
 * @date 2026/8/31 19:22
 */
@Component
@RequiredArgsConstructor
public class TestConfigInitializer implements ApplicationRunner {

    private final TestConfigCache configCache;
    private final TestConfigLoader configLoader;
    @Override
    public void run(ApplicationArguments args) throws Exception {
        TestConfig load = configLoader.load();
        configCache.refresh(load);
    }
}
