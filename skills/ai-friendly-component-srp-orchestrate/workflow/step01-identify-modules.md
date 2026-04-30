# Step 01: 识别所有模块

## 执行者
SubAgent（调用 `ai-friendly-module-identifier` skill）

## 输入
- `project_path`: 项目根目录绝对路径

## 输出
- `state/modules.json`: 模块清单（从 `.claude/skills/ai-friendly-module-identifier/output/modules.json` 复制而来）

## 执行说明

1. **触发 SubAgent**：使用 Agent tool 调用 `ai-friendly-module-identifier`
   - `subagent_type`: "general-purpose"
   - `prompt`: "识别项目 {project_path} 的所有模块，scan_depth=shallow，output_path=.claude/skills/ai-friendly-component-srp-orchestrate/state/modules.json"

2. **等待完成**：SubAgent 会将结果直接写入 `state/modules.json`

3. **提取模块列表**：从 `state/modules.json` 的 `modules` 字段中提取所有模块的 `path` 和 `name`，供 step02 使用

## 输出格式验证

`state/modules.json` 必须包含：
- `modules` 对象：按架构层分类（核心业务域、数据持久层、接口适配层、基础设施层、公共工具层）
- 每个模块包含：`path`（相对路径）、`name`（目录名）、`depth`、`files`（文件列表）

## SubAgent 返回值

SubAgent 应返回极简 JSON：
```json
{
  "ok": true,
  "total_modules": 20,
  "state_path": "state/modules.json"
}
```

## 验证检查点

- [ ] `state/modules.json` 文件存在
- [ ] JSON 包含 `modules` 字段（对象类型）
- [ ] `modules` 至少包含一个架构层分类
- [ ] 每个模块包含必需字段：`path`、`name`、`files`
- [ ] `statistics.total_modules` > 0