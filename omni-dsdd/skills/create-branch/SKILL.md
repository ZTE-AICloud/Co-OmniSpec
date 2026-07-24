---
name: create-branch
description: 为功能开发准备工作环境——创建或复用 Git 分支与功能目录（changes/...），并初始化 spec.md 规格文档。当需要开始新功能开发、修复缺陷、创建分支、新建功能、切换分支、或切换到特定功能上下文时使用。
user-invocable: true
allowed-tools: Read, Bash(git, mkdir, test, python3), Write
---

# create-branch

## 适用场景

当需要为功能规格创建或复用工作上下文时使用本技能。目标是确定并返回：

- `BRANCH_NAME`
- `FEATURE_DIR`
- `SPEC_FILE`

本技能处理两类问题：

- 是否需要创建、切换或复用 Git 分支
- 是否需要创建、复用或推导 `changes/...` 功能目录

---

## 输入

从用户指令与上下文中解析两个驱动量；未出现则视为**未指定**：

| 输入 | 含义 | 视为已指定 |
|------|------|------------|
| `BRANCH_NAME` | Git 分支名 | 显式给出；或「在 `xxx` 分支」「使用当前分支」等可解析为单一分支名 |
| `FEATURE_DIR` | 功能目录，位于 `${CLAUDE_WORKING_DIR}/changes/` 下 | 显式路径 `changes/foo`、仅目录名 `foo`（补全为 `changes/foo`）、或等价表述 |

若两者都未指定，可根据 `description` 推导 `short_core`（英文动-名词核心），**编号与最终 `BRANCH_NAME` 必须由 Harness 分配**，不得由 Agent 臆造 `001`/`002`。

**上游 `specify` 步骤 1 预解析**：若用户通过 CLI 或 `export` 指定了 `FEATURE_DIR` / `BRANCH_NAME`（或二者之一并由预解析补全），`specify` 步骤 2 调用本技能时会**显式透传**二者，**禁止** `allocate`；目录已存在则 `resolve` + `checkout`，不存在则 `create-new-feature` 显式创建。同一变量 CLI 与 export 同时存在时，**以 CLI 参数为准**。本技能返回值是后续 skill 的**唯一真值源**。

---

## 环境初始化

本技能**所有**路径拼接与脚本调用，均依赖以下两个变量。后续步骤不得绕过它们自行推断路径。

| 变量 | 含义 | 用途 |
|------|------|------|
| `CLAUDE_PLUGIN_ROOT` | Omni 插件安装根目录（含 `skills/`、`scripts/`、`.claude-plugin/`） | 定位本技能及插件内脚本 |
| `CLAUDE_WORKING_DIR` | 用户当前工作区/目标工程根目录 | 定位 `changes/`、Git 操作、Harness 落盘 |

### Step 0.1 检查变量是否已存在

```bash
test -n "${CLAUDE_PLUGIN_ROOT:-}" && test -d "${CLAUDE_PLUGIN_ROOT}"
test -n "${CLAUDE_WORKING_DIR:-}" && test -d "${CLAUDE_WORKING_DIR}"
```

两项均通过 → 进入「执行顺序」Step 1。  
任一项失败 → 执行 Step 0.2。

### Step 0.2 补全缺失变量（仅 Agent 层执行一次）

**`CLAUDE_PLUGIN_ROOT`（插件路径）**

1. 若 Claude Code 已注入且目录存在：沿用。
2. 若仍缺失，按顺序降级（每项须验证 `${路径}/skills/create-branch/SKILL.md` 存在）：
   - 使用 Skill 加载上下文中的插件安装根目录；
   - 在已知的 `${CLAUDE_WORKING_DIR}` 或其上级查找含 `.claude-plugin/plugin.json` 的目录，取该目录为插件根（开发态内嵌插件）；
