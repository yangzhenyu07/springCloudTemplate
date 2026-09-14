package com.example.config.common;

import com.example.utils.SingletonStorage;
import org.apache.commons.lang3.StringUtils;
import org.springframework.context.annotation.Condition;
import org.springframework.context.annotation.ConditionContext;
import org.springframework.core.env.Environment;
import org.springframework.core.type.AnnotatedTypeMetadata;


/**
* @author yangzhenyu
* @date 2024/7/12 9:29
* @version 1.0
*/
public class MyRedisConditional implements Condition,BaseCondition {
    @Override
    public boolean matches(ConditionContext conditionContext, AnnotatedTypeMetadata annotatedTypeMetadata) {
        Environment environment = conditionContext.getEnvironment();
        String numberSwitch = environment.getProperty(REDIS_CONFIG_KEY);
        SingletonStorage storage = SingletonStorage.getInstance();
        storage.setNumberSwitch(numberSwitch);
        if(StringUtils.equals(TAG,numberSwitch)){
            return Boolean.TRUE;
        }
        return Boolean.FALSE;
    }
}
