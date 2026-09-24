package com.example.validation.config;

import com.example.validation.SceneEnum;
import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.DeserializationFeature;
import com.fasterxml.jackson.databind.ObjectMapper;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.io.IOException;
import java.io.InputStream;
import java.util.Collections;
import java.util.EnumMap;
import java.util.HashMap;
import java.util.Map;
import java.util.concurrent.atomic.AtomicReference;

/**
 * 校验规则注册表
 *
 * <p>启动时由 {@code RuleConfigLoader} 一次性装载，运行期只读。
 * 数据结构为两级：场景 -> 字段key -> 规则集合，
 * <b>同一个字段 key 可以被多个字段注解引用，规则集中一处修改即可</b>。</p>
 *
 * @author yzy
 */
public final class RuleRegistry {

    /** 日志 */
    private static final Logger LOGGER = LoggerFactory.getLogger(RuleRegistry.class);

    /** ObjectMapper 线程安全，静态复用 */
    private static final ObjectMapper MAPPER = new ObjectMapper()
            .configure(DeserializationFeature.FAIL_ON_UNKNOWN_PROPERTIES, false);

    /** 规则快照容器：整体替换，保证读取的一致性 */
    private static final AtomicReference<Holder> HOLDER = new AtomicReference<>(Holder.EMPTY);

    private RuleRegistry() {
    }

    /**
     * 装载规则文件（可重复调用，后一次覆盖前一次）
     *
     * @param in JSON 输入流
     * @return 成功装载的场景数量
     * @throws IOException JSON 解析失败
     */
    public static int load(InputStream in) throws IOException {
        RuleConfigFile file = MAPPER.readValue(in, new TypeReference<RuleConfigFile>() {
        });
        Map<SceneEnum, Map<String, RuleConfig>> parsed = new EnumMap<>(SceneEnum.class);
        if (file.getScenes() != null) {
            for (Map.Entry<String, Map<String, RuleConfig>> entry : file.getScenes().entrySet()) {
                SceneEnum scene = parseScene(entry.getKey());
                if (scene == null) {
                    continue;
                }
                Map<String, RuleConfig> fieldRules = entry.getValue() == null
                        ? Collections.<String, RuleConfig>emptyMap() : new HashMap<>(entry.getValue());
                parsed.put(scene, fieldRules);
            }
        }
        HOLDER.set(new Holder(file.getVersion(), parsed));
        return parsed.size();
    }

    /**
     * 查询某场景下某字段 key 的规则
     *
     * @param scene 场景
     * @param key   字段 key
     * @return 规则；null 表示该场景未配置该 key（调用方跳过校验）
     */
    public static RuleConfig rule(SceneEnum scene, String key) {
        Map<String, RuleConfig> fieldRules = HOLDER.get().rules.get(scene);
        return fieldRules == null ? null : fieldRules.get(key);
    }

    /**
     * 当前配置版本号
     *
     * @return 版本号
     */
    public static String version() {
        return HOLDER.get().version;
    }

    /**
     * 是否已装载规则
     *
     * @return true = 已装载
     */
    public static boolean loaded() {
        return HOLDER.get() != Holder.EMPTY;
    }

    /**
     * 获取全部规则快照（只读）
     *
     * @return 场景 -> 字段key -> 规则
     */
    public static Map<SceneEnum, Map<String, RuleConfig>> snapshot() {
        return Collections.unmodifiableMap(HOLDER.get().rules);
    }

    /**
     * 场景名转枚举，未知场景名打印异常并跳过（避免非法配置拖垮整体装载）
     *
     * @param sceneName 场景名
     * @return 场景枚举；null = 未知场景
     */
    private static SceneEnum parseScene(String sceneName) {
        try {
            return SceneEnum.valueOf(sceneName);
        } catch (IllegalArgumentException e) {
            LOGGER.error("[校验配置] 未知场景名，已跳过该场景规则，scene={}", sceneName, e);
            return null;
        }
    }

    /**
     * 规则快照持有对象（version + 两级规则映射）
     */
    private static final class Holder {

        /** 空快照：未装载时的默认值 */
        private static final Holder EMPTY = new Holder(null, Collections.<SceneEnum, Map<String, RuleConfig>>emptyMap());

        /** 配置版本 */
        private final String version;

        /** 场景 -> 字段key -> 规则 */
        private final Map<SceneEnum, Map<String, RuleConfig>> rules;

        /**
         * 构造快照
         *
         * @param version 版本号
         * @param rules   两级规则映射
         */
        private Holder(String version, Map<SceneEnum, Map<String, RuleConfig>> rules) {
            this.version = version;
            this.rules = rules;
        }
    }
}
