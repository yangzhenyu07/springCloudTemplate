package com.example.gateway.utils;

import org.springframework.http.HttpHeaders;
import org.springframework.http.MediaType;
import org.springframework.http.server.reactive.ServerHttpRequest;

import java.nio.charset.Charset;

/**
 * @author Dell
 * @version 1.0
 * @date 2026/8/11 20:54
 */
public class GatewayHttpUtil {

    public static Charset getRequestHeadersCharset(ServerHttpRequest request){
        if (request == null){
            return null;
        }
        HttpHeaders httpHeaders = request.getHeaders();
        MediaType contentType = httpHeaders.getContentType();
        if (contentType == null){
            return null;
        }
        return contentType.getCharset();
    }
}
