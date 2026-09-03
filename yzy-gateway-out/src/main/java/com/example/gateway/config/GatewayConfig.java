package com.example.gateway.config;

import org.springframework.cloud.gateway.route.InMemoryRouteDefinitionRepository;
import org.springframework.cloud.gateway.route.RouteDefinitionRepository;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

/**
 * @author yangzhenyu
 * @version 1.0
 * @date 2026/8/15 10:32
 */
@Configuration
public class GatewayConfig {


    @Bean
    public RouteDefinitionRepository routeDefinitionRepository(){
        //  内存版路由仓库，路由全部存在 JVM 内存
        return new InMemoryRouteDefinitionRepository();
    }
}
