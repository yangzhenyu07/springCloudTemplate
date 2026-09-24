package com.example.validation.config;

import com.example.validation.SceneEnum;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;

import javax.annotation.PostConstruct;
import java.io.IOException;
import java.io.InputStream;
import java.util.Map;

/**
 * 校验规则启动加载器
 *
 * <p>应用启动时读取 JSON 规则文件并完成 {@link RuleRegistry} 装载；
 * 装载失败按 fail-fast 处理——规则缺失会让校验静默失效，比启动失败危害更大。</p>
 *
 * @author yzy
 */
@Slf4j
@Component
public class RuleConfigLoader {

    /** 规则文件路径（classpath 相对）：缺省值保证脱离 Spring 容器（如单测 new 出来）也能工作 */
    @Value("${validation.rule.path:validation-rules.json}")
    private String ruleFilePath = "validation-rules.json";

    /**
     * 启动加载：读取 classpath 规则文件并写入注册表
     *
     * @throws IOException 文件缺失或解析失败
     */
    @PostConstruct
    public void load() throws IOException {
        try (InputStream in = RuleConfigLoader.class.getClassLoader().getResourceAsStream(ruleFilePath)) {
            if (in == null) {
                throw new IllegalStateException("校验规则文件不存在: classpath:" + ruleFilePath);
            }
            int sceneCount = RuleRegistry.load(in);
            log.info("[校验配置] 规则加载完成，file={}, version={}, 场景数={}", ruleFilePath, RuleRegistry.version(), sceneCount);
        }
    }

    /**
     * 获取当前生效的场景 -> 字段规则快照（只读，便于排障与自检）
     *
     * @return 场景到字段规则的映射
     */
    public Map<SceneEnum, Map<String, RuleConfig>> snapshot() {
        return RuleRegistry.snapshot();
    }
}
