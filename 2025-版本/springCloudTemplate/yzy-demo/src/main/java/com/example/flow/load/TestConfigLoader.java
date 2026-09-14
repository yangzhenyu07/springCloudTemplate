package com.example.flow.load;

import com.example.entity.SysUser;
import com.example.flow.raw.TestConfig;
import com.example.service.SysUserService;
import lombok.RequiredArgsConstructor;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Component;

import java.util.List;
import java.util.Map;
import java.util.stream.Collectors;

/**
 * @author yangzhenyu
 * @version 1.0
 * @description:
 * @date 2026/8/31 19:23
 */
@Component
@RequiredArgsConstructor
public class TestConfigLoader {

    @Autowired
    public SysUserService service;

    public TestConfig load(){
        TestConfig config = new TestConfig();
        List<SysUser> sysUsers = service.listActiveUsers();
        Map<Long, SysUser> collect = sysUsers.stream().collect(Collectors.toMap(SysUser::getId, item -> item));
        config.setStringSysUserMap(collect);
        return config;
    }


}
