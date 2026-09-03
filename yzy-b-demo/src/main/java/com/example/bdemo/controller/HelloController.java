package com.example.bdemo.controller;

import com.example.bdemo.entity.SysUser;
import com.example.bdemo.service.SysUserService;
import com.example.common.result.Result;
import com.example.common.trace.TraceIdUtil;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Qualifier;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.web.bind.annotation.*;

import javax.annotation.Resource;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

/**
 * yzy-b-demo 测试控制器
 * 网关路由 /api/b/** 到此服务
 *
 * @author yzy
 * @version 1.0
 */
@Slf4j
@RestController
@RequestMapping(value = "api/b")
public class HelloController {

    @Resource
    private SysUserService sysUserService;

    @Qualifier("stringRedisStdTemplate")
    @Resource
    private StringRedisTemplate stringRedisTemplate;

    @Value("${test.message:local-default}")
    private String nacosConfigMessage;

    @Value("${server.port:8089}")
    private int serverPort;

    /**
     * Hello接口 - 返回DB数据、Redis数据、Nacos配置、traceId
     *
     * @return 测试数据
     */
    @GetMapping("/hello")
    public Result<Map<String, Object>> hello() {
        String traceId = TraceIdUtil.getTraceId();
        log.info("yzy-b-demo /api/b/hello 被调用, traceId={}", traceId);

        Map<String, Object> result = new HashMap<>();

        // Nacos配置中心
        result.put("nacosConfig", nacosConfigMessage);

        // DB数据
        List<SysUser> users = sysUserService.listActiveUsers();
        result.put("dbUsers", users);

        // Redis数据
        String redisKey = "yzy-b-demo:hello:" + System.currentTimeMillis();
        stringRedisTemplate.opsForValue().set(redisKey, "hello-from-b-demo");
        String redisVal = stringRedisTemplate.opsForValue().get(redisKey);
        result.put("redisTest", redisVal);

        // 服务信息
        result.put("service", "yzy-b-demo");
        result.put("port", serverPort);

        Result<Map<String, Object>> r = Result.success(result);
        r.setTraceId(traceId);
        return r;
    }

    /**
     * Hello接口 - 返回DB数据、Redis数据、Nacos配置、traceId
     *
     * @return 测试数据
     */
    @PostMapping("/postHello")
    public Result<Map<String, Object>> postHello(@RequestBody String msg) {
        String traceId = TraceIdUtil.getTraceId();
        log.info("yzy-b-demo /api/b/hello 被调用, traceId={},参数:{}", traceId, msg);

        Map<String, Object> result = new HashMap<>();

        // Nacos配置中心
        result.put("nacosConfig", nacosConfigMessage);

        // DB数据
        List<SysUser> users = sysUserService.listActiveUsers();
        result.put("dbUsers", users);

        // Redis数据
        String redisKey = "yzy-b-demo:hello:" + System.currentTimeMillis();
        stringRedisTemplate.opsForValue().set(redisKey, "hello-from-b-demo");
        String redisVal = stringRedisTemplate.opsForValue().get(redisKey);
        result.put("redisTest", redisVal);

        // 服务信息
        result.put("service", "yzy-b-demo");
        result.put("port", serverPort);

        Result<Map<String, Object>> r = Result.success(result);
        r.setTraceId(traceId);
        return r;
    }
}
