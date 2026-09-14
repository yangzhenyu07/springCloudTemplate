package com.example.bdemo;

import org.mybatis.spring.annotation.MapperScan;
import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.cloud.client.discovery.EnableDiscoveryClient;

/**
 * yzy-b-demo 服务启动类
 * 集成 DB(MyBatis-Plus) + Redis + Nacos(配置中心/注册中心)
 *
 * @author yzy
 * @version 1.0
 */
@EnableDiscoveryClient
@MapperScan("com.example.bdemo.mapper")
@SpringBootApplication(scanBasePackages = {"com.example.bdemo", "com.example.config"})
public class YzyBDemoApplication {

    public static void main(String[] args) {
        SpringApplication.run(YzyBDemoApplication.class, args);
    }
}
