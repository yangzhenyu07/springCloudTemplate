package com.example.service.impl;

import com.example.service.CustomerProfileService;
import com.example.validation.SceneEnum;
import com.example.validation.annotation.ConfigCheck;
import com.example.vo.CustomerProfileVO;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;

/**
 * 客户档案服务实现
 *
 * <p>方法上只声明 {@link ConfigCheck} 场景，校验规则全部来自 JSON 配置，
 * 方法体内是纯业务逻辑——改规则不需要动这里一行代码。</p>
 *
 * @author yzy
 */
@Slf4j
@Service
public class CustomerProfileServiceImpl implements CustomerProfileService {

    /**
     * 提交资料（CREATE 场景校验）
     *
     * @param vo 客户档案
     * @return 处理结果
     */
    @Override
    @ConfigCheck(SceneEnum.CREATE)
    public String submit(CustomerProfileVO vo) {
        log.info("[客户档案] 提交，customerName={}, phone={}", vo.getCustomerName(), vo.getPhone());
        return "submitted:" + vo.getCustomerName();
    }

    /**
     * 修改资料（UPDATE 场景校验）
     *
     * @param vo 客户档案
     * @return 处理结果
     */
    @Override
    @ConfigCheck(SceneEnum.UPDATE)
    public String update(CustomerProfileVO vo) {
        log.info("[客户档案] 修改，customerNo={}", vo.getCustomerNo());
        return "updated:" + vo.getCustomerNo();
    }

    /**
     * 审核资料（AUDIT 场景校验）
     *
     * @param vo 客户档案
     * @return 处理结果
     */
    @Override
    @ConfigCheck(SceneEnum.AUDIT)
    public String review(CustomerProfileVO vo) {
        log.info("[客户档案] 审核，customerNo={}, creditLevel={}", vo.getCustomerNo(), vo.getCreditLevel());
        return "reviewed:" + vo.getCustomerNo();
    }
}
