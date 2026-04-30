---
name: tasks
description: 基于可用的设计文档为功能特性生成可执行的、按依赖关系排序的 tasks.md。在用户要求生成任务列表、制定实施计划、从 spec/design 产出 tasks 时使用。
argument-hint: "[功能目录或任务生成上下文]"
context: fork
---

# 生成 tasks.md

## 用户输入

```text
$ARGUMENTS
```

在继续之前，**必须**考虑用户输入（若不空）。

## 概述

0. 开始执行步骤之前，需要进行一些打点记录工作，记录本skill的执行时间到 `start_time`字段：
   - 判断当前操作系统，windows还是linux系统;
   - 针对不同操作系统运行脚本获取配置
     windows: `Get-Date -Format "yyyy-MM-dd HH:mm:ss"`
     linux: `date +"%Y-%m-%d %H:%M:%S"`
   - 将获取的时间记录到 `start_time`

1. **设置**
    - 判断当前操作系统（Windows / Linux），从仓库根目录运行：
        - Windows: `scripts/powershell/check-prerequisites.ps1 --json`
        - Linux: `scripts/bash/check-prerequisites.sh --json`
    - 解析 FEATURE_DIR 与 AVAILABLE_DOCS。所有路径为绝对路径。参数值中含单引号时用转义（如 `'I'\''m Groot'`）或双引号。

2. **加载设计文档**（自 FEATURE_DIR）
    - **必需**: design.md（技术栈、库、结构）, spec.md（带优先级的场景）
    - **可选**: data-model.md（实体）, contracts/（API 端点）, research.md（决策）, quickstart.md（测试场景）, e2e-test.md(端到端测试用例)
    - 按实际存在的文档生成任务。

3. **执行任务生成工作流**
    - 从 design.md 提取技术栈、库、项目结构
    - 从 spec.md 提取带优先级的场景（P1、P2、P3…）
    - 若存在 data-model.md：提取实体并映射到场景
    - 若存在 contracts/：将端点映射到场景
    - 若存在 research.md：提取影响任务设置的决策
    - 按场景生成任务（格式与规则见 [reference.md](reference.md)）
    - 生成场景完成顺序的依赖关系图
    - 为每个场景给出可并行执行示例
    - 验证完整性：每个场景具备所需任务、可独立测试
    - **修改点严格检查（强制）**：基于 design/spec/context 提取修改点并逐条校验：
      1. 是否已经支持（已有实现可复用）
      2. 是否遵循利旧原则（复用既有架构与代码实现）
      3. 是否遵循最小化原则（仅生成必要改动任务，避免扩散）

   **E2E 测试策略**:
   - **TDD 模式**（如果章程要求或用户明确选择）:
     - 为每个场景生成测试任务
     - 测试任务在实现任务之前
     - 遵循红-绿-重构循环
   - **非 TDD 模式**（默认）:
     - 测试任务在实现任务之后
     - 关注核心功能的单元测试和集成测试
     - 不强制要求测试先行

4. **生成 tasks.md**
   使用 `.infra/templates/tasks-template.md` 作为结构，填充：
    - design.md 中的功能名称
    - **阶段 1**：设置（项目初始化）
    - **阶段 2**：基础任务（所有场景的阻塞先决条件）
    - **阶段 3+**：按 spec.md 优先级顺序，每个场景一个阶段
        - 每阶段含：场景目标、独立测试标准、测试（若请求）、实现任务
        - 每任务带清晰 [Scenario] 标签（S1、S2、S3…）
        - 场景内可并行任务标 [P]
        - 每场景阶段后检查点
    - **最终阶段**：完善与横切关注点
    - 按执行顺序编号（T001、T002…）、每任务带清晰文件路径
    - 依赖关系部分、每场景并行执行示例、实现策略（MVP 优先、增量交付）
    - 对每个场景增加“修改点检查任务”（可为任务组或检查项），至少包含：
      - `[ ] [Scenario] 校验修改点支持状态（已支持/部分支持/不支持）`
      - `[ ] [Scenario] 校验利旧实现路径（模块/接口/函数）`
      - `[ ] [Scenario] 校验最小化改动边界（文件与函数范围）`

5. **报告**
   输出生成的 tasks.md 路径与摘要：总任务数、每场景任务数、并行机会、每场景独立测试标准、建议 MVP 范围（通常为场景 1）。
   同时输出“修改点严格检查摘要”：修改点总数、已支持数量、利旧通过数量、最小化通过数量、需澄清数量。

任务生成上下文: $ARGUMENTS

tasks.md 应立即可执行——每项任务足够具体，使 LLM 无需额外上下文即可完成。
若“修改点严格检查”未通过且无合理说明，不得输出为最终可执行版本，必须先回填检查任务并收敛范围。

6. **记录本skill的运行日志信息**：执行`runlog-record` skill，请将前面获取到的`start_time`的值作为参数传入`runlog-record` skill

## 任务格式与规则

生成任务时**严格遵循** [reference.md](reference.md) 中的：检查清单格式（TaskID、[P]、[Scenario]、文件路径）、任务组织（来自 spec/合约/数据模型/基础设施）、阶段结构。仅当规范明确要求或用户要求 TDD 时才生成测试任务。
