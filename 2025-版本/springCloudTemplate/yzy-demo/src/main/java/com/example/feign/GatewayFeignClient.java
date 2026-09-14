package com.example.feign;

import com.example.common.result.Result;
import org.springframework.cloud.openfeign.FeignClient;
import org.springframework.web.bind.annotation.GetMapping;

/**
 * 网关服务Feign客户端
 * 通过OpenFeign调用yzy-gateway服务，网关再路由到yzy-b-demo
 *
 * @author yzy
 * @version 1.0
 */
@FeignClient(name = "yzy-gateway-in", contextId = "gatewayFeignClient")
public interface GatewayFeignClient {

    /**
     * 通过网关调用yzy-b-demo的hello接口
     *
     * @return yzy-b-demo返回的信息
     */
    @GetMapping("/api/b/hello")
    Result callBDemoHello();
}
