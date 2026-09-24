package com.example.statemachine.entity;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import lombok.Data;

import java.io.Serializable;
import java.util.Date;

/**
 * 订单状态机状态表实体（trade_order_state）
 *
 * <p>每笔业务单号（biz_no）对应一条状态记录（唯一索引 uk_biz_no）。
 * 状态流转通过「条件更新」实现乐观锁语义：
 * {@code UPDATE ... SET state=目标 WHERE biz_no=? AND state=前置状态}，
 * 即使消息重复投递或乱序到达，非法流转也会因 WHERE 条件不匹配而影响行数为 0，
 * 从数据库层面保证状态一致性（第三道幂等防线）。</p>
 *
 * @author yzy
 * @version 1.0
 */
@Data
@TableName("trade_order_state")
public class TradeOrderState implements Serializable {

    private static final long serialVersionUID = 1L;

    /** 主键（数据库自增） */
    @TableId(value = "id", type = IdType.AUTO)
    private Long id;

    /** 业务单号（唯一索引 uk_biz_no） */
    private String bizNo;

    /** 当前状态：INIT / CREATED / PAID / FINISHED */
    private String state;

    /** 流转前状态（首次创建为 null） */
    private String preState;

    /** 流转次数（每次合法流转 +1，用于观测与对账） */
    private Integer version;

    /** 创建时间 */
    private Date createTime;

    /** 更新时间 */
    private Date updateTime;
}
