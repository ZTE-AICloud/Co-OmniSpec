# Skill Validation Report

## 基本信息

| 项目 | 内容 |
|------|------|
| 技能名称 | {SKILL_NAME} |
| 技能路径 | {SKILL_PATH} |
| 验证时间 | {VALIDATION_TIME} |
| 执行模式 | {EXECUTION_MODE} |
| 执行检查项 | {CHECK_ITEMS} |
| 验证器版本 | {VALIDATOR_VERSION} |

---

## 检查摘要

| 指标 | 数量 | 百分比 |
|------|------|--------|
| 总检查项 | {TOTAL_CHECKS} | 100% |
| ✅ 通过 | {PASSED_CHECKS} | {PASSED_PERCENT}% |
| 🟡 警告 | {WARNING_CHECKS} | {WARNING_PERCENT}% |
| 🔴 严重问题 | {CRITICAL_CHECKS} | {CRITICAL_PERCENT}% |
| 🔵 优化建议 | {SUGGESTION_CHECKS} | {SUGGESTION_PERCENT}% |
| **通过率** | **{PASS_RATE}%** | - |

---

## 📋 问题总结表格

| 问题 | 问题所在位置 | 级别 | 产生影响 | 修复建议 |
|------|--------------|------|----------|----------|
{ISSUES_SUMMARY_TABLE}

---

## 📝 问题详情

### 🔴 严重问题 [必选项]

{CRITICAL_ISSUES_DETAILS}

### 🟡 警告 [警告]

{WARNING_ISSUES_DETAILS}

### 🔵 优化建议 [可选项]

{SUGGESTION_ISSUES_DETAILS}

---

## 阶段验证结果

### 阶段1：基础识别

| 检查项 | 检查点数 | 通过 | 警告 | 严重问题 | 优化建议 | 通过率 |
|--------|----------|------|--------|----------|----------|--------|
| 01-基础结构与层级检查 | {01_TOTAL} | {01_PASSED} | {01_WARNING} | {01_CRITICAL} | {01_SUGGESTION} | {01_RATE}% |
| 02-技能类型识别 | {02_TOTAL} | {02_PASSED} | {02_WARNING} | {02_CRITICAL} | {02_SUGGESTION} | {02_RATE}% |
| 03-前置元数据验证 | {03_TOTAL} | {03_PASSED} | {03_WARNING} | {03_CRITICAL} | {03_SUGGESTION} | {03_RATE}% |

**阶段1统计**：
- 总检查点：{STAGE1_TOTAL}
- 通过：{STAGE1_PASSED} ({STAGE1_PASSED_PERCENT}%)
- 警告：{STAGE1_WARNING} ({STAGE1_WARNING_PERCENT}%)
- 严重问题：{STAGE1_CRITICAL} ({STAGE1_CRITICAL_PERCENT}%)
- 优化建议：{STAGE1_SUGGESTION} ({STAGE1_SUGGESTION_PERCENT}%)
- **阶段通过率：{STAGE1_RATE}%**

### 阶段2：内容验证

| 检查项 | 检查点数 | 通过 | 警告 | 严重问题 | 优化建议 | 通过率 |
|--------|----------|------|--------|----------|----------|--------|
| 04-内容结构与格式 | {04_TOTAL} | {04_PASSED} | {04_WARNING} | {04_CRITICAL} | {04_SUGGESTION} | {04_RATE}% |
| 05-附属文件检查 | {05_TOTAL} | {05_PASSED} | {05_WARNING} | {05_CRITICAL} | {05_SUGGESTION} | {05_RATE}% |
| 06-内容类型一致性 | {06_TOTAL} | {06_PASSED} | {06_WARNING} | {06_CRITICAL} | {06_SUGGESTION} | {06_RATE}% |

**阶段2统计**：
- 总检查点：{STAGE2_TOTAL}
- 通过：{STAGE2_PASSED} ({STAGE2_PASSED_PERCENT}%)
- 警告：{STAGE2_WARNING} ({STAGE2_WARNING_PERCENT}%)
- 严重问题：{STAGE2_CRITICAL} ({STAGE2_CRITICAL_PERCENT}%)
- 优化建议：{STAGE2_SUGGESTION} ({STAGE2_SUGGESTION_PERCENT}%)
- **阶段通过率：{STAGE2_RATE}%**

### 阶段3：配置验证

| 检查项 | 检查点数 | 通过 | 警告 | 严重问题 | 优化建议 | 通过率 |
|--------|----------|------|--------|----------|----------|--------|
| 07-权限配置检查 | {07_TOTAL} | {07_PASSED} | {07_WARNING} | {07_CRITICAL} | {07_SUGGESTION} | {07_RATE}% |
| 08-子代理配置检查 | {08_TOTAL} | {08_PASSED} | {08_WARNING} | {08_CRITICAL} | {08_SUGGESTION} | {08_RATE}% |
| 09-高级用法检查 | {09_TOTAL} | {09_PASSED} | {09_WARNING} | {09_CRITICAL} | {09_SUGGESTION} | {09_RATE}% |

**阶段3统计**：
- 总检查点：{STAGE3_TOTAL}
- 通过：{STAGE3_PASSED} ({STAGE3_PASSED_PERCENT}%)
- 警告：{STAGE3_WARNING} ({STAGE3_WARNING_PERCENT}%)
- 严重问题：{STAGE3_CRITICAL} ({STAGE3_CRITICAL_PERCENT}%)
- 优化建议：{STAGE3_SUGGESTION} ({STAGE3_SUGGESTION_PERCENT}%)
- **阶段通过率：{STAGE3_RATE}%**

