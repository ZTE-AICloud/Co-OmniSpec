---
name: implement
description: 执行实施计划，通过处理并执行 tasks.md 中定义的所有任务完成实施。强制遵循 TDD（RED→GREEN→REFACTOR）范式。
allowed-tools: Read Write Edit Glob Grep Bash Skill
context: fork
---

# implement

根据 `${FEATURE_DIR}/tasks.md` 中的任务分解与 design 技术计划，按阶段、依赖与 TDD 要求在**工作区代码树**中执行实施，并产出任务执行报告。

---

## 环境初始化

本节子步骤编号为 **1、2、3**（整数），与下方「指令」区 **步骤 0–11** 独立，勿混用。

本技能**所有**路径解析与脚本调用均依赖以下变量。代码改动落在 **`CLAUDE_WORKING_DIR`** 指向的工程树内（可与 Git 仓库根不同，例如子目录工作区）。

| 变量 | 含义 | 用途 |
|------|------|------|
| `CLAUDE_PLUGIN_ROOT` | Omni 插件安装根目录 | `check-prerequisites`、`workflow-gate` 等 |
| `CLAUDE_WORKING_DIR` | 用户当前工作区目录 | 工程根、`.cache/`、`.gitignore` 等横切文件 |
| `FEATURE_DIR` | 当前特性目录 | `tasks.md`、`design.md`、制品与 checklists |

### 工作区路径约定

| 符号 | 展开路径 |
|------|----------|
| 任务清单 | `${FEATURE_DIR}/tasks.md` |
| 设计 | `${FEATURE_DIR}/design.md` 或 `IMPL_DESIGN`（来自 `env.sh` / JSON） |
| 规范 | `${FEATURE_DIR}/spec.md` |
| E2E 实现设计（可选） | `${FEATURE_DIR}/e2e-impl-design.md` |
| 代码质量综合评测采集JSON | `${FEATURE_DIR}/.runs/evaluations/code.diff.json` |
| 代码质量综合评测报告 | `${FEATURE_DIR}/.runs/evaluations/eval-code-report.txt` |
| 检查清单目录 | `${FEATURE_DIR}/checklists/` |
| 上下文成本日志 | `${CLAUDE_WORKING_DIR}/.cache/context_cost.log` |
| Harness 环境 | `${FEATURE_DIR}/.runs/env.sh` |

### 1. 检查变量

```bash
test -n "${CLAUDE_PLUGIN_ROOT:-}" && test -d "${CLAUDE_PLUGIN_ROOT}"
test -n "${CLAUDE_WORKING_DIR:-}" && test -d "${CLAUDE_WORKING_DIR}"
```

任一项失败 → 执行 **步骤 2** 补全。

### 2. 补全变量

`CLAUDE_WORKING_DIR` 缺失时：

```bash
export CLAUDE_WORKING_DIR="$(pwd)"
```

**不用** `git rev-parse --show-toplevel`。

### 3. 校验

```bash
test -f "${CLAUDE_PLUGIN_ROOT}/scripts/bash/check-prerequisites.sh"
test -d "${CLAUDE_WORKING_DIR}"
mkdir -p "${CLAUDE_WORKING_DIR}/.cache"
```

**推荐**（workflow 进入 implement 前通常已具备）：

```bash
source "${FEATURE_DIR}/.runs/env.sh"
```

### 路径拼接约定

- 插件脚本：`${CLAUDE_PLUGIN_ROOT}/scripts/bash/...`、`${CLAUDE_PLUGIN_ROOT}/scripts/powershell/...`
- `check-prerequisites` 须在 **`CLAUDE_WORKING_DIR`** 下执行，且带 `--require-tasks --include-tasks`
- **禁止**仅用 Git 分支或裸 `check-prerequisites` 猜 `FEATURE_DIR`（优先 `paths.json` / `env.sh`）
- workflow 编排方可在 implement 前后调用：`${CLAUDE_PLUGIN_ROOT}/scripts/bash/workflow-gate.sh --feature-dir "$FEATURE_DIR" --check <pre-implement|post-implement|...>`

---

## 指令

### 执行步骤总览（TodoList）

**须按下面顺序执行**：上一项未完成（或未达到其「可跳过」条件），不得进入下一项。**【关键规则】所有任务必须全部完成才能结束，包括：功能代码任务、测试任务（TDD/单元测试/集成测试）、文档任务。任何未完成任务都是不完整的交付。**每完成一项，在会话中勾选或明确回复「步骤 N 已完成」。**步骤 N 与正文 §N 一一对应。**涉及 `clear` 与 `.cache/context_cost.log` 的规则见「上下文成本日志」及 §1、§7。

