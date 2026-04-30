---
name: ai-friendly-arch-measure
version: v1.0
description: AI 友好架构度量元编排 skill，提供统一入口对代码库执行多维度架构质量评估。支持全量、按维度、按 skill、默认集四种执行模式。通过注册表驱动调度已注册的度量 skill，聚合所有结果输出 aia_component_summary 格式报告。当需要对代码库进行 AI 友好架构全面度量、多指标聚合报告或 CI 集成统一度量时使用此技能。
user-invokable: false
---

# ai-friendly-arch-measure

以代码库为粒度，编排所有已注册的 AI 友好架构度量 skill，输出跨维度聚合报告。

## 输入参数

| 参数　　　　　 | 类型　 | 必填 | 说明　　　　　　　　　　　　　　　　　　　　　　　　　　　　|
| ----------------| --------| ------| -------------------------------------------------------------|
| `project_path` | string | ✅　　| 待分析项目根目录（绝对路径）　　　　　　　　　　　　　　　　|
| `execute_mode` | enum　 | ❌　　| 执行模式：`default`（默认）/ `all` / `dimension` / `skills` |
| `dimension`　　| string | ❌　　| 指定维度（`execute_mode=dimension` 时必填）　　　　　　　　 |
| `skill_ids`　　| string | ❌　　| 逗号分隔的 skill ID（`execute_mode=skills` 时必填）　　　　 |
| `output_path`　| string | ❌　　| 最终报告路径（默认 `output/arch-measure-report.json`）　　　|

## 工作流

| Step | 职责　　　　　　　　　| 执行者　　　　　　　　　　　　　　　| 文档　　　　　　　　　　　　　　　　　　　　　 | 输入　　　　　　　　　　　　　　　　　　　　　| 输出　　　　　　　　　　　　　　　|
| ------| -----------------------| -------------------------------------| ------------------------------------------------| -----------------------------------------------| -----------------------------------|
| 01   | 解析待执行 skill 列表 | 脚本 `scripts/resolve-skills.py`　　| [step01](workflow/step01-resolve-skills.md)　　| `config/metric-registry.json` + 执行参数　　　| `state/resolved-skills.json`　　　|
| 02   | 顺序执行各度量 skill　| Main Agent　　　　　　　　　　　　　| [step02](workflow/step02-execute-skills.md)　　| `state/resolved-skills.json`　　　　　　　　　| `output/<skill>/summary.json`　　 |
| 03   | 聚合所有结果　　　　　| 脚本 `scripts/aggregate-metrics.py` | [step03](workflow/step03-aggregate-metrics.md) | `state/resolved-skills.json` + skill 输出文件 | `output/arch-measure-report.json` |

## 编排逻辑

### Step 1：解析 skill 列表

执行 `scripts/resolve-skills.py`，根据执行参数从注册表解析 skill 列表：

```bash
python scripts/resolve-skills.py \
  --registry config/metric-registry.json \
  --output state/resolved-skills.json \
  [--all | --dimension <维度名> | --skills <skill_id,...>]
```

验证 `state/resolved-skills.json` 存在且可解析后，进入 Step 2。

### Step 2：顺序执行各度量 skill

读取 `state/resolved-skills.json` 中的 `resolved` 列表，按顺序调用每个 skill：

```
对 resolved 列表中的每个 skill：
  调用技能 `<skill_id>`
  参数：
    project_path: <project_path>
    output_path: <output_path_hint>
  等待完成，验证输出文件存在
  若失败：记录到失败列表，继续下一个 skill
```

**容错策略**：单个 skill 失败不阻断其余 skill 执行。

### Step 3：聚合结果

执行 `scripts/aggregate-metrics.py`，读取各 skill 输出并生成总报告：

```bash
python scripts/aggregate-metrics.py \
  --resolved-skills state/resolved-skills.json \
  --output-dir output \
  --output output/arch-measure-report.json \
  --project-path <project_path>
```

验证 `output/arch-measure-report.json` 存在且可解析。

## 注册表扩展

新增度量 skill 只需在 `config/metric-registry.json` 追加记录，无需修改本文件：

```json
{
  "skill_id": "ai-friendly-metric-xxx",
  "display_name": "新指标名称",
  "dimension": "目标维度",
  "tags": ["default"],
  "enabled": true,
  "description": "指标说明",
  "output_path_hint": "output/xxx/summary.json"
}
```

## 目录结构

```
state/
  resolved-skills.json          # Step 1 产物
output/
  srp/
    summary.json                # SRP skill 产物（aia_metric_fact 格式）
  arch-measure-report.json      # 最终聚合报告（aia_component_summary 格式）
```

## 输出格式

### 最终报告（`output/arch-measure-report.json`）

采用双 key 顶层结构，字段定义详见 `config/data_model.md`：

| Key | 类型 | 说明 |
|-----|------|------|
| `aia_metric_fact` | list | 各 skill 完整详情（`identity_info`、`execution_ctx`、`core_metrics`、`evaluation_details`、`violation_records`、`scan_statistics`）；失败/跳过的 skill 有最小占位 fact |
| `aia_component_summary` | dict | 组件汇总（`identity_info`、`scan_result`、`dimension_data`、`relation_mapping`、`_meta`）；各字段从 `aia_metric_fact` 列表推导聚合；`_meta` 为本 skill 私有扩展字段 |

## 失败处理

| 场景 | 处理 |
|------|------|
| Step 1 失败（registry 解析错误） | 阻断流程，报告错误 |
| 某 skill 执行失败 | 容错继续，记录 `_meta.failed_skills` |
| 所有 skill 均失败 | `_meta.execute_status: "failed"` |
| Step 3 失败 | 各 skill 原始输出仍存在，可手动查阅 |
