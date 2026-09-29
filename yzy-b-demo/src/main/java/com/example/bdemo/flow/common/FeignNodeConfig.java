package com.example.bdemo.flow.common;

import lombok.Data;

import java.util.Map;

@Data
public class FeignNodeConfig {
    private String serverId;
    private String apiPatch;
    private String method;
    private String timeoutMs;
    private String nodeCode;
    private String charset;
    private Map<String,String> headers;
}