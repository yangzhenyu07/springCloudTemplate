package com.example.controller;

import com.baomidou.mybatisplus.core.metadata.IPage;
import com.example.common.result.Result;
import com.example.entity.SysUser;
import com.example.service.SysUserService;
import com.example.vo.UserPageQuery;
import com.example.vo.UserVo;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import jakarta.annotation.Resource;
import jakarta.validation.Valid;
import lombok.extern.slf4j.Slf4j;
import org.springframework.validation.annotation.Validated;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

/**
 * 用户接口（含 MyBatis-Plus 分页 demo）
 *
 * @author 杨镇宇
 * @version 1.0
 */
@Tag(name = "用户")
@RestController
@Slf4j
@Validated
@RequestMapping(value = "/api/a/user")
public class SysUserController {

    @Resource
    private SysUserService sysUserService;

    /**
     * 分页查询：GET /api/a/user/page?current=1&size=10&username=zhang&status=1
     *
     * @param query 分页查询条件
     * @return 分页结果
     */
    @Operation(summary = "分页查询用户（返回实体）", description = "MyBatis-Plus 分页插件 demo")
    @GetMapping("/page")
    public Result<IPage<SysUser>> page(@Valid UserPageQuery query) {
        return Result.success(sysUserService.pageUsers(query));
    }

    /**
     * 分页查询并转成 VO：GET /api/a/user/pageVo?current=1&size=10
     *
     * @param query 分页查询条件
     * @return 分页结果
     */
    @Operation(summary = "分页查询用户（返回VO）", description = "实体不直接对外暴露，用 IPage#convert 转换")
    @GetMapping("/pageVo")
    public Result<IPage<UserVo>> pageVo(@Valid UserPageQuery query) {
        return Result.success(sysUserService.pageUserVos(query));
    }
}