- [ ] **步骤 0** — skill 执行开始时间打点，记录 `start_time`（见 **§0**）
- [ ] **步骤 1** — 阶段开始：上下文快照、`clear`（或 fork 豁免 + `no_clear` 行）、仅依赖落盘文件（见 **§1**）
- [ ] **步骤 2** — 设置：继承 **FEATURE_DIR**（见 **§2**）；`check-prerequisites` 仅校验 **AVAILABLE_DOCS**
- [ ] **步骤 3** — 检查清单状态：扫描 `FEATURE_DIR/checklists/`；无该目录则本步记为跳过（见 **§3**）
- [ ] **步骤 4** — 加载与分析实施上下文：读取 tasks.md、design.md 及 §4 所列可选文档（见 **§4**）
- [ ] **步骤 5** — 项目设置验证：创建/校验各忽略文件（见 **§5**）
- [ ] **步骤 6** — 解析 tasks.md：阶段、依赖、[P]、执行顺序（见 **§6**）
- [ ] **步骤 7** — 按任务计划执行实施：分阶段 / TDD / 同文件协调；**每批结束后** `clear` + 日志；下一批前重读 `tasks.md` 等；实施中遵守 §7 内「实施执行规则」与「进度与错误处理」（见 **§7**）
- [ ] **步骤 8** — 完成验证与任务状态分析：复验 tasks.md、未完成项归类（见 **§8**）
- [ ] **步骤 9** — 代码质量综合评测: (1) 采集代码变更生成 JSON；(2) 调用 LLM 进行代码质量评估（见 **§9**）
- [ ] **步骤 10** — 生成最终报告、技能结束快照与 `skill_end` 日志行（见 **§10**）
- [ ] **步骤 11** — 记录本 skill 运行日志（`omni-dsdd:runlog-record`）（见 **§11**）

说明：若 **§3** 清单未通过且用户选择不继续，在 **步骤 3** 终止。

### 上下文成本日志（`.cache/context_cost.log`）

日志文件：**`${CLAUDE_WORKING_DIR}/.cache/context_cost.log`**（**不要**用 `git rev-parse --show-toplevel` 替代 `CLAUDE_WORKING_DIR`）。在写入前 `mkdir -p "${CLAUDE_WORKING_DIR}/.cache"`。**只追加**，勿覆盖。**每次** `clear`（或等价清理）须先写 `before_clear`、后写 `after_clear`（§1 入场、§7 每批等）；读不到占用时 `after_clear` 填 `unavailable`。豁免 clear 时写一行：`...|no_clear|reason=<说明>`。

行格式（`|` 分隔，UTF-8）：  
`<ISO8601>|implement|<事件>|before_clear|<Token 或 unavailable>`  
`<ISO8601>|implement|<事件>|after_clear|<Token 或 unavailable>`  
事件示例：`phase_start`、`batch:设置`、`batch:子批-1`。技能结束见 §10，追加一行：`<ISO8601>|implement|skill_end|context|<…>`。

### 0. skill执行开始时间打点记录

开始执行步骤之前，需要进行一些打点记录工作，记录本skill的执行时间到 `start_time`字段：
 - 判断当前操作系统，windows还是linux系统;
 - 针对不同操作系统运行脚本获取配置
   windows: `Get-Date -Format "yyyy-MM-dd HH:mm:ss"`
   linux: `date +"%Y-%m-%d %H:%M:%S"`
 - 将获取的时间记录到 `start_time`

### 1. 阶段开始：上下文快照、清理与执行边界

本技能**一开始**（进入步骤 2 之前）须完成下列事项，以降低上下文超限风险；**不得**跳过后续对文件的读取。

1. **记录上下文规模**  
   - 若宿主（如 Claude Code / Cursor）提供当前会话的 Token 用量、上下文占用比例或等价指标，在回复中输出一行快照，例如：`[implement 阶段开始] 上下文/Token：<数值或说明>`。  
   - 若环境无法读取，输出：`[implement 阶段开始] 上下文规模：不可用`，然后继续。  
   - **写入日志**：在随后执行第 2 步 **`clear`（或等价清理）之前**，按「**上下文成本日志**」追加 **`before_clear`**；清理完成后追加 **`after_clear`**（事件标识 `phase_start`）。

