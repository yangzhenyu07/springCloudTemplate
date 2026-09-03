package com.example.config;

import com.alibaba.cloud.commons.lang.StringUtils;
import com.example.common.trace.TraceIdUtil;
import com.example.exception.RemoteInvokeException;
import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.PropertyNamingStrategies;
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
import java.nio.charset.StandardCharsets;
import java.text.SimpleDateFormat;
import java.util.*;
import java.util.concurrent.TimeUnit;

/**
 * 通用 Feign HTTP 调用器
 *
 * <p>特点：</p>
 * <ul>
 *     <li>基于 Spring Cloud LoadBalancer 进行服务实例选择</li>
 *     <li>支持 application/json</li>
 *     <li>支持 text/plain</li>
 *     <li>支持 application/x-www-form-urlencoded</li>
 *     <li>支持 application/octet-stream</li>
 *     <li>支持自定义请求 Header</li>
 *     <li>支持自定义连接、读取超时</li>
 *     <li>支持 String、byte[]、JSON 对象响应</li>
 * </ul>
 *
 * @author Dell
 * @version 2.0
 * @date 2026/8/12
 */
@Component
@RequiredArgsConstructor
@Slf4j
public class FeignInvoker {

    private static final int DEFAULT_CONNECT_TIMEOUT_MS = 3000;
    private static final int DEFAULT_READ_TIMEOUT_MS = 3000;

    private static final String HEADER_CONTENT_TYPE = "Content-Type";
    private static final String HEADER_ACCEPT = "Accept";
    private static final String HEADER_CONTENT_LENGTH = "Content-Length";

    private static final String CONTENT_TYPE_JSON = "application/json";
    private static final String CONTENT_TYPE_TEXT = "text/plain";
    private static final String CONTENT_TYPE_FORM = "application/x-www-form-urlencoded";
    private static final String CONTENT_TYPE_OCTET_STREAM = "application/octet-stream";

    private final Client feignClient;
    private final ObjectMapper objectMapper;

    /**
     * 通用远程调用入口
     *
     * @param config      远程调用配置
     * @param requestBody 请求体
     * @param responseType 响应类型
     * @return 响应对象
     */
    public Object invoke(RemoteInvokeConfig config, Object requestBody, Class<?> responseType) {
        validateConfig(config);
        try {
            return doFeignCall(config, requestBody, responseType);
        } catch (RemoteInvokeException e) {
            // 已经是业务明确的远程调用异常，不重复包装
            throw e;
        } catch (Exception e) {
            log.error("【公共逻辑FeignInvoker.invoke】远程调用异常, method={}, serviceName={}, path={}",
                    config.getMethod(), config.getServiceName(), config.getPath(), e);
            throw new RemoteInvokeException(
                    "Feign remote call error",
                    config.getMethod(),
                    config.getServiceName(),
                    config.getPath(),
                    null,
                    null,
                    e
            );
        }
    }

    /**
     * 执行 Feign 调用
     */
    private Object doFeignCall(RemoteInvokeConfig config, Object requestBody, Class<?> responseType) throws Exception {
        Request.HttpMethod httpMethod = parseMethod(config.getMethod());

        /*
         * 注意：
         * 这里仍然使用 serviceName。
         * 例如：http://yzy-gateway/api/b/postHello
         * 不要在这里解析成具体 IP。
         * 后续由 FeignBlockingLoadBalancerClient + Spring Cloud LoadBalancer 完成实例选择。
         */
        String url = buildUri(config.getServiceName(), config.getPath());
        log.info("【公共逻辑FeignInvoker】准备远程调用, method={}, url={}", httpMethod, url);

        // 超时
        int connectMs = config.getConnectTimeoutMillis() != null
                ? config.getConnectTimeoutMillis()
                : DEFAULT_CONNECT_TIMEOUT_MS;
        int readMs = config.getReadTimeoutMillis() != null
                ? config.getReadTimeoutMillis()
                : DEFAULT_READ_TIMEOUT_MS;

        Request.Options options = new Request.Options(
                connectMs, TimeUnit.MILLISECONDS,
                readMs, TimeUnit.MILLISECONDS,
                true
        );

        Charset charset = resolveCharset(config.getCharset());
        String contentType = resolveContentType(config);
        byte[] bodyBytes = buildRequestBody(requestBody, contentType, charset);
        Map<String, Collection<String>> headers = mergeHeaders(config, contentType);

        // 自动传递 traceId 到下游服务（与 FeignTraceInterceptor 行为一致）
        String traceId = TraceIdUtil.getTraceId();
        if (StringUtils.isNotBlank(traceId)) {
            headers.put(TraceIdUtil.TRACE_ID_HEADER, list(traceId));
        }

        Request request = Request.create(httpMethod, url, headers, bodyBytes, charset);

        try (Response response = feignClient.execute(request, options)) {
            String actualUrl = response.request() != null ? response.request().url() : url;
            log.info("【公共逻辑FeignInvoker】负载均衡路由: {} -> {}", url, actualUrl);

            int status = response.status();
            byte[] raw = readBodyBytes(response);
            Charset responseCharset = resolveResponseCharset(response, charset);

            String bodyText = (raw == null || raw.length == 0) ? null : new String(raw, responseCharset);
            log.info("【公共逻辑FeignInvoker】远程响应, status={}, body={}", status, bodyText);

            if (status < 200 || status > 299) {
                log.error("method:{},serviceName:{},path:{},status:{},bodyText:{}", httpMethod.name(),
                        config.getServiceName(),
                        config.getPath(),
                        status,
                        bodyText);
                throw new RemoteInvokeException(
                        "HTTP remote call failed",
                        httpMethod.name(),
                        config.getServiceName(),
                        config.getPath(),
                        status,
                        bodyText,
                        null
                );
            }

            return mapResponse(bodyText, raw, responseType, responseCharset);
        }
    }

