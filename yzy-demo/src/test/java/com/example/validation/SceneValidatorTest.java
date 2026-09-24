package com.example.validation;

import com.example.vo.OrderFormVO;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;

import java.util.List;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

/**
 * 场景校验器单测（纯 JUnit，不依赖 Spring 容器）
 *
 * <p>验证目标：
 * 1. 同一个 VO 在不同场景下校验规则不同；
 * 2. 同一字段可在多个场景触发生效；
 * 3. 支持非空与长度校验；
 * 4. 无规则字段不参与校验。</p>
 *
 * @author yzy
 */
class SceneValidatorTest {

    /**
     * 构造三个场景全部合法的 VO
     *
     * @return 全合法 VO
     */
    private OrderFormVO fullValidVo() {
        return OrderFormVO.builder()
                .orderNo("ORD20260915")
                .customerName("张三")
                .phone("13800000000")
                .address("广东省深圳市南山区")
                .remark("备注")
                .amount(100L)
                .build();
    }

    @Test
    @DisplayName("CREATE 场景：字段齐全时校验通过")
    void create_allFieldsValid_pass() {
        SceneValidator.validate(fullValidVo(), SceneEnum.CREATE);
    }

    @Test
    @DisplayName("CREATE 场景：手机号必填，缺失时抛出异常且提示命中 phone")
    void create_missingPhone_throw() {
        OrderFormVO vo = fullValidVo();
        vo.setPhone(null);
        SceneValidateException e = assertThrows(SceneValidateException.class,
                () -> SceneValidator.validate(vo, SceneEnum.CREATE));
        assertTrue(e.getMessage().contains("phone"));
        assertTrue(e.getMessage().contains("新增时手机号必填"));
    }

    @Test
    @DisplayName("CREATE 场景：orderNo 可空但超长触发长度校验（规则与 UPDATE 场景不同）")
    void create_orderNoTooLong_throw() {
        OrderFormVO vo = fullValidVo();
        vo.setOrderNo(null);
        // CREATE 场景 orderNo 可空：不抛异常
        SceneValidator.validate(vo, SceneEnum.CREATE);

        vo.setOrderNo("A23456789012345678901234567890123");
        SceneValidateException e = assertThrows(SceneValidateException.class,
                () -> SceneValidator.validate(vo, SceneEnum.CREATE));
        assertTrue(e.getMessage().contains("orderNo"));
        assertTrue(e.getMessage().contains("[6,32]"));
    }

    @Test
    @DisplayName("UPDATE 场景：手机号可空（与 CREATE 规则不同），但订单号必填")
    void update_phoneOptionalButOrderNoRequired() {
        OrderFormVO vo = fullValidVo();
        vo.setPhone(null);
        // UPDATE 场景手机号非必填：通过
        SceneValidator.validate(vo, SceneEnum.UPDATE);

        vo.setOrderNo("  ");
        SceneValidateException e = assertThrows(SceneValidateException.class,
                () -> SceneValidator.validate(vo, SceneEnum.UPDATE));
        assertTrue(e.getMessage().contains("订单号不能为空"));
    }

    @Test
    @DisplayName("AUDIT 场景：地址必填，姓名/手机号完全不校验（场景隔离）")
    void audit_addressRequiredOnly() {
        OrderFormVO vo = fullValidVo();
        vo.setCustomerName(null);
        vo.setPhone("1");
        // 姓名、手机号在 AUDIT 场景无规则：通过
        SceneValidator.validate(vo, SceneEnum.AUDIT);

        vo.setAddress(null);
        SceneValidateException e = assertThrows(SceneValidateException.class,
                () -> SceneValidator.validate(vo, SceneEnum.AUDIT));
        assertTrue(e.getMessage().contains("审核时地址必填"));
    }

    @Test
    @DisplayName("同一字段多场景生效：orderNo 长度规则在 CREATE/UPDATE/AUDIT 都触发")
    void sameFieldMultipleScenes() {
        OrderFormVO vo = fullValidVo();
        vo.setOrderNo("AB");
        for (SceneEnum scene : new SceneEnum[]{SceneEnum.CREATE, SceneEnum.UPDATE, SceneEnum.AUDIT}) {
            SceneValidateException e = assertThrows(SceneValidateException.class,
                    () -> SceneValidator.validate(vo, scene), "场景 " + scene + " 应拦截过短 orderNo");
            assertTrue(e.getMessage().contains("orderNo"));
        }
    }

    @Test
    @DisplayName("多字段同时违规：违规项全部聚合在一次异常里")
    void multipleViolations_aggregated() {
        OrderFormVO vo = OrderFormVO.builder().build();
        List<String> violations = SceneValidator.validateToList(vo, SceneEnum.UPDATE);
        // UPDATE 场景：orderNo 非空 + customerName 非空 = 2 条（phone/remark/address 无值但非必填）
        assertEquals(2, violations.size());
        assertTrue(violations.stream().anyMatch(v -> v.startsWith("orderNo")));
        assertTrue(violations.stream().anyMatch(v -> v.startsWith("customerName")));
    }

    @Test
    @DisplayName("无规则字段不参与校验：amount 任意值/空值在所有场景均通过")
    void noRuleField_neverChecked() {
        OrderFormVO vo = fullValidVo();
        vo.setAmount(null);
        for (SceneEnum scene : SceneEnum.values()) {
            SceneValidator.validate(vo, scene);
        }
    }

    @Test
    @DisplayName("备注超长仅在 UPDATE 场景拦截，CREATE 场景放行（规则按场景隔离）")
    void remark_onlyCheckedInUpdate() {
        StringBuilder sb = new StringBuilder();
        for (int i = 0; i < 201; i++) {
            sb.append("x");
        }
        OrderFormVO vo = fullValidVo();
        vo.setRemark(sb.toString());
        // CREATE 场景 remark 无规则：通过
        SceneValidator.validate(vo, SceneEnum.CREATE);
        // UPDATE 场景限长 200：拦截
        assertThrows(SceneValidateException.class, () -> SceneValidator.validate(vo, SceneEnum.UPDATE));
    }

    @Test
    @DisplayName("边界入参：null VO 与 null 场景都有明确违规提示")
    void nullInput_guarded() {
        assertTrue(SceneValidator.validateToList(null, SceneEnum.CREATE).get(0).contains("待校验对象"));
        assertTrue(SceneValidator.validateToList(fullValidVo(), null).get(0).contains("校验场景"));
    }
}
