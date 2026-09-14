package com.example.config;

import com.alibaba.fastjson.serializer.SerializerFeature;
import com.alibaba.fastjson.support.config.FastJsonConfig;
import com.alibaba.fastjson.support.spring.FastJsonHttpMessageConverter;
import org.springframework.context.annotation.Configuration;
import org.springframework.http.MediaType;
import org.springframework.http.converter.HttpMessageConverter;
import org.springframework.web.servlet.config.annotation.WebMvcConfigurer;

import java.util.Collections;
import java.util.List;

/**
 * @author yangzhenyu
 * @version 1.0
 * @description:
 * @date 2026/9/5 13:39
 */
@Configuration
public class ControllerJacksonConfig implements WebMvcConfigurer {

    @Override
    public void extendMessageConverters(List<HttpMessageConverter<?>> converters) {

        // 创建 FastJSON 转换器
        FastJsonHttpMessageConverter converter =
                new FastJsonHttpMessageConverter();
        // 配置 FastJSON
        FastJsonConfig config = new FastJsonConfig();

        // transient 修饰的字段不参与 JSON 序列化
        config.setSerializerFeatures(
                SerializerFeature.SkipTransientField
        );
        converter.setFastJsonConfig(config);
        // 只处理 application/json
        converter.setSupportedMediaTypes(
                Collections.singletonList(MediaType.APPLICATION_JSON)
        );
        // 放到最前面，优先使用 FastJSON
        converters.add(0, converter);
    }
}