2. **清理上下文**  
   - **Claude Agent / Claude Code**：在记录完第 1 步快照后、进入步骤 2「设置」之前，使用宿主提供的 **`clear`** 指令（或等价「清空上下文」操作）清理当前对话上下文，再仅依据文件继续；清理后在回复中注明 `[implement] 已执行 clear`。  
   - **其他宿主（如 Cursor）**：在宿主支持的前提下，通过**新开会话、清空对话历史、使用摘要/压缩**等方式，主动释放本技能调用之前累积的长对话占用。  
   - 若本技能已通过 `context: fork`（或等价机制）在**隔离子会话**中执行，在快照中注明 `已 fork/隔离`，可不再要求执行 `clear`/手动清历史，但仍须遵守第 3 条文件边界；豁免时按「上下文成本日志」写 **`no_clear`** 说明行。  
   - 清理或隔离之后，**不得**依赖对「进入本技能之前」长对话内容的逐条记忆推进实施。

3. **仅以前序产物为准**  
   - 实施所需信息**必须**来自 `${CLAUDE_WORKING_DIR}` 工程树与 `${FEATURE_DIR}` 下已由前序步骤（specify / design / tasks / analyze 等）**写入磁盘**的文件；缺信息时**打开文件读取**，禁止仅凭对话记忆补全可能已过期的细节。  
   - 步骤 4「加载与分析实施上下文」所列文档为本阶段的权威来源。

### 2. 设置

- 判断当前操作系统（Windows 或 Linux）
- **§1 `clear` 后须从磁盘重解析**（fork 子进程同理）；**禁止**用 Git 当前分支猜 `FEATURE_DIR`：
  1. workflow prompt 的 `FEATURE_DIR`（若有）→ `design-resolve-context --export` → `source "${FEATURE_DIR}/.runs/env.sh"`
     ```bash
     eval "$(bash "${CLAUDE_PLUGIN_ROOT}/skills/design/scripts/bash/design-resolve-context.sh" \
       --plugin-root "${CLAUDE_PLUGIN_ROOT}" \
       --working-dir "${CLAUDE_WORKING_DIR}" \
       ${FEATURE_DIR:+--feature-dir "$FEATURE_DIR"} \
       --export)"
     source "${FEATURE_DIR}/.runs/env.sh"
     ```
  2. **最后** `check-prerequisites --require-tasks --include-tasks`（**仅校验**制品；须带 `--working-dir`/`--plugin-root`，不得以 Git 分支覆盖已解析的 `FEATURE_DIR`）
- **强制校验** `FEATURE_DIR` 位于 `${CLAUDE_WORKING_DIR}/changes/` 下；路径使用绝对路径。

### 3. 检查清单状态

（若存在 `${FEATURE_DIR}/checklists/`）

- 扫描 checklists/ 目录中的所有清单文件
- 对于每个清单, 统计:
    - 总项目数: 所有匹配 `- [ ]` 或 `- [X]` 或 `- [x]` 的行
    - 已完成项目数: 匹配 `- [X]` 或 `- [x]` 的行
    - 未完成项目数: 匹配 `- [ ]` 的行
- 创建状态表:
    ```
    | Checklist | Total | Completed | Incomplete | Status |
    |-----------|-------|-----------|------------|--------|
    | ux.md     | 12    | 12        | 0          | ✓ PASS |
    | test.md   | 8     | 5         | 3          | ✗ FAIL |
    | security.md | 6   | 6         | 0          | ✓ PASS |
    ```
- 计算总体状态:
    - **PASS**: 所有清单都有 0 个未完成项目
    - **FAIL**: 一个或多个清单有未完成项目

- **若有清单未完成**
    - 显示含未完成项数量的表格
    - **停止**并询问："Some checklists are incomplete. Do you want to proceed with implementation anyway? (yes/no)"
    - 等待用户响应后再继续
    - 用户回复 "no" / "wait" / "stop" → 停止；"yes" / "proceed" / "continue" → 进入步骤 4

- **若所有清单均已完成**
    - 显示所有清单通过的表格
    - 自动进入步骤 4

### 4. 加载与分析实施上下文

- **必需**: 读取 `${FEATURE_DIR}/tasks.md` 获取完整任务列表和执行计划
- **必需**: 读取 `${FEATURE_DIR}/design.md`（或 `IMPL_DESIGN`）获取技术栈、架构和文件结构
- **如果存在**: `${FEATURE_DIR}/data-model.md`
- **如果存在**: `${FEATURE_DIR}/contracts/`
- **如果存在**: `${FEATURE_DIR}/research.md`
- **如果存在**: `${FEATURE_DIR}/quickstart.md`
- **如果存在**: `${FEATURE_DIR}/context.md`

