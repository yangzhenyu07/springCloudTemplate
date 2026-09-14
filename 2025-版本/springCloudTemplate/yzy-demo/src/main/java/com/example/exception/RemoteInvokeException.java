package com.example.exception;

import lombok.Getter;

/**
 * 远程调用异常
 *
 * @author Dell
 * @version 1.0
 */
@Getter
public class RemoteInvokeException extends RuntimeException {

    /**
     * HTTP 方法
     */
    private final String method;

    /**
     * 服务名称
     */
    private final String serviceName;

    /**
     * 请求路径
     */
    private final String path;

    /**
     * HTTP 状态码
     */
    private final Integer status;

    /**
     * 服务端响应内容
     */
    private final String responseBody;

    public RemoteInvokeException(
            String message,
            String method,
            String serviceName,
            String path,
            Integer status,
            String responseBody,
            Throwable cause) {

        super(message, cause);

        this.method = method;
        this.serviceName = serviceName;
        this.path = path;
        this.status = status;
        this.responseBody = responseBody;
    }
}