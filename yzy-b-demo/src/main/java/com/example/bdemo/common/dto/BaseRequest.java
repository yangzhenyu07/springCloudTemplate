package com.example.bdemo.common.dto;

import com.alibaba.fastjson2.annotation.JSONField;
import com.fasterxml.jackson.annotation.JsonProperty;
import lombok.Data;

@Data
public class BaseRequest<T> {

    @JSONField(name = "Head")
    @JsonProperty("Head")
    private KfhlReqHead Head;

    @JSONField(name = "Data")
    @JsonProperty("Data")
    private BaseReqData<T> Data;
}