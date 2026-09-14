package com.example.utils;

import com.example.config.common.MyRedisConditional;
import com.example.service.NumberToolService;
import org.apache.commons.lang3.StringUtils;
import org.springframework.context.annotation.Conditional;
import org.springframework.stereotype.Component;

@Component
@Conditional(MyRedisConditional.class)
public class NumberTool {
    private static NumberToolService service;

    public NumberTool(NumberToolService numberToolService){
        service = numberToolService;
    }

    // 开关
    public boolean check(){
        String numberCheck = SingletonStorage.getInstance().getNumberSwitch();
        return StringUtils.equals("true",numberCheck)?Boolean.FALSE:Boolean.TRUE;
    }


}