3. `export CLAUDE_PLUGIN_ROOT="<解析到的绝对路径>"`
4. 仍无法解析 → **终止**，提示用户安装/启用 omni 插件或手动 `export CLAUDE_PLUGIN_ROOT=...`

**`CLAUDE_WORKING_DIR`（工作区路径）**

1. 若已注入且目录存在：沿用。
2. 若缺失：
   - 无论 Git/非 Git：`export CLAUDE_WORKING_DIR="$(pwd)"`
3. 仍无法解析 → **终止**，提示切换到目标工程目录后重试。

### Step 0.3 校验（必须通过）

```bash
test -f "${CLAUDE_PLUGIN_ROOT}/skills/create-branch/scripts/python/create_branch_harness.py"
test -f "${CLAUDE_PLUGIN_ROOT}/skills/create-branch/scripts/bash/create-new-feature.sh"
test -f "${CLAUDE_PLUGIN_ROOT}/skills/create-branch/scripts/bash/create-branch-allocate.sh"
test -d "${CLAUDE_WORKING_DIR}"
mkdir -p "${CLAUDE_WORKING_DIR}/changes"
```

**Git 状态（供后续脚本 `--has-git` 使用，仅此步骤允许探测一次）：**

```bash
if git -C "${CLAUDE_WORKING_DIR}" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  export CREATE_BRANCH_HAS_GIT=true
else
  export CREATE_BRANCH_HAS_GIT=false
fi
```

✅ Checkpoint: `CLAUDE_PLUGIN_ROOT=...`, `CLAUDE_WORKING_DIR=...`, `CREATE_BRANCH_HAS_GIT=true|false`

### 路径拼接约定

- 插件内脚本（按类型分目录）：
  - `scripts/bash/` — `create-new-feature.sh`（组合入口）、`ensure-git-branch.sh`、`create-feature-dir.sh`、`create-branch-common.sh`
  - `scripts/python/` — Harness（`create_branch_harness.py`）
  - `scripts/powershell/` — `create-new-feature.ps1`、`Ensure-GitBranch.ps1`、`Create-FeatureDir.ps1`、`Create-BranchCommon.ps1`、`create-branch-allocate.ps1`、`create-branch-record.ps1`
- 工作区数据：`${CLAUDE_WORKING_DIR}/changes/...`
- 调用脚本时**必须**传入 `--working-dir "${CLAUDE_WORKING_DIR}"`；调用封装脚本时**必须**传入 `--plugin-root "${CLAUDE_PLUGIN_ROOT}"`
- **禁止**在业务脚本内用 `pwd`、`git rev-parse`、`__file__`、`SCRIPT_DIR` 推断插件根或工作区根

---

## Harness 执行契约（分支名真值）

**目标**：`BRANCH_NAME`（尤其 `001-` 这类三位序号前缀）在同一次需求、重试、断点恢复时保持稳定；与 `specify` 的 `.runs/paths.json` 一致，由 Harness 落盘后再透传。

| 文件 | 作用 |
|------|------|
| `${CLAUDE_WORKING_DIR}/changes/.branch-naming-pending.json` | 待创建特性的幂等分配缓存 |
| `${CLAUDE_WORKING_DIR}/changes/<dir>/.runs/branch-naming.json` | 已创建特性的分支命名真值 |

### 何时必须调用 Harness

| 场景 | 命令 |
|------|------|
| 新建且需分配/确认 `BRANCH_NAME`（含序号或 `feature/`/`fix/`/`chore/`） | `allocate` |
| `create-new-feature` 成功创建目录/分支后 | `record` |
| 复用已有 `FEATURE_DIR`、需读取稳定分支名 | `resolve` |
| 输出给调用方前自检 | `gate` |

### 命令（Step 0 完成后执行）

