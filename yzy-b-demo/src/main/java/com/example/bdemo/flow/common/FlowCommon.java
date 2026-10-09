package com.example.bdemo.flow.common;

import com.example.bdemo.flow.condition.SpelConditionEvaluator;
import com.example.bdemo.flow.executor.FlowExecutorVersion;
import com.example.bdemo.flow.executor.NodeExecutorVersion;
import com.example.bdemo.flow.executor.SceneExecutorVersion;
import com.example.bdemo.flow.factory.TradeFlowFactory;
import lombok.Data;

import java.util.List;

/**
 * @author yangzhenyu
 * @version 1.0
 * @description:
 * @date 2026/9/28 20:03
 */
@Data
public class FlowCommon {
    // 中心
    private String center;

    private List<FlowHistory> flowHistoryList;

    private List<String> pre;
}
