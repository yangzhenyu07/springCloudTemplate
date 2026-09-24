package com.example.service;

import com.example.vo.OrderFormVO;

/**
 * 订单表单服务（场景校验示例）
 *
 * @author yzy
 */
public interface OrderFormService {

    /**
     * 新增订单（CREATE 场景：姓名/手机号必填，订单号选填但限长）
     *
     * @param vo 订单表单
     * @return 处理结果
     */
    String create(OrderFormVO vo);

    /**
     * 修改订单（UPDATE 场景：订单号/姓名必填，手机号选填但限长，备注限长 200）
     *
     * @param vo 订单表单
     * @return 处理结果
     */
    String update(OrderFormVO vo);

    /**
     * 审核订单（AUDIT 场景：订单号/地址必填，姓名手机号不关心）
     *
     * @param vo 订单表单
     * @return 处理结果
     */
    String audit(OrderFormVO vo);
}
