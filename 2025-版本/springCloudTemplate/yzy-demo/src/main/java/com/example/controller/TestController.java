package com.example.controller;

import com.example.vo.TestVo;
import io.swagger.v3.oas.annotations.tags.Tag;
import lombok.extern.slf4j.Slf4j;
import org.springframework.validation.annotation.Validated;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

/**
 * @author yangzhenyu
 * @version 1.0
 * @description:
 * @date 2026/9/29 10:17
 */
@Tag(name = "测试")
@RestController
@Slf4j
@Validated
@RequestMapping(value = "/api/a/user")
public class TestController {

    /**
     * 测试序列化
     *
     * @return 测试数据
     */
    @PostMapping("/postHello")
    public TestVo test(){
        TestVo testVo = new TestVo();
        testVo.setI("45");
        return testVo;
    }
}
