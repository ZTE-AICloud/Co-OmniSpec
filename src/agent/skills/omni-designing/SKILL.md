---
name: omni-designing
description: 执行实施规划工作流, 使用计划模板生成设计制品，在代码之前建立可执行的技术决策体系。仅通过 /omni.design 命令调用，不自动触发。
---
# omni-designing

执行实施规划工作流，使用计划模板生成设计制品，在代码之前建立可执行的技术决策体系。

## 输入

- **用户参数**：`$ARGUMENTS`（可为空）

## 输出

- `IMPL_DESIGN`：设计主文档（路径由步骤 1 脚本提供）
- `research.md`：关键技术决策与取舍（位于 FEATURE_DIR 或脚本指定位置）
- `FEATURE_DIR/data-model.md`：数据模型（若适用）
- `FEATURE_DIR/contracts/*`：接口契约（若适用）
- `FEATURE_DIR/quickstart.md`：最小可验证集成与测试路径（若适用）
- Agent 特定上下文文件：由更新脚本生成/更新

## 指令

### 1. 设置阶段
- 判断当前操作系统，windows还是linux系统;
- 针对不同操作系统从仓库根目录运行脚本
    windows:`.specify/scripts/powershell/setup-design.ps1 --json`
    linux:`.specify/scripts/bash/setup-design.sh --json`
- 解析 JSON 获取 FEATURE_SPEC、IMPL_DESIGN、CHANGES_DIR、BRANCH. 对于参数中的单引号如 "I'm Groot", 使用转义语法: 例如 'I'\''m Groot'(或尽可能使用双引号: "I'm Groot").
- **获取文档目录配置**：运行脚本获取 DOC_DIR 配置
    windows:`.specify/scripts/powershell/check-prerequisites.ps1 --json --paths-only`
    linux:`.specify/scripts/bash/check-prerequisites.sh --json --paths-only`
- 从 JSON 输出中解析 **DOC_DIR** 变量（如果未设置则默认为 "omni-doc"）
- **重要**: DOC_DIR 将用于后续所有文档路径引用，支持通过环境变量 `SPECIFY_DOC_DIR` 或 `config` 文件配置

### 2. 加载上下文
   - 读取 `.specify/memory/constitution.md` 以及 IMPL_DESIGN 模板(已复制)。
   - **优先加载 context.md**:
     * **必须检查** `FEATURE_DIR/context.md` 是否存在
     * **如果存在**, 直接读取 `context.md` 作为主要上下文源，提取以下信息:
       - 功能描述和目标
       - 提取的关键词（用于后续检索）
       - 检索到的设计文档列表（可直接参考，减少重复检索）
       - 可复用的需求和场景模式
       - 术语对齐信息
       - 约束和假设
       - **相关代码文件**（新增）：代码文件路径、函数接口、数据结构、实现模式
       - **需要新增的代码**（新增）：消息类型、消息结构、处理函数等
     * **如果不存在**, 继续执行后续检索步骤（但应提示用户先执行 `/omni.context` 生成上下文）
   - **补充检索**（仅在 context.md 信息不足时执行）:
     1. **如文档无法解答疑问**：允许深入代码仓库执行 `search`（可用 `grep`、`read_file` 逐文件阅读），直到澄清概念或接口约束，避免凭空猜测。**优先参考 context.md 中的代码文件**: 如果 context.md 中已列出相关代码文件，优先阅读这些文件，了解现有实现模式
     2.**查找文件时禁止使用限制命令**：使用 `read_file`、`grep`、`glob_file_search` 等工具时，**严禁使用 `head`、`tail`、`limit` 等命令限制输出**，必须读取完整内容以准确理解项目结构

### 3. 执行计划工作流

1. 按照 IMPL_DESIGN 模板中的结构填充内容
   - 填充技术上下文(将未知项标记为 `NEEDS CLARIFICATION`)
   - 从章程文档填充章程检查部分
   - 评估关卡（如果违规无正当理由则报错）

2. 阶段 0: 大纲与研究
   - **从技术上下文中提取未知项**:
      - 每个 `NEEDS CLARIFICATION` → 研究任务
      - 每个依赖项 → 最佳实践任务
      - 每个集成 → 模式任务

   - **生成和分发研究任务**:
      ```text
      For each unknown in Technical Context:
      Task: "Research {unknown} for {feature context}"
      For each technology choice:
      Task: "Find best practices for {tech} in {domain}"
      ```

   - **在 `research.md` 中整合发现**，使用格式:
      - Decision: [选择了什么]
      - Rationale: [为什么选择]
      - Alternatives considered: [还评估了什么]

   - **输出**: `research.md`，所有 `NEEDS CLARIFICATION` 已解决

3. 阶段 1: 技术设计建模
   - **前提条件**: `research.md` 完成

   - 调用 `omni-design-modeling` 技能，将 IMPL_DESIGN 作为参数传入该技能，并严格遵照技能指引执行。

   - **输出**: `data-model.md`、`/contracts/*`、`quickstart.md`

4. 阶段 2: Agent上下文更新
   - 判断当前操作系统，windows还是linux系统;
   - 针对不同操作系统从仓库根目录运行脚本
      windows: `.specify/scripts/powershell/update-agent-context.ps1`
      linux: `.specify/scripts/bash/update-agent-context.sh`
   - 这些脚本检测正在使用哪个 AI Agent
   - 更新相应的Agent特定上下文文件
   - 仅添加当前计划中的新技术
   - 保留标记之间的手动添加内容

   - **输出**: Agent特定文件

5. 设计后重新评估
   - 重新评估章程检查，确保设计符合项目规范

### 4. 完成并继续
- 所有阶段完成后，报告分支、IMPL_DESIGN 路径和生成的制品

## 关键规则

- 关卡失败或未解决的澄清事项时报错
