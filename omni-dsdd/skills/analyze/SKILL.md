---
name: analyze
description: 制品一致性分析技能。对 spec.md、design.md、tasks.md 做跨制品一致性分析并自动修复，不设轮数上限，全程不询问用户。残留问题完整打印后继续正常结束。用于分析制品、检查一致性、质量审查。
allowed-tools: Read, Edit, Write, Glob, Grep, Bash, Skill
---

# OmniSpec 跨制品一致性与质量分析

## 目标

在三份制品齐备后, 识别 `${FEATURE_DIR}` 下核心制品（`spec.md`、`design.md`、`tasks.md`）之间的不一致、重复、模糊和规范不足，并自动修复可消除项。**前置条件**：三份制品均已落盘。

## 用户输入

在继续之前，**必须**考虑用户的消息内容（若不为空）。

---

## 环境初始化

| 变量 | 含义 |
|------|------|
| `CLAUDE_PLUGIN_ROOT` | Omni 插件安装根目录 |
| `CLAUDE_WORKING_DIR` | 用户工作区目录 |
| `FEATURE_DIR` | 特性目录（绝对路径，应在 `${CLAUDE_WORKING_DIR}/changes/...` 下） |

### 路径约定

| 制品 | 路径 |
|------|------|
| 规范 | `${FEATURE_DIR}/spec.md` |
| 设计 | `${IMPL_DESIGN}` 或 `${FEATURE_DIR}/design.md` |
| 任务 | `${TASKS}` 或 `${FEATURE_DIR}/tasks.md` |
| 章程 | `${CLAUDE_WORKING_DIR}/.omni-infra/memory/constitution.md` |
| 环境文件 | `${FEATURE_DIR}/.runs/env.sh` |

### Step 0.1 检查变量

```bash
test -n "${CLAUDE_PLUGIN_ROOT:-}" && test -d "${CLAUDE_PLUGIN_ROOT}"
test -n "${CLAUDE_WORKING_DIR:-}" && test -d "${CLAUDE_WORKING_DIR}"
```

两项均通过且已 `source` 过 `env.sh`、`FEATURE_DIR` 非空 → 进入步骤 1。否则执行 Step 0.2。

### Step 0.2 补全变量（仅执行一次）

**`CLAUDE_PLUGIN_ROOT`**

1. 若 Claude Code 已注入且目录存在：沿用。
2. 若仍缺失，按顺序降级（须验证 `${路径}/skills/analyze/SKILL.md` 存在）：
   - Skill 加载上下文中的插件安装根；
   - 在 `${CLAUDE_WORKING_DIR}` 或其上级查找含 `.claude-plugin/plugin.json` 的目录；
3. `export CLAUDE_PLUGIN_ROOT="<绝对路径>"`
4. 失败 → 终止并提示配置插件。

**`CLAUDE_WORKING_DIR`**

1. 若已注入且目录存在：沿用。
2. 若缺失：`export CLAUDE_WORKING_DIR="$(pwd)"`（**不用** `git rev-parse --show-toplevel`）
3. 失败 → 终止。

### Step 0.3 校验（必须通过）

```bash
test -f "${CLAUDE_PLUGIN_ROOT}/scripts/bash/check-prerequisites.sh"
test -f "${CLAUDE_PLUGIN_ROOT}/skills/design/scripts/bash/design-resolve-context.sh"
test -d "${CLAUDE_WORKING_DIR}"
```

### 路径拼接约定

- 插件脚本：`${CLAUDE_PLUGIN_ROOT}/scripts/bash/...`
- 前置检查在 **`CLAUDE_WORKING_DIR`** 下执行
- **禁止**用 Git 分支推断 `FEATURE_DIR`；须以 `env.sh` / `paths.json` / `design-resolve-context.sh` 为准

---

## 操作约束

