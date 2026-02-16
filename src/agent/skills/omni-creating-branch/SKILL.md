---
name: omni-creating-branch
description: 创建特性分支并获取 BRANCH_NAME、SPEC_FILE、FEATURE_DIR。按功能描述生成短名，运行 skill 内脚本，解析 JSON。用于 /omni.specify 或单独创建特性分支。
---

# omni-creating-branch

## 步骤

1. **生成分支短名**（2–4 词）：从功能描述提取关键词，动-名词格式（如 `add-user-auth`、`fix-payment-timeout`），保留技术缩写（OAuth2、API、JWT）。不含目录路径。

2. **执行脚本**（仓库根或任意目录，脚本自解析根）：
   - Linux/macOS: `bash {AGENT_DIR}/skills/omni-create-branch/scripts/bash/create-new-feature.sh --json --short-name "<短名>"`
   - Windows: `pwsh -File {AGENT_DIR}/skills/omni-create-branch/scripts/powershell/create-new-feature.ps1 --json --short-name "<短名>"`
   - 必填 `--short-name`，仅执行一次。可选 `--number N`。

3. **解析输出**：JSON 取 `BRANCH_NAME`、`SPEC_FILE` 或 `change_file`（规范文件，用绝对路径）；`FEATURE_DIR` = 规范文件所在目录。非 JSON 则从输出行提取 `BRANCH_NAME:` 与规范文件路径。

4. **输出**：向调用方提供 `BRANCH_NAME`、`SPEC_FILE`（或 `change_file`）、`FEATURE_DIR`。
