# 环境变量（执行 init 前）

> 对应 SKILL.md 步骤 1

## 步骤 1.1 检查变量是否已存在

```bash
test -n "${CLAUDE_PLUGIN_ROOT:-}" && test -d "${CLAUDE_PLUGIN_ROOT}"
test -n "${CLAUDE_WORKING_DIR:-}" && test -d "${CLAUDE_WORKING_DIR}"
```

两项均通过 → 进入步骤 2。任一项失败 → 步骤 1.2。

## 步骤 1.2 补全缺失变量（仅 Agent 层执行一次）

**`CLAUDE_PLUGIN_ROOT`**

1. 若已注入且目录存在：沿用。
2. 若仍缺失（须验证 `${路径}/scripts/bash/init_omni_infra.sh` 存在）：Skill 上下文插件根 → 在 `${CLAUDE_WORKING_DIR}` 或其上级查找 `.claude-plugin/plugin.json`；
3. `export CLAUDE_PLUGIN_ROOT="<绝对路径>"`

**`CLAUDE_WORKING_DIR`**

1. 若已注入且目录存在：沿用。
2. 若缺失：`export CLAUDE_WORKING_DIR="$(pwd)"`（**不用** `git rev-parse --show-toplevel`）

## 完成判据

- `CLAUDE_PLUGIN_ROOT` 已存在且为有效目录
- `CLAUDE_WORKING_DIR` 已存在且为有效目录
