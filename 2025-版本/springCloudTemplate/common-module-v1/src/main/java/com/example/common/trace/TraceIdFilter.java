package com.example.common.trace;

import jakarta.servlet.*;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import java.io.IOException;

/**
 * Servlet TraceId 过滤器
 * <p>
 * 从请求头 X-Trace-Id 获取 traceId，没有则生成新的，
 * 放入 MDC 供日志使用，并写入响应头返回给调用方。
 *
 * @author yzy
 */
public class TraceIdFilter implements Filter {

    @Override
    public void doFilter(ServletRequest servletRequest, ServletResponse servletResponse, FilterChain chain)
            throws IOException, ServletException {

        HttpServletRequest request = (HttpServletRequest) servletRequest;
        HttpServletResponse response = (HttpServletResponse) servletResponse;

        // 从请求头获取 traceId，没有则生成
        String traceId = request.getHeader(TraceIdUtil.TRACE_ID_HEADER);
        TraceIdUtil.setTraceId(traceId);

        // 写入响应头
        response.setHeader(TraceIdUtil.TRACE_ID_HEADER, TraceIdUtil.getTraceId());

        try {
            chain.doFilter(servletRequest, servletResponse);
        } finally {
            TraceIdUtil.clearTraceId();
        }
    }
}
