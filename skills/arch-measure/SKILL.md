---
name: arch-measure
description: 对代码库执行 AI 友好架构全面度量，生成跨维度聚合报告。
---

# /arch-measure

对代码库执行 AI 友好架构全面度量，生成跨维度聚合报告。

## 用法

```
/arch-measure [选项]
```

## 参数

| 参数 | 说明 | 示例 |
|------|------|------|
| `--project-path <路径>` | 待分析项目根目录（绝对路径）。未指定时使用当前工作目录 | `--project-path /path/to/repo` |
| `--all` | 执行所有 `enabled: true` 的度量 skill | `--all` |
| `--dimension <维度名>` | 仅执行指定维度下的度量 skill | `--dimension 职责维度` |
| `--skills <id,...>` | 强制执行指定 skill（逗号分隔，忽略 `enabled` 状态） | `--skills ai-friendly-component-srp-orchestrate` |
| 无参数 | 执行默认集（`tags` 包含 `"default"` 且 `enabled: true`） | `/arch-measure` |

## 参数解析

1. 解析用户输入参数，确认 `project_path`（若未提供，询问用户或使用当前目录）
2. 确认执行模式：
   - `--all` → 全量模式
   - `--dimension <维度名>` → 按维度模式
   - `--skills <id,...>` → 按 skill 模式
   - 无参数 → 默认集模式

## 调用 Skill

解析参数后，调用技能 `ai-friendly-arch-measure`，传入：

```
调用技能 `ai-friendly-arch-measure`
参数：
  project_path: <project_path>
  execute_mode: <default|all|dimension|skills>
  dimension: <维度名>（按维度模式时）
  skill_ids: <id,...>（按 skill 模式时）
  output_path: output/arch-measure-report.json
```

## 报告展示

skill 执行完成后，读取 `output/arch-measure-report.json`，展示以下摘要：

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  AI 友好架构度量报告
  项目：<component_name>  路径：<component_repo>
  执行模式：<execute_mode>  评级：<overall_grade>
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  综合得分：<total_score_avg>
  总违规数：<total_violations>（P0: <p0_total>，P1: <p1_total>）

  维度得分：
    职责维度  <score>  [<status>]
    ...

  跳过 skill：<skipped_skills>（如有）
  失败 skill：<failed_skills>（如有）

  详细报告：output/arch-measure-report.json
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

### 评级说明

| 等级 | 分数区间 | 含义 |
|------|---------|------|
| S | ≥ 0.9 | 优秀 |
| A | ≥ 0.75 | 良好 |
| B | ≥ 0.6 | 一般 |
| C | ≥ 0.4 | 待改进 |
| D | < 0.4 | 严重问题 |

## 示例

```bash
# 默认集（执行已启用的默认 skill）
/arch-measure --project-path /path/to/repo

# 全量执行所有已启用 skill
/arch-measure --project-path /path/to/repo --all

# 仅执行职责维度相关 skill
/arch-measure --project-path /path/to/repo --dimension 职责维度

# 指定 skill 执行
/arch-measure --project-path /path/to/repo --skills ai-friendly-component-srp-orchestrate
```
