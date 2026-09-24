package com.example.validation.config;

import lombok.Data;

/**
 * 单个字段（key）的规则配置
 *
 * <p>对应 JSON 中 {@code scenes.<场景>.<字段key>} 的值，
 * 是该字段在本场景下的规则全集（非空 + 长度区间 + 失败文案）。</p>
 *
 * <p>全部字段均可缺省，缺省表示该维度不做约束。</p>
 *
 * @author yzy
 */
@Data
public class RuleConfig {

    /**
     * 是否必填
     */
    private Boolean notNull;

    /**
     * 最小长度（含），缺省不限
     */
    private Integer minLen;

    /**
     * 最大长度（含），缺省不限
     */
    private Integer maxLen;

    /**
     * 自定义失败文案，缺省使用默认提示
     */
    private String message;
}
