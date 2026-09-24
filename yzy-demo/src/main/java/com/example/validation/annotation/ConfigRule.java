package com.example.validation.annotation;

import java.lang.annotation.Documented;
import java.lang.annotation.ElementType;
import java.lang.annotation.Retention;
import java.lang.annotation.RetentionPolicy;
import java.lang.annotation.Target;

/**
 * 配置化字段校验注解（字段级）
 *
 * <p>注解本身<b>不携带任何规则值</b>，只携带"寻址 key"——
 * 真正的规则（必填、长度区间、失败文案）配置在 validation-rules.json 中，
 * 以 {@code 场景 -> 字段key -> 规则} 的字段维度组织。</p>
 *
 * <p>一个 VO 上有多少个待校验字段，就写多少个本注解（字段维度），
 * 同一个 key 也可以被多个字段共用，改配置即可同时生效。</p>
 *
 * @author yzy
 */
@Target(ElementType.FIELD)
@Retention(RetentionPolicy.RUNTIME)
@Documented
public @interface ConfigRule {

    /**
     * 规则寻址 key
     *
     * <p>缺省为"" 时使用字段名本身作为 key，
     * 便于不同 VO 之间复用同一批配置（如两个 VO 的 remark 共用一个 key）。</p>
     *
     * @return 配置 key
     */
    String value() default "";
}
