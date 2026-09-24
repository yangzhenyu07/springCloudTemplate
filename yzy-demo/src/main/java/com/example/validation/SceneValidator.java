package com.example.validation;

import com.example.validation.annotation.SceneLength;
import com.example.validation.annotation.SceneNotNull;

import java.lang.reflect.Field;
import java.lang.reflect.Modifier;
import java.util.ArrayList;
import java.util.List;

/**
 * 场景校验器（核心引擎）
 *
 * <p>按场景扫描 VO 字段上的 {@link SceneNotNull} / {@link SceneLength} 注解，
 * 只执行命中当前场景的规则，聚合全部违规项。
 * 纯静态工具、无 Spring 依赖，可独立单测，也可被 AOP 切面复用。</p>
 *
 * @author yzy
 */
public final class SceneValidator {

    private SceneValidator() {
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
     * 校验并返回违规描述列表（不抛异常，便于调用方自行处理）
     *
     * @param target 待校验 VO
     * @param scene  校验场景
     * @return 违规描述列表，空列表表示校验通过
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
            checkNotNull(field, target, scene, violations);
            checkLength(field, target, scene, violations);
        }
        return violations;
    }

    /**
     * 执行单字段的场景化非空规则
     *
     * @param field      字段
     * @param target     VO 实例
     * @param scene      当前场景
     * @param violations 违规收集器
     */
    private static void checkNotNull(Field field, Object target, SceneEnum scene, List<String> violations) {
        SceneNotNull rule = field.getAnnotation(SceneNotNull.class);
        if (rule == null || !containsScene(rule.scenes(), scene)) {
            return;
        }
        if (isEmptyValue(readField(field, target))) {
            violations.add(field.getName() + ": " + (rule.message().isEmpty() ? "不能为空" : rule.message()));
        }
    }

    /**
     * 执行单字段的场景化长度规则（null 值跳过，交由非空规则约束）
     *
     * @param field      字段
     * @param target     VO 实例
     * @param scene      当前场景
     * @param violations 违规收集器
     */
    private static void checkLength(Field field, Object target, SceneEnum scene, List<String> violations) {
        SceneLength rule = field.getAnnotation(SceneLength.class);
        if (rule == null || !containsScene(rule.scenes(), scene)) {
            return;
        }
        Object value = readField(field, target);
        if (value == null) {
            return;
        }
        int len = String.valueOf(value).length();
        if (len < rule.min() || len > rule.max()) {
            String tip = rule.message().isEmpty()
                    ? "长度需在[" + rule.min() + "," + rule.max() + "]之间，实际为" + len
                    : rule.message();
            violations.add(field.getName() + ": " + tip);
        }
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
     * 判断规则是否命中当前场景
     *
     * @param scenes 规则声明的场景列表
     * @param scene  当前场景
     * @return true = 命中
     */
    private static boolean containsScene(SceneEnum[] scenes, SceneEnum scene) {
        for (SceneEnum item : scenes) {
            if (item == scene) {
                return true;
            }
        }
        return false;
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
