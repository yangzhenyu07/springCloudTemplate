package com.example.bdemo.flow.raw;

import com.example.bdemo.entity.*;
import lombok.Data;

import java.util.List;

/**
 * @author yangzhenyu
 * @version 1.0
 * @description:
 * @date 2026/9/28 19:40
 */
@Data
public class TradeFlowRawConfig {
    private List<SceneInfo> scenes;
    private List<FlowInfo> flows;

    private List<SceneFlowRelation> sceneFlowRels;
    private List<FlowNode> nodes;
    private List<FlowNodeRelation> flowNodeRels;
}
