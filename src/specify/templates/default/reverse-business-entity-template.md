# 业务实体文档：{{entity_name}}

## 基本信息
- **实体ID**: {{entity_id}}
- **实体名称**: {{entity_name}}
- **业务含义**: {{business_meaning}}
- **所属领域**: {{domain}}
- **所属子域**: {{subdomain}}
- **限界上下文**: {{bounded_context}}

## 业务概念
{{#business_concepts}}
- **{{name}}**：{{description}}
  - 所属领域：{{domain}}
  - 业务规则：
  {{#business_rules}}
    - {{.}}
  {{/business_rules}}
{{/business_concepts}}

{{^business_concepts}}
暂未识别出明确的业务概念。
{{/business_concepts}}

## 实体属性
{{#has_attributes}}
| 属性名 | 类型 | 说明 | 是否必需 | 业务规则 |
|--------|------|------|----------|----------|
{{#attributes}}
| {{name}} | {{type}} | {{description}} | {{#required}}是{{/required}}{{^required}}否{{/required}} | {{business_rule}} |
{{/attributes}}
{{/has_attributes}}
{{^has_attributes}}
该实体暂无明确定义的属性。
{{/has_attributes}}

## 实体关系
{{#entity_relationships}}
### {{relationship_type}}
{{#relationships}}
- **{{source_entity}}** {{relationship_description}} **{{target_entity}}**
  - 关系描述：{{description}}
  - 关系基数：{{cardinality}}
  - 关系强度：{{strength}}
  {{#business_meaning}}
  - 业务含义：{{business_meaning}}
  {{/business_meaning}}
{{/relationships}}
{{/entity_relationships}}

{{^entity_relationships}}
暂未识别出明确的实体关系。
{{/entity_relationships}}

## 边界信息
### 技术边界
- **架构层级**: {{technical_layer}}
- **模块**: {{module}}
- **包**: {{package}}
- **访问级别**: {{access_level}}

### 业务边界
- **业务领域**: {{business_domain}}
- **子领域**: {{business_subdomain}}
- **限界上下文**: {{bounded_context}}
- **聚合根**: {{#is_aggregate_root}}是{{/is_aggregate_root}}{{^is_aggregate_root}}否{{/is_aggregate_root}}

### 一致性边界
- **一致性类型**: {{consistency_boundary}}

## 调用链层级
{{#call_chain_levels}}
### 层级 {{level}}
{{#chains}}
- **调用链ID**: {{chain_id}}
  - 入口点：{{entry_point}}
  - 业务流程：{{business_process}}
  - 调用深度：{{call_depth}}
{{/chains}}
{{/call_chain_levels}}

{{^call_chain_levels}}
暂未识别出明确的调用链层级信息。
{{/call_chain_levels}}

## 业务规则
{{#business_rules}}
{{#.}}
- {{.}}
{{/.}}
{{/business_rules}}

{{^business_rules}}
暂未识别出明确的业务规则。
{{/business_rules}}

## 数据流向
{{#data_flows}}
### {{flow_type}}
- **数据源**: {{source}}
- **数据目标**: {{target}}
- **数据类型**: {{data_type}}
{{/data_flows}}

{{^data_flows}}
暂未识别出明确的数据流向。
{{/data_flows}}

## 源码位置
{{#source_locations}}
- {{.}}
{{/source_locations}}

{{^source_locations}}
暂无源码位置信息。
{{/source_locations}}

## 置信度评估
- **语义识别置信度**: {{semantic_confidence}}%
- **边界定义置信度**: {{boundary_confidence}}%
- **层级分析置信度**: {{hierarchy_confidence}}%
- **综合置信度**: {{overall_confidence}}%

## 备注
{{#notes}}
{{.}}
{{/notes}}

{{^notes}}
暂无备注信息。
{{/notes}}