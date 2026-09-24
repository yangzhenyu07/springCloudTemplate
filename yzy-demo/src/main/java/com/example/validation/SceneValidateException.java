package com.example.validation;

import java.util.Collections;
import java.util.List;

/**
 * 场景校验失败异常
 *
 * <p>聚合本轮场景命中的全部违规项，一次性抛出，
 * 便于调用方（如全局异常处理器）把完整校验结果返回前端。</p>
 *
 * @author yzy
 */
public class SceneValidateException extends RuntimeException {

    private static final long serialVersionUID = 1L;

    /** 全部违规描述（格式：字段名: 提示） */
    private final List<String> violations;

    /**
     * 构造校验异常
     *
     * @param violations 违规描述列表
     */
    public SceneValidateException(List<String> violations) {
        super(String.join("; ", violations));
        this.violations = Collections.unmodifiableList(violations);
    }

    /**
     * 获取全部违规描述
     *
     * @return 违规描述列表（只读）
     */
    public List<String> getViolations() {
        return violations;
    }
}
