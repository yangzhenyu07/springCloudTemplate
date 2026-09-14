package com.example.flow.factory;

import com.example.entity.SysUser;
import com.example.flow.cache.TestConfigCache;
import com.example.flow.raw.TestConfig;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Component;

import java.util.Map;

/**
 * @author yangzhenyu
 * @version 1.0
 * @description:
 * @date 2026/8/31 19:23
 */
@Component
@RequiredArgsConstructor
public class TestConfigFactory {

    private final TestConfigCache configCache;

    public Map<Long, SysUser> get(){
        TestConfig config = configCache.get();
        if (config == null){
            throw new IllegalArgumentException("testConfig not found");
        }

        return  config.getStringSysUserMap();
    }

}
