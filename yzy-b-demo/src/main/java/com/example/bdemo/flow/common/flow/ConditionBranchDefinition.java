package com.example.bdemo.flow.common.flow;

import lombok.Data;
import org.springframework.expression.Expression;

/**
 * @author yangzhenyu
 * @version 1.0
 * @description:
 * @date 2026/9/29 14:28
 */

@Data
public class ConditionBranchDefinition {

    private String condition;

    private String subFlowCode;

    private Integer sortNo;

    private Expression compiledExpression;

    private String subSceneCode;

}