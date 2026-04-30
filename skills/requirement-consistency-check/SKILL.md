---
name: requirement-consistency-check
description: 需求边界一致性检查的过程性知识。定义三类检查维度、代码读取策略、问题严重度分级。由 requirement-consistency-reviewer（Robin）引用，适用于 spec_review、design_scope_check、detail_design_review 三种审核模式。
disable-model-invocation: true
user-invokable: false
---

# 需求边界一致性检查

## 三类检查维度（所有模式通用）

- **Scope Creep 检测**：目标文档中每个变更点，能否在参照文档中找到对应业务需求依据？
- **需求覆盖检测**：参照文档的所有 FR-xxx 是否都有对应的设计条目？（仅 spec_review 模式检查）
- **语义一致性检测**：目标文档对业务场景的描述是否与参照文档一致？

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

**示例**：读 `LiteSummaryFileService` 时，包路径 `app.application.lite.service` 和类注释揭示它服务于 Lite APP 定时备份，而非 USC 主流程的周期备份推送 → 判定 Scope Creep，blocking。

---

## 问题严重度分级

| 级别 | 示例 |
|------|------|
| **blocking** | 变更文件/类无 spec 中的需求依据、Scope Creep、关键诉求遗漏 |
| **warning** | 语义描述模糊、覆盖不完整 |
| **info** | 文字润色建议 |
