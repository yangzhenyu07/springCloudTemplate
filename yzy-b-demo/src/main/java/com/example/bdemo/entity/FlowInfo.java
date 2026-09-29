package com.example.bdemo.entity;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import java.io.Serializable;
import java.time.LocalDateTime;
import lombok.Getter;
import lombok.Setter;

/**
 * <p>
 * 流程表
 * </p>
 *
 * @author yzy
 * @since 2026-09-28 17:45:25
 */
@Getter
@Setter
@TableName("flow_info")
public class FlowInfo implements Serializable {

    private static final long serialVersionUID = 1L;

    /**
     * ID
     */
    @TableId(value = "ID", type = IdType.AUTO)
    private Long id;

    /**
     * 场景编号
     */
    private String flowCode;

    /**
     * 场景名称
     */
    private String flowName;

    /**
     * 场景类型
     */
    private String flowType;

    /**
     * 场景描述
     */
    private String sceneDes;

    /**
     * 创建时间
     */
    private LocalDateTime createTime;

    /**
     * 更新时间
     */
    private LocalDateTime updateTime;


}