### 5. 项目设置验证

- **必需**：基于实际项目设置创建或验证忽略文件。

**检测与创建逻辑**

- 在 **`CLAUDE_WORKING_DIR`** 下检查是否为 Git 仓库（若是，则创建/验证 `${CLAUDE_WORKING_DIR}/.gitignore`）：

    ```sh
    git -C "${CLAUDE_WORKING_DIR}" rev-parse --git-dir 2>/dev/null
    ```

- 存在 `Dockerfile*` 或 design.md 提及 Docker → 创建/验证 `.dockerignore`
- 存在 `.eslintrc*` 或 `eslint.config.*` → 创建/验证 `.eslintignore`
- 存在 `.prettierrc*` → 创建/验证 `.prettierignore`
- 存在 `.npmrc` 或 `package.json` 且需发布 → 创建/验证 `.npmignore`
- 存在 Terraform 文件 `*.tf` → 创建/验证 `.terraformignore`
- 存在 Helm charts → 创建/验证 `.helmignore`

**若忽略文件已存在**：校验是否包含基本模式，仅追加缺失的关键模式。
 **若忽略文件不存在**：为检测到的技术创建完整模式集。

**按技术栈的通用模式**（参考 design.md）：

- **Node.js/JavaScript**: `node_modules/`, `dist/`, `build/`, `*.log`, `.env*`
- **Python**: `__pycache__/`, `*.pyc`, `.venv/`, `venv/`, `dist/`, `*.egg-info/`
- **Java**: `target/`, `*.class`, `*.jar`, `.gradle/`, `build/`
- **C#/.NET**: `bin/`, `obj/`, `*.user`, `*.suo`, `packages/`
- **Go**: `*.exe`, `*.test`, `vendor/`, `*.out`
- **Ruby**: `.bundle/`, `log/`, `tmp/`, `*.gem`, `vendor/bundle/`
- **PHP**: `vendor/`, `*.log`, `*.cache`, `*.env`
- **Rust**: `target/`, `debug/`, `release/`, `*.rs.bk`, `*.rlib`, `*.prof*`, `.idea/`, `*.log`, `.env*`
- **Kotlin**: `build/`, `out/`, `.gradle/`, `.idea/`, `*.class`, `*.jar`, `*.iml`, `*.log`, `.env*`
- **C++**: `build/`, `bin/`, `obj/`, `out/`, `*.o`, `*.so`, `*.a`, `*.exe`, `*.dll`, `.idea/`, `*.log`, `.env*`
- **C**: `build/`, `bin/`, `obj/`, `out/`, `*.o`, `*.a`, `*.so`, `*.exe`, `Makefile`, `config.log`, `.idea/`, `*.log`, `.env*`
- **Swift**: `.build/`, `DerivedData/`, `*.swiftpm/`, `Packages/`
- **R**: `.Rproj.user/`, `.Rhistory`, `.RData`, `.Ruserdata`, `*.Rproj`, `packrat/`, `renv/`
- **通用**: `.DS_Store`, `Thumbs.db`, `*.tmp`, `*.swp`, `.vscode/`, `.idea/`

**工具特定模式**

- **Docker**: `node_modules/`, `.git/`, `Dockerfile*`, `.dockerignore`, `*.log*`, `.env*`, `coverage/`
- **ESLint**: `node_modules/`, `dist/`, `build/`, `coverage/`, `*.min.js`
- **Prettier**: `node_modules/`, `dist/`, `build/`, `coverage/`, `package-lock.json`, `yarn.lock`, `pnpm-lock.yaml`
- **Terraform**: `.terraform/`, `*.tfstate*`, `*.tfvars`, `.terraform.lock.hcl`
- **Kubernetes/k8s**：`*.secret.yaml`, `secrets/`, `.kube/`, `kubeconfig*`, `*.key`, `*.crt`

### 6. 解析 tasks.md 结构并提取

- **任务阶段**：设置、测试、核心、集成、完善
- **任务依赖**：顺序与并行规则
- **任务详情**：ID、描述、文件路径、并行标记 [P]
- **执行流程**：顺序与依赖要求

### 7. 按任务计划执行实施

