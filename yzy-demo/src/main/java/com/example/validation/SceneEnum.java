package com.example.validation;

/**
 * 校验场景枚举（校验上下文）
 *
 * <p>同一个 VO 在不同 Service 方法中对应不同场景，字段规则按场景生效。
 * 新增业务场景时在此扩展枚举值即可，无需改动校验框架代码。</p>
 *
 * @author yzy
 */
public enum SceneEnum {

    /** 新增场景 */
    CREATE,

    /** 修改场景 */
    UPDATE,

    /** 审核场景 */
    AUDIT,

    /** 查询场景 */
    QUERY
}
