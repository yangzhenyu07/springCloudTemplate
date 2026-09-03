package com.example.service.impl;

import com.example.config.common.MyRedisConditional;
import com.example.service.NumberToolService;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Qualifier;
import org.springframework.context.annotation.Conditional;
import org.springframework.data.redis.core.RedisTemplate;
import org.springframework.stereotype.Service;

import javax.annotation.Resource;

@Slf4j
@Conditional(MyRedisConditional.class)
@Service
public class NumberToolServiceImpl implements NumberToolService {
    public NumberToolServiceImpl(){
        log.info("===================任务号工具类集成===================");
    }

    @Qualifier("redisCommonTemplate")
    @Resource
    private RedisTemplate<String, Object> redisTemplate;
}
