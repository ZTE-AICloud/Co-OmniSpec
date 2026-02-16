# 接口扫描配置确认（已弃用）

⚠️ 注意：此模板已被新的分步向导模式替代，请使用以下新模板：
- 接口类型选择：interface-type-selection-template.md
- 约束规则配置：constraint-configuration-template.md
- 最终确认：final-confirmation-template.md

请确认以下接口扫描配置：

## 1. 接口类型选择

请选择要扫描的接口类型（可多选）：

- [ ] RESTful API
- [ ] 消息类接口
- [ ] 模块间接口
- [ ] 命令行接口
- [ ] RPC 接口
- [ ] 函数接口
- [ ] 其他类型接口

## 2. 约束规则配置（可选）

您可以配置以下约束规则来精确控制扫描范围：

### 文件路径过滤
请输入要包含的文件路径模式（如src/api/*）：
```
{{include_paths}}
```

### 函数名模式
请输入要匹配的函数名模式（如get_*、post_*）：
```
{{function_patterns}}
```

### 排除模式
请输入要排除的文件或函数模式：
```
{{exclude_patterns}}
```

## 3. 扫描范围和预估工作量

基于架构识别结果，关键模块包括：
{{key_modules}}

预估扫描文件总数：{{estimated_files}} 个

预计处理方式：{{processing_mode}}

## 4. 确认操作

请确认以上配置是否正确：

- 输入 `y` 或 `yes` 确认配置并开始扫描
- 输入 `n` 或 `no` 重新配置
- 输入具体的修改建议

确认 [Y/n]: