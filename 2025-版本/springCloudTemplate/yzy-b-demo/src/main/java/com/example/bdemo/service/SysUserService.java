package com.example.bdemo.service;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.example.bdemo.entity.SysUser;
import com.example.bdemo.mapper.SysUserMapper;
import lombok.extern.slf4j.Slf4j;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.stereotype.Service;

import jakarta.annotation.Resource;
import java.util.List;
import java.util.concurrent.TimeUnit;

/**
 * 系统用户服务
 *
 * @author yzy
 * @version 1.0
 */
@Slf4j
@Service
public class SysUserService {

    @Resource
    private SysUserMapper sysUserMapper;

    @Resource
    private StringRedisTemplate stringRedisTemplate;

    private static final String CACHE_KEY = "yzy-b-demo:users:active";

    /**
     * 查询所有启用用户（带Redis缓存）
     *
     * @return 启用用户列表
     */
    public List<SysUser> listActiveUsers() {
        // 先查Redis缓存
        String cached = stringRedisTemplate.opsForValue().get(CACHE_KEY);
        if (cached != null) {
            log.info("从Redis缓存获取用户列表");
        }

        // 查数据库
        LambdaQueryWrapper<SysUser> wrapper = new LambdaQueryWrapper<>();
        wrapper.eq(SysUser::getStatus, 1);
        List<SysUser> users = sysUserMapper.selectList(wrapper);

        // 写入Redis缓存
        stringRedisTemplate.opsForValue().set(CACHE_KEY, "cached-" + System.currentTimeMillis(), 60, TimeUnit.SECONDS);
        log.info("查询数据库获取用户列表，共{}条", users.size());

        return users;
    }
}
