# 场景清单

**生成时间**: {{generated_at}}
**场景总数**: {{total_count}}

## 业务领域统计

{{#domain_statistics}}
- **{{domain_name}}**: {{count}} 个
{{/domain_statistics}}

## 场景类型统计

{{#type_statistics}}
- **{{type_name}}场景**: {{count}} 个
{{/type_statistics}}

## 场景列表

| 场景ID | 场景名称 | 业务领域 | 场景类型 | 优先级 | 来源入口 | 场景文件 |
|--------|----------|----------|----------|--------|----------|----------|
{{#scenarios}}
| {{scenario_id}} | {{scenario_name}} | {{business_domain}} | {{scenario_type}} | {{priority}} | {{origin_hint}} | [{{scenario_link_text}}](./{{scenario_doc_file}}) |
{{/scenarios}}
