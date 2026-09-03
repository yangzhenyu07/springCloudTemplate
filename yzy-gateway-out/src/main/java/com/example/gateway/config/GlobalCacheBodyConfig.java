package com.example.gateway.config;

import com.example.gateway.constants.FilterConstants;
import lombok.extern.slf4j.Slf4j;
import org.springframework.cloud.gateway.filter.GlobalFilter;
import org.springframework.cloud.gateway.support.ServerWebExchangeUtils;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.core.annotation.Order;

/**
 * 网关全局配置
 *
 * @author Dell
 * @version 1.1
 * @date 2026/8/11 16:06
 */
@Slf4j
@Configuration
public class GlobalCacheBodyConfig {

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
            String path = exchange.getRequest().getPath().value();
            String methodValue = exchange.getRequest().getMethodValue();
            log.info("【对外网关】接受请求 path:{},method:{}",path,methodValue);
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
