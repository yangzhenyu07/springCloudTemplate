package com.example.bdemo.common.dto;

import lombok.Data;

@Data
public class UwapHeader {
    /**
     * 报文编号
     */
    private String msgType;

    /**
     * 版本号
     */
    private String versionID;
}