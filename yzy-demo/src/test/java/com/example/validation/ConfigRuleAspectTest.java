package com.example.validation;

import com.example.service.CustomerProfileService;
import com.example.service.impl.CustomerProfileServiceImpl;
import com.example.validation.config.RuleConfigLoader;
import com.example.validation.config.RuleRegistry;
import com.example.vo.CustomerProfileVO;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.context.annotation.EnableAspectJAutoProxy;
import org.springframework.test.context.junit.jupiter.SpringJUnitConfig;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

/**
 * 配置化校验 AOP 切面测试
 *
 * <p>轻量 Spring 容器（不启动整个 Boot 应用）：注入启动加载器模拟应用启动装载，
 * 验证标注 {@code @ConfigCheck} 的方法在业务执行前被拦截校验。</p>
 *
 * @author yzy
 */
@SpringJUnitConfig(ConfigRuleAspectTest.Config.class)
class ConfigRuleAspectTest {

    @Autowired
    private CustomerProfileService customerProfileService;

    @Autowired
    private RuleConfigLoader ruleConfigLoader;

    /**
     * 轻量容器配置：业务 Bean + 切面 + 启动加载器
     */
    @Configuration
    @EnableAspectJAutoProxy
    static class Config {

        /**
         * 业务服务
         *
         * @return 客户档案服务
         */
        @Bean
        public CustomerProfileService customerProfileService() {
            return new CustomerProfileServiceImpl();
        }

        /**
         * 校验切面
         *
         * @return 切面
         */
        @Bean
        public ConfigRuleAspect configRuleAspect() {
            return new ConfigRuleAspect();
        }

        /**
         * 启动加载器（@PostConstruct 自动装载规则）
         *
         * @return 加载器
         */
        @Bean
        public RuleConfigLoader ruleConfigLoader() {
            return new RuleConfigLoader();
        }
    }

    /**
     * 容器启动后规则注册表应已装载
     */
    @Test
    @DisplayName("容器启动-规则已由启动加载器装载")
    void contextStarted_rulesLoaded() {
        assertTrue(RuleRegistry.loaded());
        assertTrue(ruleConfigLoader.snapshot().containsKey(SceneEnum.CREATE));
    }

    /**
     * 合法资料：切面放行，业务正常执行
     */
    @Test
    @DisplayName("合法资料-切面放行并返回业务结果")
    void validVo_passThrough() {
        CustomerProfileVO vo = CustomerProfileVO.builder()
                .customerNo("C20260924001")
                .customerName("张三")
                .phone("13800138000")
                .idCard("110101199001011234")
                .build();

        assertEquals("submitted:张三", customerProfileService.submit(vo));
    }

    /**
     * 非法资料：切面在业务方法体执行前拦截并抛校验异常
     */
    @Test
    @DisplayName("非法资料-切面拦截-业务方法不执行")
    void invalidVo_blockedBeforeBusiness() {
        CustomerProfileVO vo = CustomerProfileVO.builder()
                .customerNo("C20260924001")
                .customerName(null)
                .phone("13800138000")
                .build();

        SceneValidateException ex = assertThrows(SceneValidateException.class,
                () -> customerProfileService.submit(vo));
        assertTrue(ex.getViolations().stream().anyMatch(v -> v.startsWith("customerName")));
    }

    /**
     * 同一 VO 不同方法（场景）校验结果不同：UPDATE 要求编号必填、AUDIT 要求信用等级必填
     */
    @Test
    @DisplayName("同一VO-不同方法校验规则不同")
    void sameVo_differentMethods_differentRules() {
        CustomerProfileVO noRequiredFields = CustomerProfileVO.builder()
                .customerName("张三")
                .phone("13800138000")
                .build();

        assertThrows(SceneValidateException.class, () -> customerProfileService.update(noRequiredFields));
        assertThrows(SceneValidateException.class, () -> customerProfileService.review(noRequiredFields));
        assertEquals("submitted:张三", customerProfileService.submit(noRequiredFields));
    }
}
