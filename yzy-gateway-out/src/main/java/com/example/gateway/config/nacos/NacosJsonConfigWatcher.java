package com.example.gateway.config.nacos;

import com.alibaba.cloud.nacos.NacosConfigManager;
import com.alibaba.fastjson2.JSON;
import com.alibaba.fastjson2.JSONObject;
import com.alibaba.nacos.api.config.ConfigService;
import com.alibaba.nacos.api.config.listener.Listener;
import com.alibaba.nacos.api.exception.NacosException;
import lombok.extern.slf4j.Slf4j;
import org.springframework.aop.support.AopUtils;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.config.BeanPostProcessor;
import org.springframework.stereotype.Component;
import org.springframework.util.ReflectionUtils;
import org.springframework.util.StringUtils;

import javax.annotation.PreDestroy;
import java.lang.reflect.Field;
import java.lang.reflect.Modifier;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.CopyOnWriteArrayList;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

/**
 * Nacos JSON 配置监听器
 * <p>
 * 一个 dataId + group 只注册一个 Listener。
 *
 * @author yangzhenyu
 * @version 1.0
 * @date 2026/8/24
 */
@Component
@Slf4j
public class NacosJsonConfigWatcher implements BeanPostProcessor {

    @Autowired
    private NacosConfigManager nacosConfigManager;

    /**
     * Nacos 默认 group
     */
    private static final String DEFAULT_GROUP = "DEFAULT_GROUP";

    /**
     * Nacos 配置读取超时时间
     */
    private static final long DEFAULT_TIMEOUT_MS = 3000L;

    /**
     * Nacos Listener 统一线程池
     */
    private final ExecutorService listenerExecutor = Executors.newFixedThreadPool(2);

    /**
     * dataId + group 作为key，一个配置对应一个 Listener
     */
    private final ConcurrentHashMap<String, ConfigRegistration> registrations = new ConcurrentHashMap<>();


    @Override
    public Object postProcessAfterInitialization(Object bean, String beanName) {
        // 解决 Bean 被 Spring AOP 代理后的问题
        Class<?> targetClass = AopUtils.getTargetClass(bean);
        if (targetClass == null) {
            targetClass = bean.getClass();
        }

        // Spring ReflectionUtils 支持遍历父类字段
        ReflectionUtils.doWithFields(targetClass, field -> processField(bean, field));
        return bean;
    }


    /**
     * 处理被 @NacosConfig 标记的字段
     */
    private void processField(Object bean, Field field) {
        NacosConfig annotation = field.getAnnotation(NacosConfig.class);
        if (annotation == null) {
            return;
        }

        validateField(field);

        String dataId = annotation.dataId();
        String group = StringUtils.hasText(annotation.group()) ? annotation.group() : DEFAULT_GROUP;
        String jsonPath = annotation.value();
        String registrationKey = dataId + "|" + group;

        FieldHolder holder = new FieldHolder(bean, field, dataId, group, jsonPath);

        // computeIfAbsent 内部禁止做 Nacos 网络IO
        ConfigRegistration registration = registrations.computeIfAbsent(registrationKey, key -> new ConfigRegistration(dataId, group));
        registration.addHolder(holder);

        try {
            registration.registerListener();
        } catch (NacosException e) {
            log.error("Nacos Listener 注册失败: dataId={}, group={}", dataId, group, e);
            registrations.remove(registrationKey, registration);
            throw new IllegalStateException("Nacos Listener 注册失败: " + dataId + " / " + group, e);
        }

        // 初始化赋值
        try {
            ConfigService configService = nacosConfigManager.getConfigService();
            String content = configService.getConfig(dataId, group, DEFAULT_TIMEOUT_MS);
            String value = extractJsonValue(content, jsonPath, dataId);

            ReflectionUtils.makeAccessible(field);
            ReflectionUtils.setField(field, bean, value);

            log.info("Nacos JSON 配置初始化成功: dataId={}, group={}, field={}, path={}",
                    dataId, group, field.getName(), jsonPath);
        } catch (NacosException e) {
            log.error("Nacos 配置读取失败: dataId={}, group={}, field={}", dataId, group, field.getName(), e);
            throw new IllegalStateException("Nacos 配置读取失败: " + dataId + " / " + group, e);
        } catch (Exception e) {
            log.error("Nacos JSON 配置注入失败: dataId={}, group={}, field={}", dataId, group, field.getName(), e);
            throw new IllegalStateException("Nacos JSON 配置注入失败: " + dataId + " / " + group + " / " + field.getName(), e);
        }
    }


