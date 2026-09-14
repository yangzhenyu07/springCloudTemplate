package com.example.controller;

import com.example.config.common.RedsCondition;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import lombok.extern.slf4j.Slf4j;
import org.apache.commons.lang3.StringUtils;
import org.springframework.beans.factory.annotation.Qualifier;
import org.springframework.data.redis.core.RedisTemplate;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.client.RestTemplate;

import jakarta.annotation.Resource;
import java.util.ArrayList;
import java.util.List;


/**
 * @author 杨镇宇
 * @version 1.0
 */
@Tag(name = "初始化")
@RestController
@Slf4j
@RequestMapping(value="api/a/init")
public class InitController {

    @Qualifier("redisStdTemplate")
    @Resource
    RedisTemplate<String, Object> redisTemplate;

    public List<String> getData(String flag){
        List<String> idList = new ArrayList<>();
        for (int i = 1; i < 5000; i++) {
            String id = "";
            if (StringUtils.equals("9",flag)) {
                id = String.format("%09d", i);
            } else if (StringUtils.equals("11",flag)) {
                id = String.format("%011d", i);
            } else if (StringUtils.equals("7",flag)) {
                id = String.format("%07d", i);
            } else if (StringUtils.equals("14",flag)){
                id = String.format("%014d", i);
            }
            idList.add(id);
        }
        return idList;
    }
    /**
     * 测试https a
     * @return
     */
    @Operation(summary = "redis初始化", description = "redis初始化")
    @GetMapping("/initData")
    public ResponseEntity<String> initData() {
        try {
            List<String> data = getData("14");
            redisTemplate.opsForList().rightPushAll(RedsCondition.MESSAGE_IDENTIFIER_KEY, data);
            List<String> data1 = getData("11");
            redisTemplate.opsForList().rightPushAll(RedsCondition.WALLET_ID_KEY, data1);


            // 综合前置流水号 7位
            List<String> data2 = getData("7");
            redisTemplate.opsForList().rightPushAll(RedsCondition.COMPREHENSIVE_SERIAL_NUMBER_KEY, data2);

            // 交易中心流水号(行内其他渠道) 7位
            List<String> data3 = getData("7");
            redisTemplate.opsForList().rightPushAll(RedsCondition.TRANSACTION_CENTER_SERIAL_NUMBER_OTHER_KEY, data3);

            // 交易中心流水号(系统内微服务) 7位
            List<String> data4 = getData("7");
            redisTemplate.opsForList().rightPushAll(RedsCondition.TRANSACTION_CENTER_SERIAL_NUMBER_KEY, data4);

            // 业务跟踪码 9 位
            List<String> data5 = getData("9");
            redisTemplate.opsForList().rightPushAll(RedsCondition.CASE_NUMBER_KEY, data5);

            return ResponseEntity.ok("ok");

        } catch (Exception e) {
            e.printStackTrace();
            return ResponseEntity.ok(null);

        }
    }

}
