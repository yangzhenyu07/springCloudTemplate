package com.example.service.impl;

import com.example.service.OrderFormService;
import com.example.validation.SceneEnum;
import com.example.validation.annotation.SceneCheck;
import com.example.vo.OrderFormVO;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;

/**
 * 订单表单服务实现
 *
 * <p>方法上只声明 {@link SceneCheck} 场景注解，校验由切面完成，
 * 方法体内是纯业务逻辑，不出现任何字段校验 if 判断。</p>
 *
 * @author yzy
 */
@Slf4j
@Service
public class OrderFormServiceImpl implements OrderFormService {

    /**
     * 新增订单（CREATE 场景校验）
     *
     * @param vo 订单表单
     * @return 处理结果
     */
    @Override
    @SceneCheck(SceneEnum.CREATE)
    public String create(OrderFormVO vo) {
        log.info("[订单表单] 新增，customerName={}", vo.getCustomerName());
        return "created:" + vo.getCustomerName();
    }

    /**
     * 修改订单（UPDATE 场景校验）
     *
     * @param vo 订单表单
     * @return 处理结果
     */
    @Override
    @SceneCheck(SceneEnum.UPDATE)
    public String update(OrderFormVO vo) {
        log.info("[订单表单] 修改，orderNo={}", vo.getOrderNo());
        return "updated:" + vo.getOrderNo();
    }

    /**
     * 审核订单（AUDIT 场景校验）
     *
     * @param vo 订单表单
     * @return 处理结果
     */
    @Override
    @SceneCheck(SceneEnum.AUDIT)
    public String audit(OrderFormVO vo) {
        log.info("[订单表单] 审核，orderNo={}", vo.getOrderNo());
        return "audited:" + vo.getOrderNo();
    }
}