```bash
# 1) 分配稳定分支名（JSON 一行）
python3 "${CLAUDE_PLUGIN_ROOT}/skills/create-branch/scripts/python/create_branch_harness.py" \
  --working-dir "${CLAUDE_WORKING_DIR}" \
  allocate \
  --description "<功能描述>" \
  --short-core "<英文核心，如 thread-table-aging>"

# 显式分支名：不重新算号，仅解析结构
python3 "${CLAUDE_PLUGIN_ROOT}/skills/create-branch/scripts/python/create_branch_harness.py" \
  --working-dir "${CLAUDE_WORKING_DIR}" \
  allocate \
  --branch-name "001-thread-table-aging"

# 2) 创建成功后落盘真值
python3 "${CLAUDE_PLUGIN_ROOT}/skills/create-branch/scripts/python/create_branch_harness.py" \
  --working-dir "${CLAUDE_WORKING_DIR}" \
  record \
  --feature-dir "${CLAUDE_WORKING_DIR}/changes/<dir>" \
  --branch-name "<BRANCH_NAME>" \
  --idempotency-key "<allocate 返回的 idempotency_key>"

# 3) 复用目录时解析
python3 "${CLAUDE_PLUGIN_ROOT}/skills/create-branch/scripts/python/create_branch_harness.py" \
  resolve \
  --feature-dir "${CLAUDE_WORKING_DIR}/changes/<dir>"
```

Harness 封装脚本（与上文 `python3` 直调等价；须传 `--plugin-root`、`--working-dir`；参数风格与 bash 相同）：

- Linux：`scripts/bash/create-branch-allocate.sh`、`create-branch-record.sh`
- Windows：`scripts/powershell/create-branch-allocate.ps1`、`create-branch-record.ps1`

### 编号分配规则（由 Harness 实现，Agent 禁止手算）

1. **业务前缀**（描述含 `feature:` / `fix:` / `chore:` 等通用约定）：`branch_name = {业务前缀}[-{short_core}]`，不追加 `001-` 通用序号。
2. **通用序号**（无业务前缀）：扫描 `${CLAUDE_WORKING_DIR}/changes/*` 与本地 `git branch` 的 leading 数字，取 `max+1` 格式化为三位 `feature_num`。
3. **幂等**：相同 `description` + `short_core` 在 pending 未 `record` 前多次 `allocate`，必须返回**同一** `feature_num` / `branch_name`。
4. **显式** `--branch-name`：Harness 只解析，不重新分配序号。

---

## 执行顺序

严格按以下顺序执行，不要跳步：

0. 完成「环境初始化」Step 0.1–0.3（若变量未就绪则不得继续）。
1. 解析用户是否显式给出了 `BRANCH_NAME`、`FEATURE_DIR`（含上游 `specify` 步骤 1 预解析后透传的值）。
2. 先规范化 `FEATURE_DIR`（均相对 `${CLAUDE_WORKING_DIR}`）：
   - 若是绝对路径，直接使用。
   - 若是 `changes/foo`，规范为 `${CLAUDE_WORKING_DIR}/changes/foo`。
   - 若只是目录名 `foo`，规范为 `${CLAUDE_WORKING_DIR}/changes/foo`。
3. 只有在完成规范化后，才允许检查目录是否存在。
4. 若目标分支和目标目录都已存在，并且当前场景是复用：对已有目录执行 `resolve`，以 `branch-naming.json` / `paths.json` 为准输出 `BRANCH_NAME`；**不得**再调用 `allocate` 或 `create-new-feature` 创建同名/递增目录。
5. 若需**新建**且 `BRANCH_NAME` 未显式给定：先由 Agent 从描述提炼 `short_core`，再调用 Harness `allocate`（禁止 Agent 手填 `001`/`002`）；若 `allocate` 返回 `source=existing_feature_dir`，视为复用，跳至 `resolve`/`record`（已 record 则仅 `gate`）。
6. 只要**确实需要**创建分支或目录，才走 `create-new-feature`；目录已存在时脚本会短路为仅 `checkout`；成功后必须 Harness `record`（仅首次创建时）。
7. 输出前对已有目录执行 `gate`（可选，新建后建议执行）。

