package com.example.common.enums;

/**
 * 统一响应码枚举
 *
 * @author yzy
 */
public enum ResultCode {

    SUCCESS(200, "成功"),
    FAILED(500, "系统异常"),
    PARAM_ERROR(400, "参数校验失败"),
    UNAUTHORIZED(401, "未认证"),
    FORBIDDEN(403, "无权限"),
    NOT_FOUND(404, "资源不存在"),
    SERVICE_ERROR(503, "服务不可用");

    private final int code;
    private final String message;

    ResultCode(int code, String message) {
        this.code = code;
        this.message = message;
    }

    public int getCode() {
        return code;
    }

    public String getMessage() {
        return message;
    }
}
