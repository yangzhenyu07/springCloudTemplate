package com.example.dto;

import io.swagger.annotations.ApiModel;
import io.swagger.annotations.ApiModelProperty;
import lombok.Data;

import javax.validation.constraints.NotBlank;
import javax.validation.constraints.Size;
import java.io.Serializable;

/**
 * 交易报文提交请求 DTO
 *
 * <p>参数校验说明：@NotBlank + Controller 侧 @Valid 完成 入口参数硬校验，
 * 防止空 bizNo/idemKey 进入业务逻辑（否则 Redis 幂等 key 会退化为
 * {@code idem:trade:null}，所有空参请求共享同一把"幂等锁"互相误判）。</p>
 *
 * @author yzy
 * @version 1.0
 */
@Data
@ApiModel(value = "TradeSubmitDTO", description = "交易中心报文提交请求")
public class TradeSubmitDTO implements Serializable {

    private static final long serialVersionUID = 1L;

    @NotBlank(message = "业务单号 bizNo 不能为空")
    @Size(max = 64, message = "业务单号 bizNo 长度不能超过 64")
    @ApiModelProperty(value = "业务单号（顺序消息 hashKey，同一单号保证消费顺序）", required = true, example = "B20260915001")
    private String bizNo;

    @NotBlank(message = "交易事件 event 不能为空")
    @Size(max = 32, message = "交易事件 event 长度不能超过 32")
    @ApiModelProperty(value = "交易事件：TRADE_CREATE / TRADE_PAY / TRADE_FINISH", required = true, example = "TRADE_CREATE")
    private String event;

    @NotBlank(message = "幂等key idemKey 不能为空")
    @Size(max = 64, message = "幂等key idemKey 长度不能超过 64")
    @ApiModelProperty(value = "幂等key（客户端每次请求唯一，如 UUID）", required = true, example = "9f8e7d6c-1111-2222-3333-444455556666")
    private String idemKey;

    /**
     * 入口仅做防恶意超大报文的 sanity 上限（4096）；业务长度约束（1024）由
     * trade_message_flow.message_body VARCHAR(1024) 兜底——超长报文在 DB 层
     * 触发异常 → 事务回滚 → Redis 幂等 key 不删除（需求 2.3 语义）。
     */
    @Size(max = 4096, message = "交易报文 messageBody 长度不能超过 4096")
    @ApiModelProperty(value = "交易报文原文", example = "{\"amount\":100.00}")
    private String messageBody;
}
