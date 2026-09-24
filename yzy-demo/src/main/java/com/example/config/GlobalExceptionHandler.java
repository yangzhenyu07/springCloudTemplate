package com.example.config;

import com.example.common.enums.ResultCode;
import com.example.common.result.Result;
import com.example.common.trace.TraceIdUtil;
import lombok.extern.slf4j.Slf4j;
import org.springframework.web.bind.MethodArgumentNotValidException;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.RestControllerAdvice;

/**
 * yzy-demo 全局异常处理器
 *
 * <p>职责：把所有未捕获异常统一转换为 {@link Result} JSON 响应
 * （带 traceId），避免 Spring 默认错误页/错误 JSON 泄露内部细节、
 * 且保证调用方（前端/网关/测试脚本）拿到一致的响应结构。</p>
 *
 * <p>注意：本处理器不吞异常——所有异常均记录 ERROR 日志（含堆栈与 traceId），
 * 只是在 HTTP 响应层做统一格式化。</p>
 *
 * @author yzy
 * @version 1.0
 */
@Slf4j
@RestControllerAdvice
public class GlobalExceptionHandler {

    /**
     * 参数校验失败（@Valid + @NotBlank/@Size）
     *
     * <p>返回 400 语义的 PARAM_ERROR，message 携带第一条校验失败原因，
     * 便于调用方定位问题字段。</p>
     *
     * @param e 参数校验异常
     * @return 统一响应（code=400）
     */
    @ExceptionHandler(MethodArgumentNotValidException.class)
    public Result<Void> handleValidException(MethodArgumentNotValidException e) {
        String message = e.getBindingResult().getFieldErrors().isEmpty()
                ? "参数校验失败"
                : e.getBindingResult().getFieldErrors().get(0).getDefaultMessage();
        log.warn("[全局异常] 参数校验失败，traceId={}, message={}", TraceIdUtil.getTraceId(), message);
        Result<Void> r = Result.failed(ResultCode.PARAM_ERROR, message);
        r.setTraceId(TraceIdUtil.getTraceId());
        return r;
    }

    /**
     * 兜底异常处理
     *
     * <p>典型场景：交易中心 DB 落库异常（如报文超长触发回滚）。
     * 事务已由业务层回滚，Redis 幂等 key 保留等待 3 天过期（需求 2.3），
     * 同 idemKey 的重试请求会被幂等层判重拒绝。</p>
     *
     * @param e 未捕获异常
     * @return 统一响应（code=500，message 不透出内部异常细节）
     */
    @ExceptionHandler(Exception.class)
    public Result<Void> handleException(Exception e) {
        String traceId = TraceIdUtil.getTraceId();
        log.error("[全局异常] 未捕获异常，traceId={}", traceId, e);
        Result<Void> r = Result.failed(ResultCode.FAILED);
        r.setTraceId(traceId);
        return r;
    }
}
