package com.example.api.config;


import com.alibaba.fastjson2.support.spring6.http.converter.FastJsonHttpMessageConverter;
import feign.codec.Decoder;
import feign.codec.Encoder;
import org.springframework.beans.factory.ObjectFactory;
import org.springframework.boot.autoconfigure.http.HttpMessageConverters;
import org.springframework.cloud.openfeign.support.SpringDecoder;
import org.springframework.cloud.openfeign.support.SpringEncoder;
import org.springframework.context.annotation.Bean;
import org.springframework.http.MediaType;
import org.springframework.http.converter.HttpMessageConverter;

import java.util.ArrayList;
import java.util.List;
public class FeignFastJsonCodecConfig {
    public FeignFastJsonCodecConfig() {
    }

    @Bean
    public Encoder feignEncoder() {
        FastJsonHttpMessageConverter converter = new FastJsonHttpMessageConverter();
        List<MediaType> mediaTypes = new ArrayList<>();
        mediaTypes.add(MediaType.APPLICATION_JSON);
        mediaTypes.add(MediaType.APPLICATION_JSON_UTF8);
        converter.setSupportedMediaTypes(mediaTypes);
        ObjectFactory<HttpMessageConverters> factory = () -> new HttpMessageConverters(new HttpMessageConverter[]{converter});
        return new SpringEncoder(factory);
    }

    @Bean
    public Decoder feignDecoder() {
        FastJsonHttpMessageConverter converter = new FastJsonHttpMessageConverter();
        List<MediaType> mediaTypes = new ArrayList<>();
        mediaTypes.add(MediaType.APPLICATION_JSON);
        mediaTypes.add(MediaType.APPLICATION_JSON_UTF8);
        converter.setSupportedMediaTypes(mediaTypes);
        ObjectFactory<HttpMessageConverters> factory = () -> new HttpMessageConverters(new HttpMessageConverter[]{converter});
        return new SpringDecoder(factory);
    }
}