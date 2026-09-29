package com.example.bdemo.common.dto;

import com.alibaba.fastjson2.annotation.JSONField;
import lombok.Data;

@Data
public class BaseReqData<T> {

    @JSONField(name="msgHeader")
    private UwapHeader msgHeader;

    @JSONField(name="body")
    private T body;
}
