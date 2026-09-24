package com.example.validation;

import com.example.validation.config.RuleConfigLoader;
import com.example.validation.config.RuleRegistry;
import com.example.vo.CustomerProfileVO;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;

import java.io.IOException;
import java.io.InputStream;
import java.math.BigDecimal;
import java.util.List;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

/**
 * 配置化场景校验器单元测试
 *
 * <p>覆盖：多字段注解（字段维度）、同一 key 多字段复用、同字段跨场景换规则、
 * 未配置 key 跳过、失败文案优先、改配置不改代码、启动期装载。</p>
 *
 * @author yzy
 */
class ConfigValidatorTest {

    /**
     * 每个用例前重新装载主配置（避免用例间静态状态互相污染）
     *
     * @throws IOException 装载失败
     */
    @BeforeEach
    void reloadMainConfig() throws IOException {
        try (InputStream in = getResource("validation-rules.json")) {
            RuleRegistry.load(in);
        }
    }

    /**
     * 读取 classpath 资源
     *
     * @param name 文件名
     * @return 输入流
     */
    private static InputStream getResource(String name) {
        InputStream in = ConfigValidatorTest.class.getClassLoader().getResourceAsStream(name);
        if (in == null) {
            throw new IllegalStateException("资源不存在: " + name);
        }
        return in;
    }

    /**
     * 构造一份 CREATE 场景完全合法的客户档案
     *
     * @return 客户档案
     */
    private CustomerProfileVO validCreateVo() {
        return CustomerProfileVO.builder()
                .customerNo("C20260924001")
                .customerName("张三")
                .phone("13800138000")
                .idCard("110101199001011234")
                .address("北京市朝阳区")
                .remark("新客户")
                .memo("开户")
                .balance(new BigDecimal("100.00"))
                .build();
    }

    /**
     * CREATE 场景：资料合法应通过
     */
    @Test
    @DisplayName("CREATE场景-合法资料-校验通过")
    void create_validVo_pass() {
        assertTrue(ConfigValidator.validateToList(validCreateVo(), SceneEnum.CREATE).isEmpty());
    }

    /**
     * CREATE 场景：姓名/手机号必填缺失，两条违规一起聚合
     */
    @Test
    @DisplayName("CREATE场景-多个字段注解各自生效-违规聚合")
    void create_multiFieldAnnotations_aggregateViolations() {
        CustomerProfileVO vo = validCreateVo();
        vo.setCustomerName(null);
        vo.setPhone("");

        SceneValidateException ex = assertThrows(SceneValidateException.class,
                () -> ConfigValidator.validate(vo, SceneEnum.CREATE));
        List<String> violations = ex.getViolations();
        assertTrue(violations.stream().anyMatch(v -> v.startsWith("customerName")));
        assertTrue(violations.stream().anyMatch(v -> v.startsWith("phone")));
        assertEquals(2, violations.size());
    }

    /**
     * 同一个字段在不同场景下规则不同：phone 在 CREATE 必填、在 UPDATE 可空但限 11 位
     */
    @Test
    @DisplayName("同一字段-跨场景规则不同-CREATE必填UPDATE可不填但限长")
    void sameField_differentRulesPerScene() {
        CustomerProfileVO vo = validCreateVo();
        vo.setPhone(null);

        assertFalse(ConfigValidator.validateToList(vo, SceneEnum.CREATE).isEmpty(), "CREATE 场景手机号必填");
        assertTrue(ConfigValidator.validateToList(vo, SceneEnum.UPDATE).isEmpty(), "UPDATE 场景手机号可为空");

        vo.setPhone("138001380");
        assertFalse(ConfigValidator.validateToList(vo, SceneEnum.UPDATE).isEmpty(), "UPDATE 场景手机号仍限 11 位");
    }

