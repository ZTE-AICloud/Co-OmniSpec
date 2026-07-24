---
name: eval-specify
description: Spec 产出物内容质量评测量规。定义四维评分（业务价值、技术完整性、清晰度与可测性、可追溯性）的检查项、打分标准、YAML 报告格式。由 evaluation-analyst（Eva）引用，适用于 spec_eval 模式。
user-invokable: false
allowed-tools: Read, Write, Glob, Grep
---

# Spec 内容质量评测

## 适用范围

当前仅定义 **spec_eval** 模式的量规。design_eval、detail_eval 的量规待后续扩展。

---

## 四维评分（每维 25 分，满分 100）

### 维度 1：Business Value（业务价值）- 25 分

**评估内容**：
- 需求是否真正解决业务痛点（不是伪需求）
- 用户故事是否合理、可验证
- 优先级划分是否合理（P1/P2 的依据充分）
- 业务背景描述是否清晰

**检查项**：
1. 业务背景/痛点描述是否具体、可理解
2. 用户故事是否基于真实业务场景，非虚构
3. P1/P2 优先级是否有明确依据（如：核心路径 vs 增强功能）
4. 业务价值阐述是否避免空泛表述（如"提升用户体验"无具体说明）

**典型扣分项**：
- 用户故事脱离实际业务场景
- 优先级划分缺乏依据
- 业务价值阐述空泛

**打分参考**：
- 25 分：全部满足，无扣分项
- 20-24 分：1 处 minor 问题
- 15-19 分：2 处问题或 1 处明显问题
- 10-14 分：多处问题
- 0-9 分：严重缺失

---

### 维度 2：Technical Completeness（技术完整性）- 25 分

**评估内容**：
- 功能需求覆盖是否全面（关键场景无遗漏）
- 边界条件、异常情况是否考虑
- 非功能性需求（性能、安全、兼容性）是否提及
- GWT 场景是否具体、可测试

**检查项**：
1. 主流程、异常流程、边界场景是否都有覆盖
2. 是否考虑并发、重试、回滚、超时等常见技术场景
3. 性能、安全、兼容性等 NFR 是否提及（若适用）
4. GWT 场景的 Given/When/Then 是否完整、具体

**典型扣分项**：
- 遗漏关键边界场景（如并发、重试、回滚）
- 性能要求缺失或过于模糊
- 验收场景不完整

**打分参考**：同维度 1

---

### 维度 3：Clarity & Testability（清晰度与可测性）- 25 分

**评估内容**：
- FR 描述是否无歧义、可量化
- 验收标准是否明确（避免"及时"、"合理"等模糊词）
- 术语使用是否一致
- 是否避免过于抽象的描述

**检查项**：
1. FR 描述是否可被不同读者一致理解
2. 验收条件是否可量化（时间、次数、阈值等）
3. 是否避免模糊词汇（"尽快"、"合理"、"较快"、"及时"）
4. 术语（如：网元、推送、校验码）前后是否一致

**典型扣分项**：
- 使用模糊词汇（"尽快"、"合理"、"较快"）
- 验收条件无法量化
- 术语前后不一致

**打分参考**：同维度 1

---

### 维度 4：Traceability（可追溯性）- 25 分

**评估内容**：
- 每条 FR 是否能追溯到 feature_description
- 用户故事与 FR 的对应关系是否清晰
- 验收场景与 FR 的覆盖关系

**检查项**：
1. 每条 FR 是否能在 feature_description 中找到对应诉求
2. 是否引入了原始需求之外的功能（scope creep）
3. 用户故事与 FR 的映射关系是否清晰
4. 验收场景是否覆盖了对应的 FR

**典型扣分项**：
- FR 无法追溯到原始需求
- 引入了原始需求之外的功能（scope creep）
- 用户故事与 FR 对应关系混乱

**打分参考**：同维度 1

---

## Finding 结构

每个 finding 必须包含以下字段：

| 字段 | 类型 | 说明 |
|------|------|------|
| severity | string | info \| warning \| error |
| location | string | 问题位置（章节名、FR 编号、用户故事编号等） |
| message | string | 问题描述 |
| recommendation | string | 改进建议 |
| line | number \| null | 行号（可选，无法定位时为 null） |
| gene_related | string \| null | 若问题位置与 Genome Usage Metadata 中某基因的 locations 匹配，填写该 gene_id；否则为 null |
| gene_contribution | string \| null | 当 gene_related 非空时必填：positive（基因预填充有助于质量）、negative（基因预填充导致或加剧问题）、neutral（与基因无关或无法判断） |

**severity 分级**：
- **info**：提示性建议，不影响可实施性
- **warning**：建议改进，可能影响验收或实施
- **error**：严重问题，需修复才能通过

---

## YAML 报告格式规范

### 文件路径

`FEATURE_DIR/.runs/evaluations/eval-specify-report.yaml`

### 结构要求

1. **report_version**：语义化版本，如 "1.0"
2. **metadata**：tool、eval_mode、timestamp、feature_dir、evaluated_files
3. **evaluations**：数组，支持追加。当前仅 spec 阶段，每个条目包含：
   - stage、timestamp、overall_score、status（pass \| warning \| fail）
   - dimensions：四个维度的 score、max、weight、findings
   - summary、strengths、issues
4. **final_score**：当前仅 spec 时等于 spec 的 overall_score
5. **trend**：当前为空，未来可追加 spec_to_design、design_to_detail

### status 阈值

- **pass**：overall_score >= 95
- **warning**：80 <= overall_score < 95
- **fail**：overall_score < 80

### 注释要求

YAML 报告需带详细注释（`#` 开头），便于人工阅读和配置调整。每个主要区块应有分隔注释说明用途。
