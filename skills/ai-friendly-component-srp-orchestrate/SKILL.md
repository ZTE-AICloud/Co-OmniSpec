---
name: ai-friendly-component-srp-orchestrate
version: v1.2
description: 以代码库（组件库）为粒度，编排多模块业务职责一致性分析的完整流水线。支持全量和增量两种模式。全量模式分析所有模块；增量模式仅分析 git diff 涉及的变更模块，可用于 CI 门禁。先识别模块，再并发调用 ai-friendly-arch-guard-module-single-responsibility 分析各模块SRP，最后聚合生成整体报告。当需要对代码库进行模块单一职责原则合规性检查或 CI 门禁时使用此技能。
---

# component-srp-orchestrate

以代码库为粒度，完成模块一致性检测。支持**全量模式**和**增量模式**。

## 输入要求

### 全量模式
- **project_path**：待分析的项目根目录（绝对路径）

### 增量模式（额外参数）
- **base_commit**：对比基线（如 `origin/master`）
- **target_commit**：目标提交（默认 `HEAD`）
- **enable_gate**：是否启用门禁判定（默认 `false`）
- **detect_untracked**：是否检测 untracked 新增文件（默认 `true`，自动检测 `git ls-files --others`）
- **detect_staged**：是否检测 staged 变更（默认 `false`）

## 工作流

### 全量模式

