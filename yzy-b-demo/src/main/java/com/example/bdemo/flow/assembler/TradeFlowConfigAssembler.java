package com.example.bdemo.flow.assembler;

import com.alibaba.nacos.common.utils.StringUtils;
import com.example.bdemo.entity.*;
import com.example.bdemo.flow.common.flow.*;
import com.example.bdemo.flow.condition.SpelConditionEvaluator;
import com.example.bdemo.flow.raw.TradeFlowRawConfig;
import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.node.ArrayNode;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Component;

import java.util.*;
import java.util.stream.Collectors;

/**
 * @author yangzhenyu
 * @version 1.0
 * @description:
 * @date 2026/9/29 14:08
 */
@Slf4j

@Component
@RequiredArgsConstructor
public class TradeFlowConfigAssembler {

    private final SpelConditionEvaluator spelConditionEvaluator;
    private final ObjectMapper objectMapper;

    public TradeFlowConfig assemble(TradeFlowRawConfig raw){
        Map<String, NodeDefinition> nodeMap = assembleNodes(raw.getNodes());
        Map<String, FlowDefinition> flowMap = assembleFlows(raw.getFlows(), raw.getFlowNodeRels());
        Map<String, SceneDefinition> sceneMap = assembleScenes(raw.getScenes(), raw.getSceneFlowRels());

        TradeFlowConfig config = new TradeFlowConfig();
        config.setSceneMap(Collections.unmodifiableMap(sceneMap));
        config.setFlowMap(Collections.unmodifiableMap(flowMap));
        config.setNodeMap(Collections.unmodifiableMap(nodeMap));
        return config;
    }

    private Map<String, NodeDefinition> assembleNodes(List<FlowNode> nodeEntities){
        Map<String, NodeDefinition> nodeMap = new LinkedHashMap<String, NodeDefinition>();
        if(nodeEntities == null){
            return nodeMap;
        }
        for(FlowNode e: nodeEntities){
            NodeDefinition def = new NodeDefinition();
            def.setNodeCode(e.getNodeCode());
            def.setNodeName(e.getNodeName());
            def.setNodeType(e.getNodeType());
            def.setHandlerBeanName(e.getHandlerBeanName());
            def.setNodeConfig(e.getNodeConfig());
            def.setNodeDesc(e.getNodeDesc());
            nodeMap.put(e.getNodeCode(), def);
        }
        return nodeMap;
    }

    private Map<String, FlowDefinition> assembleFlows(List<FlowInfo> flowEntities, List<FlowNodeRelation> flowNodeRels){
        Map<String, List<FlowNodeRelation>> flowToRels = new HashMap<>();
        if(flowNodeRels != null){
            for(FlowNodeRelation rel : flowNodeRels){
                flowToRels.computeIfAbsent(rel.getFlowCode(), k -> new ArrayList<>()).add(rel);
            }
        }
        Map<String, List<String>> flowToNodes = new HashMap<>();
        for(Map.Entry<String, List<FlowNodeRelation>> entry : flowToRels.entrySet()){
            List<FlowNodeRelation> rels = entry.getValue();
            rels.sort(Comparator.comparingInt(rel -> rel.getSortNo() == null ? 0 : rel.getSortNo()));
            flowToNodes.put(entry.getKey(), rels.stream()
                    .map(FlowNodeRelation::getNodeCode)
                    .collect(Collectors.toList()));
        }

        Map<String, FlowDefinition> flowMap = new LinkedHashMap<>();
        if(flowEntities == null){
            return flowMap;
        }
        for(FlowInfo e: flowEntities){
            FlowDefinition def = new FlowDefinition();
            def.setFlowCode(e.getFlowCode());
            def.setFlowName(e.getFlowName());
            def.setFlowType(e.getFlowType());
            def.setFlowDesc(e.getSceneDesc());
            def.setNodeCodes(flowToNodes.getOrDefault(e.getFlowCode(), new ArrayList<>()));
            flowMap.put(e.getFlowCode(), def);
        }
        return flowMap;
    }

