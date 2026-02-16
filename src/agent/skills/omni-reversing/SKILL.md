---
name: reversing
description: 代码逆向分析技能. 从现有代码库逆向生成完整规范文档, 包含项目入口分析、接口识别、实体提取、功能分析、架构梳理、场景归纳、需求抽象、上下文建模和文档生成. 仅通过 /omni.reverse 命令调用, 不自动触发.
---

# omni-reversing

从现有代码库逆向生成完整规范文档的多阶段分析技能.

## 使用时机

- 执行 /omni.reverse 命令时

## 阶段总览

逆向分析分为 9 个有序阶段, 每个阶段的详细指令在同级的阶段文件中:

| 阶段 | 文件 | 输入 | 输出 | 描述 |
|------|------|------|------|------|
| 0 | `phase-0-project-entry.md` | 当前目录代码 | `project-entry.md` | 分析项目入口 |
| 1 | `phase-1-interface-overview.md` | `project-entry.md` | `interface-overview.md` | 识别对外接口 |
| 1b | `phase-1b-interface-specs.md` | `interface-overview.md` | `omni-doc/specs/interfaces/API-XXX-*.md` | 生成接口规范 |
| 2 | `phase-2-entity-overview.md` | `interface-overview.md` | `entity-overview.md` | 提取逻辑实体 |
| 2b | `phase-2b-entity-specs.md` | `entity-overview.md` | `omni-doc/specs/entities/ENTITY-XXX-*.md` | 生成实体规范 |
| 3 | `phase-3-function-overview.md` | `interface-overview.md` + `entity-overview.md` | `function-overview.md` | 分析业务功能 |
| 3b | `phase-3b-function-specs.md` | `function-overview.md` | `omni-doc/specs/functions/FUNC-XXX-*.md` | 生成功能规范 |
| 4 | `phase-4-architecture.md` | `entity-overview.md` | `logic_architecture.md` | 分析逻辑架构 |
| 5 | `phase-5-scenario-overview.md` | `omni-doc/specs/functions/` | `scenario-overview.md` | 归纳业务场景 |
| 5b | `phase-5b-scenario-specs.md` | `scenario-overview.md` | `omni-doc/specs/scenarios/SCN-XXX-*.md` | 生成场景规范 |
| 6 | `phase-6-requirement-overview.md` | `scenario-overview.md` | `requirement-overview.md` | 抽象需求 |
| 6b | `phase-6b-requirement-specs.md` | `requirement-overview.md` | `omni-doc/specs/requirements/REQ-XXX-*.md` | 生成需求规范 |
| 7 | `phase-7-context.md` | `scenario-overview.md` | `context.md` | 建模系统上下文 |
| done | `phase-done.md` | 所有中间产物 + 规范文件 | 质量报告 + 关系文件 + SUMMARY.md | 质量审查与收尾 |

阶段 1b、2、2b、3、3b 和 5b 各有一个单元分析子提示词, 在批量循环中被反复调用:
- `phase-1b-interface-specs-unit.md` — 单个接口的规范文件生成指令
- `phase-2-entity-overview-unit.md` — 单个接口的逻辑实体分析指令
- `phase-2b-entity-specs-unit.md` — 单个实体的规范文件生成指令
- `phase-3-function-overview-unit.md` — 单个接口的业务功能分析指令
- `phase-3b-function-specs-unit.md` — 单个功能的规范文件生成指令
- `phase-5b-scenario-specs-unit.md` — 单个场景的规范文件生成指令
- `phase-6b-requirement-specs-unit.md` — 单个需求的规范文件生成指令

## 指令

### 1. 初始化

- 确认工作目录为项目根目录
- 确保 `omni-doc/specs-temp/intermediate/` 目录存在, 不存在则创建
- 确保 `omni-doc/specs/` 及其子目录存在, 不存在则创建

### 2. 确定执行范围

根据用户输入判断执行范围:

- **无参数或 `all`**: 从阶段 0 开始, 按顺序执行所有阶段
- **指定阶段号** (如 `3` 或 `phase-3`): 仅执行指定阶段
- **指定范围** (如 `3-6`): 执行阶段 3 到阶段 6
- **`continue`**: 检查进度文件 `omni-doc/specs-temp/task_process.md`, 从上次中断处继续

### 3. 按序执行阶段

对每个待执行阶段:

1. **读取阶段文件**: 从当前 skill 目录读取对应的 `phase-X-*.md` 文件
2. **检查前置条件**: 验证该阶段所需的输入文件是否存在
3. **执行阶段指令**: 严格按照阶段文件中的步骤执行
4. **验证输出**: 确认输出文件已正确生成
5. **报告进度**: 告知用户当前阶段完成, 输出文件位置

### 4. Token 超限处理

- **监控阈值**: 当本次会话累计 Token 数达到 **100,000** 时暂停
- **暂停提示**: 提示用户已完成的阶段和下一个待执行阶段
- **恢复建议**: 建议用户在新会话中使用 `/omni.reverse continue` 或指定阶段号继续

### 5. 完成报告

所有阶段执行完毕后, phase-done 会生成 `omni-doc/specs/SUMMARY.md` 并向用户展示, 包含:

- 工程概况（项目名称、主要语言、源文件数、代码行数）
- 制品统计（接口/实体/功能/场景/需求各多少个、合计规范文件数）
- 引用链路图
- 执行信息（会话数、耗时、质量审查状态）

## 关键规则

- 严格按阶段顺序执行, 除非用户指定跳过
- 每个阶段的详细指令以阶段文件为准, 本文件仅负责编排
- 所有中间产物存放在 `omni-doc/specs-temp/intermediate/`
- 最终文档存放在 `omni-doc/specs/`
- 分析必须基于代码实际内容, 不能主观推测