- **分阶段**：完成当前阶段后再进入下一阶段
- **依赖**：顺序任务按序执行，带 [P] 的并行任务可一并执行
- **TDD（默认）**：
  - 每个场景的任务执行必须遵循以下循环：
    1. **RED**：编写/运行测试，确认测试失败
       - 确保测试可编译且被执行
       - 失败原因必须是业务逻辑缺失，不是语法错误或测试框架问题
    2. **GREEN**：编写最少代码使测试通过
       - 只写让测试通过的最少代码
       - 运行测试，确认通过
    3. **REFACTOR**（可选）：在测试通过的前提下优化代码
       - 重构后重新运行测试确认仍然通过
  - **禁止跳过 RED 阶段**：不得在没有失败测试的情况下编写实现代码
  - **禁止跳过 GREEN 验证**：实现后必须运行测试确认通过
  - **TDD 执行证据日志（强制）**：每个任务完成 RED/GREEN/REFACTOR 后，须把证据**追加**写入 `${FEATURE_DIR}/.runs/tdd-execution-report.md`（写入前 `mkdir -p "${FEATURE_DIR}/.runs"`；UTF-8、仅追加），作为 TDD 执行证据，并在 §10 最终报告中引用该路径。每任务以 `### 任务 N：<描述>` 分节，记录：
    - **RED 证据**：失败现象（编译失败 / 断言失败的期望 vs 实际）、测试命令、结果（如 `FAIL [build failed]`、`FAIL`）
    - **GREEN 证据**：修改的文件与改动要点、测试命令、结果（如 `PASS`，附断言数）
    - **REFACTOR**：重构说明，或「无需重构」
    - 文件首部含 Feature ID、执行时间、总体结果（`**PASS/FAIL** -- <总述>`） 
    - **末尾追加「验收标准覆盖」表**：从 `${FEATURE_DIR}/spec.md` 逐条列出验收标准（AC）及其覆盖测试（列：`AC | 验收标准 | 测试覆盖`），每条 AC 至少映射到一个测试；无测试覆盖的 AC 须标注并说明原因

####  TDD 阶段 Gate 验证标准

每个阶段必须满足以下**明确的验收条件**才能进入下一阶段：

**RED 阶段 Gate（必须全部满足）**：
```
✅ 编译成功（返回码 0，无语法/类型/链接错误）
✅ 测试可执行（无框架加载错误、段错误、核心 dump）
✅ 测试运行失败（返回码 != 0）
✅ 失败输出包含 EXPECT/ASSERT 断言失败关键字
   （如 "EXPECT_TRUE"、"EXPECT_EQ"、"ASSERT_FALSE"、"FAILED" 等）
❌ 失败原因不是：
   - 编译错误（语法错误、类型错误）
   - 链接错误（undefined reference）
   - 运行时段错误/核心 dump
   - 测试框架配置错误
```

**GREEN 阶段 Gate（必须全部满足）**：
```
✅ 编译成功（返回码 0）
✅ 测试运行成功（返回码 0）
✅ 失败输出为空或不包含 EXPECT/ASSERT 失败关键字
✅ 所有断言均通过
```

**REFACTOR 阶段 Gate（如执行）**：
```
✅ 编译成功（返回码 0）
✅ 测试运行成功（返回码 0）
✅ 行为与重构前完全一致
```

#### TDD 失败诊断与恢复流程

当测试结果不符合预期 Gate 时，按以下流程处理：

**RED 阶段异常处理**：

| 异常情况 | 诊断 | 恢复动作 |
|---------|------|---------|
| 编译失败 | 检查测试代码语法、类型、头文件 | 修复测试代码 → 重新编译运行 |
| 测试意外通过 | 业务逻辑已存在或测试断言不足 | 报告 RED 阶段违反：测试不应在实现前通过 |
| 段错误/核心 dump | 测试框架问题或测试代码错误 | 修复测试代码 → 重新运行 |
| 无 EXPECT/ASSERT 失败但返回码非0 | 可能是 fixture/setup 错误 | 检查测试框架输出，修复后重新运行 |

**GREEN 阶段异常处理**：

| 异常情况 | 诊断 | 恢复动作 |
|---------|------|---------|
| 编译失败 | 实现代码有语法/类型错误 | 修复实现代码 → 重新编译运行 |
| 测试失败（断言未通过） | 实现代码不足或错误 | 补充/修正实现代码 → 重新运行 |
| 链接错误 | 缺少函数定义或符号导出 | 检查 CMake/构建配置 → 修正后重新运行 |
| 段错误/核心 dump | 实现代码有内存问题 | 使用 AddressSanitizer 诊断 → 修复后重新运行 |


