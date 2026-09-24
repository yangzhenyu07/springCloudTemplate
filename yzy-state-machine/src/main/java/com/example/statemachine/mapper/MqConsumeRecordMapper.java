package com.example.statemachine.mapper;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import com.example.statemachine.entity.MqConsumeRecord;
import org.apache.ibatis.annotations.Mapper;

/**
 * MQ 消费去重表 Mapper（mq_consume_record）
 *
 * <p>去重逻辑：insert 命中 uk_flow_id 唯一索引抛出 DuplicateKeyException
 * 即判定为重复消息（先查后插存在竞态，唯一索引是唯一可靠的判断方式）。</p>
 *
 * @author yzy
 * @version 1.0
 */
@Mapper
public interface MqConsumeRecordMapper extends BaseMapper<MqConsumeRecord> {
}
