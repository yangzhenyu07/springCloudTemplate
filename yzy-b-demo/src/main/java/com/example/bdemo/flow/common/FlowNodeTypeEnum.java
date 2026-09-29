package com.example.bdemo.flow.common;

import lombok.AllArgsConstructor;
import lombok.Getter;

@Getter
@AllArgsConstructor
public enum FlowNodeTypeEnum {
    FEIGN("FEIGN", "远程接口"),
    LOCAL("LOCAL", "本地接口");
    private final String code;
    private final String desc;
    // 快速获取枚举（简化使用）
    public static FlowNodeTypeEnum getByCode(String code) {
        for (FlowNodeTypeEnum status : values()) {
            if (status.getCode().equals(code)) {
                return status;
            }
        }
        return null;
    }
}