- **同文件协调**：影响同一文件的任务须顺序执行
- **检查点**：每阶段完成后验证再继续
- **【强制要求】所有任务必须完成**：
  - 功能代码任务：所有标记为代码实现的任务必须完成并通过编译/语法检查
  - **测试任务：所有测试任务（包括单元测试、集成测试任务）必须实现，测试代码必须生成到文件**
  - 文档任务：所有文档更新任务必须完成
  - **禁止提前结束**：即使功能代码已完成，仍须完成所有测试任务才能进入步骤 8

- **【关键】测试任务的定义是"生成测试代码"，不是"验证测试编译"**：
  - **测试代码生成**：编写测试文件，这是**必须完成的**，与编译环境无关
  - **测试编译验证**：运行测试命令（如 `go test`、`pytest`、`npm test` 等）验证编译，这**依赖环境**
  - **正确行为**：当编译环境不可用时，**仍然要生成测试代码**，只是跳过验证步骤
  - **禁止行为**：因为无法验证编译就跳过测试代码生成
  - 示例：
    - ❌ 错误：编译器不可用 → 跳过测试任务
    - ✅ 正确：编译器不可用 → 生成测试代码到文件 → 报告"测试代码已生成，但编译验证待环境修复后执行"

- **【关键】环境限制的处理原则**：
  - 环境限制（如编译器/解释器不可用）不能作为跳过任务的理由
  - 任务可分两类：
    1. **可无环境执行**：生成代码、生成测试文件，写配置 → **必须完成**
    2. **必须依赖环境**：编译验证、运行测试 → **报告问题但继续其他任务**
  - 测试代码生成属于"可无环境执行"类别
  - 只有"必须依赖环境"的任务才能因环境问题而跳过

#### 每批任务完成后的上下文清理（避免超限）

- **一批**的默认含义：`tasks.md` 中**一个任务阶段**（设置 / 测试 / 核心 / 集成 / 完善）内，本轮应执行的任务已全部完成，且本阶段**检查点**已通过、`tasks.md` 中对应项已更新为 `- [X]`。若单阶段任务过多、上下文增长过快，可将「一批」细分为更小的子批（例如每完成若干顺序任务、或每轮 `[P]` 并行任务全部结束）并在每个子批结束后同样执行下列清理。
- **每批结束前须落盘**：本批涉及的代码与配置已保存；`tasks.md` 中本批任务已勾选，避免 `clear` 后丢失进度。
- **每批结束后清理上下文**：在 **Claude Agent / Claude Code** 下执行 **`clear`**（与 §1 第 2 条一致），并在回复中注明 `[implement] 批次完成，已 clear：<阶段名或子批说明>`。**每次**执行 `clear` 前、后，按「**上下文成本日志**」向 **`${CLAUDE_WORKING_DIR}/.cache/context_cost.log`** 追加 **`before_clear` / `after_clear`**（事件标识使用 `batch:<阶段名>` 或 `batch:子批-<说明>`）。其他宿主用 §1 所述等价方式。若本技能始终在 **`context: fork`** 子会话中执行且宿主对子会话自动轮换，可按 §1 说明在快照中说明豁免条件，豁免时同样写入 **`no_clear`** 说明行；但仍须保证**下一批**从文件恢复状态。
- **下一批仅依赖文件**：清理后推进下一批任务时，须**重新读取** `${FEATURE_DIR}/tasks.md`（及 design 等 §4 所列文档）确认当前进度与约束，**禁止**仅凭对本批对话的长记忆继续实施。

#### 实施执行规则（§7 内持续遵守）

- **【禁止自动提交】**：禁止自动执行 `git commit` 操作。代码修改仅保存到本地文件，不主动提交。如需提交代码，必须等待用户明确要求。
- **设置**：初始化项目结构、依赖、配置
- **TDD（默认）**：严格遵循 RED → GREEN → REFACTOR顺序执行（规则见 §7）。当存在 `${FEATURE_DIR}/e2e-impl-design.md` 时，按照**e2e 用例实施**方法进行编写
- **核心开发**：模型、服务、CLI、端点
- **集成**：数据库、中间件、日志、外部服务
- **收尾**：覆盖率验证（行覆盖率 90% / 分支覆盖率 70%）、性能与文档

