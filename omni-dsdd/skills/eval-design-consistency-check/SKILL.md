---
name: eval-design-consistency-check
description: 需求一致性检查知识库，提供需求边界一致性检查、Scope Creep 检测、需求覆盖检测、语义一致性分析三类维度及代码读取判断业务归属策略。由 requirement-consistency-reviewer（Robin）引用，适用于 spec_review、design_scope_check、detail_design_review 三种审核模式。
argument-hint: [目标文档] [参照文档] [审核模式]
when_to_use: 当用户提到"需求一致性"、"检查边界"、"Scope Creep"、"需求覆盖"、审核设计文档、对比 spec 与 design 时触发。适用于 spec_review、design_scope_check、detail_design_review 审核流程。
user-invokable: false
allowed-tools: Read, Grep, Glob
---

# 需求边界一致性检查

## 概览（职责与输入输出）

### 职责
本技能提供需求边界一致性检查的知识定义和执行策略，帮助审核人员：
- 检测 Scope Creep（变更超出需求范围）
- 检查需求覆盖完整性
- 验证语义一致性

### 输入前提
- 需要对比的两份文档（目标文档和参照文档）
- 可选：代码文件路径（用于判断业务场景归属）

### 输出产物
- 一致性检查结论（blocking/warning/info）
- 具体的问题描述和定位

## 行为准则（会话全程有效，不因对话长度放松）

1. ❗ 每个发现必须引用来源（文件路径 + 行号）— 每次输出前自检
2. ❗ 评分基于检查清单客观打分（按清单定义的 0/1/2 或 Pass/Partial/Fail）— 每次输出前自检
3. ❗ 禁止单边修复 — 改文档必须同步改实现，改实现必须同步改文档 — 每次修改前自检

## 执行流程

**Step 1: Scope Creep 检测**
- [ ] 提取目标文档中每个变更点
- [ ] 在参照文档中查找对应业务需求依据（Grep FR-xxx / 功能点编号）
- [ ] 标记无需求依据的变更（blocking）
- 完成性要求: 已检查变更数 == 提取的变更总数
- 失败降级: 参照文档不可读 → 标注 "UNABLE TO ASSESS: 参照文档不可用"
- ✅ Checkpoint: "Step 1 完成: 检查 X 个变更点，Y 个无需求依据"

**Step 2: 语义一致性检测**
- [ ] 对比目标与参照文档的业务场景描述
- [ ] 识别语义不一致的描述（warning）
- [ ] 区分事实性差异和表述差异
- 完成性要求: 已对比场景数 == 两文档场景总数
- 失败降级: 语义无法判断 → 标注 "UNABLE TO ASSESS: [原因]" + 禁止推测
- ✅ Checkpoint: "Step 2 完成: 对比 X 个场景，Y 个语义不一致"

**Step 3（仅 spec_review 模式）: 需求覆盖检测**
- [ ] 逐条检查参照文档的每个 FR-xxx
- [ ] 确认每个 FR 有对应设计条目
- [ ] 记录覆盖不完整的需求（warning）
- 完成性要求: 已检查 FR 数 == 参照文档 FR 总数
- 失败降级: 目标文档格式无法解析 → 标注 "UNABLE TO ASSESS: [原因]"
- ✅ Checkpoint: "Step 3 完成: 检查 X 个 FR，Y 个覆盖不完整"

---

## 代码读取策略

**目的**：仅凭文档描述无法判断一个类属于哪个业务路径。例如 `LiteSummaryFileService` 的文档描述是"按 FTP 汇总成功推送的网元"，与 spec.md 的"FTP 推送"场景语义上看起来匹配，无法发现越界。必须读取代码才能判断业务场景归属。

**与 design-reviewer 的区分**：

| Agent | 读代码的目的 | 读什么 |
|-------|------------|-------|
| design-reviewer | 验证技术实现是否准确（调用链、方法签名） | 详细实现代码 |
| requirement-consistency-reviewer | 理解变更文件的**业务场景归属** | 包路径、类注释、类级 JavaDoc，**不读方法体** |

**执行规则**：
1. 从目标文档中提取所有涉及的变更文件列表
2. 先尝试从文档上下文（包路径、类名、变更说明）推断业务场景归属
3. 当文档上下文不足以确认时，读取对应代码文件的**类级信息**（包声明、类注释、类签名），不读方法体
4. 判断目标："这个类服务于哪个业务路径/应用模块"，而非"这个方法的实现是否正确"

**代码读取示例命令**：
```bash
# 读取文件开头30行获取包路径和类注释
head -n 30 /path/to/FileName.java

# 搜索类定义行
Grep "^public class|^class" /path/to/*.java

# 按包路径筛选文件
Glob "app/application/lite/**/*.java"
```

**示例**：读 `LiteSummaryFileService` 时，包路径 `app.application.lite.service` 和类注释揭示它服务于 Lite APP 定时备份，而非 USC 主流程的周期备份推送 → 判定 Scope Creep，blocking。

---

## 问题严重度分级

| 级别 | 示例 |
|------|------|
| **blocking** | 变更文件/类无 spec 中的需求依据、Scope Creep、关键诉求遗漏 |
| **warning** | 语义描述模糊、覆盖不完整 |
| **info** | 文字润色建议 |

---

## Decision Gate

### Signal 只能启动调查，不能直接生成结论

| Claim Type | 触发信号 | Required Evidence | Counter-Evidence | Completeness 上限 |
|------------|---------|-------------------|------------------|-------------------|
| authority（Scope Creep blocking） | 变更点无 FR 编号 | 完整的 FR 搜索记录（Grep 结果） + 需求文档版本 | 是否存在非 FR 格式的其他需求依据 | partial（无完整搜索记录时） |
| semantic（语义不一致 warning） | 两文档描述用词差异 | 双方原文摘录 + 术语定义来源 | 是否因文档版本不同导致 | partial（无版本信息时） |
| relational（代码场景归属） | 包路径与设计意图不匹配 | 类级信息（包声明、类注释、类签名）+ 文档上下文 | 文档描述与代码注释矛盾时以代码为准 | partial（无类级信息时） |

决策规则:
- Signal without evidence → unresolved
- Strong decisions require complete evidence AND checked counter-evidence
- Partial evidence → tentative
- 无来源引用 → 禁止输出

---

## 使用示例

### 基本用法
当审核设计文档时，检查变更点是否有对应的需求依据：

1. 读取设计文档，提取变更文件列表
2. 对每个变更文件，使用 Grep 搜索对应的 FR 编号
3. 如未找到 FR 依据，标记为 Scope Creep（blocking）

### spec_review 模式
1. 对照 spec.md 的 FR-xxx 清单
2. 检查每个 FR 是否有对应设计条目
3. 检查设计是否超出 FR 范围

### 代码场景归属判断
读取变更类的包路径和类注释，判断业务模块归属：
- `app.application.lite.*` → Lite APP 模块
- `app.application.usc.*` → USC 主流程模块
- 包路径不匹配设计意图 → Scope Creep
