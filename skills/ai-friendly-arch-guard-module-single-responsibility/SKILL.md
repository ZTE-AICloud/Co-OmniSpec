---
name: ai-friendly-arch-guard-module-single-responsibility
version: v1.3
description: 分析模块内部职责是否单一的架构守护技能。当需要检查模块单一职责原则、评估模块内聚性、检测职责混杂问题时使用此技能。
---

# Architecture Guard: Module Single Responsibility Analysis

分析指定模块目录的单一职责原则遵守情况，输出标准化JSON格式报告。

## 执行方式

**必须使用subagent执行此技能**，通过Agent tool调用，subagent_type为"general-purpose"。

## 输入参数

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `module_path` | string | ✅ | 待分析的模块目录路径（绝对路径或相对路径） |
| `scan_mode` | enum | ❌ | 扫描模式：`full`（全量）或 `increment`（增量），默认 `increment` |
| `output_path` | string | ❌ | 分析结果的保存路径。由编排 skill 调用时传入具体路径（如 `state/step02-analyze-modules/{module_name}.json`）；单独调用时默认保存到 `.claude/skills/ai-friendly-arch-guard-module-single-responsibility/output/analysis_result.json` |

## 分析维度

1. **目录单一性** (directory_single_score): 目录结构是否清晰、职责明确
2. **模块内聚性** (module_cohesion_score): 模块内文件间的关联度
3. **文件单一性** (file_single_score): 单个文件职责是否单一

## 输出格式

输出严格遵循 `schema/output-schema.json` 定义的 JSON Schema（完整字段定义见该文件）。

关键字段摘要：

| 字段路径 | 类型 | 说明 |
|---------|------|------|
| `skill_id` | string | 固定值 |
| `rule_version` | string | 当前 `v1.3` |
| `module_path` | string | 模块目录相对路径（供编排层读取） |
| `scan_mode` | enum | `increment` \| `full` |
| `execute_status` | enum | `success` \| `failed` |
| `metric_result.total_score` | number(0-100) | 综合得分 |
| `metric_result.confidence` | number(0-1) | 置信度 |
| `metric_result.score_detail` | object | 三维度得分明细 |
| `metric_result.confidence_detail` | object | 三维度置��度明细 |
| `violation_info.total_count` | integer | 违规总数 |
| `violation_info.level_summary` | object | P0/P1/P2 分级统计 |
| `violation_info.list` | array | 违规详情列表 |
| `violation_info.exempt_list` | array | 豁免列表 |
| `statistic_info` | object | 扫描单元统计（目录/模块/文件） |

## 分析流程

1. **扫描模块结构**: 遍历目录，识别子模块和文件
2. **职责识别**: 分析每个文件/目录的职责
3. **内聚性评估**: 计算模块内部关联度
4. **违规检测**: 识别职责不单一的情况
5. **打分计算**: 综合三个维度计算总分
6. **生成报告**: 输出标准JSON格式

## 违规类型定义

- **过度碎片化拆分**: 职责过度分散，缺乏统一入口
- **职责混杂**: 单个模块/文件承担多个不相关职责
- **层次混乱**: 不同抽象层次的逻辑混在一起

## 豁免场景

- **标准设计模式**: 策略模式、工厂模式等合理拆分
- **框架约定**: 框架要求的特定结构
- **历史遗留**: 标记为待重构的已知问题

## 评分标准

| 等级 | 分数区间 | 含义　　　　　　　　　　　　　|
| ------| ----------| -------------------------------|
| S 级 | 90-100　 | AI 原生友好，可全自动开发　　 |
| A 级 | 75-89　　| AI 友好优良，适合 AI 辅助开发 |
| B 级 | 60-74　　| 基础可用，需适度优化　　　　　|
| C 级 | 40-59　　| AI 开发困难，需重构　　　　　 |
| D 级 | 0-39　　 | 不适合 AI 开发　　　　　　　　|