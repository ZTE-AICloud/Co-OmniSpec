# Step 02: 并发 SRP 分析

## 执行者
Main Agent 协调，每批 5 个 SubAgent 并发

## 输入
- `state/modules.json`: step01 输出的模块清单

## 输出
- `state/step02-analyze-modules/{module_name}.json`: 每个模块的 SRP 分析结果（一个模块一个文件）

## 执行说明

### 1. 读取模块清单
```python
# 从 state/modules.json 提取所有模块
modules = []
for category, module_list in data["modules"].items():
    for mod in module_list:
        modules.append({
            "name": mod["name"],
            "path": mod["path"],
            "category": category
        })
```

### 2. 分批处理
将模块列表分批，每批最多 5 个模块。

### 3. 并发执行（关键）

**对每一批，在同一条消息中并发发起 5 个 Agent tool call**：

```
批次 1（5个模块）：
┌─────────────────────────────────────────────────────────────────┐
│ Agent tool call 1: ai-friendly-arch-guard-module-single-responsibility │
│   - module_path: "pdmcli/commands"                              │
│   - output_path: "state/step02-analyze-modules/commands.json"  │
├─────────────────────────────────────────────────────────────────┤
│ Agent tool call 2: ai-friendly-arch-guard-module-single-responsibility │
│   - module_path: "pdmcli/tools"                                 │
│   - output_path: "state/step02-analyze-modules/tools.json"     │
├─────────────────────────────────────────────────────────────────┤
│ ... (最多5个)                                                    │
└─────────────────────────────────────────────────────────────────┘
等待本批全部完成 → 再发起批次 2
```

**调用参数**：
- `subagent_type`: "general-purpose"
- `prompt`: "分析模块 {module_path} 的单一职责原则，output_path={output_path}"

**关键约束**：
- 必须通过 `output_path` 参数指定每个模块的输出文件路径，避免并发写入冲突
- 每个 SubAgent 只写自己的文件：`state/step02-analyze-modules/{module_name}.json`

### 4. SubAgent 返回值

每个 SubAgent 返回极简 JSON：
```json
{
  "ok": true,
  "module": "commands",
  "output_path": "state/step02-analyze-modules/commands.json"
}
```

### 5. 验证

所有批次完成后，验证：
- `state/step02-analyze-modules/` 目录下的 JSON 文件数量 == 模块总数
- 每个文件包含 `metric_result.total_score`、`metric_result.confidence`、`violation_info.total_count`

## 并发策略总结

| 项目 | 策略 |
|------|------|
| 调用的 skill | `ai-friendly-arch-guard-module-single-responsibility` |
| 并发粒度 | 每批 5 个 SubAgent |
| 并发方式 | 在同一条消息中发起多个 Agent tool call |
| 批次控制 | 等待本批全部完成后，再发起下一批 |
| 输出隔离 | 通过 `output_path` 参数指定唯一文件路径 |

## 验证检查点

- [ ] `state/step02-analyze-modules/` 目录存在
- [ ] 目录下 JSON 文件数量 == `state/modules.json` 中的模块总数
- [ ] 每个 JSON 文件包含必需字段：`metric_result.total_score`、`confidence`、`violation_info.total_count`
- [ ] 所有 `total_score` 值在 0-100 范围内
- [ ] 无 `processing_summary.json` 等非模块文件混入