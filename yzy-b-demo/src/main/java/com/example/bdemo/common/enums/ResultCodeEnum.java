package com.example.bdemo.common.enums;

import lombok.AllArgsConstructor;
import lombok.Getter;
import org.apache.commons.lang3.StringUtils;

import java.text.MessageFormat;

/**
 * @author yangzhenyu
 * @version 1.0
 * @description:
 * @date 2026/9/30 09:24
 */
@Getter
@AllArgsConstructor
public enum ResultCodeEnum {
    SUCCESS("SUCCESS","0000","成功"),
    FALSE("FALSE","9999","失败"),
    PARAM_CHECK("PARAM_CHECK","1111","{0} 传参不能为空");

    private final String sts;
    private final String code;
    private final String desc;


    public static ResultCodeEnum getByCode(String code){
        for (ResultCodeEnum resultCodeEnum: values()){
            if (resultCodeEnum.getCode().equals(code)){
                return resultCodeEnum;
            }
        }
        return null;
    }

    public static String getDesc(ResultCodeEnum resultCodeEnum){
        String formattedDesc = "";
        String desc = resultCodeEnum.getDesc();
        if (StringUtils.isNotEmpty(desc)){
            if (desc.contains("{0}")){
                formattedDesc = MessageFormat.format(desc, desc);
            }
        }
        return formattedDesc;
    }



}
