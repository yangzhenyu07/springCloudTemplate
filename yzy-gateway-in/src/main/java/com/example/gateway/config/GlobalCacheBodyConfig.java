package com.example.gateway.config;

import com.example.gateway.constants.FilterConstants;
import lombok.extern.slf4j.Slf4j;
import org.springframework.cloud.gateway.filter.GatewayFilter;
import org.springframework.cloud.gateway.filter.GlobalFilter;
import org.springframework.cloud.gateway.filter.factory.CacheRequestBodyGatewayFilterFactory;
import org.springframework.cloud.gateway.support.ServerWebExchangeUtils;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.core.annotation.Order;

/**
 * @author Dell
 * @version 1.0
 * @date 2026/8/11 16:06
 */
@Slf4j
@Configuration
public class GlobalCacheBodyConfig {


    public CacheRequestBodyGatewayFilterFactory cacheBodyFactory;

    public GlobalCacheBodyConfig(CacheRequestBodyGatewayFilterFactory cacheBodyFactory){
        this.cacheBodyFactory = cacheBodyFactory;
    }

    /*
    **
    * @description: 缓冲请求过滤器
    * @param:
    * @return:
    * @author Dell
    * @date: 2026/8/11 17:24
    */
    @Bean
    @Order(-2000)
    public GlobalFilter cacheRequestBodyGlobalFilter(){
        CacheRequestBodyGatewayFilterFactory.Config config = cacheBodyFactory.newConfig();
        GatewayFilter gatewayFilter = cacheBodyFactory.apply(config);
        return gatewayFilter::filter;
    }

    /*
    **
    * @description: 请求耗时统计过滤器、记录每个请求的处理耗时
    * @param: 
    * @return: 
    * @author Dell
    * @date: 2026/8/11 20:18
    */
    
    @Bean
    @Order(-1)
    public GlobalFilter startTimeGlobalFilter(){
        return (exchange,chain) ->{
            long start = System.currentTimeMillis();
            exchange.getAttributes().put(FilterConstants.START_TIME_ATTR,start);
            return chain.filter(exchange).doFinally(signalType -> {
                Long startT = exchange.getAttribute(FilterConstants.START_TIME_ATTR);
                if (startT == null){
                    return;
                }
                long end = System.currentTimeMillis();
                long cost = end - startT;
                log.info("下游服务{}耗时:{}ms",exchange.getAttributes().get(ServerWebExchangeUtils.GATEWAY_REQUEST_URL_ATTR),cost);
            });
        };
    }


    
}