    /**
     * 两个字段共用同一配置 key（remark / memo 都指向 commonRemark），规则同时生效
     */
    @Test
    @DisplayName("同一key被多个字段引用-规则同时生效")
    void sharedKey_appliesToBothFields() {
        CustomerProfileVO vo = validCreateVo();
        String overLen = repeat("字", 51);
        vo.setRemark(overLen);
        vo.setMemo(overLen);

        List<String> violations = ConfigValidator.validateToList(vo, SceneEnum.CREATE);
        assertEquals(2, violations.size());
        assertTrue(violations.stream().anyMatch(v -> v.startsWith("remark")));
        assertTrue(violations.stream().anyMatch(v -> v.startsWith("memo")));
    }

    /**
     * JSON 中未配置的 key（email）跳过校验，不因配置缺失而误报错
     */
    @Test
    @DisplayName("未配置规则的key-跳过校验")
    void keyNotConfigured_skipped() {
        CustomerProfileVO vo = validCreateVo();
        vo.setEmail(null);
        assertTrue(ConfigValidator.validateToList(vo, SceneEnum.CREATE).isEmpty());

        vo.setEmail(repeat("e", 300));
        assertTrue(ConfigValidator.validateToList(vo, SceneEnum.CREATE).isEmpty());
    }

    /**
     * 只在部分场景配置的 key：creditLevel 仅在 AUDIT 必填
     */
    @Test
    @DisplayName("仅在部分场景配置的key-CREATE跳过AUDIT必填")
    void keyConfiguredInSomeScenes_only() {
        CustomerProfileVO vo = validCreateVo();
        vo.setCreditLevel(null);

        assertTrue(ConfigValidator.validateToList(vo, SceneEnum.CREATE).isEmpty());
        assertFalse(ConfigValidator.validateToList(vo, SceneEnum.AUDIT).isEmpty());
    }

    /**
     * 失败文案优先取 JSON 中的 message
     */
    @Test
    @DisplayName("长度违规-使用JSON中的自定义文案")
    void lengthViolation_usesConfiguredMessage() {
        CustomerProfileVO vo = validCreateVo();
        vo.setPhone("1380013800");

        List<String> violations = ConfigValidator.validateToList(vo, SceneEnum.CREATE);
        assertEquals(1, violations.size());
        assertTrue(violations.get(0).contains("手机号必须为11位"));
    }

    /**
     * 改配置不改代码：装载收紧后的配置，同一份 VO 由通过变为失败
     *
     * @throws IOException 装载失败
     */
    @Test
    @DisplayName("改配置不改代码-同一VO由通过变失败")
    void changeConfigWithoutCodeChange_sameVoFails() throws IOException {
        CustomerProfileVO vo = validCreateVo();
        vo.setCustomerName("张三丰太极传人");
        assertTrue(ConfigValidator.validateToList(vo, SceneEnum.CREATE).isEmpty());

        try (InputStream in = getResource("validation-rules-alt.json")) {
            RuleRegistry.load(in);
        }
        List<String> violations = ConfigValidator.validateToList(vo, SceneEnum.CREATE);
        assertFalse(violations.isEmpty());
        assertTrue(violations.get(0).contains("收紧后：姓名最多5个字"));
        assertEquals("1.0-alt", RuleRegistry.version());
    }

    /**
     * 启动加载器：@PostConstruct 后注册表应完成装载
     *
     * @throws IOException 装载失败
     */
    @Test
    @DisplayName("启动加载器-装载后注册表可用")
    void startupLoader_registryLoaded() throws IOException {
        new RuleConfigLoader().load();

        assertTrue(RuleRegistry.loaded());
        assertEquals("1.0", RuleRegistry.version());
        assertTrue(RuleRegistry.rule(SceneEnum.CREATE, "customerName") != null);
    }

    /**
     * 生成指定长度的重复字符串
     *
     * @param unit 单元字符
     * @param times 重复次数
     * @return 拼接结果
     */
    private static String repeat(String unit, int times) {
        StringBuilder sb = new StringBuilder();
        for (int i = 0; i < times; i++) {
            sb.append(unit);
        }
        return sb.toString();
    }
}
