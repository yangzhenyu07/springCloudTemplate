package com.example.service;

import com.example.entity.SysUser;

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
}
