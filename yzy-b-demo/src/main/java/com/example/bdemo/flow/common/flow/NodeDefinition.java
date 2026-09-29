package com.example.bdemo.flow.common.flow;

import lombok.Data;

/**
 * @author yangzhenyu
 * @version 1.0
 * @description:
 * @date 2026/9/28 20:06
 */
@Data
public class NodeDefinition {

    private String flowCode;

    private String nodeCode;

    private String nodeName;

    private String nodeType;

    private String handlerBeanName;

    private String nodeConfig;

    private String nodeDesc;

    private Boolean nodeEnable = true;
}