package com.example.config;

import com.alibaba.cloud.commons.lang.StringUtils;
import com.fasterxml.jackson.annotation.JsonInclude;
import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.PropertyNamingStrategies;
import com.fasterxml.jackson.datatype.jsr310.JavaTimeModule;
import feign.Client;
import feign.Request;
import feign.Response;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Component;

import java.io.ByteArrayOutputStream;
import java.io.IOException;
import java.io.InputStream;
import java.nio.charset.Charset;
import java.text.SimpleDateFormat;
import java.util.*;
import java.util.concurrent.TimeUnit;

/**
 * @author Dell
 * @version 1.0
 * @date 2026/8/12 15:44
 */
@Component
@RequiredArgsConstructor
@Slf4j
public class FeignInvoker_copy {

    private static final int DEFAULT_CONNECT_TIMEOUT_MS = 3000;
    private static final int DEFAULT_READ_TIMEOUT_MS = 3000;

    private final Client feignClient;
    private final ObjectMapper objectMapper;

    public Object invoke(RemoteInvokeConfig config, Object requestBody, Class responseType){
        try {
            return doFeignCall(config, requestBody, responseType);
        } catch (JsonProcessingException e) {
            log.error("【公共逻辑FeignInvoker.invoke】系统异常，",e);
            return null;
        }
    }

    private Object doFeignCall(RemoteInvokeConfig config, Object requestBody, Class responseType) throws JsonProcessingException {
        Request.HttpMethod httpMethod = parseMethod(config.getMethod());
        String url = buildUri(config.getServiceName(), config.getPath());
        if (log.isInfoEnabled()){
            log.info("【公共逻辑FeignInvoker.doFeignCall】url is {}", url);
        }

        int connectMs = config.getConnectTimeoutMillis() != null ? config.getConnectTimeoutMillis() : DEFAULT_CONNECT_TIMEOUT_MS;
        int readMs = config.getReadTimeoutMillis() != null ? config.getReadTimeoutMillis() : DEFAULT_READ_TIMEOUT_MS;
        Request.Options options = new Request.Options(connectMs, TimeUnit.MILLISECONDS, readMs, TimeUnit.MILLISECONDS, true);

        String charsetName = StringUtils.isBlank(config.getCharset()) ? "UTF-8" : config.getCharset();
        Charset charset = Charset.forName(charsetName);
        byte[] bodyBytes = buildRequestBody(httpMethod, requestBody, charsetName);
        Map<String, Collection<String>> headers = mergeHeaders(config.getHeaders(), bodyBytes);

        Request request = Request.create(httpMethod, url, headers, bodyBytes, charset);
        try (Response response = feignClient.execute(request, options)){
            // 负载均衡实际选中的节点：FeignBlockingLoadBalancerClient会将服务名替换为真实host:port
            String actualUrl = (response.request() != null) ? response.request().url() : url;
            log.info("【公共逻辑FeignInvoker.doFeignCall】负载均衡路由: {} -> {}", url, actualUrl);
            int status = response.status();
            byte[] raw = readBodyBytes(response);
            String bodyText = raw == null || raw.length == 0 ? null : new String(raw, charset);
            if (log.isInfoEnabled()){
                log.info("【公共逻辑FeignInvoker.doFeignCall】bodyText is {}", bodyText);
            }

            if(status< 200 || status > 299){
                throw new IllegalArgumentException("http call failed");
            }
            return mapSuccessResponse(bodyText, raw, responseType);
        } catch (Exception e) {
            log.error("【公共逻辑FeignInvoker.doFeignCall】系统异常，",e);
            throw new IllegalArgumentException("http call error"); // todo 异常处理
        }
    }

    private static Request.HttpMethod parseMethod(String method){
        if (method == null || StringUtils.isBlank(method)){
            throw new IllegalArgumentException("method not be null");
        }
        try {
            return Request.HttpMethod.valueOf(method.trim().toUpperCase(Locale.ROOT));
        } catch (Exception e){
            throw new IllegalArgumentException("unsupport http method");
        }
    }

    private static String buildUri(String serviceName, String path){
        if(serviceName == null || StringUtils.isBlank(serviceName)){
            throw new IllegalArgumentException("serviceName not be null");
        }
        String host = serviceName.trim();
        while (host.endsWith("/")){
            host = host.substring(0, host.length()-1);
        }
        String p = (path == null || StringUtils.isBlank(serviceName)) ? "/" : path.trim();
        if(!p.startsWith("/")){
            p = "/" + p;
        }
        return "http://" + host + p;
    }

    private Map<String, Collection<String>> mergeHeaders(Map<String, String> custom, byte[] bodyBytes){
        Map<String, Collection<String>> merged = new LinkedHashMap<>();
        merged.put("Content-Type", list("application/json"));
        merged.put("Accept", list("application/json"));
        if(custom != null){
            for(Map.Entry<String, String> e : custom.entrySet()){
                if(e.getKey()!=null && !StringUtils.isBlank(e.getKey()) && e.getValue()!= null){
                    merged.put(e.getKey(), list(e.getValue()));
                }
                if("Content-Length".equals(e.getKey())){
                    merged.put("Content-Length", list(String.valueOf(bodyBytes.length)));
                }
            }
        }
        return merged;
    }

    private static List<String> list(String v) {
        return Collections.singletonList(v);
    }

    private byte[] buildRequestBody(Request.HttpMethod method, Object requestBody, String charsetName) throws JsonProcessingException {
        if(requestBody == null){
            return null;
        }
        ObjectMapper cusObjectMapper = new ObjectMapper();
        ObjectMapper includeObjectMapper = cusObjectMapper.setSerializationInclusion(JsonInclude.Include.NON_EMPTY);
        cusObjectMapper.registerModule(new JavaTimeModule());
        // 使用指定字符集进行编码
        String json = includeObjectMapper.writeValueAsString(requestBody);
        return json.getBytes(Charset.forName(charsetName));
    }

    private static byte[] readBodyBytes(Response response) throws IOException {
        if (response.body() == null) {
            return null;
        }
        try (InputStream in = response.body().asInputStream()) {
            ByteArrayOutputStream bos = new ByteArrayOutputStream();
            byte[] buffer = new byte[4096];
            int len;
            while ((len = in.read(buffer)) != -1) {
                bos.write(buffer, 0, len);
            }
            return bos.toByteArray();
        }
    }

    private Object mapSuccessResponse(String bodyText, byte[] raw, Class responseType) throws Exception{
        if(responseType == null){
            throw new IllegalArgumentException("responseType must not be null");
        }
        if(bodyText == null){
            return null;
        }
        objectMapper.setDateFormat(new SimpleDateFormat("yyyy-MM-dd"));
        objectMapper.setPropertyNamingStrategy(PropertyNamingStrategies.LOWER_CAMEL_CASE);
        Object o = objectMapper.readValue(bodyText, responseType);
        return o;
    }
}