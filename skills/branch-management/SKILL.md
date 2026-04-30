---
name: branch-management
description: 通用分支与特性目录管理Skill. 当需要基于需求编号创建或复用特性分支和目录时触发.
user-invokable: false
---

# 分支与特性目录管理Skill（branch-management）

## 概览（职责与输入输出）

- **职责**：统一管理基于“需求编号”的分支与特性目录创建/复用流程：
  - 解析并验证需求编号（强制要求）
  - 根据需求编号检查当前分支是否匹配
  - 必要时创建新的特性分支与目录
- **典型调用方**：
  - `reverse-on-demand`（按需反构阶段1）
  - 其他基于需求编号驱动的命令/Skill
- **输出变量**：
  - `REQUIREMENT_ID`：需求编号
  - `BRANCH_MATCHES_REQUIREMENT`：布尔值，当前分支是否匹配需求编号
  - `BRANCH_NAME`：最终选定/创建的特性分支名称
  - `FEATURE_DIR`：特性目录绝对路径（例如 `<REPO_ROOT>/changes/<short-name>/`）
  - `TARGET_FILE`：目标文件绝对路径（可选；本流程下允许为空）
  - `REPO_ROOT`：仓库根目录（在调用本 Skill 前由调用方提供或通过前置步骤获取）

> 本 Skill 将分支与特性目录管理流程封装为可复用 Skill，可被 reverse-on-demand 等命令/Skill 调用。

## 输入与前置条件

- **输入**：
  - 用户输入文本（包含 `$ARGUMENTS` 中的内容），其中需要有“需求编号”信息；
  - 调用方可选择是否需要本 Skill 帮助获取 `REPO_ROOT`。
- **前置条件**：
  - 需求编号是强制要求：如果未提供需求编号，本 Skill 必须给出中文错误并终止后续流程。

## 核心步骤（对应原命令文档）

### 步骤0（可选）：获取环境信息（REPO_ROOT）

- 何时执行：
  - 若调用方未明确提供 `REPO_ROOT`，且后续步骤需要使用绝对路径；
  - 若调用方已提供 `REPO_ROOT`，可以跳过。
- 操作（跨平台脚本）：
  - Linux: `bash scripts/bash/check-prerequisites.sh --paths-only --json`
  - Windows: `pwsh scripts/powershell/check-prerequisites.ps1 --paths-only --json`
  - 从 JSON 输出中解析 `REPO_ROOT`（必须为绝对路径）。

### 步骤1：解析与验证需求编号

- **解析**：
  - 从用户输入中解析“需求编号”，支持多种格式：
    - 章节形式：`## 需求编号` + 下一行 ID（如 `TCF-123456`）
    - 行内形式：`需求编号: TCF-123456`、`MR: TCF-123456`、`Requirement ID: BUG-123456`、`PR: TCF-123456` 等。
- **验证**：
  - `REQUIREMENT_ID` 不为 `null`，不为空字符串，去除首尾空白后非空；
  - 若验证失败：
    - 用中文输出明确错误说明（需求编号是强制要求，并给出格式示例）；
    - 终止后续分支管理流程。

### 步骤2：检查当前分支是否匹配需求编号

- 逻辑：
  - 当前分支名以 `<REQUIREMENT_ID>-` 为前缀（不区分大小写）视为匹配；
  - 示例：`TCF-123456-feature-name`、`tcf-123456-fix-bug` 等。
- 输出：
  - `BRANCH_MATCHES_REQUIREMENT = true/false`
  - 若为 true：默认复用当前分支。

### 步骤3：生成分支简短名称（仅在需要创建新分支时）

- 前提：`BRANCH_MATCHES_REQUIREMENT == false`
- 逻辑：
  - 从功能描述中提取 2–4 个关键词，组合成简短英文/拼音短语（如 `user-auth`、`fix-payment-bug`）；
  - 分支名格式：`<REQUIREMENT_ID>-<short-name>`（如 `TCF-123456-user-auth`）。
  - 特性目录短名格式：`<short-name>`（如 `rdma-sharepf-extend`）。

### 步骤4：创建或复用特性分支与目录

- 首先检查是否已有可复用的分支/目录（按原文档优先级）：
  1. `BRANCH_MATCHES_REQUIREMENT == true`：复用当前分支，查找匹配目录；
  2. 当前分支已是特性分支且目录存在：直接复用；
  3. 搜索 `NNN-` 或需求编号前缀的目录并选择合适的一个。
- 若上述检查都未命中：
  - 调用创建特性分支脚本（仓库根目录下）：
    - Linux: `scripts/bash/create-new-feature.sh --json --branch-name "<REQUIREMENT_ID>-<short-name>" --feature-dir "changes/<short-name>"`
    - Windows: `scripts/powershell/create-new-feature.ps1 --json --branch-name "<REQUIREMENT_ID>-<short-name>" --feature-dir "changes/<short-name>"`
  - 从脚本 JSON 输出中解析得到：
    - `BRANCH_NAME`
    - `TARGET_FILE`（可为空；不再要求由本流程创建 `spec.md`）
    - `FEATURE_DIR`（特性目录绝对路径）
  - `FEATURE_DIR` 以脚本返回值为准；不得依赖 `TARGET_FILE` 反推目录路径。
  - 🔴 强制校验：`FEATURE_DIR` 必须匹配 `<REPO_ROOT>/changes/<short-name>/`；若不匹配，立即报错并终止流程。

### 步骤5：输出变量与终止条件

- 成功时，本 Skill 向调用方返回（或在上下文中设置）以下变量：
  - `REQUIREMENT_ID`
  - `BRANCH_MATCHES_REQUIREMENT`
  - `BRANCH_NAME`
  - `FEATURE_DIR`
  - `TARGET_FILE`（若适用）
  - `REPO_ROOT`（若在步骤0中获取）
- 终止条件：
  - 需求编号验证失败；
  - 其他脚本错误或路径解析错误（需用中文说明原因，并终止后续依赖步骤）。

## 参考说明

本 Skill 的详细逻辑已整合于上文步骤中；脚本参数、JSON 输出格式等以 `create-new-feature` 与 `check-prerequisites` 脚本的文档为准。执行本 Skill 时，AI Agent 应按上述步骤完成解析、校验与分支/目录创建或复用。

