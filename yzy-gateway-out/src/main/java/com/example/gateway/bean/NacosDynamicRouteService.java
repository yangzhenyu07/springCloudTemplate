package com.example.gateway.bean;

import com.alibaba.cloud.nacos.NacosConfigManager;
import com.alibaba.fastjson2.JSON;
import com.alibaba.nacos.api.config.ConfigService;
import com.alibaba.nacos.api.config.listener.Listener;
import com.alibaba.nacos.api.exception.NacosException;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.boot.context.event.ApplicationReadyEvent;
import org.springframework.cloud.gateway.event.RefreshRoutesEvent;
import org.springframework.cloud.gateway.route.InMemoryRouteDefinitionRepository;
import org.springframework.cloud.gateway.route.RouteDefinition;
import org.springframework.cloud.gateway.route.RouteDefinitionRepository;
import org.springframework.cloud.gateway.route.RouteDefinitionWriter;
import org.springframework.context.ApplicationEventPublisher;
import org.springframework.context.ApplicationEventPublisherAware;
import org.springframework.context.event.EventListener;
import org.springframework.stereotype.Component;
import reactor.core.publisher.Mono;

import java.lang.reflect.Field;
import java.util.List;
import java.util.Map;
import java.util.concurrent.Executor;

/**
 * Nacos动态路由服务
 * <p>
 * 监听Nacos配置中心路由配置变更，实时更新网关路由。
 * 使用Spring Cloud Alibaba注入的NacosConfigManager获取ConfigService，
 * 确保namespace认证等配置与Spring容器一致。
 *
 * @author yzy
 * @version 1.1
 */
@Slf4j
@Component
public class NacosDynamicRouteService implements ApplicationEventPublisherAware {

    @Value("${spring.cloud.nacos.config.data-id}")
    private String dataId;
    @Value("${spring.cloud.nacos.config.group}")
    private String group;

    private final NacosConfigManager nacosConfigManager;
    private final RouteDefinitionWriter routeDefinitionWriter;
    private final RouteDefinitionRepository routeDefinitionRepository;
    private ApplicationEventPublisher publisher;

    public NacosDynamicRouteService(NacosConfigManager nacosConfigManager,
                                    RouteDefinitionWriter routeDefinitionWriter,
                                    RouteDefinitionRepository routeDefinitionRepository) {
        this.nacosConfigManager = nacosConfigManager;
        this.routeDefinitionWriter = routeDefinitionWriter;
        this.routeDefinitionRepository = routeDefinitionRepository;
    }

    @EventListener(ApplicationReadyEvent.class)
    public void init() {
        log.info("=== 初始化Nacos动态路由服务 ===");
        log.info("dataId={}, group={}", dataId, group);
        try {
            ConfigService configService = nacosConfigManager.getConfigService();
            log.info("ConfigService状态: {}", configService);

            // 首次拉取配置
            String configInfo = configService.getConfig(dataId, group, 5000);
            log.info("首次拉取路由配置: {}", configInfo);
            if (configInfo != null && !configInfo.trim().isEmpty()) {
                updateRoutes(configInfo);
                publisher.publishEvent(new RefreshRoutesEvent(this));
                log.info("首次路由加载完成，已发布RefreshRoutesEvent");
            } else {
                log.warn("Nacos中未找到路由配置，dataId={}, group={}", dataId, group);
            }

            // 注册配置变更监听器
            configService.addListener(dataId, group, new Listener() {
                @Override
                public Executor getExecutor() {
                    return Runnable::run;
                }

                @Override
                public void receiveConfigInfo(String configInfo) {
                    log.info("=== 收到Nacos配置变更通知 ===");
                    log.info("新配置内容: {}", configInfo);
                    if (configInfo != null && !configInfo.trim().isEmpty()) {
                        updateRoutes(configInfo);
                        publisher.publishEvent(new RefreshRoutesEvent(this));
                        log.info("路由刷新完成，已发布RefreshRoutesEvent");
                    }
                }
            });
            log.info("Nacos配置监听器注册成功，等待配置变更...");
        } catch (NacosException e) {
            log.error("Nacos配置监听初始化失败", e);
        }
    }

    /**
     * 反射清空InMemoryRouteDefinitionRepository内部全部路由
     */
    @SuppressWarnings("unchecked")
    private void clearAllRoutes() {
        if (!(routeDefinitionRepository instanceof InMemoryRouteDefinitionRepository)) {
            log.warn("当前不是内存仓库，跳过清空");
            return;
        }
        try {
            InMemoryRouteDefinitionRepository memoryRepo = (InMemoryRouteDefinitionRepository) routeDefinitionRepository;
            Field field = InMemoryRouteDefinitionRepository.class.getDeclaredField("routes");
            field.setAccessible(true);
            Map<String, RouteDefinition> routesMap = (Map<String, RouteDefinition>) field.get(memoryRepo);
            int before = routesMap.size();
            routesMap.clear();
            log.info("反射清空内存路由完成，清除{}条旧路由", before);
        } catch (Exception e) {
            log.error("反射清空路由失败", e);
        }
    }

    /**
     * 解析JSON路由配置并更新内存路由仓库
     *
     * @param configInfo Nacos返回的JSON格式路由配置
     */
    private void updateRoutes(String configInfo) {
        try {
            List<RouteDefinition> routeDefinitions = JSON.parseArray(configInfo, RouteDefinition.class);
            if (routeDefinitions == null) {
                log.warn("路由解析结果为空");
                return;
            }

            log.info("解析到{}条路由定义", routeDefinitions.size());
            for (RouteDefinition rd : routeDefinitions) {
                log.info("  路由: id={}, uri={}, predicates={}",
                        rd.getId(), rd.getUri(), rd.getPredicates());
            }

            // 反射清空全部旧路由
            clearAllRoutes();

            // 写入新路由
            for (RouteDefinition definition : routeDefinitions) {
                routeDefinitionWriter.save(Mono.just(definition))
                        .subscribe(
                                unused -> log.info("  保存路由成功: id={}", definition.getId()),
                                err -> log.error("  保存路由id={}失败", definition.getId(), err)
                        );
            }
            log.info("路由更新完成，共{}条", routeDefinitions.size());
        } catch (Exception e) {
            log.error("解析/更新路由失败", e);
        }
    }

    @Override
    public void setApplicationEventPublisher(ApplicationEventPublisher applicationEventPublisher) {
        this.publisher = applicationEventPublisher;
    }
}
