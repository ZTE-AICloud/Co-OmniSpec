# 阶段 0：环境初始化（主循环前置，对齐 design）

进入 Step 1（init + gate `0-init`）之前的就绪准备。本阶段只做环境变量检查/补全与脚本存在性校验，**不落盘、不跑 CI、不改代码**。

## 关键变量

| 变量 | 用途 |
|------|------|
| `CLAUDE_PLUGIN_ROOT` | 插件根 |
| `CLAUDE_WORKING_DIR` | 工程路径 / Git 工作区 |

## Step 0.1 检查

```bash
test -n "${CLAUDE_PLUGIN_ROOT:-}" && test -d "${CLAUDE_PLUGIN_ROOT}"
test -n "${CLAUDE_WORKING_DIR:-}" && test -d "${CLAUDE_WORKING_DIR}"
```

## Step 0.2 补全

```bash
export CLAUDE_WORKING_DIR="$(pwd)"
```

## Step 0.3 校验

```bash
test -f "${CLAUDE_PLUGIN_ROOT}/skills/local-sandbox-fix/scripts/python/local_sandbox_fix_harness.py"
test -f "${CLAUDE_PLUGIN_ROOT}/skills/local-sandbox-fix/scripts/bash/local-sandbox-fix-init-harness.sh"
```

## Step 0.4 — FEATURE_DIR 解析（自动从记录文件获取）

`FEATURE_DIR` 由 harness `init` 自动解析，无需手工推断；可选显式 `--feature-dir` 覆盖。解析优先级（`omnispec_state.resolve_feature_dir`）：

1. 显式 `--feature-dir`（命令行）
2. 环境变量 `OMNISPEC_FEATURE_DIR` / `FEATURE_DIR`
3. `.active-feature`（工作区当前活跃特性标记）
4. 最新 `changes/*/.runs/.omnispec-state.json`（按 mtime）
5. prerequisites 探测

所有候选须落在 `<CLAUDE_WORKING_DIR>/changes/` 下且 `.runs/` 存在。解析不到 → init 报错（`FEATURE_DIR 无法从记录文件解析`）。也可沿用 design 的解析器（结果一致）：

```bash
eval "$(bash "${CLAUDE_PLUGIN_ROOT}/skills/design/scripts/bash/design-resolve-context.sh" \
  --plugin-root "${CLAUDE_PLUGIN_ROOT}" \
  --working-dir "${CLAUDE_WORKING_DIR}" \
  ${FEATURE_DIR:+--feature-dir "$FEATURE_DIR"} \
  --export)" 2>/dev/null || true
[[ -f "${FEATURE_DIR}/.runs/env.sh" ]] && source "${FEATURE_DIR}/.runs/env.sh"
```

## Step 0.5 — devops_config.yaml 存在性预检（决定是否进入主循环）

业务配置文件 `devops_config.yaml`（= `${CLAUDE_WORKING_DIR}/devops_config.yaml`）为**可选**配置，其存在性决定整个 skill 是否继续：

```bash
test -f "${CLAUDE_WORKING_DIR}/devops_config.yaml"
```

- **存在** → 继续进入 Step 1：gate `0-init` 内 cp 到 `${DEVOPS_DST}` → 主循环，后续跑 CI / 修码 / code-review。
- **不存在** → gate `0-init`（`next_action=skip`）**直接以 `status=success`（skipped）结束整个 skill**：不进入主循环、不跑 CI、不修码、不做 code-review，退出码 = 0。**不得**报错、**不得**询问、**不得**构造空 yaml。

> 该「存在性预判 + cp / 缺失即跳过」语义由 Step 1 的 gate `0-init` 承担（`_prepare_devops_config` + `_skip_devops_missing` → `cmd_finalize` 成功收尾）；此处为编排层面的预判。

## 完成后

进入 [Step 1 — init + gate `0-init`](../../SKILL.md)（详见 SKILL.md「Step 1」）。
