package com.example.validation.annotation;

import com.example.validation.SceneEnum;

import java.lang.annotation.Documented;
import java.lang.annotation.ElementType;
import java.lang.annotation.Retention;
import java.lang.annotation.RetentionPolicy;
import java.lang.annotation.Target;

/**
 * 配置化校验切入点注解（方法级）
 *
 * <p>标注在 Service 方法上声明本方法所用场景，
 * 由切面在方法执行前按规则配置校验指定 VO 参数。</p>
 *
 * @author yzy
 */
@Target(ElementType.METHOD)
@Retention(RetentionPolicy.RUNTIME)
@Documented
public @interface ConfigCheck {

    /**
     * 本方法对应的校验场景
     *
     * @return 校验场景
     */
    SceneEnum value();

    /**
     * 待校验 VO 在方法参数列表中的下标，默认第一个参数
     *
     * @return 参数下标
     */
    int argIndex() default 0;
}
