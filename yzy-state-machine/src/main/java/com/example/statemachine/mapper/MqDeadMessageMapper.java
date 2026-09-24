package com.example.statemachine.mapper;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import com.example.statemachine.entity.MqDeadMessage;
import org.apache.ibatis.annotations.Mapper;

/**
 * MQ 死信记录表 Mapper（mq_dead_message）
 *
 * @author yzy
 * @version 1.0
 */
@Mapper
public interface MqDeadMessageMapper extends BaseMapper<MqDeadMessage> {
}
