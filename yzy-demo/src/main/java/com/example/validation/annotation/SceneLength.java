package com.example.validation.annotation;

import com.example.validation.SceneEnum;

import java.lang.annotation.Documented;
import java.lang.annotation.ElementType;
import java.lang.annotation.Retention;
import java.lang.annotation.RetentionPolicy;
import java.lang.annotation.Target;

/**
 * 场景化长度校验注解（字段级）
 *
 * <p>仅当当前校验场景命中 {@link #scenes()} 之一时，才校验字段值长度
 * （按 {@code String.valueOf(value).length()} 计）。字段值为 null 时跳过，
 * null 约束由 {@link SceneNotNull} 表达，两类规则职责分离。</p>
 *
 * @author yzy
 */
@Target(ElementType.FIELD)
@Retention(RetentionPolicy.RUNTIME)
@Documented
public @interface SceneLength {

    /**
     * 生效场景列表（命中任一即校验）
     *
     * @return 场景数组
     */
    SceneEnum[] scenes();

    /**
     * 最小长度（含）
     *
     * @return 最小长度
     */
    int min() default 0;

    /**
     * 最大长度（含）
     *
     * @return 最大长度
     */
    int max() default Integer.MAX_VALUE;

    /**
     * 校验失败提示，为空时使用默认提示（含允许区间与实际长度）
     *
     * @return 提示信息
     */
    String message() default "";
}