---

## 防重复创建（路径改造后高发）

下列情况**只复用、不新建**第二套分支/目录：

| 场景 | 正确做法 |
|------|----------|
| `${CLAUDE_WORKING_DIR}/changes/<dir>` 已存在且含 `.runs/branch-naming.json` 或 `spec.md` | `resolve` + 仅 `git checkout`（`create-new-feature` 会自动短路） |
| 上游（deep workflow / reverse-on-demand）已给出 `BRANCH_NAME`、`FEATURE_DIR` | 显式传入；**禁止**再次 `allocate` 递增 `001`→`002` |
| 同一次需求内第二次调用本技能 | 必须先 `resolve` 已有目录；仅缺 Git 才 `ensure-git-branch` |
| `allocate` 算出的 `branch_name` 在 `changes/` 下已有同名目录 | Harness 返回 `source=existing_feature_dir`，勿 `record` 到新目录 |

**根因说明（改造前少见）**：旧逻辑用 `git rev-parse --show-toplevel` 作工作区，改造后用 **`CLAUDE_WORKING_DIR`（常为 `pwd`）**。若两次调用工作区根不一致，会在仓库根与子目录各生成一套 `changes/00N-*`，表现为「创建了两次分支和文件夹」。

## 禁止事项

- 不要为 Git 或目录操作而 `cd` 到 `${CLAUDE_WORKING_DIR}`（会污染调用方工作目录）；应使用 `git -C "${CLAUDE_WORKING_DIR}"` 与绝对路径。
- 不要在规范化前直接检查裸目录名。
- **禁止** Agent 手工扫描 `changes/*` 或 `git branch` 推算序号；序号只许 Harness `allocate` 产出。
- 不要在技能侧手工创建目录后再把状态“补齐”给脚本。
- 不要在“应复用”的场景里再次创建同名目录或同名分支。
- 禁止在未 `record` 的情况下更换已 `allocate` 的 `feature_num`。
- **禁止**在 `create-new-feature`、Harness 等业务脚本内自行推断插件根或工作区根。

---

## 生成 short_core 与调用 allocate

Agent 只负责语义层 **short_core**（或确认用户显式 `BRANCH_NAME`）；**最终带编号的 `BRANCH_NAME` 一律来自 Harness**。

- **复用已有分支/目录**：不调 `allocate`；目录存在时 `resolve` 得 `BRANCH_NAME`。
- **显式命名**：`allocate --branch-name "<用户完整名称>"`。
- **基于描述新建**：`allocate --description "..." --short-core "..."` → 取 `feature_dir_basename` 传入 `create-new-feature`。
- **含 `feature:`/`fix:`/`chore:`**：仍先 `allocate`；Harness 用业务前缀组装。

---

## 决策流程

在 Step 0 完成后，根据 `CREATE_BRANCH_HAS_GIT` 与 `BRANCH_NAME` × `FEATURE_DIR` 是否指定走分支（逻辑同前，路径均基于 `${CLAUDE_WORKING_DIR}`）。

非 Git 场景（`CREATE_BRANCH_HAS_GIT=false`）仅维护 `${CLAUDE_WORKING_DIR}/changes/<dir>/`；不执行 Git 分支操作。

---

## 脚本调用

### 脚本职责拆分

| 脚本 | 职责 |
|------|------|
| `ensure-git-branch.sh` / `Ensure-GitBranch.ps1` | 仅 Git：checkout / track / 新建分支；设置 `SPECIFY_FEATURE` |
| `create-feature-dir.sh` / `Create-FeatureDir.ps1` | 仅目录：解析路径、`mkdir`、`changes/`；输出 JSON |
| `create-new-feature.sh` / `create-new-feature.ps1` | **组合入口**（默认）：有分支名时先调 Git 脚本，再调目录脚本；行为与拆分前一致 |

