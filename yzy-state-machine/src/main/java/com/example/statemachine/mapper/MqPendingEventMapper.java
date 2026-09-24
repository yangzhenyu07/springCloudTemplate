package com.example.statemachine.mapper;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import com.example.statemachine.entity.MqPendingEvent;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;
import org.apache.ibatis.annotations.Select;

import java.util.List;

/**
 * 乱序超前事件暂存表 Mapper（mq_pending_event）
 *
 * <p>回放语义：按 flow_id 升序（近似入队顺序）取出暂存事件逐个尝试应用，
 * 应用成功即删除；不可应用的（状态还没追上）留待下次流转后重试。</p>
 *
 * @author yzy
 * @version 1.0
 */
@Mapper
public interface MqPendingEventMapper extends BaseMapper<MqPendingEvent> {

    /**
     * 按业务单号查询暂存事件（flow_id 升序）
     *
     * @param bizNo 业务单号
     * @return 暂存事件列表（通常 0-2 条，乱序窗口很小）
     */
    @Select("SELECT id, biz_no, flow_id, event, message_body, trace_id, msg_id, create_time "
            + "FROM mq_pending_event WHERE biz_no = #{bizNo} ORDER BY flow_id ASC")
    List<MqPendingEvent> selectByBizNo(@Param("bizNo") String bizNo);
}
