package com.example.config;

import com.baomidou.mybatisplus.annotation.DbType;
import com.baomidou.mybatisplus.extension.plugins.MybatisPlusInterceptor;
import com.baomidou.mybatisplus.extension.plugins.inner.PaginationInnerInterceptor;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

/**
 * MyBatis-Plus 插件配置
 * <p>
 * 关键点：分页必须注册 PaginationInnerInterceptor，否则 selectPage 不会拼接 LIMIT，
 * 会退化成「查全表 + 内存截取」，数据量大时直接把库打爆。
 * <p>
 * 注意 MybatisPlusInterceptor 是「总入口」，内部拦截器有顺序要求：
 * 多租户 -> 动态表名 -> 分页 -> 乐观锁，分页一般放在最后。
 *
 * @author 杨镇宇
 * @version 1.0
 */
@Configuration
public class MybatisPlusConfig {

    /**
     * 单页最大条数（兜底防御，防止前端传 size=999999）
     */
    private static final Long MAX_LIMIT = 500L;

    @Bean
    public MybatisPlusInterceptor mybatisPlusInterceptor() {
        MybatisPlusInterceptor interceptor = new MybatisPlusInterceptor();

        PaginationInnerInterceptor paginationInterceptor = new PaginationInnerInterceptor(DbType.MYSQL);
        // 单页条数上限，超过则按 MAX_LIMIT 截断
        paginationInterceptor.setMaxLimit(MAX_LIMIT);
        // 超过总页数后是否回到第一页：false = 返回空列表（推荐，语义更清晰）
        paginationInterceptor.setOverflow(false);
        // count 查询优化：无 ORDER BY 时直接用 count(*)，有 ORDER BY 才包子查询
        paginationInterceptor.setOptimizeJoin(true);

        interceptor.addInnerInterceptor(paginationInterceptor);
        return interceptor;
    }
}
