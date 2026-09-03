package com.example.gateway.filter;

import com.example.gateway.config.LocalMsgCane;
import com.example.gateway.constants.FilterConstants;
import com.example.gateway.utils.GatewayHttpUtil;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.cloud.gateway.filter.GatewayFilterChain;
import org.springframework.cloud.gateway.filter.GlobalFilter;
import org.springframework.core.Ordered;
import org.springframework.core.io.buffer.DataBuffer;
import org.springframework.core.io.buffer.DataBufferFactory;
import org.springframework.core.io.buffer.DataBufferUtils;
import org.springframework.http.HttpHeaders;
import org.springframework.http.MediaType;
import org.springframework.http.server.reactive.ServerHttpRequest;
import org.springframework.http.server.reactive.ServerHttpRequestDecorator;
import org.springframework.stereotype.Component;
import org.springframework.web.server.ServerWebExchange;
import reactor.core.publisher.Flux;
import reactor.core.publisher.Mono;

import java.nio.charset.Charset;
import java.nio.charset.StandardCharsets;

/**
 * 请求字符集转换全局过滤器
 * <p>
 * 不同系统使用不同字符编码（如A系统GBK，B系统UTF-8），
 * 网关层统一将请求体从源字符集转换为UTF-8，避免后端服务各自处理字符集问题。
 * 通过请求头 {@code X-System-Code} 判断属于哪个系统。
 * <p>
 * 直接使用 DataBufferUtils.join 读取请求体，不依赖 CacheRequestBodyGatewayFilterFactory。
 *
 * @author yzy
 * @version 1.1
 */
@Slf4j
@Component
public class RequestCharsetConvertFilter implements GlobalFilter, Ordered {

    @Autowired
    private LocalMsgCane localMsgCane;

    @Override
    public Mono<Void> filter(ServerWebExchange exchange, GatewayFilterChain chain) {
        // 读取系统标识
        String systemCode = exchange.getRequest().getHeaders().getFirst(FilterConstants.SYSTEM_CODE_HEADER);
        // 获取对应系统要转的编码格式
        Charset targetCharset = FilterConstants.getCharsetBySystemCode(systemCode,localMsgCane);
        // 当前请求编码
        Charset requestHeadersCharset = GatewayHttpUtil.getRequestHeadersCharset(exchange.getRequest());
        if (requestHeadersCharset == null){
            requestHeadersCharset = StandardCharsets.UTF_8;
        }

        // 存储源字符集到exchange attributes，供响应过滤器使用
        exchange.getAttributes().put(FilterConstants.SOURCE_CHARSET_ATTR, requestHeadersCharset.name());
        exchange.getAttributes().put(FilterConstants.TARGET_CHARSET_ATTR, targetCharset.name());

        // 源字符集为UTF-8时无需转换
        if (targetCharset == requestHeadersCharset) {
            log.info("【字符集转换-请求】systemCode={}, sourceCharset={}, targetCharset={}, 无需转换",systemCode,requestHeadersCharset.name(), targetCharset.name() );
            return chain.filter(exchange);
        }

        log.info("【字符集转换-请求】systemCode={}, sourceCharset={}, targetCharset={}",systemCode, requestHeadersCharset.name(), targetCharset.name());

        // 直接读取请求体
        Charset finalRequestHeadersCharset = requestHeadersCharset;
        return DataBufferUtils.join(exchange.getRequest().getBody())
                .flatMap(dataBuffer -> {
                    // 读取原始字节并转换字符集
                    byte[] originBytes = new byte[dataBuffer.readableByteCount()];
                    dataBuffer.read(originBytes);
                    DataBufferUtils.release(dataBuffer);

                    String bodyStr = new String(originBytes, finalRequestHeadersCharset);
                    byte[] convertedBytes = bodyStr.getBytes(targetCharset);
                    log.info("【字符集转换-请求】请求体转换完成, 原始{}字节→转换后{}字节, charset={}→{}}",
                            originBytes.length, convertedBytes.length, finalRequestHeadersCharset.name(),targetCharset.name());

                    DataBufferFactory bufferFactory = exchange.getResponse().bufferFactory();

                    // 构造装饰请求，下游看到的是对应系统编码的请求体
                    ServerHttpRequest decoratedRequest = new ServerHttpRequestDecorator(exchange.getRequest()) {
                        @Override
                        public Flux<DataBuffer> getBody() {
                            return Flux.just(bufferFactory.wrap(convertedBytes));
                        }

                        @Override
                        public HttpHeaders getHeaders() {
                            HttpHeaders headers = new HttpHeaders();
                            headers.putAll(exchange.getRequest().getHeaders());
                            headers.setContentLength(convertedBytes.length);
                            MediaType contentType = exchange.getRequest().getHeaders().getContentType();
                            if (contentType != null) {
                                headers.setContentType(new MediaType(
                                        contentType.getType(), contentType.getSubtype(), targetCharset));
                            }
                            return headers;
                        }
                    };

                    return chain.filter(exchange.mutate().request(decoratedRequest).build());
                })
                .switchIfEmpty(Mono.defer(() -> {
                    // GET请求等无body场景，仅记录字符集，不转换请求体
                    log.info("【字符集转换-请求】无请求体，仅记录字符集");
                    return chain.filter(exchange);
                }));
    }

    @Override
    public int getOrder() {
        return -100;
    }
}