- **允许**编辑 `${FEATURE_DIR}` 下 `spec.md`、`design.md`、`tasks.md`（及修复所必需的最小范围）。
- 完成步骤 1–6 后 **必须**进入步骤 7 修复—验证循环；**不设轮数上限**，直至单轮无可自动修复项（收敛）。
- **禁止**向用户确认「是否修复/继续」；**禁止**只读报告代替自动修复。
- **残留问题不得阻断**：收敛后须完整打印残留项；本技能仍**正常完成**，**禁止**将残留问题记为技能失败。

**章程权威**：`${CLAUDE_WORKING_DIR}/.omni-infra/memory/constitution.md` 中 MUST 原则不可协商；冲突须通过编辑制品消除。

## 执行步骤

完成下列步骤 0–6 后 **必须**执行步骤 7, 不得在 analyze 执行期间停下来等待用户输入.

### 0. skill执行开始时间打点记录

开始执行步骤之前，需要进行一些打点记录工作，记录本skill的执行时间到 `start_time`字段：
 - 判断当前操作系统（windows 还是 linux 系统）
 - 针对不同操作系统获取时间：
   windows: `Get-Date -Format "yyyy-MM-dd HH:mm:ss"`
   linux: `date +"%Y-%m-%d %H:%M:%S"`
 - 将获取的时间记录到 `start_time`

### 1. 继承上游特性上下文（禁止 Git 猜目录）

与 **`tasks`** / **`design`** 一致：**禁止**用当前 Git 分支推断 `FEATURE_DIR`。

**解析顺序**：

1. workflow prompt 注入的 `FEATURE_DIR`（若有）
2. 运行 `design-resolve-context`（读 specify 链路的 `paths.json` / `.active-feature` / `env.sh`）：

```bash
eval "$(bash "${CLAUDE_PLUGIN_ROOT}/skills/design/scripts/bash/design-resolve-context.sh" \
  --plugin-root "${CLAUDE_PLUGIN_ROOT}" \
  --working-dir "${CLAUDE_WORKING_DIR}" \
  ${FEATURE_DIR:+--feature-dir "$FEATURE_DIR"} \
  --export)"
source "${FEATURE_DIR}/.runs/env.sh"
```

3. 若 `env.sh` 未含 `IMPL_DESIGN`/`TASKS`，读取 `${FEATURE_DIR}/.runs/paths.json` 的 `design_file`、`tasks_file`、`spec_file`
4. **最后**运行 `check-prerequisites --require-tasks --include-tasks`（**仅校验** `AVAILABLE_DOCS` 与制品存在性；`FEATURE_DIR` 已由上游确定，不得以 Git 分支覆盖）：
   - windows: `pwsh "${CLAUDE_PLUGIN_ROOT}/scripts/powershell/check-prerequisites.ps1" --json --require-tasks --include-tasks --working-dir "${CLAUDE_WORKING_DIR}" --plugin-root "${CLAUDE_PLUGIN_ROOT}"`
   - linux: `bash "${CLAUDE_PLUGIN_ROOT}/scripts/bash/check-prerequisites.sh" --json --require-tasks --include-tasks --working-dir "${CLAUDE_WORKING_DIR}" --plugin-root "${CLAUDE_PLUGIN_ROOT}"`

**路径赋值**（`source env.sh` 后优先用环境变量）：

- SPEC = `${FEATURE_SPEC}` 或 `${FEATURE_DIR}/spec.md`
- DESIGN = `${IMPL_DESIGN}` 或 `${FEATURE_DIR}/design.md`
- TASKS = `${TASKS}` 或 `${FEATURE_DIR}/tasks.md`

**强制校验**：

- `FEATURE_DIR` 位于 `${CLAUDE_WORKING_DIR}/changes/` 下
- `spec.md`、`design.md`、`tasks.md` 均存在；缺失则中止并提示补跑上游 `specify`/`design`/`tasks`
- 日志：`analyze 继承上游: FEATURE_DIR=..., source=specify-chain`