- **e2e 用例实施**（仅当存在 `${FEATURE_DIR}/e2e-impl-design.md` 时）:
  * **强制前置检查**: 在实施 e2e 用例前，必须：
    - 读取并完整理解 `${FEATURE_DIR}/e2e-impl-design.md`
    - 读取 `${FEATURE_DIR}/tasks.md` 中与 e2e 相关的任务定义
    - 确认理解所有约定：测试数据格式、Fake定义、验证逻辑、入口函数签名等
  * **严格实施约束**:
    - 必须严格按照 tasks.md 中定义的步骤顺序实施，不得调换或跳过
    - 必须严格遵循 e2e-impl-design.md 中的约定：
      - 测试数据必须完全按照约定格式构造
      - Mock 对象必须使用约定的 Fake 实现和配置
      - 验证逻辑必须实现约定的检查点，不得遗漏或简化
      - 入口函数签名必须与约定完全一致
    - **禁止自行发挥**：不得"优化"、"简化"或"改进"约定，任何偏差必须立即报告
  * **实施后校验并输出报告**:
  ```
  ## 📋 e2e 用例实施校验报告
  - 对比实施步骤与 tasks.md 定义的一致性: ✅
  - 对比测试数据格式与 e2e-impl-design.md 约定: ✅
  - 对比 Fake 对象使用与约定: ✅
  - 对比验证逻辑实现与约定: ✅
  - 对比入口函数签名与约定: ✅
  - 偏离检查: 无偏离
  - 校验结果: ✅ e2e 用例实现严格遵循约定，无任何偏移
  ```

#### 进度与错误处理（§7 内持续遵守）

- 每完成一项任务即报告进度
- 非并行任务失败则停止；并行任务 [P] 中失败的单独报告，其余继续
- 错误信息需包含调试上下文；无法继续时给出下一步建议
- **重要**：已完成任务须在 `${FEATURE_DIR}/tasks.md` 中标记为 `- [X]`。

### 8. 完成验证与任务状态分析

- **重新读取 `${FEATURE_DIR}/tasks.md`**：获取最新状态，统计已完成（`- [X]`）与未完成（`- [ ]`）任务。

- **任务完成度验证**
    - 对已标记完成的任务做实际校验：
        - 验证所有必需任务已完成
        - 检查实施功能是否与原始规范匹配
	   - 验证测试通过且覆盖率满足要求
        - 确认实施遵循技术计划
    - 校验不通过的任务改回未完成。

- **【关键】未完成任务必须继续执行**：
    - 评估每个未完成任务是否可执行：
        - 检查依赖项(其他任务、外部服务、工具)是否满足
        - 检查所需文件或资源是否存在
        - 检查权限或配置问题
    - **所有可执行的未完成任务（包括测试任务）必须继续执行**，不得跳过
    - 只有因外部依赖不可用（如等待其他团队提供的 API）而确实无法执行的任务才能标记为"等待依赖"
    - 环境限制（如缺少编译器）应报告解决方案，而不是跳过任务

- **任务执行处理**
    - **可执行**：立即按依赖顺序执行，**不得询问用户是否继续**
    - **无法执行**：生成分析报告（任务 ID、原因、阻塞说明、解决建议），并继续尝试执行其他可执行任务

### 9. 代码质量综合评测

**执行流程**：
1. 确认 `${FEATURE_DIR}/.runs/env.sh` 已存在并 source 环境变量
2. **调用 `Skill` 工具**：`skill: "omni-dsdd:eval-code"`（这是唯一正确的调用方式）
3. 等待 `omni-dsdd:eval-code` 完成以下子步骤：
   - 阶段 1：调用 `omni-dsdd:eval-code-collector` 采集代码变更信息，生成 `code.diff.json`
   - 阶段 2：调用 `omni-dsdd:eval-code-evaluator` 执行代码质量评估，生成 `eval-code-report.txt`
4. 读取并展示评测报告内容
5. 根据评分决定是否需要进行修复和重新评测
  - 当 综合评分 >= 0.95, 则检查通过，进入下一步
  - 当 综合评分 < 0.95, 根据主要问题和改进建议，修复问题，并在完成修复后重新执行 `omni-dsdd:eval-code` 进行评测
    - 最多执行 3 轮
    - 3 轮后仍不通过，在报告中标记问题，警告用户，附上 `Warning: 代码评测结果不通过`
  
#### 重要说明：omni-dsdd:eval-code 与编译环境无关

