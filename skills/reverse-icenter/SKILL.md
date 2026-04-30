---
name: reverse-icenter
description: iCenter 知识反构（拉取页面→架构关联→按 target 提取知识）的编排Skill. 当 reverse 的 --source 为 icenter 时触发.
user-invokable: false
---

# iCenter 知识反构 Skill（拉取 + 关联 + 提取）

## 概览（职责与输入输出）

- **职责**：按阶段编排，从 iCenter 拉取页面并完成架构-文档关联，然后按 `--target` 提取并落盘以下一种或多种知识产物：
  - `requirements`
  - `system-contexts`
  - `scenarios`
  - `logical-architectures`
- **输入前提**：
  - 用户通过 `reverse --source icenter ...`；
  - `--page-root` **必须**由用户提供（支持英文逗号分隔多个 URL）；
  - `--target` 未指定时，必须默认使用 `all`（不再二次询问用户）。
- **输出产物**：
  - iCenter 缓存目录：`{REPO_ROOT}/.cache/icenter/`
    - `page_ids.json`
    - `page/*.md`
    - `architecture_doc_links/` 文件目录
    - 状态文件：`.cache-status.json`
  - 文档目录：`{REPO_ROOT}/omni-doc/specs/{target}/`


## Python 虚拟环境与依赖（执行前置）

- **适用范围**：本 Skill 涉及的 `./references/scripts/` 脚本（拉取页面、架构关联、提取前置处理）。
- **依赖文件**：`./references/scripts/requirement-icenter.txt`
- **约束**：执行本 Skill 的任何阶段脚本前，必须先完成以下 venv 初始化与依赖安装（避免污染全局 Python 环境）。

在 `{REPO_ROOT}` 下执行（Linux/macOS Bash）：

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r ./references/scripts/requirement-icenter.txt
```

在 `{REPO_ROOT}` 下执行（Windows PowerShell）：

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r .\references\scripts\requirement-icenter.txt
```

> 注意：如果你的环境里 `python` 指向的不是目标版本，请改用 `python3`；若在受限网络环境中安装失败，应按组织规范配置 pip 源/代理后再重试。

## 与 `reverse` 命令的关系

- `reverse` 负责：
  - 解析 `$ARGUMENTS`，统一处理 `--source icenter`、`--target`、`--page-root` 等参数；
  - 获取 `REPO_ROOT` 与全局缓存目录；
- 本 Skill 负责：
  - 严格按阶段顺序驱动 iCenter 反构；
  - 每阶段按缓存状态决定跳过/执行；
  - 将详细执行规则`references/stages/*.md`，并要求执行时逐条遵守。

## 阶段总览

本 Skill 按以下阶段编排，阶段详细说明见本 Skill 目录下 `references/stages/`：

0. **阶段0：缓存状态检查**
1. **阶段1：获取子页面 ID**
2. **阶段2：下载文档到本地**
3. **阶段3：架构节点与页面匹配**
4. **阶段4：提取知识（按 target 分支）**

### 阶段0：缓存状态检查
- 检查{REPO_ROOT}/.cache/icenter/.cache-status.json是否存在
- 不存在则按照如下格式创建文件
**缓存状态文件格式**：
```json
{
  "fetch_page_ids": {
    "confirmed": false
  },
  "fetch_pages_local": {
    "confirmed": false
  },
  "architecture_linking": {
    "confirmed": false
  },
  "extract_requirements": {
    "confirmed": false
  },
  "extract_scenarios": {
    "confirmed": false
  },
  "extract_system_contexts": {
    "confirmed": false
  },
  "extract_logical_architectures": {
    "confirmed": false
  }
}
```

## 阶段1：获取子页面 ID

- **阶段说明来源**：本 Skill 内 [references/stages/01-fetch-page-ids.md](references/stages/01-fetch-page-ids.md)
- **目标**：从 iCenter 获取所有子页面 ID 并写入缓存文件。
- **关键输出**：`{REPO_ROOT}/.cache/icenter/page_ids.json`

## 阶段2：下载文档到本地

- **阶段说明来源**：本 Skill 内 [references/stages/02-fetch-pages-local.md](references/stages/02-fetch-pages-local.md)
- **目标**：根据 `page_ids.json` 批量下载页面 Markdown 到本地缓存目录。
- **关键输出**：`{REPO_ROOT}/.cache/icenter/page/*.md`

## 阶段3：架构节点与页面匹配

- **阶段说明来源**：本 Skill 内 [references/stages/03-icenter-doc-architecture-linking.md](references/stages/03-icenter-doc-architecture-linking.md)
- **目标**：完成架构-文档关联，产出架构节点对应的页面匹配结果。
- **关键输出**：`{REPO_ROOT}/.cache/icenter/architecture_doc_links/`文件目录

## 阶段4：提取知识（按 target 分支）

### 阶段4.1：提取需求(target=all或requirements)
- **目标**：提取知识并保存。
- **操作**：读取文件并提取知识。
- **输出**：`{REPO_ROOT}/omni-doc/specs/requirements/`。
- **阶段文件**：`.claude/commands/reverse.icenter/stages/04a-extract-knowledge.md`

### 阶段4.2：提取场景(target=all或scenarios)
- **目标**：提取知识并保存。
- **操作**：读取文件并提取知识。
- **输出**：`{REPO_ROOT}/omni-doc/specs/scenarios/`。
- **阶段文件**：`.claude/commands/reverse.icenter/stages/04a-extract-knowledge.md`

### 阶段4.3：提取系统上下文(target=all或system-contexts)
- **目标**：提取知识并保存。
- **操作**：读取文件并提取知识。
- **输出**：`{REPO_ROOT}/omni-doc/specs/system-contexts/`。
- **阶段文件**：`.claude/commands/reverse.icenter/stages/04b-extract-whole-knowledge.md`

### 阶段4.4：提取逻辑架构(target=all或logical-architectures)
- **目标**：提取知识并保存。
- **操作**：读取文件并提取知识。
- **输出**：`{REPO_ROOT}/omni-doc/specs/logical-architectures/`。
- **阶段文件**：`.claude/commands/reverse.icenter/stages/04b-extract-whole-knowledge.md`

## 参考文档（本 Skill 内）

- 阶段 1：[references/stages/01-fetch-page-ids.md](references/stages/01-fetch-page-ids.md)
- 阶段 2：[references/stages/02-fetch-pages-local.md](references/stages/02-fetch-pages-local.md)
- 阶段 3：[references/stages/03-icenter-doc-architecture-linking.md](references/stages/03-icenter-doc-architecture-linking.md)
- 阶段 4.1、4.2：[references/stages/04a-extract-knowledge.md](references/stages/04a-extract-knowledge.md)
- 阶段 4.3、4.4：[references/stages/04b-extract-knowledge.md](references/stages/04b-extract-knowledge.md)

AI Agent 在执行本 Skill 时，必须逐一读取上述阶段文档，并严格按照其中描述的约束与脚本调用方式执行。

