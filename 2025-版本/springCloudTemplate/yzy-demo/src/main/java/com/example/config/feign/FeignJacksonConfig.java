package com.example.config.feign;

import com.alibaba.fastjson2.JSONWriter;
import com.alibaba.fastjson2.support.config.FastJsonConfig;
import com.alibaba.fastjson2.support.spring6.http.converter.FastJsonHttpMessageConverter;
import org.springframework.context.annotation.Configuration;
import org.springframework.http.MediaType;
import org.springframework.http.converter.HttpMessageConverter;
import org.springframework.web.servlet.config.annotation.WebMvcConfigurer;

import java.util.ArrayList;
import java.util.List;

/**
 * Feign/MVC JSON 消息转换器（fastjson2 / Spring6）
 * <p>
 * 原实现基于 fastjson v1，迁移到 fastjson2 官方 Spring6 扩展：
 * <ul>
 *     <li>NotWriteDefaultValue：序列化时不输出 Java 对象默认值字段</li>
 *     <li>循环引用检测：fastjson2 默认关闭（等价原 DisableCircularReferenceDetect）</li>
 * </ul>
 *
 * @author yangzhenyu
 * @version 2.0
 * @description:
 * @date 2026/9/5 13:59
 */
@Configuration
public class FeignJacksonConfig implements WebMvcConfigurer {

    @Override
    public void extendMessageConverters(List<HttpMessageConverter<?>> converters) {

        FastJsonHttpMessageConverter fastJsonHttpMessageConverter = new FastJsonHttpMessageConverter();
        FastJsonConfig fastJsonConfig = new FastJsonConfig();
        fastJsonConfig.setWriterFeatures(
                JSONWriter.Feature.NotWriteDefaultValue // 序列化时，不输出 Java 对象中的默认值字段。
        );
        fastJsonHttpMessageConverter.setFastJsonConfig(fastJsonConfig);
        List<MediaType> mediaTypes = new ArrayList<>();
        mediaTypes.add(MediaType.APPLICATION_JSON);
        fastJsonHttpMessageConverter.setSupportedMediaTypes(mediaTypes);
        // 放到最前面，优先使用 fastjson2
        converters.add(0, fastJsonHttpMessageConverter);
    }

}
