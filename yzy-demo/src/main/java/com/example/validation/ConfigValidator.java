package com.example.validation;

import com.example.validation.annotation.ConfigRule;
import com.example.validation.config.RuleConfig;
import com.example.validation.config.RuleRegistry;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.lang.reflect.Field;
import java.lang.reflect.Modifier;
import java.util.ArrayList;
import java.util.List;

/**
 * 配置化场景校验器
 *
 * <p>按场景遍历 VO 上标注 {@link ConfigRule} 的字段，
 * 从 {@link RuleRegistry} 取该字段在本场景下的规则并执行；
 * 规则值全部来自 JSON 配置，代码零硬编码。</p>
 *
 * <p>关键约定：JSON 中未配置该 key → 该字段在该场景下不做校验（跳过并告警），
 * 使"配置缺失"可见但不阻断业务，避免配置漏配变成静默放行。</p>
 *
 * @author yzy
 */
public final class ConfigValidator {

    /** 日志 */
    private static final Logger LOGGER = LoggerFactory.getLogger(ConfigValidator.class);

    private ConfigValidator() {
    }

    /**
     * 校验并在存在违规时抛出 {@link SceneValidateException}
     *
     * @param target 待校验 VO
     * @param scene  校验场景
     */
    public static void validate(Object target, SceneEnum scene) {
        List<String> violations = validateToList(target, scene);
        if (!violations.isEmpty()) {
            throw new SceneValidateException(violations);
        }
    }

    /**
     * 校验并返回违规描述列表
     *
     * @param target 待校验 VO
     * @param scene  校验场景
     * @return 违规描述列表，空列表表示通过
     */
    public static List<String> validateToList(Object target, SceneEnum scene) {
        List<String> violations = new ArrayList<>();
        if (scene == null) {
            violations.add("校验场景不能为空");
            return violations;
        }
        if (target == null) {
            violations.add("待校验对象不能为空");
            return violations;
        }
        for (Field field : allFields(target.getClass())) {
            ConfigRule configRule = field.getAnnotation(ConfigRule.class);
            if (configRule == null) {
                continue;
            }
            String key = configRule.value().isEmpty() ? field.getName() : configRule.value();
            RuleConfig rule = RuleRegistry.rule(scene, key);
            if (rule == null) {
                LOGGER.warn("[校验配置] 场景{}未配置字段规则，已跳过，key={}", scene, key);
                continue;
            }
            applyRule(field, target, key, rule, violations);
        }
        return violations;
    }

    /**
     * 对单字段执行规则（非空 + 长度）
     *
     * @param field      字段
     * @param target     VO 实例
     * @param key        配置 key
     * @param rule       规则
     * @param violations 违规收集器
     */
    private static void applyRule(Field field, Object target, String key, RuleConfig rule, List<String> violations) {
        Object value = readField(field, target);
        if (Boolean.TRUE.equals(rule.getNotNull()) && isEmptyValue(value)) {
            violations.add(field.getName() + ": " + defaultMessage(rule, "不能为空"));
            return;
        }
        if (value == null) {
            return;
        }
        int len = String.valueOf(value).length();
        int min = rule.getMinLen() == null ? 0 : rule.getMinLen();
        int max = rule.getMaxLen() == null ? Integer.MAX_VALUE : rule.getMaxLen();
        if (len < min || len > max) {
            violations.add(field.getName() + ": " + defaultMessage(rule, "长度需在[" + min + "," + max + "]之间，实际为" + len));
        }
    }

    /**
     * 优先使用配置文案，未配置时用默认提示
     *
     * @param rule      规则
     * @param defaultTip 默认提示
     * @return 提示文案
     */
    private static String defaultMessage(RuleConfig rule, String defaultTip) {
        return rule.getMessage() == null || rule.getMessage().isEmpty() ? defaultTip : rule.getMessage();
    }

    /**
     * 收集类层级上的全部实例字段（含父类，排除 static 与合成字段）
     *
     * @param type VO 类型
     * @return 字段列表
     */
    private static List<Field> allFields(Class<?> type) {
        List<Field> fields = new ArrayList<>();
        for (Class<?> current = type; current != null && current != Object.class; current = current.getSuperclass()) {
            for (Field field : current.getDeclaredFields()) {
                if (!Modifier.isStatic(field.getModifiers()) && !field.isSynthetic()) {
                    fields.add(field);
                }
            }
        }
        return fields;
    }

    /**
     * 反射读取字段值
     *
     * @param field  字段
     * @param target VO 实例
     * @return 字段值
     */
    private static Object readField(Field field, Object target) {
        try {
            field.setAccessible(true);
            return field.get(target);
        } catch (IllegalAccessException e) {
            throw new IllegalStateException("读取字段失败: " + field.getName(), e);
        }
    }

    /**
     * 判空：null 视为空；字符串去空白后为空也视为空
     *
     * @param value 字段值
     * @return true = 空
     */
    private static boolean isEmptyValue(Object value) {
        if (value == null) {
            return true;
        }
        return value instanceof CharSequence && value.toString().trim().isEmpty();
    }
}
