package com.example.validation.annotation;

import com.example.validation.SceneEnum;

import java.lang.annotation.Documented;
import java.lang.annotation.ElementType;
import java.lang.annotation.Retention;
import java.lang.annotation.RetentionPolicy;
import java.lang.annotation.Target;

/**
 * 场景化非空校验注解（字段级）
 *
 * <p>仅当当前校验场景命中 {@link #scenes()} 之一时，才要求字段非空；
 * 字符串类型额外要求去空白后非空。同一字段可声明多个场景。</p>
 *
 * @author yzy
 */
@Target(ElementType.FIELD)
@Retention(RetentionPolicy.RUNTIME)
@Documented
public @interface SceneNotNull {

    /**
     * 生效场景列表（命中任一即校验）
     *
     * @return 场景数组
     */
    SceneEnum[] scenes();

    /**
     * 校验失败提示，为空时使用默认提示"不能为空"
     *
     * @return 提示信息
     */
    String message() default "";
}