| Step | 职责　　　　　　　　　　 | 执行者　　　　　　　　　　　　　　　　　　　　　　　　　　　　　　　　　　　　 | 文档　　　　　　　　　　　　　　　　　　　　　 | 输入　　　　　　　　　　　　　　　　| 输出　　　　　　　　　　　　　　　　|
| ------| --------------------------| --------------------------------------------------------------------------------| ------------------------------------------------| -------------------------------------| -------------------------------------|
| 01   | 识别所有模块　　　　　　 | SubAgent → ai-friendly-module-identifier　　　　　　　　　　　　　　　　　　　 | [step01](workflow/step01-identify-modules.md)　| project_path　　　　　　　　　　　　| state/modules.json　　　　　　　　　|
| 02   | 并发 SRP 分析（每批5个） | Main Agent → 多 SubAgent → ai-friendly-arch-guard-module-single-responsibility | [step02](workflow/step02-analyze-modules.md)　 | state/modules.json　　　　　　　　　| state/step02-analyze-modules/*.json |
| 03   | 聚合汇总　　　　　　　　 | 脚本 scripts/aggregate.py　　　　　　　　　　　　　　　　　　　　　　　　　　　| [step03](workflow/step03-aggregate-results.md) | state/step02-analyze-modules/*.json | output/summary.json　　　　　　　　 |

### 增量模式

| Step | 职责 | 执行者 | 文档 | 输入 | 输出 |
|------|------|--------|------|------|------|
| 01 | 识别所有模块 | SubAgent → ai-friendly-module-identifier | [step01](workflow/step01-identify-modules.md) | project_path | state/modules.json |
| 02 | 识别变更模块（含 Orphan 文件追踪） | 脚本 scripts/identify-changed-modules.sh | [step02](workflow/step00.5-identify-changed-modules.md) | state/modules.json + base_commit + target_commit | state/changed-modules.json（含 orphan_files 字段） |
| 03 | 并发 SRP 分析（每批5个） | Main Agent → 多 SubAgent → ai-friendly-arch-guard-module-single-responsibility | [step03](workflow/step02-analyze-modules.md) | state/changed-modules.json | state/step02-analyze-modules/*.json |
| 04 | 聚合汇总 | 脚本 scripts/aggregate.py | [step04](workflow/step03-aggregate-results.md) | state/step02-analyze-modules/*.json + state/changed-modules.json | output/srp/summary.json |
| 05 | 门禁判定（可选） | 脚本 scripts/gate-check.py | - | output/srp/summary.json + .gate-config.json | output/gate-result.json |

## 执行原则

- **状态隔离**：所有中间产物存入 `state/` 目录；各 SubAgent 只写自己负责的文件，返回极简 JSON
- **并发控制**：step02 每批最多 5 个 SubAgent，在**同一条消息**中并发发起，等待本批全部完成后再发起下一批
- **脚本优先**：统计汇总（step03）由脚本执行，不消耗 AI token

## 目录结构

```
state/
  modules.json                    # step01 产物：全量模块清单
  changed-modules.json            # step0.5 产物：变更模块清单（增量模式）
  step02-analyze-modules/         # step02 产物：每模块 SRP 分析
    {module_name}.json
output/
  srp/
    summary.json                  # step03 产物：最终汇总报告（aia_metric_fact 格式）
  gate-result.json                # step04 产物：门禁判定结果（可选）
.gate-config.json                 # 门禁阈值配置（可选）
```

## 最终输出

### `output/summary.json`（aia_metric_fact 格式）

- `identity_info.skill_id`：`"ai-friendly-component-srp-orchestrate"`
- `identity_info.arch_dimension`：`"结构可导航性"`
- `execution_ctx.skill_version`：技能版本号
- `execution_ctx.scan_mode`：扫描模式（`"full"` 或 `"increment"`）
- `execution_ctx.execute_status`：执行状态（`"success"` 或 `"failed"`）
- `execution_ctx.start_time` / `end_time` / `duration_ms`：执行时间信息
- `core_metrics.total_score`：综合得分（0~100）
- `core_metrics.confidence_score`：置信度得分（0~1）
- `core_metrics.total_violation_count`：总违规数
- `core_metrics.p0_violation_count`：P0 级别违规数
- `core_metrics.p1_violation_count`：P1 级别违规数
- `evaluation_details.score_detail`：各子维度得分明细（目录单一性、模块内聚、文件单一性）
- `evaluation_details.score_distribution`：得分分档分布（excellent/good/medium/poor）
- `violation_records.level_summary`：违规级别汇总（P0/P1）
- `violation_records.violation_infos`：违规详情列表（最多 50 条）
- `scan_statistics.total_units.modules`：扫描模块总数
- `scan_statistics.violation_units.modules`：存在违规的模块数
- `scan_statistics.valid_units.modules`：无违规模块数
- `modules`：每个模块的摘要（扩展字段，非 aia_metric_fact 标准字段）

#### `state/changed-modules.json`（增量模式输出，step0.5 产物）

- `mode`：扫描模式（`"incremental"`）
- `base_commit` / `target_commit`：对比区间
- `modules`：按架构层分类的变更模块列表，每个模块含 `changed_files`
- `orphan_files`：未匹配到任何模块的变更文件（新增模块、删除文件残留）
- `statistics.orphan_files_count`：`orphan_files` 数量

### `output/gate-result.json`（启用门禁时）
- `gate_passed`：是否通过门禁（`true`/`false`）
- `thresholds`：使用的阈值配置
- `actual_values`：实际度量值
- `violations`：未通过的检查项

## 使用示例

### 全量模式
```
调用技能 ai-friendly-component-srp-orchestrate
参数：
  project_path: /path/to/repo
```

### 增量模式（CI 门禁）
```
调用技能 ai-friendly-component-srp-orchestrate
参数：
  project_path: /path/to/repo
  base_commit: origin/master
  enable_gate: true

# 跳过 untracked 新增文件，仅分析已 commit 的 diff
参数追加：detect_untracked: false

# 同时检测已 staged 但未 commit 的变更
参数追加：detect_staged: true
```

## 参考文档

- [DESIGN.md](DESIGN.md) — 设计背景与扩展点
- [CHANGELOG.md](CHANGELOG.md) — 版本变更历史
- [CHANGES-DETAIL.md](CHANGES-DETAIL.md) — 字段迁移映射详情（aia_metric_fact 迁移记录）
- [README-INCREMENTAL.md](README-INCREMENTAL.md) — 增量模式使用指南

## 门禁配置

编辑 `.gate-config.json` 自定义阈值：
```json
{
  "min_avg_score": 0.7,
  "max_avg_violation_count": 5,
  "min_confidence": 0.6
}
```