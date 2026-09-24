package com.example.validation;

import com.example.service.OrderFormService;
import com.example.service.impl.OrderFormServiceImpl;
import com.example.vo.OrderFormVO;
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
 * 场景校验切面集成单测（轻量 Spring 容器，不启动整个 Boot 应用）
 *
 * <p>验证目标：Service 方法经 Spring 代理调用时，@SceneCheck 声明的场景
 * 校验在业务方法执行前生效——业务代码零 if 校验，非法 VO 根本进不了方法体。</p>
 *
 * @author yzy
 */
@SpringJUnitConfig(OrderFormServiceAspectTest.Config.class)
class OrderFormServiceAspectTest {

    /**
     * 最小容器配置：仅装配被测 Service 与校验切面
     */
    @Configuration
    @EnableAspectJAutoProxy
    static class Config {

        @Bean
        OrderFormService orderFormService() {
            return new OrderFormServiceImpl();
        }

        @Bean
        SceneCheckAspect sceneCheckAspect() {
            return new SceneCheckAspect();
        }
    }

    @Autowired
    private OrderFormService orderFormService;

    /**
     * 构造 CREATE 场景合法 VO（orderNo 可空）
     *
     * @return CREATE 合法 VO
     */
    private OrderFormVO createVo() {
        return OrderFormVO.builder()
                .customerName("张三")
                .phone("13800000000")
                .build();
    }

    @Test
    @DisplayName("create：合法 VO 通过切面校验并正常返回")
    void create_valid_passThrough() {
        assertEquals("created:张三", orderFormService.create(createVo()));
    }

    @Test
    @DisplayName("create：缺手机号被切面拦截，业务方法未执行")
    void create_invalid_blockedByAspect() {
        OrderFormVO vo = createVo();
        vo.setPhone("");
        SceneValidateException e = assertThrows(SceneValidateException.class,
                () -> orderFormService.create(vo));
        assertTrue(e.getMessage().contains("新增时手机号必填"));
    }

    @Test
    @DisplayName("update：同一 VO 换个方法规则不同——手机号可空但订单号必填")
    void update_differentRulesOnSameVo() {
        OrderFormVO vo = createVo();
        vo.setOrderNo("ORD20260915");
        // 无手机号也能过 UPDATE：规则随场景切换
        assertEquals("updated:ORD20260915", orderFormService.update(vo));

        vo.setOrderNo(null);
        assertThrows(SceneValidateException.class, () -> orderFormService.update(vo));
    }

    @Test
    @DisplayName("audit：姓名手机号全缺也能过，只要求订单号+地址")
    void audit_onlyOrderNoAndAddress() {
        OrderFormVO vo = OrderFormVO.builder()
                .orderNo("ORD20260915")
                .address("广东省深圳市南山区")
                .build();
        assertEquals("audited:ORD20260915", orderFormService.audit(vo));

        vo.setAddress(null);
        assertThrows(SceneValidateException.class, () -> orderFormService.audit(vo));
    }
}
