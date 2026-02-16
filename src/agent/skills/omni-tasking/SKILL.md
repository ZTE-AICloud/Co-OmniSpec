---
name: omni-tasking
description: 基于可用的设计文档为功能特性生成可执行的、按依赖关系排序的 tasks.md。在用户要求生成任务列表、制定实施计划、从 spec/design 产出 tasks 时使用。
argument-hint: "[功能目录或任务生成上下文]"
---

# 生成 tasks.md

## 用户输入

```text
$ARGUMENTS
```

在继续之前，**必须**考虑用户输入（若不空）。

## 概述

1. **设置**
    - 判断当前操作系统（Windows / Linux），从仓库根目录运行：
        - Windows: `.specify/scripts/powershell/check-prerequisites.ps1 --json`
        - Linux: `.specify/scripts/bash/check-prerequisites.sh --json`
    - 解析 FEATURE_DIR 与 AVAILABLE_DOCS。所有路径为绝对路径。参数值中含单引号时用转义（如 `'I'\''m Groot'`）或双引号。

2. **加载设计文档**（自 FEATURE_DIR）
    - **必需**: design.md（技术栈、库、结构）, spec.md（带优先级的用户故事）
    - **可选**: data-model.md（实体）, contracts/（API 端点）, research.md（决策）, quickstart.md（测试场景）
    - 按实际存在的文档生成任务。

3. **执行任务生成工作流**
    - 从 design.md 提取技术栈、库、项目结构
    - 从 spec.md 提取带优先级的用户故事（P1、P2、P3…）
    - 若存在 data-model.md：提取实体并映射到用户故事
    - 若存在 contracts/：将端点映射到用户故事
    - 若存在 research.md：提取影响任务设置的决策
    - 按用户故事生成任务（格式与规则见 [reference.md](reference.md)）
    - 生成故事完成顺序的依赖关系图
    - 为每个用户故事给出可并行执行示例
    - 验证完整性：每个故事具备所需任务、可独立测试

4. **生成 tasks.md**  
   使用 `.specify/templates/tasks-template.md` 作为结构，填充：
    - design.md 中的功能名称
    - **阶段 1**：设置（项目初始化）
    - **阶段 2**：基础任务（所有用户故事的阻塞先决条件）
    - **阶段 3+**：按 spec.md 优先级顺序，每个用户故事一个阶段
        - 每阶段含：故事目标、独立测试标准、测试（若请求）、实现任务
        - 每任务带清晰 [Story] 标签（US1、US2、US3…）
        - 故事内可并行任务标 [P]
        - 每故事阶段后检查点
    - **最终阶段**：完善与横切关注点
    - 按执行顺序编号（T001、T002…）、每任务带清晰文件路径
    - 依赖关系部分、每故事并行执行示例、实现策略（MVP 优先、增量交付）

5. **报告**  
   输出生成的 tasks.md 路径与摘要：总任务数、每故事任务数、并行机会、每故事独立测试标准、建议 MVP 范围（通常为用户故事 1）。

任务生成上下文: $ARGUMENTS

tasks.md 应立即可执行——每项任务足够具体，使 LLM 无需额外上下文即可完成。

## 任务格式与规则

生成任务时**严格遵循** [reference.md](reference.md) 中的：检查清单格式（TaskID、[P]、[Story]、文件路径）、任务组织（来自 spec/合约/数据模型/基础设施）、阶段结构。仅当规范明确要求或用户要求 TDD 时才生成测试任务。

## 可选后续

完成后可建议用户：

- **分析一致性**：运行项目一致性分析（如项目中有 /omni.analyze 或等价流程）。
- **实施项目**：根据生成的 tasks.md 实施项目（如 /omni.implement 或等价流程）。
