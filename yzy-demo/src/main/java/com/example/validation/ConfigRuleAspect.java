package com.example.validation;

import com.example.validation.annotation.ConfigCheck;
import org.aspectj.lang.ProceedingJoinPoint;
import org.aspectj.lang.annotation.Around;
import org.aspectj.lang.annotation.Aspect;
import org.springframework.stereotype.Component;

/**
 * 配置化校验 AOP 切面
 *
 * <p>拦截标注 {@link ConfigCheck} 的 Service 方法，在业务执行前
 * 按方法声明的场景 + JSON 规则校验 VO 参数。</p>
 *
 * @author yzy
 */
@Aspect
@Component
public class ConfigRuleAspect {

    /**
     * 方法执行前完成配置化校验，通过则放行
     *
     * @param joinPoint   连接点
     * @param configCheck 方法上的校验注解
     * @return 业务方法返回值
     * @throws Throwable 校验异常或业务异常
     */
    @Around("@annotation(configCheck)")
    public Object around(ProceedingJoinPoint joinPoint, ConfigCheck configCheck) throws Throwable {
        Object[] args = joinPoint.getArgs();
        int index = configCheck.argIndex();
        Object target = index < args.length ? args[index] : null;
        ConfigValidator.validate(target, configCheck.value());
        return joinPoint.proceed();
    }
}
