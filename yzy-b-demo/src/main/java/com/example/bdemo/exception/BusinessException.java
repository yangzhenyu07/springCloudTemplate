package com.example.bdemo.exception;

import com.example.bdemo.common.enums.ResultCodeEnum;

public class BusinessException extends RuntimeException {

    private String code;
    private String desc;


    public BusinessException(ResultCodeEnum resultCodeEnum){
        super(ResultCodeEnum.getDesc(resultCodeEnum));
        this.code = code;
        this.desc = ResultCodeEnum.getDesc(resultCodeEnum);


    }

}
