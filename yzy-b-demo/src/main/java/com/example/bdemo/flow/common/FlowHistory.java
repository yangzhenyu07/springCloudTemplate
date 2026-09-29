package com.example.bdemo.flow.common;

import lombok.Data;

import java.text.MessageFormat;

/**
 * @author yangzhenyu
 * @version 1.0
 * @description:
 * @date 2026/9/28 20:03
 */
@Data
public class FlowHistory {

    private String nodeCode;
    private String nodeDesc;
    // 当前时间戳
    private long nodeTimeStamp;
    // 耗时
    private long consumingTime;

    @Override
    public String toString(){
        String msg = "nodeCode:{0} | nodeDesc:{1} | consumingTime:{2}ms";
        return MessageFormat.format(msg,
                nodeCode,
                nodeDesc,
                consumingTime);
    }
}
