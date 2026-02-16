# 接口清单

**生成时间**: {{generated_at}}
**接口总数**: {{total_count}}

## 接口类型统计

{{#type_statistics}}
- **{{type_name}}接口**: {{count}} 个
{{/type_statistics}}

## 业务领域统计

{{#domain_statistics}}
- **{{domain_name}}**: {{count}} 个
{{/domain_statistics}}

## 接口列表

| 接口ID | 业务名称 | 接口类型 | 业务领域 | 接口文件 |
|--------|----------|----------|----------|----------|
{{#interfaces}}
| {{interface_id}} | {{business_name}} | {{interface_type}} | {{business_domain}} | [{{interface_doc_title}}](./{{interface_doc_file}}) |
{{/interfaces}}

