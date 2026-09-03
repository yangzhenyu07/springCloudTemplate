package com.example.gateway.config.nacos;

import java.lang.annotation.ElementType;
import java.lang.annotation.Retention;
import java.lang.annotation.RetentionPolicy;
import java.lang.annotation.Target;

/**
 * Nacos JSON 配置
 *
 * @author yangzhenyu
 * @version 1.0
 * @date 2026/8/21
 */
@Target(ElementType.FIELD)
@Retention(RetentionPolicy.RUNTIME)
public @interface NacosConfig {

    /**
     * Nacos 配置 dataId
     */
    String dataId();

    /**
     * JSON 路径
     * 例如：
     * a.b.c
     */
    String value() default "";

    /**
     * Nacos group
     */
    String group() default "DEFAULT_GROUP";
}