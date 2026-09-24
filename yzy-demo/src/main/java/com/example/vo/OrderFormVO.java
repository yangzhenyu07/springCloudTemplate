package com.example.vo;

import com.example.validation.SceneEnum;
import com.example.validation.annotation.SceneLength;
import com.example.validation.annotation.SceneNotNull;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

/**
 * 订单表单大 VO（场景校验示例）
 *
 * <p>同一个 VO 贯穿新增/修改/审核多个 Service 方法，
 * 各字段按场景声明规则：同一字段可在多个场景生效，不同场景规则不同。
 * amount 字段不挂任何规则，用于验证"无规则字段不参与校验"。</p>
 *
 * @author yzy
 */
@Data
@Builder
@AllArgsConstructor
@NoArgsConstructor
public class OrderFormVO {

    /** 订单号：修改/审核必填；三个场景都限长 6~32 */
    @SceneNotNull(scenes = {SceneEnum.UPDATE, SceneEnum.AUDIT}, message = "订单号不能为空")
    @SceneLength(scenes = {SceneEnum.CREATE, SceneEnum.UPDATE, SceneEnum.AUDIT}, min = 6, max = 32)
    private String orderNo;

    /** 客户姓名：新增/修改必填且限长 20，审核不关心 */
    @SceneNotNull(scenes = {SceneEnum.CREATE, SceneEnum.UPDATE})
    @SceneLength(scenes = {SceneEnum.CREATE, SceneEnum.UPDATE}, max = 20)
    private String customerName;

    /** 手机号：仅新增必填；新增/修改限长 11 位 */
    @SceneNotNull(scenes = {SceneEnum.CREATE}, message = "新增时手机号必填")
    @SceneLength(scenes = {SceneEnum.CREATE, SceneEnum.UPDATE}, min = 11, max = 11, message = "手机号必须为11位")
    private String phone;

    /** 地址：仅审核必填；三个场景限长 100 */
    @SceneNotNull(scenes = {SceneEnum.AUDIT}, message = "审核时地址必填")
    @SceneLength(scenes = {SceneEnum.CREATE, SceneEnum.UPDATE, SceneEnum.AUDIT}, max = 100)
    private String address;

    /** 备注：仅修改场景限长 200，其余场景完全不校验 */
    @SceneLength(scenes = {SceneEnum.UPDATE}, max = 200)
    private String remark;

    /** 金额：不挂任何规则，任何场景都不校验 */
    private Long amount;
}
