package com.example.config;

import com.fasterxml.jackson.annotation.JsonAutoDetect;
import com.fasterxml.jackson.annotation.JsonTypeInfo;
import com.fasterxml.jackson.annotation.PropertyAccessor;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.jsontype.impl.LaissezFaireSubTypeValidator;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.autoconfigure.condition.ConditionalOnExpression;
import org.springframework.boot.autoconfigure.condition.ConditionalOnWebApplication;
import org.springframework.boot.autoconfigure.data.redis.RedisProperties;
import org.springframework.boot.context.properties.EnableConfigurationProperties;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.data.redis.connection.RedisClusterConfiguration;
import org.springframework.data.redis.connection.RedisNode;
import org.springframework.data.redis.connection.RedisSentinelConfiguration;
import org.springframework.data.redis.connection.jedis.JedisConnectionFactory;
import org.springframework.data.redis.core.RedisTemplate;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.data.redis.serializer.Jackson2JsonRedisSerializer;
import org.springframework.data.redis.serializer.RedisSerializer;
import org.springframework.data.redis.serializer.StringRedisSerializer;
import redis.clients.jedis.JedisPoolConfig;

import java.util.ArrayList;
import java.util.List;
import java.util.Objects;

/**
 * @author yangzhenyu
 * @version 1.0
 */
@Configuration
@ConditionalOnWebApplication
@ConditionalOnExpression("${spring.redis.my.flag:false} == true")
@EnableConfigurationProperties({RedisStdProperties.class})
public class RedisStdConfig {
    private static final Logger log = LoggerFactory.getLogger(RedisStdConfig.class);

    public RedisStdConfig() {
        log.info("===================集成 redis 配置===================");
    }

    private JedisConnectionFactory getJedisConnectionFactoryFromRedisLockProperties(RedisStdProperties redisStdProperties) {
        JedisConnectionFactory factory = null;
        JedisPoolConfig poolConfig = redisStdProperties.getPool() == null ? new JedisPoolConfig() : jedisPoolConfig(redisStdProperties);
        if (redisStdProperties.getSentinel() != null) {
            //Sentinel
            RedisSentinelConfiguration redisSentinelConfiguration = new RedisSentinelConfiguration();
            RedisStdProperties.Sentinel sentinel = redisStdProperties.getSentinel();
            redisSentinelConfiguration.setMaster(sentinel.getMaster());
            List<String> nodesStr = sentinel.getNodes();
            List<RedisNode> sentinels = new ArrayList<>();
            for (String s : nodesStr) {
                sentinels.add(new RedisNode(s.split(":")[0], Integer.parseInt(s.split(":")[1])));
            }
            redisSentinelConfiguration.setSentinels(sentinels);
            if (redisStdProperties.getPassword() != null) {
                redisSentinelConfiguration.setPassword(redisStdProperties.getPassword());
            }
            factory = new JedisConnectionFactory(redisSentinelConfiguration, poolConfig);
        } else if (redisStdProperties.getCluster() != null) {
            //Cluster
            RedisClusterConfiguration clusterConfig = new RedisClusterConfiguration();
            RedisStdProperties.Cluster cluster = redisStdProperties.getCluster();
            Integer maxRedirects = cluster.getMaxRedirects();
            clusterConfig.setMaxRedirects(maxRedirects);
            List<String> nodes = cluster.getNodes();
            List<RedisNode> clusterNodes = new ArrayList<>();
            for (String clusterNode : nodes) {

                clusterNodes.add(new RedisNode(clusterNode.split(":")[0], Integer.parseInt(clusterNode.split(":")[1])));
            }
            clusterConfig.setClusterNodes(clusterNodes);
            // 设置集群的密码
            if (redisStdProperties.getPassword() != null) {
                clusterConfig.setPassword(redisStdProperties.getPassword());  // 为集群配置密码
            }
            factory = new JedisConnectionFactory(clusterConfig, poolConfig);
        } else {
            factory = new JedisConnectionFactory(poolConfig);
            Objects.requireNonNull(factory.getStandaloneConfiguration()).setHostName(redisStdProperties.getHost());
            factory.getStandaloneConfiguration().setPort(redisStdProperties.getPort());
        }
        Objects.requireNonNull(factory.getStandaloneConfiguration()).setDatabase(redisStdProperties.getDatabase());

        if (redisStdProperties.getPassword() != null) {
            factory.getStandaloneConfiguration().setPassword(redisStdProperties.getPassword());
        }

        factory.afterPropertiesSet();
        return factory;
    }