使用原则：

- 分支与目录均已存在且仅复用 → **不调用**脚本。
- 涉及创建分支或目录 → 调用脚本；编号由 Harness `allocate` 产出。
- 仅缺分支 → 只调 `ensure-git-branch`；仅缺目录 → 只调 `create-feature-dir`；两者都缺 → 调 `create-new-feature`（或依次调两个子脚本）。
- `spec.md` 正文由下游 `specify` 渲染；目录脚本仅约定 `${FEATURE_DIR}/spec.md` 路径。

### 组合入口（推荐，与拆分前相同）

| 环境 | 命令 |
|------|------|
| Linux / macOS / Git Bash | `bash "${CLAUDE_PLUGIN_ROOT}/skills/create-branch/scripts/bash/create-new-feature.sh" --json --working-dir "${CLAUDE_WORKING_DIR}" --has-git "${CREATE_BRANCH_HAS_GIT}" --branch-name "<BRANCH_NAME>" --feature-dir "<DIR_NAME>"` |
| Windows（PowerShell） | `pwsh "${CLAUDE_PLUGIN_ROOT}/skills/create-branch/scripts/powershell/create-new-feature.ps1" -Json -WorkingDir "${CLAUDE_WORKING_DIR}" -HasGit "${CREATE_BRANCH_HAS_GIT}" -BranchName "<BRANCH_NAME>" -FeatureDir "<DIR_NAME>"` |

### 仅创建 Git 分支

```bash
bash "${CLAUDE_PLUGIN_ROOT}/skills/create-branch/scripts/bash/ensure-git-branch.sh" \
  --working-dir "${CLAUDE_WORKING_DIR}" \
  --has-git "${CREATE_BRANCH_HAS_GIT}" \
  --branch-name "<BRANCH_NAME>"
```

### 仅创建功能目录（输出 JSON）

```bash
bash "${CLAUDE_PLUGIN_ROOT}/skills/create-branch/scripts/bash/create-feature-dir.sh" \
  --json \
  --working-dir "${CLAUDE_WORKING_DIR}" \
  --has-git "${CREATE_BRANCH_HAS_GIT}" \
  --feature-dir "<DIR_NAME>"
```

说明：

- `--has-git` 使用 Step 0.3 的 `CREATE_BRANCH_HAS_GIT`。
- `FEATURE_DIR` 优先传目录名（如 `001-foo`），会补到 `${CLAUDE_WORKING_DIR}/changes/...`。
- 仅提供 `FEATURE_DIR` 时只调 `create-feature-dir`，不执行 Git。

### 解析输出

- `BRANCH_NAME`
- `SPEC_FILE`：`${FEATURE_DIR}/spec.md`
- `FEATURE_DIR`：绝对路径（位于 `${CLAUDE_WORKING_DIR}/changes/...`）
- `HAS_GIT`

---

## 询问模板

**询问 A**（Git，无 `BRANCH_NAME`，已有或刚建 `FEATURE_DIR`）：

```text
已关联功能目录 <FEATURE_DIR>，请选择分支操作：
  A. 复用已有分支（请说明分支名，或“使用当前分支”）
  B. 新建特性分支（建议名：<建议 BRANCH_NAME>）
```

**询问 B**（Git，两者均未指定，已生成目录或建议名）：

```text
已准备功能目录 <FEATURE_DIR>，请选择分支操作：
  A. 复用某个已有分支（请说明分支名）
  B. 新建特性分支（建议名：<建议 BRANCH_NAME>）
```

---

## 输出

| 变量 | 说明 |
|------|------|
| `BRANCH_NAME` | 最终采用的分支名 |
| `FEATURE_DIR` | `${CLAUDE_WORKING_DIR}/changes/<dir>` 绝对路径 |
| `SPEC_FILE` | `${FEATURE_DIR}/spec.md` |

将以上三个值统一传给调用方技能，例如 `specify`。
