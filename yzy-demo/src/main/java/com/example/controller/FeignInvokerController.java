package com.example.controller;

import com.example.common.result.Result;
import com.example.common.trace.TraceIdUtil;
import com.example.config.FeignInvoker;
import com.example.config.FeignInvoker_copy;
import com.example.config.RemoteInvokeConfig;
import io.swagger.annotations.Api;
import io.swagger.annotations.ApiOperation;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.util.HashMap;
import java.util.Map;

/**
 * @author Dell
 * @version 1.0
 * @date 2026/8/12 16:01
 */
@Api(value = "编排feign执行测试", tags = {"编排feign执行测试"})
@RestController
@Slf4j
@RequestMapping(value = "api/a/feign")
public class FeignInvokerController {
    @Autowired
    FeignInvoker_copy feignInvoker;

    @ApiOperation(value = "编排feign[get]执行测试", notes = "编排feign[get]执行测试")
    @GetMapping("/testFeign")
    public Result<Map<String, Object>> testFeign() {
        String traceId = TraceIdUtil.getTraceId();
        log.info("收到请求, traceId={}", traceId);

        Map<String, Object> result = new HashMap<>();

        try {
            //1.构造调用配置
            RemoteInvokeConfig config = new RemoteInvokeConfig();
            config.setMethod("GET");
            config.setServiceName("yzy-gateway-in");
            config.setPath("/api/b/hello");
            Map<String, String> customHeaders = new HashMap<>();
            customHeaders.put("yzy", "yzy");
            config.setHeaders(customHeaders);
            //2. 请求体：GET无body传null
            Object requestBody = null;
            //3. 指定返回类型，对应原来接口返回 Result
            Class<Result> responseType = Result.class;
            //4. feignInvoker是被@RequiredArgsConstructor注入的bean
            Result bDemoResponse = (Result) feignInvoker.invoke(config, requestBody, responseType);
            result.put("feignInvoker", bDemoResponse);
            result.put("status", "SUCCESS");
            log.info("Feign调用成功, traceId={}", traceId);
        } catch (Exception e) {
            log.error("Feign调用网关失败, traceId={}", traceId, e);
            result.put("feignInvoker", "ERROR: " + e.getMessage());
            result.put("status", "PARTIAL_SUCCESS");
        }

        Result<Map<String, Object>> r = Result.success(result);
        r.setTraceId(traceId);
        return r;
    }

    @ApiOperation(value = "编排feign[post]执行测试", notes = "编排feign[post]执行测试")
    @GetMapping("/testPostFeign")
    public Result<Map<String, Object>> testPostFeign() {
        String traceId = TraceIdUtil.getTraceId();
        log.info("收到请求, traceId={}", traceId);

        Map<String, Object> result = new HashMap<>();

        try {
            //1.构造调用配置
            RemoteInvokeConfig config = new RemoteInvokeConfig();
            config.setServiceName("yzy-gateway-in");
            config.setPath("/api/b/postHello");
            config.setMethod("POST");

            //config.setContentType("application/json");
            // config.setAccept("application/json");
            //2. 请求体：POST,请求String
            Object requestBody = "post 测试";
            // 覆盖header：text/plain
            Map<String, String> customHeaders = new HashMap<>();
            customHeaders.put("yzy", "yzy");
            config.setHeaders(customHeaders);
            //3. 指定返回类型，对应原来接口返回 Result
            Class<Result> responseType = Result.class;
            //4. feignInvoker是被@RequiredArgsConstructor注入的bean
            Result bDemoResponse = (Result) feignInvoker.invoke(config, requestBody, responseType);
            result.put("feignInvoker", bDemoResponse);
            result.put("status", "SUCCESS");
            log.info("Feign调用成功, traceId={}", traceId);
        } catch (Exception e) {
            log.error("Feign调用网关失败, traceId={}", traceId, e);
            result.put("feignInvoker", "ERROR: " + e.getMessage());
            result.put("status", "PARTIAL_SUCCESS");
        }

        Result<Map<String, Object>> r = Result.success(result);
        r.setTraceId(traceId);
        return r;
    }

}