对于参数中的单引号, 如 "I'm Groot", 使用转义语法: 例如 'I'\''m Groot'(或尽可能使用双引号: "I'm Groot").

### 2. 加载制品(渐进式展示)

仅从每个制品加载最小必需的上下文:

**从 `${FEATURE_DIR}/spec.md`:**

- 概述/上下文
- 功能需求
- 非功能需求
- 用户故事
- 边缘情况(如果存在)

**从 design（`${IMPL_DESIGN}` 或 `${FEATURE_DIR}/design.md`）:**

- 架构/技术栈选择
- 数据模型引用
- 阶段
- 技术约束

**从 `${FEATURE_DIR}/tasks.md`:**

- 任务 ID
- 描述
- 阶段分组
- 并行标记 [P]
- 引用的文件路径

**从章程:**

- 加载 `${CLAUDE_WORKING_DIR}/.omni-infra/memory/constitution.md` 进行原则验证

### 3. 构建语义模型

创建内部表示(输出中不包含原始制品):

- **需求清单**: 每个功能和非功能需求, 带有稳定键(基于祈使短语推导 slug; 例如, "User can upload file" -> `user-can-upload-file`)
- **用户故事/操作清单**: 带有验收标准的离散用户操作
- **任务覆盖映射**: 将每个任务映射到一个或多个需求或故事(通过关键词/显式引用模式推断, 如 ID 或关键短语)
- **章程规则集**: 提取原则名称和 MUST/SHOULD 规范性声明

### 4. 检测过程(高效令牌分析)

专注于高信号发现. 限制总共 50 个发现; 在溢出摘要中聚合其余部分.

#### A. 重复检测

- 识别近似重复的需求
- 标记较低质量的表述以进行合并

#### B. 模糊性检测

- 标记缺乏可测量标准的模糊形容词(快速、可扩展、安全、直观、稳健)
- 标记未解决的占位符(TODO、TKTK、???、`<placeholder>` 等)

#### C. 规范不足

- 有动词但缺少对象或可测量结果的需求
- 缺少验收标准对齐的用户故事
- 引用规范/计划中未定义的文件或组件的任务

#### D. 章程对齐

- 与 MUST 原则冲突的任何需求或计划元素
- 章程中缺失的强制部分或质量门控

#### E. 覆盖缺口

- 没有关联任务的需求
- 没有映射需求/故事的任务
- 未在任务中反映的非功能需求(例如, 性能、安全性)

#### F. 不一致性

- 术语漂移(相同概念在不同文件中命名不同)
- 计划中引用但在规范中缺失的数据实体(反之亦然)
- 任务排序矛盾(例如, 集成任务在基础设置任务之前而没有依赖说明)
- 冲突需求(例如, 一个要求 Next.js 而另一个指定 Vue)

### 5. 严重性分配

使用此启发式方法对发现进行优先级排序:

- **严重**: 违反章程 MUST、缺失核心规范制品, 或零覆盖的需求阻止基线功能
- **高**: 重复或冲突需求、模糊的安全/性能属性、不可测试的验收标准
- **中**: 术语漂移、缺失非功能任务覆盖、规范不足的边缘情况
- **低**: 风格/措辞改进、不影响执行顺序的轻微冗余

### 6. 生成紧凑分析报告

每轮检测输出 Markdown 分析报告(不单独写入报告文件; 自动修复时对制品的编辑照常写入对应 `spec.md` / `design.md` / `tasks.md`), 结构如下:

## 规范分析报告

| ID  | 类别 | 严重性 | 位置             | 摘要            | 建议                       |
| --- | ---- | ------ | ---------------- | --------------- | -------------------------- |
| A1  | 重复 | 高     | spec.md:L120-134 | 两个相似需求... | 合并表述; 保留更清晰的版本 |

(每个发现添加一行; 生成以类别首字母为前缀的稳定 ID.)

**覆盖摘要表:**

| 需求键 | 有任务？ | 任务 ID | 备注 |
| ------ | -------- | ------- | ---- |

