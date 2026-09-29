package com.example.controller;

import com.alibaba.fastjson.JSON;
import com.example.api.feign.TestApiClient;
import com.example.api.vo.ApiSdkVoRep;
import com.example.api.vo.ApiSdkVoRes;
import io.swagger.annotations.Api;
import lombok.extern.slf4j.Slf4j;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

/**
 * api sdk 测试接口
 *
 * <p>实现 {@link TestApiClient} 的目的是让「HTTP 接口」与「对外 SDK 契约」在同一份签名上对齐：
 * 一旦改动方法签名而没同步 yzy-demo-api，这里会直接编译失败，而不是等到调用方报 404/序列化错。
 *
 * @author yangzhenyu
 * @version 1.0
 */
@Api(value = "api sdk 测试", tags = {"api sdk 测试"})
@Slf4j
@RestController
@RequestMapping("api/sdk")
public class TestApiController implements TestApiClient {

    @Override
    @PostMapping("/apiTest")
    public ApiSdkVoRep apiTest(@RequestBody ApiSdkVoRes res) {
        log.info("传参:{}", JSON.toJSONString(res));

        ApiSdkVoRep apiSdkVoRep = new ApiSdkVoRep();
        apiSdkVoRep.setId("222");
        apiSdkVoRep.setName("yangzhenyu");
        return apiSdkVoRep;
    }
}
