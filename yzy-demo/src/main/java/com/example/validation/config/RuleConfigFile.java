package com.example.validation.config;

import lombok.Data;

import java.util.Map;

/**
 * 校验规则配置文件根节点
 *
 * <p>反序列化 validation-rules.json 的目标对象，结构为两级 Map：
 * {@code scenes: { 场景名: { 字段key: RuleConfig } }}。</p>
 *
 * @author yzy
 */
@Data
public class RuleConfigFile {

    /**
     * 配置版本号（便于灰度、日志追踪）
     */
    private String version;

    /**
     * 配置说明
     */
    private String desc;

    /**
     * 场景 -> 字段key -> 规则集合
     */
    private Map<String, Map<String, RuleConfig>> scenes;
}
