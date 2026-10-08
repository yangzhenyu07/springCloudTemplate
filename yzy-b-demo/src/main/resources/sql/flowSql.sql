
INSERT INTO scene_info
( SCENE_CODE, SCENE_NAME, SCENE_DESC, CREATE_TIME, UPDATE_TIME)
VALUES( 'yzv_test', '流程编排测试', '','2026-05-28 16:02:57', '2026-05-28 16:02:57');

INSERT INTO scene_flow_relation
( SCENE_CODE, FLOW_CODE, SORT_NO, CONDITIONAL, CREATE_TIME, UPDATE_TIME)
VALUES( 'yzv_test', 'yes_t_test', 1, '','2026-06-24 12:35:39.565', '2026-06-24 12:35:39.565');

INSERT INTO scene_flow_relation
( SCENE_CODE, FLOW_CODE, SORT_NO, CONDITIONAL, CREATE_TIME, UPDATE_TIME)
VALUES( 'yzv_test', 'no_t_test', 2, '[  { "condition": "#context.conditionCheck.versionId.contains(\'v1\')  and #context.conditionCheck.id == \'1\'",
"subFlowCode": "no_t_test_v1",  "sortNo": 1  },
{ "condition": "#context.conditionCheck.versionId.contains(\'v2\')  and #context.conditionCheck.id == \'2\'",
"subFlowCode": "no_t_test_v2",  "sortNo": 2  } ]', '2026-06-16 19:19:37.772', '2026-06-16 19:19:41.974');


INSERT INTO flow_info
( FLOW_CODE, FLOW_NAME, FLOW_TYPE, SCENE_DESC, CREATE_TIME, UPDATE_TIME)
VALUES( 'no_t_test', '无事务流程编排测试(条件)', 'CONDITION', '无事务流程编排测试(条件)', '2026-06-12 19:03:51.406', '2026-06-12 19:03:54.966');

INSERT INTO flow_info
( FLOW_CODE, FLOW_NAME, FLOW_TYPE, SCENE_DESC, CREATE_TIME, UPDATE_TIME)
VALUES( 'no_t_test_v1', '无事务流程编排测试-版本1', 'SERIAL', '无事务流程编排测试-版本1', '2026-06-03 17:22:15.949', '2026-06-03 17:22:19.933');

INSERT INTO flow_info
( FLOW_CODE, FLOW_NAME, FLOW_TYPE, SCENE_DESC, CREATE_TIME, UPDATE_TIME)
VALUES( 'no_t_test_v2', '无事务流程编排测试-版本2', 'SERIAL', '无事务流程编排测试-版本2', '2026-06-03 17:22:15.949', '2026-06-03 17:22:19.933');

INSERT INTO flow_info
( FLOW_CODE, FLOW_NAME, FLOW_TYPE, SCENE_DESC, CREATE_TIME, UPDATE_TIME)
VALUES( 'yes_t_test', '事务流程编排测试', 'SERIAL', '事务流程编排测试', '2026-06-03 17:22:15.949', '2026-06-03 17:22:19.933');

INSERT INTO flow_node_relation ( FLOW_CODE, NODE_CODE, SORT_NO, CREATE_TIME, UPDATE_TIME)
VALUES( 'yes_t_test', 'testTransFeignHandler', 1, '2026-06-03 17:25:09.488', '2026-06-03 17:25:15.292');

INSERT INTO flow_node_relation ( FLOW_CODE, NODE_CODE, SORT_NO, CREATE_TIME, UPDATE_TIME)
VALUES( 'yes_t_test', 'testTransBusiHandler', 2, '2026-06-03 17:25:09.488', '2026-06-03 17:26:04.022');

INSERT INTO flow_node_relation ( FLOW_CODE, NODE_CODE, SORT_NO, CREATE_TIME, UPDATE_TIME)
VALUES( 'no_t_test_v1', 'testFeignHandler', 1, '2026-06-03 17:25:09.488', '2026-06-03 17:25:15.292');

INSERT INTO flow_node_relation ( FLOW_CODE, NODE_CODE, SORT_NO, CREATE_TIME, UPDATE_TIME)
VALUES( 'no_t_test_v1', 'testV1BusiHandler', 2, '2026-06-03 17:25:58.984', '2026-06-03 17:26:04.022');

INSERT INTO flow_node_relation ( FLOW_CODE, NODE_CODE, SORT_NO, CREATE_TIME, UPDATE_TIME)
VALUES( 'no_t_test_v2', 'testFeignHandler', 1, '2026-06-03 17:25:09.488', '2026-06-03 17:25:15.292');

INSERT INTO flow_node_relation ( FLOW_CODE, NODE_CODE, SORT_NO, CREATE_TIME, UPDATE_TIME)
VALUES( 'no_t_test_v2', 'testV2BusiHandler', 2, '2026-06-03 17:25:58.984', '2026-06-03 17:26:04.022');



INSERT INTO flow_node ( NODE_CODE, NODE_NAME, NODE_DESC, NODE_TYPE, HANDLER_BEAN_NAME, NODE_CONFIG, CREATE_TIME, UPDATE_TIME)
VALUES( 'testV1BusiHandler', 'testV1BusiHandler v1 无事务版本测试', 'BusiHandler v1 版本测试', 'LOCAL', 'testV1BusiHandler', '{}','2026-06-03 17:31:22.792', '2026-06-03 17:31:27.845');

INSERT INTO flow_node ( NODE_CODE, NODE_NAME, NODE_DESC, NODE_TYPE, HANDLER_BEAN_NAME, NODE_CONFIG, CREATE_TIME, UPDATE_TIME)
VALUES( 'testV2BusiHandler', 'testV1BusiHandler v2 无事务版本测试', 'BusiHandler v2 版本测试', 'LOCAL', 'testV2BusiHandler', '{}','2026-06-03 17:31:22.792', '2026-06-03 17:31:27.845');

INSERT INTO flow_node ( NODE_CODE, NODE_NAME, NODE_DESC, NODE_TYPE, HANDLER_BEAN_NAME, NODE_CONFIG, CREATE_TIME, UPDATE_TIME)
VALUES( 'testFeignHandler', 'testFeignHandler feign 无事务调用测试', 'testFeignHandler feign 调用测试', 'FEIGN', 'testFeignHandler', '{"serverId":"yzy-demo","apiPatch":"/api/sdk/apiTest","method":"POST"},"method":"POST"}','2026-06-24 17:33:27.960','2026-06-24 17:33:27.960');


INSERT INTO flow_node ( NODE_CODE, NODE_NAME, NODE_DESC, NODE_TYPE, HANDLER_BEAN_NAME, NODE_CONFIG, CREATE_TIME, UPDATE_TIME)
VALUES( 'testTransBusiHandler', 'testTransBusiHandler 事务版本测试', 'testTransBusiHandler 事务版本测试', 'LOCAL', 'testTransBusiHandler', '{}','2026-06-03 17:31:22.792',
'2026-06-03 17:31:27.845');

INSERT INTO flow_node ( NODE_CODE, NODE_NAME, NODE_DESC, NODE_TYPE, HANDLER_BEAN_NAME, NODE_CONFIG, CREATE_TIME, UPDATE_TIME)
VALUES( 'testTransFeignHandler', 'testTransFeignHandler feign 无事务调用测试', 'testTransFeignHandler feign 调用测试', 'FEIGN', 'testTransFeignHandler', '{"serverId":"yzy-demo","apiPatch":"/api/sdk/apiTest","method":"POST"}','2026-06-24 17:33:27.960','2026-06-24 17:33:27.960');