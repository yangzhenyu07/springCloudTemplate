package com.example.mapper;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import com.example.entity.TradeMessageFlow;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;
import org.apache.ibatis.annotations.Select;

/**
 * 报文流水表 Mapper（trade_message_flow）
 *
 * <p>继承 MyBatis-Plus BaseMapper，insert 由框架生成，
 * 幂等拦截依赖表中 uk_idem_key 唯一索引 + DuplicateKeyException 捕获。</p>
 *
 * @author yzy
 * @version 1.1
 */
@Mapper
public interface TradeMessageFlowMapper extends BaseMapper<TradeMessageFlow> {

    /**
     * 查询业务单号最新一条已受理的事件名（入口预检数据源）
     *
     * <p>入口预检（防线A）用它推导"在途状态"：最新受理事件的 to 状态。
     * 选择流水表而非 trade_order_state 的原因：状态表是<b>消费后视角</b>，
     * 消息有消费延迟（秒级～分钟级），连续快速提交同一单号的多个事件时
     * （上一事件尚未被消费）会被误判乱序；流水表是<b>受理视角</b>，
     * 落库即生效，永远不落后于受理进度。</p>
     *
     * @param bizNo 业务单号
     * @return 最新事件名（TRADE_CREATE/TRADE_PAY/TRADE_FINISH）；无流水返回 null
     */
    @Select("SELECT event FROM trade_message_flow WHERE biz_no = #{bizNo} ORDER BY id DESC LIMIT 1")
    String selectLatestEventByBizNo(@Param("bizNo") String bizNo);
}
