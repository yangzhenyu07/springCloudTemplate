package com.example.config;

import lombok.Data;

import java.util.Map;


/**
 * 远程调用配置
 *
 * @author Dell
 * @version 1.0
 * @date 2026/8/12
 */
@Data
public class RemoteInvokeConfig {

    /**
     * 服务名称
     *
     * 例如：
     * yzy-gateway
     */
    private String serviceName;

    /**
     * 请求路径
     *
     * 例如：
     * /api/b/postHello
     */
    private String path;

    /**
     * HTTP 请求方法
     *
     * 例如：
     * GET、POST、PUT、DELETE
     */
    private String method;

    /**
     * 连接超时时间，单位：毫秒
     */
    private Integer connectTimeoutMillis;

    /**
     * 读取超时时间，单位：毫秒
     */
    private Integer readTimeoutMillis;

    /**
     * Content-Type
     *
     * 例如：
     * application/json
     * text/plain;charset=UTF-8
     * application/x-www-form-urlencoded
     */
    private String contentType;

    /**
     * Accept
     *
     * 例如：
     * application/json
     * text/plain
     * */
    private String accept;

    /**
     * 自定义请求 Header
     *
     * 用于：
     * Authorization
     * traceId
     * tenantId
     * token
     * 等业务 Header
     */
    private Map<String, String> headers;

    /**
     * 请求字符集
     *
     * 默认 UTF-8
     */
    private String charset;
}