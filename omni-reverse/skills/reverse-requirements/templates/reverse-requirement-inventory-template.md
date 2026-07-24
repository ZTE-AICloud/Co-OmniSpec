# 需求清单

**生成时间**: {{generated_at}}
**需求总数**: {{total_count}}

## 需求类型统计

{{#type_statistics}}
- **{{type_name}}**: {{count}} 个
{{/type_statistics}}

## 来源场景统计

{{#source_scenario_statistics}}
- **{{scenario_id}}**: {{count}} 条需求
{{/source_scenario_statistics}}

## 需求列表

| 需求ID | 需求名称 | 类型 | 来源场景 | 需求文件 |
|--------|----------|------|----------|----------|
{{#requirements}}
| {{requirement_id}} | {{requirement_name}} | {{requirement_type}} | {{source_scenarios}} | [{{requirement_link_text}}](./{{requirement_doc_file}}) |
{{/requirements}}
