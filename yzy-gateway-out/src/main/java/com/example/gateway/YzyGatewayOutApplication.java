package com.example.gateway;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.cloud.client.discovery.EnableDiscoveryClient;

/**
 * yzy-gateway 网关服务启动类
 * Spring Cloud Gateway + Nacos(注册中心/配置中心)
 * 路由 /api/b/** → yzy-b-demo
 *
 * @author yzy
 * @version 1.0
 */
@EnableDiscoveryClient
@SpringBootApplication
public class YzyGatewayOutApplication {

    public static void main(String[] args) {
        SpringApplication.run(YzyGatewayOutApplication.class, args);
    }
}
