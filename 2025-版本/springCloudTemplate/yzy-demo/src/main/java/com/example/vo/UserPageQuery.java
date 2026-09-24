package com.example.vo;

import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.constraints.Max;
import jakarta.validation.constraints.Min;
import lombok.Data;
import org.springframework.format.annotation.DateTimeFormat;

import java.io.Serializable;
import java.time.LocalDateTime;

/**
 * 用户分页查询入参
 *
 * @author 杨镇宇
 * @version 1.0
 */
@Data
@Schema(description = "用户分页查询入参")
public class UserPageQuery implements Serializable {

    private static final long serialVersionUID = 1L;

    @Schema(description = "当前页，从 1 开始", example = "1")
    @Min(value = 1, message = "页码最小为 1")
    private Long current = 1L;

    @Schema(description = "每页条数", example = "10")
    @Min(value = 1, message = "每页条数最小为 1")
    @Max(value = 500, message = "每页条数最大为 500")
    private Long size = 10L;

    @Schema(description = "用户名（模糊匹配）")
    private String username;

    @Schema(description = "状态：0-禁用，1-启用")
    private Integer status;

    @Schema(description = "创建时间起（yyyy-MM-dd HH:mm:ss）")
    @DateTimeFormat(pattern = "yyyy-MM-dd HH:mm:ss")
    private LocalDateTime createTimeStart;

    @Schema(description = "创建时间止（yyyy-MM-dd HH:mm:ss）")
    @DateTimeFormat(pattern = "yyyy-MM-dd HH:mm:ss")
    private LocalDateTime createTimeEnd;
}
