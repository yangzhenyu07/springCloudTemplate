package com.example.cloud.trace;

import com.example.common.trace.TraceIdUtil;
import feign.RequestInterceptor;
import feign.RequestTemplate;

/**
 * OpenFeign TraceId 传递拦截器
 * <p>
 * 在 Feign 调用时，自动将当前 MDC 中的 traceId 写入请求头，
 * 实现跨服务的全链路 traceId 传递。
 *
 * @author yzy
 */
public class FeignTraceInterceptor implements RequestInterceptor {

    @Override
    public void apply(RequestTemplate template) {
        String traceId = TraceIdUtil.getTraceId();
        if (traceId != null && !traceId.isEmpty()) {
            template.header(TraceIdUtil.TRACE_ID_HEADER, traceId);
        }
    }
}
