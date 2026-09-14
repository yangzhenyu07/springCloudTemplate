package com.example.config;

import com.alibaba.fastjson2.support.config.FastJsonConfig;
import com.alibaba.fastjson2.support.spring6.http.converter.FastJsonHttpMessageConverter;
import org.springframework.context.annotation.Configuration;
import org.springframework.http.MediaType;
import org.springframework.http.converter.HttpMessageConverter;
import org.springframework.web.servlet.config.annotation.WebMvcConfigurer;

import java.util.Collections;
import java.util.List;

/**
 * MVC JSON 消息转换器（fastjson2 / Spring6）
 * <p>
 * 原实现基于 fastjson v1（com.alibaba.fastjson.support.spring），
 * fastjson v1 不支持 Spring Boot 3 / Jakarta Servlet 6，
 * 迁移到 fastjson2 官方 Spring6 扩展
 * {@link com.alibaba.fastjson2.support.spring6.http.converter.FastJsonHttpMessageConverter}。
 * 原 SerializerFeature.SkipTransientField 对应 fastjson2 默认行为
 * （transient/static 字段默认不参与序列化），无需额外配置。
 *
 * @author yangzhenyu
 * @version 2.0
 * @description:
 * @date 2026/9/5 13:39
 */
@Configuration
public class ControllerJacksonConfig implements WebMvcConfigurer {

    @Override
    public void extendMessageConverters(List<HttpMessageConverter<?>> converters) {

        // 创建 fastjson2 转换器
        FastJsonHttpMessageConverter converter =
                new FastJsonHttpMessageConverter();
        // 配置 fastjson2（transient 字段默认跳过，与 fastjson v1 SkipTransientField 语义一致）
        FastJsonConfig config = new FastJsonConfig();
        converter.setFastJsonConfig(config);
        // 只处理 application/json
        converter.setSupportedMediaTypes(
                Collections.singletonList(MediaType.APPLICATION_JSON)
        );
        // 放到最前面，优先使用 fastjson2
        converters.add(0, converter);
    }
}
