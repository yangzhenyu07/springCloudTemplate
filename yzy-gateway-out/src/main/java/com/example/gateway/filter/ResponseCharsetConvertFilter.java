package com.example.gateway.filter;

import com.example.gateway.constants.FilterConstants;
import lombok.extern.slf4j.Slf4j;
import org.springframework.cloud.gateway.filter.GatewayFilterChain;
import org.springframework.cloud.gateway.filter.GlobalFilter;
import org.springframework.core.Ordered;
import org.springframework.core.io.buffer.DataBuffer;
import org.springframework.core.io.buffer.DataBufferFactory;
import org.springframework.core.io.buffer.DataBufferUtils;
import org.springframework.http.HttpHeaders;
import org.springframework.http.MediaType;
import org.springframework.http.server.reactive.ServerHttpResponse;
import org.springframework.http.server.reactive.ServerHttpResponseDecorator;
import org.springframework.stereotype.Component;
import org.springframework.web.server.ServerWebExchange;
import reactor.core.publisher.Flux;
import reactor.core.publisher.Mono;

import java.nio.charset.Charset;
import java.nio.charset.StandardCharsets;
import java.util.Objects;

/**
 * 响应字符集转换全局过滤器
 * <p>
 * 与 {@link RequestCharsetConvertFilter} 配套使用，
 * 在响应返回给客户端之前，将响应体从UTF-8转换为目标系统字符集。
 * 例如A系统使用GBK，则响应体从UTF-8转换为GBK后再返回客户端。
 *
 * @author yzy
 * @version 1.1
 */
@Slf4j
@Component
public class ResponseCharsetConvertFilter implements GlobalFilter, Ordered {

    @Override
    public Mono<Void> filter(ServerWebExchange exchange, GatewayFilterChain chain) {
        // 从exchange attributes读取请求过滤器存储的源字符集
        String sourceCharsetName = exchange.getAttribute(FilterConstants.SOURCE_CHARSET_ATTR);
        String targetCharsetName = exchange.getAttribute(FilterConstants.TARGET_CHARSET_ATTR);

        if (Objects.equals(sourceCharsetName, targetCharsetName)) {
            return chain.filter(exchange);
        }

        Charset sourceCharset = Charset.forName(sourceCharsetName);
        Charset targetCharset = Charset.forName(targetCharsetName);
        log.info("【字符集转换-响应】sourceCharset={} , targetCharset={}, 开始包装响应装饰器", targetCharset.name(),sourceCharset.name());

        ServerHttpResponse response = exchange.getResponse();
        DataBufferFactory bufferFactory = response.bufferFactory();

        // 包装响应装饰器，拦截写入的响应体
        ServerHttpResponseDecorator decoratedResponse = new ServerHttpResponseDecorator(response) {
            @Override
            public Mono<Void> writeWith(org.reactivestreams.Publisher<? extends DataBuffer> body) {
                // 先用map转换DataBuffer，再用switchIfEmpty处理空body，最后flatMap写入
                // 避免flatMap返回Mono<Void>为空导致switchIfEmpty误触发
                return DataBufferUtils.join(Flux.from(body))
                        .map(joinedBuffer -> {
                            byte[] bytes = new byte[joinedBuffer.readableByteCount()];
                            joinedBuffer.read(bytes);
                            DataBufferUtils.release(joinedBuffer);

                            // UTF-8 → 目标字符集
                            String content = new String(bytes, targetCharset);
                            byte[] converted = content.getBytes(sourceCharset);
                            log.info("【字符集转换-响应】响应体转换完成, 原始{}字节→转换后{}字节, charset={}",
                                    bytes.length, converted.length, sourceCharset.name());

                            // 更新响应头Content-Type charset
                            HttpHeaders headers = getDelegate().getHeaders();
                            MediaType contentType = headers.getContentType();
                            if (contentType != null) {
                                headers.setContentType(new MediaType(
                                        contentType.getType(), contentType.getSubtype(), sourceCharset));
                            }
                            headers.setContentLength(converted.length);

                            return bufferFactory.wrap(converted);
                        })
                        .switchIfEmpty(Mono.defer(() -> {
                            log.info("【字符集转换-响应】响应体为空，跳过转换");
                            return Mono.empty();
                        }))
                        .flatMap(output -> getDelegate().writeWith(Mono.just(output)));
            }
        };

        return chain.filter(exchange.mutate().response(decoratedResponse).build());
    }

    @Override
    public int getOrder() {
        return -99;
    }
}
