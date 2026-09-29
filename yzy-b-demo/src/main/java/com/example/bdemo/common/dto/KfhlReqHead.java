package com.example.bdemo.common.dto;

import com.alibaba.fastjson2.annotation.JSONField;
import com.fasterxml.jackson.annotation.JsonProperty;
import lombok.Data;

@Data
public class KfhlReqHead {
    /**
     * 应用唯一标识
     */
    @JSONField(name = "APPID")
    @JsonProperty("APPID")
    private String APPID;

    /**
     * 产品唯一标识
     */
    @JSONField(name = "PdID")
    @JsonProperty("PdID")
    private String PdID;
}