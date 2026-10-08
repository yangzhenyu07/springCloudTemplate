package com.example.bdemo.flow.condition;

import com.example.bdemo.flow.common.TradeFlowContext;
import lombok.extern.slf4j.Slf4j;
import org.springframework.expression.Expression;
import org.springframework.expression.ExpressionParser;
import org.springframework.expression.spel.standard.SpelExpressionParser;
import org.springframework.expression.spel.support.StandardEvaluationContext;
import org.springframework.stereotype.Component;

/**
 * @author yangzhenyu
 * @version 1.0
 * @description:
 * @date 2026/9/28 19:54
 */
@Component
@Slf4j
public class SpelConditionEvaluator {

    private final ExpressionParser parser = new SpelExpressionParser();

    public Expression parse(String expression) {
        try {
            return parser.parseExpression(expression);
        } catch (Exception e) {
            throw new IllegalArgumentException("condition parse failed");
        }
    }

    public boolean evaluate(String condition,Expression expression, TradeFlowContext context){
        if(expression == null){
            throw new IllegalArgumentException("expression is null");
        }
        StandardEvaluationContext evaluationContext = new StandardEvaluationContext();
        evaluationContext.setVariable("context", context);
        try {
            Boolean result = expression.getValue(evaluationContext, Boolean.class);
            return Boolean.TRUE.equals(result);
        } catch (Exception e) {

            log.error("条件评估失败、默认允许通过 | 表达式: {} | 错误: {}", condition,e.getMessage(),e);
            throw new IllegalArgumentException("condition evaluate failed");
        }
    }

    public boolean evaluatePre(String condition,Expression expression, TradeFlowContext context){
        if(expression == null){
            throw new IllegalArgumentException("expression is null");
        }
        StandardEvaluationContext evaluationContext = new StandardEvaluationContext();
        evaluationContext.setVariable("context", context);
        try {
            Boolean result = expression.getValue(evaluationContext, Boolean.class);
            return Boolean.TRUE.equals(result);
        } catch (Exception e) {
            log.warn("预流程编排模式条件评估失败、默认允许通过 | 表达式: {} | 错误: {}", condition, e.getMessage());
            return true;
        }
    }
}