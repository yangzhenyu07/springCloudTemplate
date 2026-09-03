package com.example.flow.raw;

import com.example.entity.SysUser;
import lombok.Data;

import java.util.Collections;
import java.util.Map;

/**
 * @author yangzhenyu
 * @version 1.0
 * @description:
 * @date 2026/8/31 19:23
 */
@Data
public class TestConfig {
    private Map<Long, SysUser> stringSysUserMap;

    public static TestConfig empty(){
        TestConfig config = new TestConfig();
        config.setStringSysUserMap(Collections.emptyMap());
        return config;
    }
}