### 阶段4：质量评估

| 检查项 | 检查点数 | 通过 | 警告 | 严重问题 | 优化建议 | 通过率 |
|--------|----------|------|--------|----------|----------|--------|
| 10-兼容性与部署检查 | {10_TOTAL} | {10_PASSED} | {10_WARNING} | {10_CRITICAL} | {10_SUGGESTION} | {10_RATE}% |
| 11-文档质量与最佳实践 | {11_TOTAL} | {11_PASSED} | {11_WARNING} | {11_CRITICAL} | {11_SUGGESTION} | {11_RATE}% |
| 12-性能与故障排除 | {12_TOTAL} | {12_PASSED} | {12_WARNING} | {12_CRITICAL} | {12_SUGGESTION} | {12_RATE}% |

**阶段4统计**：
- 总检查点：{STAGE4_TOTAL}
- 通过：{STAGE4_PASSED} ({STAGE4_PASSED_PERCENT}%)
- 警告：{STAGE4_WARNING} ({STAGE4_WARNING_PERCENT}%)
- 严重问题：{STAGE4_CRITICAL} ({STAGE4_CRITICAL_PERCENT}%)
- 优化建议：{STAGE4_SUGGESTION} ({STAGE4_SUGGESTION_PERCENT}%)
- **阶段通过率：{STAGE4_RATE}%**

### 阶段5：完整性验证

| 检查项 | 检查点数 | 通过 | 警告 | 严重问题 | 优化建议 | 通过率 |
|--------|----------|------|--------|----------|----------|--------|
| 13-交叉引用验证 | {13_TOTAL} | {13_PASSED} | {13_WARNING} | {13_CRITICAL} | {13_SUGGESTION} | {13_RATE}% |
| 14-章节完整性检查 | {14_TOTAL} | {14_PASSED} | {14_WARNING} | {14_CRITICAL} | {14_SUGGESTION} | {14_RATE}% |
| 15-内容质量增强 | {15_TOTAL} | {15_PASSED} | {15_WARNING} | {15_CRITICAL} | {15_SUGGESTION} | {15_RATE}% |

**阶段5统计**：
- 总检查点：{STAGE5_TOTAL}
- 通过：{STAGE5_PASSED} ({STAGE5_PASSED_PERCENT}%)
- 警告：{STAGE5_WARNING} ({STAGE5_WARNING_PERCENT}%)
- 严重问题：{STAGE5_CRITICAL} ({STAGE5_CRITICAL_PERCENT}%)
- 优化建议：{STAGE5_SUGGESTION} ({STAGE5_SUGGESTION_PERCENT}%)
- **阶段通过率：{STAGE5_RATE}%**

---

## 🎯 优先级修复建议

### 🔴 立即修复（严重问题）
{PRIORITY_CRITICAL}

### 🟡 尽快修复（警告）
{PRIORITY_WARNING}

### 🔵 后续优化（建议）
{PRIORITY_SUGGESTION}

---

## 总体评价

### 📊 评分：{OVERALL_SCORE}/100

### ✅ 优点
{PROS_LIST}

### 🔧 改进空间
- 需要修复 {CRITICAL_COUNT} 个严重问题
- 需要改进 {WARNING_COUNT} 个警告项
- 可参考 {SUGGESTION_COUNT} 个优化建议

### 🎯 总体建议

**{OVERALL_RECOMMENDATION}**

**针对严重问题的建议**：
{CRITICAL_RECOMMENDATION}

**整体提升方向**：
{IMPROVEMENT_DIRECTIONS}

---

## 修复行动计划

### 🔴 第一优先级：修复严重问题（预计 {CRITICAL_ESTIMATED_TIME}）

{CRITICAL_ACTION_ITEMS}

### 🟡 第二优先级：改进警告项（预计 {WARNING_ESTIMATED_TIME}）

{WARNING_ACTION_ITEMS}

### 🔵 第三优先级：实施优化建议（预计 {SUGGESTION_ESTIMATED_TIME}）

{SUGGESTION_ACTION_ITEMS}

---

## 下一步

- 查看生成的报告：`{SKILL_PATH}/skill-validation-report.md`
- 根据优先级修复发现的问题
- 使用 `/skill-validator [路径] fix` 自动修复可修复的问题
- 运行 `/skill-validator [路径] check all` 完整验证修复结果

---

## 附录

### 检查项编号对照表

| 编号 | 中文名称 | 英文别名 | 检查点数 |
|------|----------|----------|----------|
| 01 | 基础 | basic, structure | 23 |
| 02 | 类型 | type, category | 10 |
| 03 | 元数据 | metadata, yaml | 38 |
| 04 | 内容 | content, format | 58 |
| 05 | 附属 | auxiliary, files | 48 |
| 06 | 一致性 | consistency | 6 |
| 07 | 权限 | permission, auth | 37 |
| 08 | 子代理 | agent, subagent | 55 |
| 09 | 高级 | advanced | 12 |
| 10 | 兼容 | compatibility, deploy | 7 |
| 11 | 质量 | quality, doc | 20 |
| 12 | 性能 | performance, troubleshoot | 18 |
| 13 | 交叉引用 | cross-reference | 17 |
| 14 | 章节 | section, completeness | 13 |
| 15 | 质量增强 | quality-enhanced | 22 |

### 验证器版本信息

- 版本号：{VALIDATOR_VERSION}
- 发布日期：{RELEASE_DATE}

---

*报告生成时间：{REPORT_GENERATION_TIME}*
*验证工具：skill-validator v{VALIDATOR_VERSION}*