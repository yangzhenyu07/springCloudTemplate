package com.example.bdemo.flow.common;

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