    private JedisPoolConfig jedisPoolConfig(RedisStdProperties redisStdProperties) {
        JedisPoolConfig config = new JedisPoolConfig();
        RedisProperties.Pool props = redisStdProperties.getPool();
        config.setMaxTotal(props.getMaxActive());
        config.setMaxIdle(props.getMaxIdle());
        config.setMinIdle(props.getMinIdle());
        config.setMaxWaitMillis(props.getMaxWait().toMillis());
        config.setTestWhileIdle(true);
        return config;
    }
    //缓存操作组件
    @Bean(name = "stringRedisStdTemplate")
    public StringRedisTemplate stringRedisTemplate(@Autowired RedisStdProperties redisStdProperties){
        StringRedisTemplate stringRedisTemplate = new StringRedisTemplate();
        stringRedisTemplate.setConnectionFactory(getJedisConnectionFactoryFromRedisLockProperties(redisStdProperties));
        return stringRedisTemplate;
    }
    /**
     * RedisTemplate配置
     */
    @Bean(name = "redisStdTemplate")
    public RedisTemplate<String, Object> redisStdTemplate(@Autowired RedisStdProperties redisStdProperties, Jackson2JsonRedisSerializer<Object> jackson2JsonRedisSerializer) {
        // 设置序列化
        ObjectMapper om = new ObjectMapper();
        om.setVisibility(PropertyAccessor.ALL, JsonAutoDetect.Visibility.ANY);
        om.activateDefaultTyping(LaissezFaireSubTypeValidator.instance,
                ObjectMapper.DefaultTyping.NON_FINAL, JsonTypeInfo.As.WRAPPER_ARRAY);
        jackson2JsonRedisSerializer.setObjectMapper(om);
        // 配置redisTemplate
        RedisTemplate<String, Object> redisTemplate = new RedisTemplate<String, Object>();
        redisTemplate.setConnectionFactory(getJedisConnectionFactoryFromRedisLockProperties(redisStdProperties));
        RedisSerializer<?> stringSerializer = new StringRedisSerializer();
        // key序列化
        redisTemplate.setKeySerializer(stringSerializer);
        // value序列化
        redisTemplate.setValueSerializer(jackson2JsonRedisSerializer);
        // Hash key序列化
        redisTemplate.setHashKeySerializer(stringSerializer);
        // Hash value序列化
        redisTemplate.setHashValueSerializer(jackson2JsonRedisSerializer);
        redisTemplate.afterPropertiesSet();
        return redisTemplate;
    }

    /**
     * 使用Jackson序列化对象
     */
    @Bean
    public Jackson2JsonRedisSerializer<Object> jackson2JsonRedisSerializer() {
        Jackson2JsonRedisSerializer<Object> serializer = new Jackson2JsonRedisSerializer<Object>(Object.class);

        ObjectMapper objectMapper = new ObjectMapper();
        objectMapper.setVisibility(PropertyAccessor.ALL, JsonAutoDetect.Visibility.ANY);
        objectMapper.activateDefaultTyping(LaissezFaireSubTypeValidator.instance,
                ObjectMapper.DefaultTyping.NON_FINAL, JsonTypeInfo.As.WRAPPER_ARRAY);
        serializer.setObjectMapper(objectMapper);

        return serializer;
    }
}
