package com.example.controller;

import com.example.common.result.Result;
import com.example.common.trace.TraceIdUtil;
import com.example.entity.SysUser;
import com.example.feign.GatewayFeignClient;
import com.example.service.SysUserService;
import io.swagger.annotations.Api;
import io.swagger.annotations.ApiOperation;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Qualifier;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.data.redis.core.RedisTemplate;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import javax.annotation.Resource;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

/**
 * 集成测试控制器
 * 验证DB、Redis、Nacos配置中心、OpenFeign调用链路、TraceId跟踪
 *
 * @author yzy
 * @version 1.0
 */
@Api(value = "集成测试", tags = {"集成测试"})
@RestController
@Slf4j
@RequestMapping(value = "api/a/test")
public class FeignTestController {

    @Resource
    private SysUserService sysUserService;

    @Resource
    private GatewayFeignClient gatewayFeignClient;

    @Qualifier("redisStdTemplate")
    @Resource
    private RedisTemplate<String, Object> redisTemplate;

    @Value("${test.message:local-default}")
    private String nacosConfigMessage;

    /**
     * 完整集成测试：DB + Redis + Nacos配置 + OpenFeign调用网关→yzy-b-demo
     * 包含全链路 traceId 跟踪
     *
     * @return 测试结果
     */
    @ApiOperation(value = "完整集成测试", notes = "DB+Redis+Nacos+Feign+TraceId全链路测试")
    @GetMapping("/feign")
    public Result<Map<String, Object>> testFeign() {
        String traceId = TraceIdUtil.getTraceId();
        log.info("收到请求, traceId={}", traceId);

        Map<String, Object> result = new HashMap<>();

        // 1. Nacos配置中心测试
        result.put("nacosConfig", nacosConfigMessage);

        // 2. DB测试 - 查询启用用户
        List<SysUser> users = sysUserService.listActiveUsers();
        result.put("dbUsers", users);

        // 3. Redis测试 - 写入并读取
        String redisKey = "test:feign:" + System.currentTimeMillis();
        redisTemplate.opsForValue().set(redisKey, "feign-test-value");
        Object redisValue = redisTemplate.opsForValue().get(redisKey);
        result.put("redisTest", redisValue);

        // 4. OpenFeign调用网关 → 网关路由到yzy-b-demo
        try {
            Result bDemoResponse = gatewayFeignClient.callBDemoHello();
            result.put("feignToGatewayToBDemo", bDemoResponse);
            result.put("status", "SUCCESS");
            log.info("Feign调用成功, traceId={}", traceId);
        } catch (Exception e) {
            log.error("Feign调用网关失败, traceId={}", traceId, e);
            result.put("feignToGatewayToBDemo", "ERROR: " + e.getMessage());
            result.put("status", "PARTIAL_SUCCESS");
        }

        Result<Map<String, Object>> r = Result.success(result);
        r.setTraceId(traceId);
        return r;
    }
}