    /**
     * 校验配置
     */
    private void validateConfig(RemoteInvokeConfig config) {
        if (config == null) {
            throw new IllegalArgumentException("RemoteInvokeConfig must not be null");
        }
        if (StringUtils.isBlank(config.getMethod())) {
            throw new IllegalArgumentException("method must not be blank");
        }
        if (StringUtils.isBlank(config.getServiceName())) {
            throw new IllegalArgumentException("serviceName must not be blank");
        }
    }

    /**
     * 解析 HTTP Method
     */
    private static Request.HttpMethod parseMethod(String method) {
        if (StringUtils.isBlank(method)) {
            throw new IllegalArgumentException("method must not be blank");
        }
        try {
            return Request.HttpMethod.valueOf(method.trim().toUpperCase(Locale.ROOT));
        } catch (Exception e) {
            throw new IllegalArgumentException("Unsupported HTTP method: " + method, e);
        }
    }

    /**
     * 构造服务 URL，保留 serviceName，不解析真实 IP
     */
    private static String buildUri(String serviceName, String path) {
        if (StringUtils.isBlank(serviceName)) {
            throw new IllegalArgumentException("serviceName must not be blank");
        }
        String host = serviceName.trim();
        while (host.endsWith("/")) {
            host = host.substring(0, host.length() - 1);
        }
        String p = StringUtils.isBlank(path) ? "/" : path.trim();
        if (!p.startsWith("/")) {
            p = "/" + p;
        }
        return "http://" + host + p;
    }

    /**
     * 获取 Content‑Type，默认 JSON
     */
    private static String resolveContentType(RemoteInvokeConfig config) {
        if (!StringUtils.isBlank(config.getContentType())) {
            return config.getContentType().trim();
        }
        Map<String, String> customHeaders = config.getHeaders();
        if (customHeaders != null) {
            for (Map.Entry<String, String> entry : customHeaders.entrySet()) {
                if (entry.getKey() != null
                        && HEADER_CONTENT_TYPE.equalsIgnoreCase(entry.getKey())
                        && entry.getValue() != null) {
                    return entry.getValue().trim();
                }
            }
        }
        return CONTENT_TYPE_JSON;
    }

    /**
     * 合并请求 Header
     */
    private static Map<String, Collection<String>> mergeHeaders(RemoteInvokeConfig config, String contentType) {
        Map<String, Collection<String>> headers = new LinkedHashMap<>();
        headers.put(HEADER_CONTENT_TYPE, list(contentType));

        String accept = StringUtils.isBlank(config.getAccept()) ? CONTENT_TYPE_JSON : config.getAccept();
        headers.put(HEADER_ACCEPT, list(accept));

        Map<String, String> customHeaders = config.getHeaders();
        if (customHeaders == null) {
            return headers;
        }

        for (Map.Entry<String, String> entry : customHeaders.entrySet()) {
            String key = entry.getKey();
            String value = entry.getValue();
            if (StringUtils.isBlank(key) || value == null) {
                continue;
            }
            if (HEADER_CONTENT_TYPE.equalsIgnoreCase(key)) continue;
            if (HEADER_CONTENT_LENGTH.equalsIgnoreCase(key)) continue;
            if (HEADER_ACCEPT.equalsIgnoreCase(key)) continue;
            headers.put(key, list(value));
        }
        return headers;
    }

