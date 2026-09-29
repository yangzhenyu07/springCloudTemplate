package com.example.bdemo.flow.common.flow;

import lombok.Data;

import java.util.List;

/**
 * @author yangzhenyu
 * @version 1.0
 * @description:
 * @date 2026/9/29 14:28
 */
@Data
public class SceneFlowDefinition {

    private String sceneCode;

    private String flowCode;

    private Integer sortNo;

    private String conditionConfig;

    private List<ConditionBranchDefinition> conditionBranches;

}