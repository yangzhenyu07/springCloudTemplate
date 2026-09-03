package com.example.gateway.constants;

import com.example.gateway.config.LocalMsgCane;
import com.example.gateway.vo.OutService;

import java.nio.charset.Charset;
import java.nio.charset.StandardCharsets;
import java.util.HashMap;
import java.util.Map;

/**
 * 网关过滤器常量
 *
 * @author Dell
 * @version 1.1
 * @date 2026/8/11 20:50
 */

public class FilterConstants {


    public static final String START_TIME_ATTR = "start_time_attr";
    public static final String TRACE_ID_KEY = "traceId";
    public static final String TRACE_ID_HEADER = "X-Trace-Id";

    /** 请求头中系统标识字段名 */
    public static final String SYSTEM_CODE_HEADER = "X-System-Code";
    /** exchange attribute中存储源字符集的key */
    public static final String SOURCE_CHARSET_ATTR = "source_charset_attr";
    public static final String TARGET_CHARSET_ATTR = "target_charset_attr";




    /** 默认字符集（未识别系统时使用UTF-8） */
    public static final Charset DEFAULT_CHARSET = StandardCharsets.UTF_8;

    /**
     * 根据系统标识获取对应系统的编码累着
     *
     * @param systemCode 系统标识（A/B/...）
     * @return 对应字符集，未识别返回UTF-8
     */
    public static Charset getCharsetBySystemCode(String systemCode,LocalMsgCane localMsgCane) {
        if (systemCode == null || systemCode.trim().isEmpty()) {
            return DEFAULT_CHARSET;
        }
        Map<String, Charset> outServiceMap = localMsgCane.getOutServiceMap();
        return outServiceMap.getOrDefault(systemCode.trim().toUpperCase(), DEFAULT_CHARSET);
    }
}
