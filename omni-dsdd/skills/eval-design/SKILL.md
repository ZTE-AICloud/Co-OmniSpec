---
name: eval-design
description: 对 design.md 进行多维度质量评测，输出 badcase 清单与 surface_reason。通过阈值：score >= 95 可进入下一环节。
allowed-tools: Read Edit Write
user-invokable: false
---
# 方案文档质量评测量规

## 适用范围

由 design skill 在 design 步骤调用。对 design.md 进行多维度质量评测，输出 badcase 清单与 surface_reason。**严格不产出根因分析与提示词缺陷诊断**。

---

## 变量定义

| 变量 | 含义 | 默认值 |
|------|------|--------|
| `{SPECIFY_ROOT}` | OmniSpec 根目录 | 当前工作目录的上一级（`../`） |
| `{feature_dir}` | 设计文档所在目录 | 由调用方（design skill）传入 |

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

blocking_count = badcases 中 severity 为 critical 或 major 的数量。当 blocking_count > 0 时，视为评测不通过。

---

## badcase 字段规范

每个 badcase 必须包含：id、dimension、category、severity、location、description、evidence、surface_reason、impact。

❗ **必填字段**: evidence — 无 evidence 值 = 不允许输出该 badcase；所有结论必须引用来源

示例：
```json
{
  "id": "badcase-001",
  "dimension": "structure",
  "category": "missing_section",
  "severity": "major",
  "location": "design.md:50-60",
  "description": "第4部分缺少业务规则表",
  "evidence": "设计文档中无变更点业务规则表",
  "surface_reason": "设计文档第4部分仅描述了模块功能，未按规范提供业务规则表",
  "impact": 75
}
```

---

## Decision Gate

强结论的 evidence 要求（信号不得直接升级为结论）：

| Claim Type | Required Evidence | Counter-Evidence |
|-----------|-----------------|-----------------|
| structural (章节缺失) | 必须读取 design.md 并引用行号范围 | 该节是否在特殊场景下可省略 |
| semantic (与 spec 一致性) | 必须读取 spec.md 并引用对应段落 | spec.md 本身是否有歧义 |
| behavioral (规则准确性) | 必须引用文档原文行号 | 规则是否有版本/分支差异 |

- Signal without evidence → 输出 "unresolved"
- 未检查 counter-evidence → 最高 "tentative"
- Evidence 被 counter-evidence 抵消 → "rejected" 或 "n/a"

---

## 输出格式

- `{feature_dir}/.runs/evaluations/eval-design-summary.json`：含 meta、scores、badcases
- `{feature_dir}/.runs/evaluations/eval-design-report.md`：综合评分表、问题统计、badcase 列表

注：`{feature_dir}` 为设计文档所在目录，由调用方（design skill）传入。

---

## 通过阈值

- **score >= 95**：通过，可进入下一环节
- **score < 95**：不通过，需触发 evaluate_design_fix 修复循环

---

## 行为准则（整个会话有效，不因对话长度放松）

1. ❗ 每个 badcase 必须包含 evidence 字段且非空 — 每次输出前自检
2. ❗ 严格不产出根因分析或提示词缺陷诊断 — 仅输出 surface_reason — 每次输出前自检
3. ❗ 评分基于五维量规客观打分 — 不凭印象 — 每次输出前自检

## 执行流程

### Step 1: 读取设计文档
- 读取 `{feature_dir}/design.md`
- 完成性要求: 已读取行数 == 设计文档总行数
- 失败降级: 文件不存在 → 报告"设计文档不存在"，终止
- ✅ Checkpoint: "Step 1 完成: 读取 X 行"

### Step 2: 需求边界一致性检查
- 加载 skill `eval-design-consistency-check`, 检查 `{feature_dir}/design.md` 的需求一致性
- 输入: `{feature_dir}/spec.md`(参照) + `{feature_dir}/design.md`(目标)
- 通过标准: 无 blocking 问题

### Step 3: 五维量规逐项检查
- 按结构完整性 → 语义准确性 → 业务规则准确性 → 规则合规性 → 文档质量顺序检查
- 完成性要求: 已检查维度数 == 5
- 失败降级: 外部引用文件不存在 → 跳过该引用，基于正文检查
- ✅ Checkpoint: "Step 2 完成: 检查 X/5 维度"

### Step 4: 统计得分与识别 badcase
- 完成性要求: badcase id 唯一且连续编号
- 失败降级: 无 badcase → 输出 score=100 + "通过"
- ✅ Checkpoint: "Step 3 完成: X 个 badcase, score=Y"

### Step 5: 输出评分结果
- 生成 JSON 和 MD 报告
- 完成性要求: 输出文件数 == 2
- 失败降级: 写入失败 → 输出到 stdout
- ✅ Checkpoint: "Step 4 完成: 输出 X/2 文件"
