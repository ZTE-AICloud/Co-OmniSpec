---
name: reverse-shared
description: 反构流程共用的模板与说明文档库。当其他 reverse-* 技能（如 reverse-interfaces、reverse-rules 等）需要在阶段文档中引用确认模板、配置摘要或规则注入分析说明时，自动加载本技能提供的 references/ 内容。本技能不作为独立执行入口，仅作为共享资源被其他技能引用。
user-invocable: false
allowed-tools: Read, Grep, Glob, Bash
when_to_use: 当其他 reverse-* 技能在阶段文档中需要引用确认模板、配置摘要说明、用法变更说明或规则注入分析时自动加载。
---

# 反构共用资源 Skill（reverse-shared）

## 概览

本 Skill 存放被多个反构 Skill 共用的文档与模板，不作为独立执行入口。其他 reverse-* skill 在需要时可引用本目录下 `references/` 中的文件。


## 路径变量约定（执行前必读）

本 Skill 阶段文档中引用了以下路径变量，执行阶段命令前须先解析：

- `${CLAUDE_PLUGIN_ROOT}`：omni-reverse 插件安装根（运行期注入；指向本 skill 内专属脚本，如 `${CLAUDE_PLUGIN_ROOT}/skills/reverse-<X>/scripts/`）。
- `${DSDD}`：共享插件 omni-dsdd 安装根（含共享 `scripts/` 与 `omni-infra/`）。**首次使用前必须解析**：
  ```bash
  DSDD="$(bash "${CLAUDE_PLUGIN_ROOT}/scripts/resolve-dsdd-root.sh")" || { echo "缺少 omni-dsdd，中止"; exit 1; }
  ```
  解析器优先用 `${CLAUDE_PLUGIN_ROOT}/../omni-dsdd`，回退到脚本相对位置推算；失败则提示需与 omni-reverse 同 marketplace 安装 omni-dsdd。
- `{REPO_ROOT}` / `${CLAUDE_WORKING_DIR}`：被反构的代码工程根（运行期产物，与插件位置无关）。
- `${CLAUDE_SKILL_DIR}`：本 skill 自身目录（指向本 skill 内 `references/scripts/` 等自包含资源）。

> 说明：`${DSDD}` 不是运行期自动注入的变量，必须经 `resolve-dsdd-root.sh` 取值后方可使用。

## 本 Skill 内 references 内容

- **确认步骤模板**：[references/confirmation-template.md](references/confirmation-template.md) — 提供用户确认机制的统一模板，包含阶段结束确认和过程中确认的标准化流程
- **简化配置摘要说明**：[references/simplified-config-summary.md](references/simplified-config-summary.md) — 简化版配置文件格式的使用说明，包含配置解析逻辑和示例
- **用法变更说明**：[references/usage-changes.md](references/usage-changes.md) — 交互模式参数的使用变化说明，包含新增参数格式和向后兼容性说明
- **接口规则注入分析**：[references/interface-rules-injection-analysis.md](references/interface-rules-injection-analysis.md) — 接口规则和约束的用户注入机制分析，包含交互式配置和配置文件注入两种方式

## 使用方式

- 由 **reverse-interfaces**、**reverse-rules** 等 skill 在阶段文档中按需引用上述文件路径（相对本 repo 的 skill 根或安装后的路径）。
- 不通过 `reverse --target` 直接触发；无独立阶段或 todo。

## 使用示例

### 在其他技能中引用本技能

在其他 reverse-* skill 的阶段文档中，可以按以下方式引用本技能的文件：

```markdown
## 确认步骤
按照 `本 Skill（reverse-shared）内 references/confirmation-template.md` 中的"阶段结束确认模板"执行
```

### 引用路径格式

引用时使用相对于本 repo 的路径：
- `{REPO_ROOT}/.claude/skills/reverse-shared/references/confirmation-template.md`
