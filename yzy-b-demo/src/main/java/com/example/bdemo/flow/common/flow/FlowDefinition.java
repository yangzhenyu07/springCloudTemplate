package com.example.bdemo.flow.common.flow;

import lombok.Data;

import java.util.List;

/**
 * @author yangzhenyu
 * @version 1.0
 * @description:
 * @date 2026/9/28 20:05
 */
@Data
public class FlowDefinition {

    public static final String FLOW_TYPE_SERIAL = "SERIAL";
    public static final String FLOW_TYPE_CONDITION = "CONDITION";

    private String flowCode;

    private String flowName;

    private String flowType;

    private String flowDesc;

    private List<String> nodeCodes;
}

