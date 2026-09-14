package com.example.flow.utils;

import com.example.entity.SysUser;
import com.example.flow.factory.TestConfigFactory;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Component;

import jakarta.annotation.PostConstruct;
import java.util.Map;

/**
 * @author yangzhenyu
 * @version 1.0
 * @description:
 * @date 2026/9/2 08:28
 */
@Component
@RequiredArgsConstructor
public class TestConfigUtils {
    private final TestConfigFactory factory;

    private static TestConfigFactory staticFactory;

    @PostConstruct
    public void init(){
        staticFactory = factory;
    }

    public static Map<Long, SysUser>  get(){
        return staticFactory.get();
    }
}
