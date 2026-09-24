package com.example.config;

import org.apache.commons.lang3.StringUtils;
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
import java.util.regex.Matcher;
import java.util.regex.Pattern;

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

    /**
     * 未被 Spring Cloud LoadBalancer 包装的原生 Feign 客户端。
     * 仅在 serviceName 为 IP/host:port（如 127.0.0.1:8089、localhost:9000）时使用，
     * 绕过 LB 直接发请求，避免 LoadBalancer 把 IP 当服务名去 Nacos 查实例导致 503。
     */
    private static final Client DIRECT_CLIENT = new Client.Default(null, null);

    /**
     * host:port 形式的直连地址识别（绕过 LB）。
     * 仅做形式识别，不会发起 DNS / 网络探测。
     */
    private static final Pattern HOST_PORT_PATTERN = Pattern.compile("^(.+):(\\d+)(/)?$");

    /**
     * 严格 IPv4 字面量识别（每段 0-255）。拒绝 999.999.999.999 等非法值。
     * 仅做字符串判断，无网络探测。
     */
    private static final Pattern IPV4_PATTERN = Pattern.compile(
            "^(?:(?:25[0-5]|2[0-4]\\d|[01]?\\d\\d?)\\.){3}(?:25[0-5]|2[0-4]\\d|[01]?\\d\\d?)$");

    /**
     * 解析后的 serviceName：direct=true 时 baseUrl 已含 scheme+host+port，可直接拼 path；
     * direct=false 时 baseUrl 为原服务名，由 LoadBalancer 解析。
     */
    private record ServiceTarget(boolean direct, String baseUrl) {}

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
        ServiceTarget target = parseServiceTarget(config.getServiceName());
        String url = buildUri(target, config.getPath());
        // 命中 IP/host:port 时使用未包装的 Client.Default，绕过 Spring Cloud LoadBalancer
        Client client = target.direct() ? DIRECT_CLIENT : feignClient;
        if (log.isInfoEnabled()){
            log.info("【公共逻辑FeignInvoker.doFeignCall】url is {}, direct={}", url, target.direct());
        }

        int connectMs = config.getConnectTimeoutMillis() != null ? config.getConnectTimeoutMillis() : DEFAULT_CONNECT_TIMEOUT_MS;
        int readMs = config.getReadTimeoutMillis() != null ? config.getReadTimeoutMillis() : DEFAULT_READ_TIMEOUT_MS;
        Request.Options options = new Request.Options(connectMs, TimeUnit.MILLISECONDS, readMs, TimeUnit.MILLISECONDS, true);

        String charsetName = StringUtils.isBlank(config.getCharset()) ? "UTF-8" : config.getCharset();
        Charset charset = Charset.forName(charsetName);
        byte[] bodyBytes = buildRequestBody(httpMethod, requestBody, charsetName);
        Map<String, Collection<String>> headers = mergeHeaders(config.getHeaders(), bodyBytes);

        Request request = Request.create(httpMethod, url, headers, bodyBytes, charset);
        try (Response response = client.execute(request, options)){
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

    private static String buildUri(ServiceTarget target, String path){
        if (target == null || target.baseUrl() == null || target.baseUrl().isEmpty()){
            throw new IllegalArgumentException("serviceName not be null");
        }
        String base = target.baseUrl();
        while (base.endsWith("/")){
            base = base.substring(0, base.length()-1);
        }
        String p = (path == null || StringUtils.isBlank(path)) ? "/" : path.trim();
        if(!p.startsWith("/")){
            p = "/" + p;
        }
        return base + p;
    }

    /**
     * 把 serviceName 解析为可寻址目标（方案 A：端口存在 + 严格 IPv4 正则）。
     * <ul>
     *   <li>已带 http:// / https:// 前缀 → direct=true，原样作为 baseUrl</li>
     *   <li>形如 host:port（如 127.0.0.1:8089、localhost:9000）→ direct=true，拼出 http://host:port</li>
     *   <li>严格 IPv4 字面量无端口（如 127.0.0.1）→ direct=true，默认端口 80</li>
     *   <li>其他（如 yzy-gateway-in）→ 服务名，direct=false，走 LoadBalancer</li>
     * </ul>
     * 不发起 DNS / 网络探测；端口超出 1-65535 视为非法。
     */
    private static ServiceTarget parseServiceTarget(String serviceName){
        if (serviceName == null) {
            throw new IllegalArgumentException("serviceName not be null");
        }
        String s = serviceName.trim();
        if (s.isEmpty()) {
            throw new IllegalArgumentException("serviceName not be null");
        }
        // 1) 已带 http(s):// 前缀 → 按直连处理，原样作为 baseUrl（path 由 buildUri 拼接）
        if (s.regionMatches(true, 0, "http://", 0, 7) || s.regionMatches(true, 0, "https://", 0, 8)) {
            return new ServiceTarget(true, s);
        }
        // 2) host:port 形式 → 直连
        Matcher m = HOST_PORT_PATTERN.matcher(s);
        if (m.matches()) {
            String host = m.group(1);
            int port;
            try {
                port = Integer.parseInt(m.group(2));
            } catch (NumberFormatException e) {
                throw new IllegalArgumentException("invalid port: " + m.group(2));
            }
            if (port < 1 || port > 65535) {
                throw new IllegalArgumentException("invalid port: " + port);
            }
            return new ServiceTarget(true, "http://" + host + ":" + port);
        }
        // 3) 严格 IPv4 字面量（无端口）→ 直连 80
        if (IPV4_PATTERN.matcher(s).matches()) {
            return new ServiceTarget(true, "http://" + s + ":80");
        }
        // 4) 其他 → 服务名，走 LoadBalancer
        //    baseUrl 也必须含 scheme，否则 RetryableFeignBlockingLoadBalancerClient 会拒绝：
        //    "Request URI does not contain a valid hostname"
        return new ServiceTarget(false, "http://" + s);
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