**章程对齐问题:**(如果有)

**未映射任务:**(如果有)

**指标:**

- 总需求数
- 总任务数
- 覆盖率%(有 >=1 个任务的需求)
- 模糊性计数
- 重复计数
- 严重问题计数

### 7. 自动修复与完成

- **不要**询问用户是否修复、是否继续或是否采纳建议; **不要**输出需用户选择的「下一步命令」交互块.
- 对可自动消除的问题（术语统一、任务与需求对齐、明显遗漏的子任务、与设计不一致的表述、章程冲突在制品层面的可消除项等）**直接改文件**（路径限于 `${FEATURE_DIR}` 下三制品及修复所必需的最小范围）.
- 每轮修改后重新执行本技能的分析检测（从步骤 3 起可增量）; **不设最大迭代轮数**, 直至**连续执行的一轮中已无可自动应用的修复**（收敛）后退出修复循环.
- **结束输出**: 输出完成摘要（累计修复要点、最终覆盖指标）; **若仍有残留问题**, 须**完整列出**残留项（表格或清单, 含严重性）, 并**明确声明本技能已正常完成**, 后续步骤应继续执行, **不得**将本阶段标为失败或中止 workflow.

### 8. analyze 收尾（落盘状态）

> 本步骤仅将 `analyze` 写入状态机并跑 `pre-implement` gate。  

1. 若存在 `${FEATURE_DIR}/.runs/env.sh`：`source "${FEATURE_DIR}/.runs/env.sh"`
2. 执行 post-analyze 脚本：

```bash
bash "${CLAUDE_PLUGIN_ROOT}/scripts/bash/workflow-post-analyze.sh" \
  --feature-dir "${FEATURE_DIR}"
```

3. 输出 analyze 完成摘要（修复要点、残留问题清单）；`workflow-post-analyze.sh` 退出码 `0` 即本技能**正常结束**。

### 9. 记录本skill的运行日志信息

- 执行 `omni-dsdd:runlog-record` skill，将前面获取到的 `start_time` 作为参数传入（如 `/omni-dsdd:runlog-record "2026-05-15 10:30:00"`）

## 操作原则

### 上下文效率

- **最小高信噪比令牌**: 专注于可操作的发现, 而不是详尽的文档
- **渐进式展示**: 增量加载制品; 不要将所有内容倾倒到分析中
- **高效令牌输出**: 限制发现表为 50 行; 总结溢出部分
- **确定性结果**: 无更改重新运行应产生一致的 ID 和计数

### 分析指南

- 按上文对三制品做一致性修复; **绝不虚构缺失部分**(如果缺失, 准确报告; 应通过显式补充条目或标注依赖来解决, 而非编造不存在的代码路径)
- **禁止**以「仍有残留问题」为由输出失败状态、退出码式失败或阻断调用方; 残留问题仅通过报告列出, 本技能始终以**正常完成**收尾
- **优先处理章程违规**(这些总是严重的)
- **使用示例而非详尽规则**(引用具体实例, 而不是通用模式)
- **优雅报告零问题**(发出带有覆盖统计的成功报告)

## 参考

| 项 | 路径 |
|----|------|
| 前置检查（bash） | `${CLAUDE_PLUGIN_ROOT}/scripts/bash/check-prerequisites.sh` |
| 前置检查（pwsh） | `${CLAUDE_PLUGIN_ROOT}/scripts/powershell/check-prerequisites.ps1` |
| analyze 收尾 | `${CLAUDE_PLUGIN_ROOT}/scripts/bash/workflow-post-analyze.sh` |
| 未完成检测 | `${CLAUDE_PLUGIN_ROOT}/scripts/bash/workflow-check-incomplete.sh` |
| workflow 门禁 | `${CLAUDE_PLUGIN_ROOT}/scripts/bash/workflow-gate.sh` |
| 本技能 | `${CLAUDE_PLUGIN_ROOT}/skills/analyze/SKILL.md` |
