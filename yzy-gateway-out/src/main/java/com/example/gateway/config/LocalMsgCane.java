package com.example.gateway.config;

import com.alibaba.cloud.commons.lang.StringUtils;
import com.alibaba.fastjson2.JSON;
import com.example.gateway.config.nacos.NacosConfig;
import com.example.gateway.vo.OutService;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Component;

import java.nio.charset.Charset;
import java.util.List;
import java.util.Map;
import java.util.stream.Collectors;


/**
 * @author yangzhenyu
 * @version 1.0
 * @date 2026/8/24 20:23
 */
@Slf4j
@Component
public class LocalMsgCane {

    @NacosConfig(dataId = "out-service")
    private String msgOutService;


    private volatile Map<String, OutService> outServiceMap;

    /** 系统标识 → 源字符集映射（A系统GBK，B系统UTF-8） */
    public Map<String, Charset> getOutServiceMap(){
        log.info("解析out-service.json配置，{}",msgOutService);
        List<OutService> voList = JSON.parseArray(msgOutService, OutService.class);
        Map<String, Charset> map = voList.stream()
                .collect(Collectors.toMap(
                        OutService::getService,
                        vo -> Charset.forName(StringUtils.isBlank(vo.getCharset())?"UTF-8":vo.getCharset()),
                        (oldVal, newVal) -> newVal // key重复，后者覆盖前者，防止DuplicateKey异常
                ));
        return map;
    }
}
