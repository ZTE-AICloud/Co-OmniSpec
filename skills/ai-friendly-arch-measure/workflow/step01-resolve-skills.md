# Step 01: 解析待执行 Skill 列表

## 职责

根据执行参数，从 `config/metric-registry.json` 中解析出本次需要执行的 skill 列表，输出 `state/resolved-skills.json`。

## 输入

- `config/metric-registry.json`：度量 skill 注册表
- 执行参数（`--all` / `--dimension <名称>` / `--skills <id,...>` / 无参数）

## 输出

- `state/resolved-skills.json`：已解析的 skill 列表

## 执行流程

1. 运行 `scripts/resolve-skills.py`，传入注册表路径和执行参数
2. 等待脚本完成
3. 验证 `state/resolved-skills.json` 已生成且可解析

## 脚本调用

```bash
python scripts/resolve-skills.py \
  --registry config/metric-registry.json \
  --output state/resolved-skills.json \
  [--all | --dimension <维度名> | --skills <skill_id,...>]
```

### 执行模式说明

| 参数 | 模式 | 行为 |
|------|------|------|
| 无参数 | `default` | 执行 `tags` 包含 `"default"` 且 `enabled: true` 的 skill |
| `--all` | `all` | 执行所有 `enabled: true` 的 skill |
| `--dimension 职责维度` | `dimension` | 执行指定维度下所有 `enabled: true` 的 skill |
| `--skills ai-friendly-component-srp-orchestrate` | `skills` | 强制执行指定 skill，忽�� `enabled` 状态 |

## 产物格式

```json
{
  "execute_mode": "default|all|dimension|skills",
  "resolved": [
    {
      "skill_id": "ai-friendly-component-srp-orchestrate",
      "display_name": "模块单一职责",
      "dimension": "结构可导航性",
      "output_path_hint": "output/srp/summary.json"
    }
  ],
  "skipped": [
    {
      "skill_id": "ai-friendly-metric-token-count",
      "reason": "enabled: false"
    }
  ]
}
```

## 验证检查点

- [ ] `state/resolved-skills.json` 文件存在
- [ ] 文件可解析为合法 JSON
- [ ] `resolved` 列表中的 `skill_id` 均在注册表中存在
- [ ] `--dimension` 传入非法值时脚本以非零退出码返回，并输出清晰错误信息
- [ ] `resolved` + `skipped` 中的 skill 总数 == 注册表中 `metrics` 总数（`--skills` 模式除外）
