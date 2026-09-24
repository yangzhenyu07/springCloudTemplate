package com.example.controller;

import com.example.common.enums.ResultCode;
import com.example.common.result.Result;
import com.example.common.trace.TraceIdUtil;
import com.example.dto.TradeSubmitDTO;
import com.example.service.SubmitResult;
import com.example.service.TradeService;
import io.swagger.annotations.Api;
import io.swagger.annotations.ApiOperation;
import lombok.extern.slf4j.Slf4j;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import javax.annotation.Resource;
import javax.validation.Valid;
import java.util.HashMap;
import java.util.Map;

/**
 * 交易中心 - 交易报文提交入口
 *
 * <p>幂等设计说明：重复请求时统一返回 message=【重复请求】并终止后续业务流程，
 * 响应中附带 source 字段标识拦截层次（redis / db），便于排查与测试。</p>
 *
 * @author yzy
 * @version 1.0
 */
@Api(value = "交易中心", tags = {"交易中心"})
@Slf4j
@RestController
@RequestMapping("api/trade")
public class TradeController {

    @Resource
    private TradeService tradeService;

    /**
     * 交易报文提交（幂等校验 + 报文流水落库 + 顺序消息发送）
     *
     * @param dto 交易报文提交请求（bizNo / event / idemKey 必填）
     * @return 受理成功返回 flowId；重复请求返回【重复请求】及拦截层次
     */
    @ApiOperation(value = "交易报文提交", notes = "幂等校验+乱序预检+DB唯一索引，成功后发送顺序消息")
    @PostMapping("/submit")
    public Result<Map<String, Object>> submit(@Valid @RequestBody TradeSubmitDTO dto) {
        String traceId = TraceIdUtil.getTraceId();
        log.info("[交易中心] 收到报文提交请求，traceId={}, bizNo={}, event={}, idemKey={}",
                traceId, dto.getBizNo(), dto.getEvent(), dto.getIdemKey());

        SubmitResult result = tradeService.submit(dto);
        Map<String, Object> data = new HashMap<>(4);
        Result<Map<String, Object>> r;
        switch (result) {
            case DUPLICATE:
                // 幂等拦截：Redis 层或 DB 唯一索引层
                data.put("source", "idempotent");
                r = Result.failed("重复请求");
                log.warn("[交易中心] 返回【重复请求】，traceId={}, bizNo={}", traceId, dto.getBizNo());
                break;
            case STATE_CONFLICT:
                // 乱序拦截（防线A）：事件与订单当前状态不匹配，请求未进 MQ
                data.put("source", "state-precheck");
                r = Result.failed(ResultCode.CONFLICT, "当前状态不允许该操作");
                log.warn("[交易中心] 返回【状态冲突】（乱序预检拦截），traceId={}, bizNo={}, event={}",
                        traceId, dto.getBizNo(), dto.getEvent());
                break;
            default:
                data.put("accepted", true);
                r = Result.success("受理成功", data);
                break;
        }
        r.setTraceId(traceId);
        r.setData(data);
        return r;
    }
}
