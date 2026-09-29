package com.example.bdemo.flow.common;

import com.example.bdemo.common.dto.FlowCondition;
import com.example.bdemo.common.dto.KfhlReqHead;
import com.example.bdemo.common.dto.UwapHeader;
import com.example.bdemo.flow.common.dto.CommonParam;
import com.example.bdemo.flow.common.dto.WalletPayBaseInfo;
import lombok.Data;

/**
 * @author yangzhenyu
 * @version 1.0
 * @description:
 * @date 2026/9/28 19:56
 */
@Data
public class TradeFlowContext<T,R> extends FlowCommon{
    private String msgId; // 幂等使用
    private String sceneId;

    private R orgResponseContext;
    private boolean stopChain; // 是否停止流程

    private KfhlReqHead kfhlReqHead;

    private UwapHeader uwapHeader;

    // 流程条件
    private FlowCondition flowCondition;


    // ------------- 通用上下文 --------------
    // 钱包相关
    private WalletPayBaseInfo walletPayBaseInfo;

    // 公共参数
    private CommonParam commonParam;

}
