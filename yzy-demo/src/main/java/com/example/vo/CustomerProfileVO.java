package com.example.vo;

import com.example.validation.annotation.ConfigRule;
import io.swagger.annotations.ApiModelProperty;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.math.BigDecimal;

/**
 * 客户档案表单（配置化校验示例 VO）
 *
 * <p>每个待校验字段各自标注 {@link ConfigRule}，注解只声明"寻址 key"，
 * 规则值（必填/长度/文案）统一在 validation-rules.json 中按字段维度配置。</p>
 *
 * <p>本 VO 演示四种典型情况：</p>
 * <ul>
 *     <li>key 与字段名同名：customerNo / customerName / phone / idCard / address</li>
 *     <li>多个字段共用同一 key：remark 与 memo 共用 {@code commonRemark}</li>
 *     <li>仅在部分场景配置的 key：creditLevel 只在 AUDIT 场景必填</li>
 *     <li>未配置的 key：email 在所有场景都无规则 → 跳过校验</li>
 * </ul>
 *
 * @author yzy
 */
@Data
@Builder
@AllArgsConstructor
@NoArgsConstructor
public class CustomerProfileVO {

    @ApiModelProperty("客户编号")
    @ConfigRule("customerNo")
    private String customerNo;

    @ApiModelProperty("客户姓名")
    @ConfigRule("customerName")
    private String customerName;

    @ApiModelProperty("手机号")
    @ConfigRule("phone")
    private String phone;

    @ApiModelProperty("身份证号")
    @ConfigRule("idCard")
    private String idCard;

    @ApiModelProperty("联系地址")
    @ConfigRule("address")
    private String address;

    @ApiModelProperty("邮箱（未配置规则的字段）")
    @ConfigRule("email")
    private String email;

    @ApiModelProperty("备注（与 memo 共用 commonRemark 规则）")
    @ConfigRule("commonRemark")
    private String remark;

    @ApiModelProperty("备注2（与 remark 共用 commonRemark 规则）")
    @ConfigRule("commonRemark")
    private String memo;

    @ApiModelProperty("信用等级（仅 AUDIT 场景必填）")
    @ConfigRule("creditLevel")
    private String creditLevel;

    @ApiModelProperty("账户余额（无注解，不参与校验）")
    private BigDecimal balance;
}
