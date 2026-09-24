package com.example.validation;

import com.example.validation.annotation.SceneCheck;
import org.aspectj.lang.ProceedingJoinPoint;
import org.aspectj.lang.annotation.Around;
import org.aspectj.lang.annotation.Aspect;
import org.springframework.stereotype.Component;

/**
 * 场景校验 AOP 切面
 *
 * <p>拦截标注 {@link SceneCheck} 的 Service 方法，在业务执行前
 * 按注解声明的场景对指定下标的 VO 参数做校验；
 * 校验失败抛 {@link SceneValidateException}，业务方法体完全不感知校验逻辑。</p>
 *
 * @author yzy
 */
@Aspect
@Component
public class SceneCheckAspect {

    /**
     * 方法执行前完成场景校验，通过则放行
     *
     * @param joinPoint  连接点
     * @param sceneCheck 方法上的场景校验注解
     * @return 业务方法返回值
     * @throws Throwable 校验异常或业务异常
     */
    @Around("@annotation(sceneCheck)")
    public Object around(ProceedingJoinPoint joinPoint, SceneCheck sceneCheck) throws Throwable {
        Object[] args = joinPoint.getArgs();
        int index = sceneCheck.argIndex();
        Object target = index < args.length ? args[index] : null;
        SceneValidator.validate(target, sceneCheck.value());
        return joinPoint.proceed();
    }
}
