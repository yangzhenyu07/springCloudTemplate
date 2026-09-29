package com.example.bdemo.flow.common.flow;

import lombok.Data;

import java.util.List;

/**
 * @author yangzhenyu
 * @version 1.0
 * @description:
 * @date 2026/9/28 20:05
 */
@Data
public class SceneDefinition {

    private String sceneCode;

    private String sceneName;

    private String sceneDesc;

    private List<SceneFlowDefinition> sceneFlows;
}