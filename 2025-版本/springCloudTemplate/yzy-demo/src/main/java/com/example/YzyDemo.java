package com.example;

import org.mybatis.spring.annotation.MapperScan;
import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.cloud.client.discovery.EnableDiscoveryClient;
import org.springframework.cloud.openfeign.EnableFeignClients;
import org.springframework.scheduling.annotation.EnableAsync;

/**
 * yzy-demo 启动类
 * 集成 DB(MyBatis-Plus) + Redis + Nacos(配置中心/注册中心) + OpenFeign + Knife4j/OpenAPI3
 *
 * @author 杨镇宇
 * @version 1.0
 */
@EnableAsync
@EnableDiscoveryClient
@EnableFeignClients(basePackages = "com.example.feign")
@MapperScan("com.example.mapper")
@SpringBootApplication(scanBasePackages = {"com.example"})
public class YzyDemo {

    public static void main(String[] args) {
        SpringApplication.run(YzyDemo.class, args);
    }

}
