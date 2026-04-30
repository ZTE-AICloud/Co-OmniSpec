# Step 03: 聚合汇总

## 职责

聚合所有模块的 SRP 分析结果，生成符合 `aia_metric_fact` 格式的整体报告。

## 输入

- `state/step02-analyze-modules/*.json`：所有模块的 SRP 分析结果

## 输出

- `output/summary.json`：最终汇总报告（`aia_metric_fact` 格式）

## 执行流程

1. 读取 `state/step02-analyze-modules/` 目录下所有 JSON 文件
2. 解析每个模块的分析结果（跳过 `processing_summary.json`）
3. 计算整体统计数据：
   - `core_metrics.total_score`：所有模块 total_score 的均值
   - `core_metrics.confidence_score`：所有模块 confidence 的均值
   - `core_metrics.total_violation_count`：所有模块违规数之和
   - `core_metrics.p0_violation_count` / `p1_violation_count`：按级别聚合
   - `evaluation_details.score_detail`：各子维度均值
   - `evaluation_details.score_distribution`：得分分档分布
   - `scan_statistics`：总模块数、违规模块数、有效模块数
4. 汇总违规记录（最多保留 Top-50 条）
5. 将结果保存到 `output/summary.json`

## 脚本执行

使用 `scripts/aggregate.py` 脚本执行聚合操作，不消耗 AI token。

```bash
python scripts/aggregate.py \
  --input-dir state/step02-analyze-modules \
  --output output/summary.json \
  --project-path <project_path> \
  --arch-dimension <dimension_name> \
  [--changed-modules-json state/changed-modules.json]
```

> `--arch-dimension` 必须与 `metric-registry.json` 中该 skill 的 `dimension` 字段保持一致（默认 `"结构可导航性"`）。

> 传入 `--changed-modules-json` 后，`summary.json` 的 `execution_ctx` 中将额外包含 `orphan_files_count` 和 `orphan_files` 字段。

## 输出格式示例

```json
{
  "identity_info": {
    "skill_id": "ai-friendly-component-srp-orchestrate",
    "arch_dimension": "结构可导航性"
  },
  "execution_ctx": {
    "skill_version": "v1.0",
    "scan_mode": "full",
    "execute_status": "success",
    "start_time": "ISO8601",
    "end_time": "ISO8601",
    "duration_ms": 1234
  },
  // 以下字段仅在增量模式（传入 --changed-modules-json）时出现：
  // "scan_mode": "increment",
  // "base_commit": "abc123",
  // "target_commit": "HEAD",
  // "orphan_files_count": 0,
  // "orphan_files": [],
  "core_metrics": {
    "total_score": 85,
    "confidence_score": 0.80,
    "total_violation_count": 5,
    "p0_violation_count": 0,
    "p1_violation_count": 5
  },
  "evaluation_details": {
    "score_detail": {
      "directory_single_score": 0.85,
      "module_cohesion_score": 0.80,
      "file_single_score": 0.79
    },
    "score_distribution": { "excellent": 5, "good": 10, "medium": 3, "poor": 2 },
    "confidence_detail": {}
  },
  "violation_records": {
    "level_summary": { "P0": 0, "P1": 5 },
    "violation_infos": [ ... ],
    "exempt_infos": []
  },
  "scan_statistics": {
    "total_units": { "modules": 20 },
    "violation_units": { "modules": 3 },
    "valid_units": { "modules": 17 }
  },
  "modules": [ ... ]
}
```

## 验证检查点

- [ ] `output/summary.json` 文件存在
- [ ] ��层字段包含：`identity_info`、`execution_ctx`、`core_metrics`、`evaluation_details`、`violation_records`、`scan_statistics`、`modules`
- [ ] `scan_statistics.total_units.modules` == step02 处理的模块总数
- [ ] `core_metrics.total_score` 为 0~100 之间的有效数值
- [ ] `modules` 数组长度 == `scan_statistics.total_units.modules`
- [ ] `execution_ctx.execute_status` == `"success"`
- [ ] `evaluation_details.score_distribution` 四档之和 == `scan_statistics.total_units.modules`
