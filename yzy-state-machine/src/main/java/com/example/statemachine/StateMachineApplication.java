package com.example.statemachine;

import org.mybatis.spring.annotation.MapperScan;
import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.cloud.client.discovery.EnableDiscoveryClient;

/**
 * yzy-state-machine 状态机服务启动类
 *
 * <p>职责：顺序消费交易中心（yzy-demo）发出的 RocketMQ 顺序消息，
 * 按“状态机规则”驱动订单状态流转，并对外提供状态查询接口。</p>
 *
 * <p>集成组件：RocketMQ（ORDERLY 顺序消费）+ MyBatis-Plus + MySQL + Nacos（注册中心）</p>
 *
 * @author yzy
 * @version 1.0
 */
@EnableDiscoveryClient
@MapperScan("com.example.statemachine.mapper")
@SpringBootApplication(scanBasePackages = {"com.example.statemachine"})
public class StateMachineApplication {

    public static void main(String[] args) {
        SpringApplication.run(StateMachineApplication.class, args);
    }
}
