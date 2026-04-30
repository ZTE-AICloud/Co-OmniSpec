---
name: solution-evaluation
description: 方案文档五维质量评测量规，对齐最新 7 章设计文档结构规范和内容丰富度标准
disable-model-invocation: true
user-invokable: false
---
# 方案文档质量评测量规

## 适用范围

由 design skill 在 design 步骤调用。对 design.md 进行多维度质量评测，输出 badcase 清单与 surface_reason。**严格不产出根因分析与提示词缺陷诊断**。

---

## 五维量规（满分 100）

| 维度                             | 权重 | 评测重点                                              |
| -------------------------------- | ---- | ----------------------------------------------------- |
| 结构完整性（structure）          | 20%  | 7 章覆盖度、层级合理性（深度≤4）、逻辑顺序、粒度均衡 |
| 语义准确性（semantic）           | 30%  | 与 spec 的语义一致、关键概念覆盖、设计决策一致性      |
| 业务规则准确性（business_rules） | 20%  | 规则完整性、正确性、一致性、FMEA 覆盖度               |
| 规则合规性（compliance）         | 10%  | 格式规范（标题层级、表格格式、图表语法）              |
| 文档质量（quality）              | 20%  | 逻辑连贯性、详细程度、可读性、完整性                  |

---

## 结构完整性检查项（对齐 7 章）

参考 `{SPECIFY_ROOT}/verification/design-content-generator/references/document-structure.md`：

| 部分      | 最低要求                                                                                                      |
| --------- | ------------------------------------------------------------------------------------------------------------- |
| 第 1 部分 | 1.1 业务背景 >= 3 句话（痛点+现状+诉求）；1.2 方案价值为一段话（非列表）                                      |
| 第 2 部分 | 2.1 方案概述一段话；2.2 新旧对比表 >= 3 维度；2.3 时序图参与者 >= 4、交互步骤 >= 6、变更点红色标注、含 legend |
| 第 3 部分 | 每变更点含位置+类型+默认值+说明；无变更时简要说明                                                             |
| 第 4 部分 | 每子模块：业务说明 >= 3 句 + PlantUML + 业务规则表 >= 2 行                                                    |
| 第 5 部分 | 无风险时 >= 2 段话；有风险时含 FMEA 分析表                                                                    |
| 第 6 部分 | 无影响时 >= 2 段话；有影响时含性能评估表                                                                      |
| 第 9 部分 | 9.1 包结构 >= 2 层；9.2 组件 >= 3 个含 legend；9.3 类关系 5 分区含 legend                                     |
| 全文      | 总行数 >= 250                                                                                                 |

---

## 质量维度（内容丰富度）

参考 `{SPECIFY_ROOT}/verification/design-content-generator/references/content-richness-standards.md` 逐项检查各章节是否达到最低内容深度。

---

## severity 映射

| impact 范围  | severity |
| ------------ | -------- |
| impact ≥ 90 | critical |
| impact ≥ 70 | major    |
| impact ≥ 40 | minor    |
| 否则         | trivial  |

blocking_count = badcases 中 severity 为 critical 或 major 的数量。

---

## badcase 字段规范

每个 badcase 必须包含：id、dimension、category、severity、location、description、evidence、surface_reason、impact。

---

## 输出格式

- `{feature_dir}/.runs/evaluations/design-evaluation-summary.json`：含 meta、scores、badcases
- `{feature_dir}/.runs/evaluations/design-evaluation-report.md`：综合评分表、问题统计、badcase 列表

---

## 通过阈值

- **score >= 95**：通过，可进入下一环节
- **score < 95**：不通过，需触发 evaluate_design_fix 修复循环
