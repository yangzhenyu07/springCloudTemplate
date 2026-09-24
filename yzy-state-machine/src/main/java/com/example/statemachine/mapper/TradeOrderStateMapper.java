package com.example.statemachine.mapper;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import com.example.statemachine.entity.TradeOrderState;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;
import org.apache.ibatis.annotations.Select;
import org.apache.ibatis.annotations.Update;

/**
 * 订单状态机状态表 Mapper（trade_order_state）
 *
 * @author yzy
 * @version 1.0
 */
@Mapper
public interface TradeOrderStateMapper extends BaseMapper<TradeOrderState> {

    /**
     * 按业务单号查询状态记录
     *
     * @param bizNo 业务单号
     * @return 状态记录，不存在返回 null
     */
    @Select("SELECT id, biz_no, state, pre_state, version, create_time, update_time "
            + "FROM trade_order_state WHERE biz_no = #{bizNo}")
    TradeOrderState selectByBizNo(@Param("bizNo") String bizNo);

    /**
     * 条件更新（CAS 语义）：仅当当前状态等于预期前置状态时才流转
     *
     * <p>这是状态机防乱序/防重复的核心：消息重复或乱序时，
     * WHERE 条件不匹配 → 影响行数为 0 → 上层判定为非法流转/冲突并告警。</p>
     *
     * @param bizNo 业务单号
     * @param from  预期前置状态
     * @param to    目标状态
     * @return 影响行数（0 = 当前状态与预期不符，流转被拒绝）
     */
    @Update("UPDATE trade_order_state SET state = #{to}, pre_state = #{from}, version = version + 1 "
            + "WHERE biz_no = #{bizNo} AND state = #{from}")
    int casUpdateState(@Param("bizNo") String bizNo,
                       @Param("from") String from,
                       @Param("to") String to);
}
