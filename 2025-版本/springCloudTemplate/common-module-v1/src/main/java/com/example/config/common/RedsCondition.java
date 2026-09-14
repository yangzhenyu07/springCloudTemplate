package com.example.config.common;

public interface RedsCondition {

    // 报文标识号 14位
    String MESSAGE_IDENTIFIER_KEY = "MESSAGE_IDENTIFIER_KEY";
    // 钱包ID 11 位
    String WALLET_ID_KEY= "WALLET_ID_KEY";
    // 综合前置流水号 7位
    String COMPREHENSIVE_SERIAL_NUMBER_KEY = "COMPREHENSIVE_SERIAL_NUMBER_KEY";

    // 交易中心流水号(行内其他渠道) 7位
    String TRANSACTION_CENTER_SERIAL_NUMBER_OTHER_KEY = "TRANSACTION_CENTER_SERIAL_NUMBER_OTHER_KEY";
    // 交易中心流水号(系统内微服务) 7位
    String TRANSACTION_CENTER_SERIAL_NUMBER_KEY = "TRANSACTION_CENTER_SERIAL_NUMBER_KEY";

    // 业务跟踪码 9 位
    String CASE_NUMBER_KEY = "CASE_NUMBER_KEY";



}