    /**
     * 校验字段：禁止 static / final
     */
    private void validateField(Field field) {
        int modifiers = field.getModifiers();
        if (Modifier.isStatic(modifiers)) {
            throw new IllegalStateException("@NacosConfig 不允许修饰 static 字段: " + field);
        }
        if (Modifier.isFinal(modifiers)) {
            throw new IllegalStateException("@NacosConfig 不允许修饰 final 字段: " + field);
        }
    }


    /**
     * 按 . 分割路径提取JSON值
     * <pre>
     * { "a":{"b":{"c":"hello"}} }
     * path:a.b.c → hello
     * </pre>
     *
     * @param content nacos原始配置文本
     * @param path    json路径 a.b.c
     * @param dataId  用于日志
     * @return 提取后的字符串，null代表不存在/解析异常
     */
    private String extractJsonValue(String content, String path, String dataId) {
        if (!StringUtils.hasText(content)) {
            return null;
        }
        // path为空返回完整json字符串
        if (!StringUtils.hasText(path)) {
            return content;
        }

        try {
            JSONObject json = JSON.parseObject(content);
            String[] keys = path.split("\\.");
            Object current = json;

            for (String key : keys) {
                if (!(current instanceof JSONObject)) {
                    return null;
                }
                current = ((JSONObject) current).get(key);
                if (current == null) {
                    return null;
                }
            }

            if (current instanceof JSONObject) {
                return ((JSONObject) current).toJSONString();
            }
            return String.valueOf(current);
        } catch (Exception e) {
            log.warn("Nacos JSON 解析失败: dataId={}, path={}", dataId, path, e);
            return null;
        }
    }


    /**
     * 一个dataId+group对应一个注册实例，持有该配置下所有被监听的字段
     */
    private class ConfigRegistration {
        private final String dataId;
        private final String group;
        private final CopyOnWriteArrayList<FieldHolder> holders = new CopyOnWriteArrayList<>();
        private boolean listenerRegistered = false;

        ConfigRegistration(String dataId, String group) {
            this.dataId = dataId;
            this.group = group;
        }

        void addHolder(FieldHolder holder) {
            holders.add(holder);
        }

        /**
         * synchronized保证同一个dataId+group仅注册一次nacos listener
         */
        synchronized void registerListener() throws NacosException {
            if (listenerRegistered) {
                return;
            }
            ConfigService configService = nacosConfigManager.getConfigService();
            configService.addListener(dataId, group, new Listener() {
                @Override
                public ExecutorService getExecutor() {
                    return listenerExecutor;
                }

                @Override
                public void receiveConfigInfo(String configInfo) {
                    updateFields(configInfo);
                }
            });
            listenerRegistered = true;
            log.info("Nacos Listener 注册成功: dataId={}, group={}", dataId, group);
        }

        /**
         * nacos配置变更回调，批量更新所有绑定字段
         */
        private void updateFields(String configInfo) {
            int successCount = 0;
            for (FieldHolder holder : holders) {
                try {
                    String value = extractJsonValue(configInfo, holder.jsonPath, holder.dataId);
                    ReflectionUtils.makeAccessible(holder.field);
                    ReflectionUtils.setField(holder.field, holder.bean, value);
                    successCount++;
                } catch (Exception e) {
                    log.error("Nacos JSON 配置动态更新失败: dataId={}, group={}, field={}, path={}",
                            holder.dataId, holder.group, holder.field.getName(), holder.jsonPath, e);
                }
            }
            // 不打印configInfo，防止密钥密码泄露到日志
            log.info("Nacos JSON 配置更新完成: dataId={}, group={}, fieldCount={}, successCount={}",
                    dataId, group, holders.size(), successCount);
        }
    }

    /**
     * 保存bean实例、字段、nacos元信息、json路径
     */
    private static class FieldHolder {
        private final Object bean;
        private final Field field;
        private final String dataId;
        private final String group;
        private final String jsonPath;

        FieldHolder(Object bean, Field field, String dataId, String group, String jsonPath) {
            this.bean = bean;
            this.field = field;
            this.dataId = dataId;
            this.group = group;
            this.jsonPath = jsonPath;
        }
    }

    /**
     * 容器销毁，关闭监听线程池
     */
    @PreDestroy
    public void destroy() {
        listenerExecutor.shutdown();
        log.info("Nacos JSON 配置监听线程池已关闭");
    }
}