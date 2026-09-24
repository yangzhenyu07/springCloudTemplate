package com.example.validation.annotation;

import com.example.validation.SceneEnum;

import java.lang.annotation.Documented;
import java.lang.annotation.ElementType;
import java.lang.annotation.Retention;
import java.lang.annotation.RetentionPolicy;
import java.lang.annotation.Target;

/**
 * 场景校验切入点注解（方法级）
 *
 * <p>标注在 Service 方法上，由 AOP 切面在方法执行前对指定位置的 VO 参数
 * 按声明场景做校验，业务方法体内不出现任何校验 if 判断。</p>
 *
 * @author yzy
 */
@Target(ElementType.METHOD)
@Retention(RetentionPolicy.RUNTIME)
@Documented
public @interface SceneCheck {

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
