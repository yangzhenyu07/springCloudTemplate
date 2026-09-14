package com.example.common.trace;

import org.slf4j.MDC;

import java.util.UUID;

/**
 * 全链路 TraceId 工具类
 * <p>
 * 使用 MDC（Mapped Diagnostic Context）在日志中传递 traceId，
 * 通过 HTTP Header X-Trace-Id 在服务间传播。
 *
 * @author yzy
 */
public final class TraceIdUtil {

    public static final String TRACE_ID_KEY = "traceId";
    public static final String TRACE_ID_HEADER = "X-Trace-Id";

    private TraceIdUtil() {
    }

    /**
     * 生成新的 traceId（32位无横线 UUID）
     */
    public static String generateTraceId() {
        return UUID.randomUUID().toString().replace("-", "");
    }

    /**
     * 获取当前 MDC 中的 traceId
     */
    public static String getTraceId() {
        return MDC.get(TRACE_ID_KEY);
    }

    /**
     * 设置 traceId 到 MDC
     */
    public static void setTraceId(String traceId) {
        if (traceId == null || traceId.isEmpty()) {
            traceId = generateTraceId();
        }
        MDC.put(TRACE_ID_KEY, traceId);
    }

    /**
     * 清除 MDC 中的 traceId
     */
    public static void clearTraceId() {
        MDC.remove(TRACE_ID_KEY);
    }

    /**
     * 如果 MDC 中没有 traceId 则生成一个新的
     */
    public static String ensureTraceId() {
        String traceId = getTraceId();
        if (traceId == null || traceId.isEmpty()) {
            traceId = generateTraceId();
            setTraceId(traceId);
        }
        return traceId;
    }
}
