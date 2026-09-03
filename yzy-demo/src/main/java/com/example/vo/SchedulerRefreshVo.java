package com.example.vo;

import io.swagger.annotations.ApiModelProperty;
import lombok.*;
import org.hibernate.validator.constraints.NotEmpty;

@Data
@Builder
@AllArgsConstructor
@NoArgsConstructor
@EqualsAndHashCode(callSuper = false)
public class SchedulerRefreshVo {
    @ApiModelProperty("triggerKey")
    @NotEmpty(message ="triggerKey不能为空")
    private String triggerKey;
    @ApiModelProperty("cronExpression")
    @NotEmpty(message ="cronExpression不能为空")
    private String cronExpression;
}
