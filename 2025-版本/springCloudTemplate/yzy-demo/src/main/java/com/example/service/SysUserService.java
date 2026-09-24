package com.example.service;

import com.baomidou.mybatisplus.core.metadata.IPage;
import com.example.entity.SysUser;
import com.example.vo.UserPageQuery;
import com.example.vo.UserVo;

import java.util.List;

/**
 * 系统用户服务
 *
 * @author yzy
 * @version 1.0
 */

public interface SysUserService {



    /**
     * 查询所有启用状态的用户
     *
     * @return 启用用户列表
     */
    List<SysUser> listActiveUsers() ;

    /**
     * 根据ID查询用户
     *
     * @param id 用户ID
     * @return 用户信息
     */
    SysUser getUserById(Long id) ;

    /**
     * 分页查询用户（返回实体分页）
     *
     * @param query 分页查询条件
     * @return 分页结果
     */
    IPage<SysUser> pageUsers(UserPageQuery query);

    /**
     * 分页查询用户（返回 VO 分页，实体转 VO 由 IPage#convert 完成，分页信息不丢）
     *
     * @param query 分页查询条件
     * @return 分页结果
     */
    IPage<UserVo> pageUserVos(UserPageQuery query);
}