    private static List<String> list(String value) {
        return Collections.singletonList(value);
    }

    /**
     * 构造请求 Body，Content‑Type 决定编码方式
     */
    private byte[] buildRequestBody(Object requestBody, String contentType, Charset charset) throws JsonProcessingException {
        if (requestBody == null) {
            return null;
        }
        if (requestBody instanceof byte[]) {
            return (byte[]) requestBody;
        }
        if (isContentType(contentType, CONTENT_TYPE_TEXT)) {
            return String.valueOf(requestBody).getBytes(charset);
        }
        if (isContentType(contentType, CONTENT_TYPE_FORM)) {
            return buildFormBody(requestBody, charset);
        }
        if (isContentType(contentType, CONTENT_TYPE_JSON)) {
            String json = objectMapper.writeValueAsString(requestBody);
            return json.getBytes(charset);
        }
        if (isContentType(contentType, CONTENT_TYPE_OCTET_STREAM)) {
            if (requestBody instanceof String) {
                return ((String) requestBody).getBytes(charset);
            }
            return objectMapper.writeValueAsString(requestBody).getBytes(charset);
        }

        // 未知 Content‑Type
        if (requestBody instanceof String) {
            return ((String) requestBody).getBytes(charset);
        }
        return objectMapper.writeValueAsString(requestBody).getBytes(charset);
    }

    /**
     * 判断 Content‑Type，忽略 charset 后缀
     */
    private static boolean isContentType(String actual, String expected) {
        if (actual == null) {
            return false;
        }
        return actual.toLowerCase(Locale.ROOT).startsWith(expected.toLowerCase(Locale.ROOT));
    }

    /**
     * Form 表单请求体，只支持 Map
     */
    private byte[] buildFormBody(Object requestBody, Charset charset) {
        if (!(requestBody instanceof Map)) {
            throw new IllegalArgumentException("application/x-www-form-urlencoded requestBody must be Map");
        }
        Map<?, ?> map = (Map<?, ?>) requestBody;
        StringBuilder builder = new StringBuilder();
        for (Map.Entry<?, ?> entry : map.entrySet()) {
            if (builder.length() > 0) {
                builder.append("&");
            }
            builder.append(urlEncode(String.valueOf(entry.getKey()), charset));
            builder.append("=");
            builder.append(urlEncode(entry.getValue() == null ? "" : String.valueOf(entry.getValue()), charset));
        }
        return builder.toString().getBytes(charset);
    }

    private static String urlEncode(String value, Charset charset) {
        try {
            return java.net.URLEncoder.encode(value, charset.name());
        } catch (Exception e) {
            throw new IllegalArgumentException("URL encode error", e);
        }
    }

    /**
     * 读取响应 Body 字节
     */
    private static byte[] readBodyBytes(Response response) throws IOException {
        if (response.body() == null) {
            return null;
        }
        try (InputStream inputStream = response.body().asInputStream()) {
            ByteArrayOutputStream outputStream = new ByteArrayOutputStream();
            byte[] buffer = new byte[4096];
            int len;
            while ((len = inputStream.read(buffer)) != -1) {
                outputStream.write(buffer, 0, len);
            }
            return outputStream.toByteArray();
        }
    }

    /**
     * 解析响应字符集（当前复用请求字符集）
     */
    private static Charset resolveResponseCharset(Response response, Charset defaultCharset) {
        return defaultCharset;
    }

    /**
     * 响应体反序列化
     */
    private Object mapResponse(String bodyText, byte[] raw, Class<?> responseType, Charset charset) throws Exception {
        if (responseType == null) {
            throw new IllegalArgumentException("responseType must not be null");
        }
        if (raw == null || raw.length == 0) {
            return null;
        }
        if (responseType == byte[].class) {
            return raw;
        }
        if (responseType == String.class) {
            return new String(raw, charset);
        }

        objectMapper.setDateFormat(new SimpleDateFormat("yyyy-MM-dd"));
        objectMapper.setPropertyNamingStrategy(PropertyNamingStrategies.LOWER_CAMEL_CASE);
        return objectMapper.readValue(bodyText, responseType);
    }

    private static Charset resolveCharset(String charsetName) {
        if (StringUtils.isBlank(charsetName)) {
            return StandardCharsets.UTF_8;
        }
        try {
            return Charset.forName(charsetName.trim());
        } catch (Exception e) {
            throw new IllegalArgumentException("Unsupported charset: " + charsetName, e);
        }
    }
}