**`omni-dsdd:eval-code` skill 的执行不需要编译器**：
- `omni-dsdd:eval-code` 仅执行两个操作：(1) 采集代码变更生成 JSON；(2) 调用 LLM 进行代码质量评估
- **不涉及编译、不涉及运行测试**，因此 Go/Python/Java 等编译器是否可用**不影响** `omni-dsdd:eval-code` 执行
- **禁止**以"编译器不可用"、"无法执行单元测试"等理由跳过或忽略步骤 9
- **正确的调用方式**：使用 `Skill` 工具调用 `/omni-dsdd:eval-code`，而不是手动生成 git diff
  - ✅ 正确：`Skill: omni-dsdd:eval-code` 或调用 `omni-dsdd:eval-code-collector` + `omni-dsdd:eval-code-evaluator`
  - ❌ 错误：手动执行 `git diff` 后就认为完成了 代码质量综合评测
  - ❌ 错误：看到 "编译器不可用" 就跳过 omni-dsdd:eval-code 调用
- 如果因环境问题导致 `omni-dsdd:eval-code` 执行失败，应：
  1. 检查 Python 环境及依赖（requests, jinja2, loguru）
  2. 检查 API 配置是否正确
  3. 检查 `code.diff.json` 是否已正确生成
  4. 仍然失败时，记录详细错误信息并继续后续步骤，**不得直接跳过**

### 10. 生成最终报告

- **【关键】最终报告必须准确反映任务完成状态**：
    - 若存在未完成任务，报告**不是**"实施完成"，而是"部分完成，待完成 X 个任务"
    - 未完成的任务必须列出并说明原因

- **任务执行报告**（需包含）：

    ```
    ## 任务执行最终报告
    ### 总体统计
    - 总任务数: X
    - 已完成: Y (Z%)
    - 未完成: W (V%)
      - 可执行: A
      - 无法完成: B

    ### 已完成任务列表
    [列出所有已完成的任务ID和描述]

    ### 【重点】未完成任务列表（功能未完成，不得结束）
    [列出所有未完成的任务ID和描述]
    - 代码任务: [列表]
    - 测试任务: [列表] ← 必须完成
    - 文档任务: [列表]

    ### 无法完成的任务分析
    [列出无法完成的任务, 包含:
     - 任务ID和描述
     - 阻塞原因(等待依赖/缺少资源/环境限制/需求问题/其他)
     - 详细说明
     - 解决建议]

     ## 代码质量综合评测
     [展示第9步代码评测的结论]
    ```

- **下一步建议**
    - **全部完成 → 报告成功，注明"所有任务已完成，包括功能代码和测试用例"**
    - 存在可执行未完成任务 → **强制继续执行**，不得结束
    - 存在无法完成的任务 → 建议用户排查并解决阻塞后再执行
    - 存在无法完成的任务 → 建议用户排查并解决阻塞后再执行

- **技能结束时的上下文规模（与 §1 成对记录）**  
  - 在本技能**全部执行完毕**时（已生成上述最终报告，或因清单/错误等**明确结束**本技能时），须再输出一行**结束快照**：若宿主可提供当前会话的 Token 用量、上下文占用比例或等价指标，输出：`[implement 技能结束] 上下文/Token：<数值或说明>`。  
  - 若环境无法读取，输出：`[implement 技能结束] 上下文规模：不可用`。  
  - 该结束快照应出现在最终面向用户的回复中，便于与 §1「阶段开始」快照对照，评估本会话实施阶段的上下文占用。  
  - **写入日志**：同时将上述结束占用**追加一行**到 **`${CLAUDE_WORKING_DIR}/.cache/context_cost.log`**：  
    `<ISO8601>|implement|skill_end|context|<上下文/Token 可读值或 unavailable>`

**注意**：本技能假定 `${FEATURE_DIR}/tasks.md` 中已有完整任务分解。若任务不完整或缺失，请先通过 `/tasks` 重新生成。

### 11. 记录本 skill 的运行日志信息

- 若存在 `${FEATURE_DIR}/.runs/env.sh`：`source` 后再执行 `omni-dsdd:runlog-record`
- 将 `start_time` 传入（如 `/omni-dsdd:runlog-record "2026-05-15 10:30:00"`）

## 参考

| 项 | 路径 |
|----|------|
| 前置检查（bash） | `${CLAUDE_PLUGIN_ROOT}/scripts/bash/check-prerequisites.sh` |
| 前置检查（pwsh） | `${CLAUDE_PLUGIN_ROOT}/scripts/powershell/check-prerequisites.ps1` |
| Workflow 门禁 | `${CLAUDE_PLUGIN_ROOT}/scripts/bash/workflow-gate.sh` |
| 本技能 | `${CLAUDE_PLUGIN_ROOT}/skills/implement/SKILL.md` |
