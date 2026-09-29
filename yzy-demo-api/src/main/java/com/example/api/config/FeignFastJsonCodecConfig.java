package com.example.api.config;

import com.alibaba.fastjson.support.config.FastJsonConfig;
import com.alibaba.fastjson.support.spring.FastJsonHttpMessageConverter;
import feign.codec.Decoder;
import feign.codec.Encoder;
import org.springframework.beans.factory.ObjectFactory;
import org.springframework.boot.autoconfigure.http.HttpMessageConverters;
import org.springframework.cloud.openfeign.support.SpringDecoder;
import org.springframework.cloud.openfeign.support.SpringEncoder;
import org.springframework.context.annotation.Bean;
import org.springframework.http.MediaType;
import org.springframework.http.converter.HttpMessageConverter;

import java.nio.charset.StandardCharsets;
import java.util.Collections;
import java.util.List;

/**
 * Feign 使用 fastjson 做 JSON 编解码的配置类
 *
 * <p><b>为什么这个类刻意不加 {@code @Configuration}</b>：
 * yzy-demo / yzy-b-demo 的 {@code @SpringBootApplication(scanBasePackages = "com.example")}
 * 会扫到 {@code com.example.api.config}，一旦标注 @Configuration 被主容器加载，
 * 这里的 {@code feignEncoder}/{@code feignDecoder} 就会成为全局 bean，
 * 而 {@code FeignClientsConfiguration} 里同名 bean 是 {@code @ConditionalOnMissingBean}，
 * 结果是<b>所有</b> Feign 客户端的编解码器被静默替换掉。不加注解则只能通过显式引用生效。
 *
 * <p>两种启用方式（二选一）：
 * <ol>
 *   <li>只对某个客户端生效：{@code @FeignClient(..., configuration = FeignFastJsonCodecConfig.class)}；</li>
 *   <li>对全部客户端生效：在使用方启动类上加 {@code @Import(FeignFastJsonCodecConfig.class)}（想清楚了再加）。</li>
 * </ol>
 *
 * <p>依赖说明：用的是 {@code com.alibaba:fastjson:2.0.47}（fastjson1 兼容坐标）里的
 * {@code com.alibaba.fastjson.support.spring.FastJsonHttpMessageConverter}。
 * 不要换成 {@code fastjson2-extension-spring6} —— 那是 jakarta / Spring 6 的，
 * 和当前 Spring Boot 2.6.15(Spring 5.3) 不兼容。
 *
 * @author yangzhenyu
 * @version 1.0
 */
public class FeignFastJsonCodecConfig {

    /**
     * 构造 Feign 编码器（请求体 JSON 序列化）
     *
     * @return SpringEncoder，内部消息转换器列表以 fastjson 打头
     */
    @Bean
    public Encoder feignEncoder() {
        return new SpringEncoder(feignHttpMessageConverters());
    }

    /**
     * 构造 Feign 解码器（响应体 JSON 反序列化）
     *
     * @return SpringDecoder，内部消息转换器列表以 fastjson 打头
     */
    @Bean
    public Decoder feignDecoder() {
        return new SpringDecoder(feignHttpMessageConverters());
    }

    /**
     * 组装 Feign 专用的消息转换器工厂
     *
     * <p>关键点：{@link HttpMessageConverters} 会把「额外传入的转换器」排在默认转换器<b>之前</b>
     * （实测顺序：fastjson → ByteArray → String → ... → MappingJackson2，Jackson 在倒数第二位），
     * 所以 fastjson 会先于 Jackson 命中 application/json，替换才真正生效。
     *
     * @return HttpMessageConverters 的对象工厂
     */
    private ObjectFactory<HttpMessageConverters> feignHttpMessageConverters() {
        HttpMessageConverters converters = new HttpMessageConverters(fastJsonHttpMessageConverter());
        return () -> converters;
    }

    /**
     * 创建 fastjson 消息转换器
     *
     * @return 只支持 application/json、UTF-8 编码的 fastjson 转换器
     */
    private FastJsonHttpMessageConverter fastJsonHttpMessageConverter() {
        FastJsonConfig config = new FastJsonConfig();
        config.setCharset(StandardCharsets.UTF_8);

        FastJsonHttpMessageConverter converter = new FastJsonHttpMessageConverter();
        converter.setFastJsonConfig(config);
        List<MediaType> mediaTypes = Collections.singletonList(MediaType.APPLICATION_JSON);
        converter.setSupportedMediaTypes(mediaTypes);
        return converter;
    }
}
