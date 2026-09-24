package com.example.service.impl;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.baomidou.mybatisplus.core.metadata.IPage;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.example.entity.SysUser;
import com.example.mapper.SysUserMapper;
import com.example.service.SysUserService;
import com.example.vo.UserPageQuery;
import com.example.vo.UserVo;
import lombok.extern.slf4j.Slf4j;
import org.apache.commons.lang3.StringUtils;
import org.springframework.beans.BeanUtils;
import org.springframework.stereotype.Service;

import jakarta.annotation.Resource;
import java.util.List;

/**
 * 系统用户服务
 *
 * @author yzy
 * @version 1.0
 */
@Slf4j
@Service
public class SysUserServiceImpl implements SysUserService {

    @Resource
    private SysUserMapper sysUserMapper;

    /**
     * 查询所有启用状态的用户
     *
     * @return 启用用户列表
     */
    public List<SysUser> listActiveUsers() {
        LambdaQueryWrapper<SysUser> wrapper = new LambdaQueryWrapper<>();
        wrapper.eq(SysUser::getStatus, 1);
        return sysUserMapper.selectList(wrapper);
    }

    /**
     * 根据ID查询用户
     *
     * @param id 用户ID
     * @return 用户信息
     */
    public SysUser getUserById(Long id) {
        return sysUserMapper.selectById(id);
    }

    /**
     * 分页查询用户（返回实体分页）
     *
     * @param query 分页查询条件
     * @return 分页结果
     */
    public IPage<SysUser> pageUsers(UserPageQuery query) {
        Page<SysUser> page = Page.of(query.getCurrent(), query.getSize());
        return sysUserMapper.selectPage(page, buildWrapper(query));
    }

    /**
     * 分页查询用户（返回 VO 分页）
     * <p>
     * IPage#convert 只转换 records，total/pages/current/size 等分页信息原样保留，
     * 不要自己 new Page 再 setRecords，容易漏掉 total 导致前端算不出总页数。
     *
     * @param query 分页查询条件
     * @return 分页结果
     */
    public IPage<UserVo> pageUserVos(UserPageQuery query) {
        return pageUsers(query).convert(this::toVo);
    }

    /**
     * 构造查询条件
     *
     * @param query 分页查询条件
     * @return 查询条件包装器
     */
    private LambdaQueryWrapper<SysUser> buildWrapper(UserPageQuery query) {
        LambdaQueryWrapper<SysUser> wrapper = new LambdaQueryWrapper<>();
        wrapper.like(StringUtils.isNotBlank(query.getUsername()), SysUser::getUsername, query.getUsername())
                .eq(query.getStatus() != null, SysUser::getStatus, query.getStatus())
                .ge(query.getCreateTimeStart() != null, SysUser::getCreateTime, query.getCreateTimeStart())
                .le(query.getCreateTimeEnd() != null, SysUser::getCreateTime, query.getCreateTimeEnd())
                .orderByDesc(SysUser::getCreateTime)
                .orderByDesc(SysUser::getId);
        return wrapper;
    }

    /**
     * 实体转 VO
     *
     * @param user 用户实体
     * @return 用户VO
     */
    private UserVo toVo(SysUser user) {
        UserVo vo = new UserVo();
        BeanUtils.copyProperties(user, vo);
        return vo;
    }
}
