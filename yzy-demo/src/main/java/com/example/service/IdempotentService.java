package com.example.service;

import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Qualifier;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.stereotype.Service;

import javax.annotation.Resource;
import java.time.Duration;

/**
 * Redis 幂等校验服务（交易中心幂等设计的第一道防线）
 *
 * <p>核心原理：利用 Redis 单线程模型下的原子命令 {@code SET key value EX seconds NX}，
 * 只有多并发请求中的其中一个能设置成功（拿到幂等标记），其余全部返回失败。</p>
 *
 * <p>设计约定（重要）：</p>
 * <ul>
 *   <li>幂等 key 过期时间 259200 秒 = 3 天；</li>
 *   <li>业务执行失败时【不主动删除】幂等 key，等待 3 天自动过期——
 *       避免失败重试窗口内 key 被误删导致重复请求穿透到下游；</li>
 *   <li>Redis 层拿到标记后仍可能发生并发穿透（如 key 恰好过期），
 *       由 DB 层 trade_message_flow 表的 uk_idem_key 唯一索引兜底。</li>
 * </ul>
 *
 * @author yzy
 * @version 1.0
 */
@Slf4j
@Service
public class IdempotentService {

    /** 幂等 key 统一前缀 */
    private static final String IDEM_KEY_PREFIX = "idem:trade:";

    /** 幂等 key 有效期：259200 秒 = 3 天 */
    private static final Duration IDEM_EXPIRE = Duration.ofSeconds(259200L);

    /** 幂等标记值（仅作占位，判断依据是 key 是否存在） */
    private static final String IDEM_VALUE = "1";

    /**
     * StringRedisTemplate：key/value 均为 String 序列化，
     * setIfAbsent(key, value, timeout) 最终执行的正是 SET key value NX EX/PX 原子命令
     */
    @Qualifier("stringRedisStdTemplate")
    @Resource
    private StringRedisTemplate stringRedisTemplate;

    /**
     * 尝试获取幂等标记（非阻塞、原子性）
     *
     * <p>对应命令：{@code SET idem:trade:{idemKey} 1 EX 259200 NX}</p>
     *
     * @param idemKey 幂等 key（客户端每次请求唯一）
     * @return true  = 设置成功，拿到幂等标记，允许继续执行业务；
     *         false = key 已存在，判定为重复请求，应直接终止流程
     */
    public boolean tryAcquire(String idemKey) {
        String redisKey = IDEM_KEY_PREFIX + idemKey;
        Boolean acquired = stringRedisTemplate.opsForValue().setIfAbsent(redisKey, IDEM_VALUE, IDEM_EXPIRE);
        boolean result = Boolean.TRUE.equals(acquired);
        if (result) {
            log.info("[幂等] Redis SET NX 成功，拿到幂等标记，key={}", redisKey);
        } else {
            log.warn("[幂等] Redis SET NX 返回 false，key 已存在，判定为重复请求，key={}", redisKey);
        }
        return result;
    }
}
