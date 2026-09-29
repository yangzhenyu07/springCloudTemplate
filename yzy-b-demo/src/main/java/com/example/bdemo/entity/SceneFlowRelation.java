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
 * 场景流程关系表
 * </p>
 *
 * @author yzy
 * @since 2026-09-28 17:45:26
 */
@Getter
@Setter
@TableName("scene_flow_relation")
public class SceneFlowRelation implements Serializable {

    private static final long serialVersionUID = 1L;

    /**
     * ID
     */
    @TableId(value = "ID", type = IdType.AUTO)
    private Long id;

    /**
     * 场景编号
     */
    private String sceneCode;

    /**
     * 流程名称
     */
    private String flowCode;

    /**
     * 排序编号
     */
    private Integer sortNo;

    /**
     * 条件
     */
    private String conditional;

    /**
     * 创建时间
     */
    private LocalDateTime createTime;

    /**
     * 更新时间
     */
    private LocalDateTime updateTime;


}
