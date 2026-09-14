package com.example.vo;

import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.constraints.NotEmpty;
import lombok.*;

@Data
@Builder
@AllArgsConstructor
@NoArgsConstructor
@EqualsAndHashCode(callSuper = false)
public class SchedulerRefreshVo {
    @Schema(description = "triggerKey")
    @NotEmpty(message ="triggerKey不能为空")
    private String triggerKey;
    @Schema(description = "cronExpression")
    @NotEmpty(message ="cronExpression不能为空")
    private String cronExpression;
}
