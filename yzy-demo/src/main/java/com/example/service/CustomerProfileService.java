package com.example.service;

import com.example.vo.CustomerProfileVO;

/**
 * 客户档案服务（配置化校验示例）
 *
 * @author yzy
 */
public interface CustomerProfileService {

    /**
     * 提交资料（CREATE 场景）
     *
     * @param vo 客户档案
     * @return 处理结果
     */
    String submit(CustomerProfileVO vo);

    /**
     * 修改资料（UPDATE 场景）
     *
     * @param vo 客户档案
     * @return 处理结果
     */
    String update(CustomerProfileVO vo);

    /**
     * 审核资料（AUDIT 场景）
     *
     * @param vo 客户档案
     * @return 处理结果
     */
    String review(CustomerProfileVO vo);
}
