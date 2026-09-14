package com.example.mapper;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import com.example.entity.SysUser;
import org.apache.ibatis.annotations.Mapper;

/**
 * 系统用户Mapper接口
 *
 * @author yzy
 * @version 1.0
 */
@Mapper
public interface SysUserMapper extends BaseMapper<SysUser> {
}
