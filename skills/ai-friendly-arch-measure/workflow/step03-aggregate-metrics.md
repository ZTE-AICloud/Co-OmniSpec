# Step 03: 聚合度量结果

## 职责

读取所有已执行 skill 的输出文件，聚合生成符合 `aia_component_summary` 格式的总报告。

## 输入

- `state/resolved-skills.json`：skill 列表及 `output_path_hint`
- 各 skill 的输出文件（如 `output/srp/summary.json`）

## 输出

- `output/arch-measure-report.json`：最终聚合报告（`aia_component_summary` 格式）

## 执行流程

1. 运行 `scripts/aggregate-metrics.py`，传入 `resolved-skills.json` 和输出路径
2. 等待脚本完成
3. 验证 `output/arch-measure-report.json` 已生成且可解析

## 脚本调用

```bash
python scripts/aggregate-metrics.py \
  --resolved-skills state/resolved-skills.json \
  --output-dir output \
  --output output/arch-measure-report.json \
  --project-path <project_path> \
  [--project-id <id>] \
  [--component-id <id>] \
  [--component-name <name>]
```

## 产物格式（双 key 顶层结构）

```json
{
  "aia_metric_fact": [
    {
      "identity_info": { "skill_id": "...", "arch_dimension": "..." },
      "execution_ctx": { "skill_version": "...", "scan_mode": "...", "execute_status": "success|failed|skipped", ... },
      "core_metrics": { "total_score": 85, "confidence_score": 0.8, "total_violation_count": 5, "p0_violation_count": 0, "p1_violation_count": 5 },
      "evaluation_details": { ... },
      "violation_records": { ... },
      "scan_statistics": { ... }
    }
  ],
  "aia_component_summary": {
    "identity_info": { ... },
    "scan_result": {
      "total_skill_count": 1,
      "total_score_avg": 85,
      "total_violations": 5,
      "p0_total": 0,
      "p1_total": 5,
      "p2_total": 0,
      "scan_time": "ISO8601",
      "statistic_info": { "modules": 20 }
    },
    "dimension_data": {
      "arch_dimension_list": ["结构可导航性"],
      "dimension_summary": {
        "结构可导航性": { "score": 85, "status": "success", "skill_count": 1 }
      }
    },
    "relation_mapping": {
      "skill_id_list": ["ai-friendly-component-srp-orchestrate"],
      "dimension_metric_mapping": { "结构可导航性": ["ai-friendly-component-srp-orchestrate"] }
    },
    "_meta": {
      "execute_status": "success|partial|failed",
      "execute_mode": "default|all|dimension|skills",
      "overall_grade": "S|A|B|C|D",
      "skipped_skills": [],
      "failed_skills": []
    }
  }
}
```

**说明**：
- `aia_metric_fact`：list，每个 skill 一项，包含完整详情（violation_records、evaluation_details 等高变更字段均保留）；失败/跳过的 skill 有最小占位 fact（仅含必填字段，execute_status 标记为 `failed`/`skipped`）。
- `aia_component_summary`：汇总表，各字段从 `aia_metric_fact` 列表推导聚合；`_meta` 为本 skill 私有扩展字段。

### 评级映射

| 分数区间 | 等级 |
|---------|------|
| ≥ 90 | S |
| ≥ 75 | A |
| ≥ 60 | B |
| ≥ 40 | C |
| < 40 | D |

## 缓存说明

`output/<skill>/summary.json` 文件可能来自两种来源：
- **本次新执行**：step02 中 `[CACHE MISS]` 或 `[CACHE INVALID]` 触发的新生成文件
- **历史缓存**：step02 中 `[CACHE HIT]` 跳过的已有文件

`aggregate-metrics.py` 无需区分来源，对两种来源的处理方式完全相同：
- 文件存在且可解析 → 正常聚合（`execute_status == "success"` 时计入得分均值）
- 文件不存在或解析失败 → 写入最小占位 fact（`execute_status = "failed"`）

## 聚合规则

- `scan_result.total_score_avg`：仅统计 `execution_ctx.execute_status == "success"` 的 skill 得分均值
- `_meta.execute_status`：`success`（全部成功）/ `partial`（部分成功）/ `failed`（全部失败）
- 各 skill 失败时，该 skill 不计入得分均值，列入 `_meta.failed_skills`

## 验证检查点

- [ ] `output/arch-measure-report.json` 文件存在
- [ ] 文件可解析为合法 JSON
- [ ] `dimension_data.arch_dimension_list` 中的维度集合与 `resolved-skills.json` 中的维度一致
- [ ] `scan_result.total_score_avg` 仅计算 `execute_status: "success"` 的 skill
- [ ] `_meta.skipped_skills` 与 `resolved-skills.json` 中的 `skipped` 列表对应
