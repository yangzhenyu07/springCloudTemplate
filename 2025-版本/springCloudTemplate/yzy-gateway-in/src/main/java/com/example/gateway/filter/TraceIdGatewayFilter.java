package com.example.gateway.filter;

import com.example.gateway.constants.FilterConstants;
import org.slf4j.MDC;
import org.springframework.cloud.gateway.filter.GatewayFilterChain;
import org.springframework.cloud.gateway.filter.GlobalFilter;
import org.springframework.core.Ordered;
import org.springframework.http.server.reactive.ServerHttpRequest;
import org.springframework.http.server.reactive.ServerHttpResponse;
import org.springframework.stereotype.Component;
import org.springframework.web.server.ServerWebExchange;
import reactor.core.publisher.Mono;

import java.util.UUID;

/**
 * 网关全链路 TraceId 过滤器（WebFlux）
 * <p>
 * 从请求头 X-Trace-Id 获取 traceId，没有则生成新的，
 * 写入下游请求头和上游响应头，实现全链路 traceId 传递。
 *
 * @author yzy
 */
@Component
public class TraceIdGatewayFilter implements GlobalFilter, Ordered {



    @Override
    public Mono<Void> filter(ServerWebExchange exchange, GatewayFilterChain chain) {
        ServerHttpRequest request = exchange.getRequest();

        // 从请求头获取 traceId，没有则生成
        String traceId = request.getHeaders().getFirst(FilterConstants.TRACE_ID_HEADER);
        if (traceId == null || traceId.isEmpty()) {
            traceId = UUID.randomUUID().toString().replace("-", "");
        }

        // 写入 MDC 供日志使用
        MDC.put(FilterConstants.TRACE_ID_KEY, traceId);

        // 将 traceId 写入下游请求头
        ServerHttpRequest mutatedRequest = request.mutate()
                .header(FilterConstants.TRACE_ID_HEADER, traceId)
                .build();

        // 将 traceId 写入响应头
        ServerHttpResponse response = exchange.getResponse();
        response.getHeaders().add(FilterConstants.TRACE_ID_HEADER, traceId);


        return chain.filter(exchange.mutate().request(mutatedRequest).build())
                .doFinally(signalType -> MDC.remove(FilterConstants.TRACE_ID_KEY));
    }

    @Override
    public int getOrder() {
        return Ordered.HIGHEST_PRECEDENCE;
    }
}
