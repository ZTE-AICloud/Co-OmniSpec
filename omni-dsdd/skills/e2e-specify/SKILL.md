---
name: e2e-specify
description: 测试分析与设计(TA&TD)：使用MFQ&PPDCS方法论进行测试分析，从需求提取测试点（M单功能/F功能交互/Q质量属性），然后使用TCON方法设计黑盒测试用例。输出：测试分析报告(test-analysis.md)和黑盒测试用例(e2e-test.md)。当用户说"/e2e-specify"、"生成测试设计"、"创建测试用例"、"分析测试设计"，或在规范生成后需要生成测试设计时使用此技能。
allowed-tools: Agent, Bash
---

## 用户输入

```text
$ARGUMENTS
```

在继续之前, 你**必须**考虑用户输入(如果不为空).

## 概述

执行测试分析与设计工作流，使用 MFQ&PPDCS 方法论进行测试分析，然后使用 TCON 方法设计黑盒测试用例。

**调用场景**：
1. **初步设计**（在 `/specify` 之后）：基于初始规范生成初步测试分析和设计
2. **更新设计**（在 `/clarify` 之后）：基于澄清后的规范更新测试分析和设计

## 执行流程

### 1. [ ] 设置环境

1. **判断操作系统**：Windows 或 Linux
2. **运行前置检查脚本**：
   - Windows: `scripts/powershell/check-prerequisites.ps1 --json`
   - Linux: `scripts/bash/check-prerequisites.sh --json`
3. **解析输出**：
   - 提取 `FEATURE_DIR`（特性目录绝对路径）
   - 提取 `SPEC_FILE`（规范文件路径）
   - 提取 `AVAILABLE_DOCS`（可用文档列表）

**重要**：所有路径必须是绝对路径。

### 2. [ ] 确定调用场景

根据调用上下文确定场景类型：
- **初步设计**：如果在 `/specify` 之后调用，场景为"初步设计"
- **更新设计**：如果在 `/clarify` 之后调用，场景为"更新设计"

### 3. [ ] 启动测试分析设计 Agent

使用 Agent 工具启动 @"test-analysis-design (agent)"，传递以下参数：

**Agent 参数**：
- `subagent_type`: "general-purpose"（使用通用 agent）
- `description`: "测试分析与设计 - 生成测试分析和黑盒测试用例"
- `prompt` 包含以下内容：

```
# 测试分析与设计任务

## 调用场景
{场景类型}: 初步设计/更新设计

## 输入文件
- spec.md: {SPEC_FILE}
- feature_dir: {FEATURE_DIR}

## 任务要求
1. 读取 spec.md 规范文件
2. 使用 MFQ&PPDCS 方法论进行测试分析
3. 生成测试分析报告（test-analysis.md）
4. 使用 TCON 四步法设计黑盒测试用例
5. 生成黑盒测试用例文档（e2e-test.md）

## 输出位置
- test-analysis.md: {FEATURE_DIR}/test-analysis.md
- e2e-test.md: {FEATURE_DIR}/e2e-test.md

## 重要说明
- 如果是"初步设计"场景：所有 Issues 保持 Open 状态
- 如果是"更新设计"场景：根据澄清结果更新，将相关 Issues 标记为 Resolved
```

### 4. [ ] 验证生成文档

等待 agent 完成后，验证生成的文档：

1. **检查文档存在性**：
   - 检查 `{FEATURE_DIR}/test-analysis.md` 是否存在
   - 检查 `{FEATURE_DIR}/e2e-test.md` 是否存在

2. **验证文档内容**：
   - `test-analysis.md` 应包含：
     - KYM 分析
     - TCO 分析
     - MFQ 建模结果
     - 测试点清单
     - Issues 列表（状态应为 Open 或 Resolved）
   - `e2e-test.md` 应包含：
     - 用例清单
     - 用例详情（Given-When-Then 格式）
     - 测试数据设计
     - 追溯性矩阵

3. **处理验证结果**：
   - [成功] **验证成功**：输出完成报告，继续下一步
   - [失败] **验证失败**：
     - 记录错误信息
     - 如果是关键错误（文档未生成、内容为空），报告失败
     - 如果是非关键错误（部分内容缺失），记录警告但继续

### 5. [ ] 报告完成情况

输出完成报告，包括：

- **生成文档**：
  - test-analysis.md 路径
  - e2e-test.md 路径

- **验证结果**：
  - 文档存在性检查：[成功]/[失败]
  - 内容完整性检查：[成功]/[失败]
  - 问题列表（如有）

- **测试统计**：
  - 测试点数量（来自 test-analysis.md）
  - 测试用例数量（来自 e2e-test.md）
  - Issues 数量及状态

- **下一步建议**：
  - 如果存在 Open Issues：建议执行 `/clarify` 澄清
  - 如果测试设计完整：建议执行 `/design` 进行技术设计

## 错误处理

1. **Agent 执行失败**：
   - 记录错误信息
   - 报告失败原因
   - 建议解决方案

2. **文档生成失败**：
   - 检查 agent 输出日志
   - 验证输入文件（spec.md）是否存在且有效
   - 验证输出目录（FEATURE_DIR）是否可写

3. **内容验证失败**：
   - 如果是关键内容缺失：报告失败
   - 如果是非关键内容缺失：记录警告，继续执行

## 通用指南

### 快速指南

- 专注于测试分析和设计，不涉及测试代码实现
- 使用 MFQ&PPDCS 方法论系统化分析
- 使用 TCON 方法设计黑盒测试用例
- 关注需求覆盖率和测试点完整性
- 保持黑盒测试特性，不暴露内部实现

### AI 生成

1. **做出有根据的猜测**：使用上下文、需求描述和测试设计模式
2. **限制 Issues 数量**：仅记录真正需要澄清的问题
3. **优先级排序**：按影响范围排序 Issues（范围 > 安全 > 体验 > 细节）

## 建议后续步骤

测试分析与设计完成后，可继续执行：
- **clarify**：澄清测试相关问题（如果存在 Open Issues）
- **design**：进行技术设计
- **e2e-varify**：完善测试设计细节