    private Map<String, SceneDefinition> assembleScenes(List<SceneInfo> sceneEntities, List<SceneFlowRelation> sceneFlowRels){
        Map<String, List<SceneFlowDefinition>> sceneToFlows = new HashMap<>();
        if(sceneFlowRels != null){
            for(SceneFlowRelation rel : sceneFlowRels){
                List<ConditionBranchDefinition> branches = parseConditionConfig(rel.getConditional(),
                        "scene_flow_rel[" + rel.getSceneCode() + "/" + rel.getFlowCode() + "].condition_config");
                SceneFlowDefinition sfd = new SceneFlowDefinition();
                sfd.setSceneCode(rel.getSceneCode());
                sfd.setFlowCode(rel.getFlowCode());
                sfd.setSortNo(rel.getSortNo() == null ? 0 : rel.getSortNo());
                sfd.setConditionConfig(rel.getConditional());
                sfd.setConditionBranches(branches);
                sceneToFlows.computeIfAbsent(rel.getSceneCode(), k -> new ArrayList<>()).add(sfd);
            }
        }

        sceneToFlows.values().forEach(list ->
                list.sort(Comparator.comparingInt(rel -> rel.getSortNo() == null ? 0 : rel.getSortNo())));

        Map<String, SceneDefinition> sceneMap = new LinkedHashMap<>();
        if(sceneEntities == null){
            return sceneMap;
        }
        for(SceneInfo e: sceneEntities){
            SceneDefinition def = new SceneDefinition();
            def.setSceneCode(e.getSceneCode());
            def.setSceneName(e.getSceneName());
            def.setSceneDesc(e.getSceneDesc());
            def.setSceneFlows(sceneToFlows.getOrDefault(e.getSceneCode(), new ArrayList<>()));
            sceneMap.put(e.getSceneCode(), def);
        }
        return sceneMap;
    }

    public List<ConditionBranchDefinition> parseConditionConfig(String json, String fieldDesc){
        if(json == null || json.trim().isEmpty()){
            return Collections.emptyList();
        }
        ArrayNode array;
        try {
            array = objectMapper.readValue(json, ArrayNode.class);
        } catch (Exception e) {
            log.error("解析条件配置失败，字段: {}, 值: {}, 错误: {}", fieldDesc, json, e.getMessage());
            return Collections.emptyList();
        }
        if(array == null){
            return Collections.emptyList();
        }
        List<ConditionBranchDefinition> branches = new ArrayList<>(array.size());
        for(int i = 0; i< array.size(); i++){
            JsonNode obj = array.get(i);
            try {
                String condition = obj.get("condition").asText();
                String subFlowCode = obj.get("subFlowCode").asText();
                Integer sortNo = obj.get("sortNo") != null ? Integer.valueOf(String.valueOf(obj.get("sortNo"))) : 0;
                ConditionBranchDefinition def = new ConditionBranchDefinition();
                def.setCondition(condition);
                def.setSubFlowCode(subFlowCode);
                def.setSortNo(sortNo);
                def.setCompiledExpression(spelConditionEvaluator.parse(condition));
                branches.add(def);
            } catch (Exception e) {
                log.error("解析条件分支失败，索引: {}, 字段: {}, 数据: {}, 错误: {}",
                        i, fieldDesc, obj, e.getMessage());
            }
        }
        branches.sort(Comparator.comparingInt(b -> b.getSortNo() == null ? 0 : b.getSortNo()));
        return branches;
    }

    private Map<String, Object> parseObject(String json){
        try {
            if(StringUtils.isNotBlank(json)){
                return objectMapper.readValue(json, new TypeReference<LinkedHashMap<String, Object>>(){});
            }
            return null;
        } catch (Exception e) {
            throw new IllegalArgumentException("invalid json object");
        }
    }

}