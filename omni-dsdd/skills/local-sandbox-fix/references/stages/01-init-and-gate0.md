# 阶段 1：init + gate 0-init

主循环（Step 2）的地基。本步**不碰业务代码、不跑 CI**：init 只建地基（目录/路径/状态），gate 0-init 做就绪校验 + **文件初始化**（devops_config 的 cp / 缺失 skip）。

## init

在 `${FEATURE_DIR}/.runs/local-sandbox-fix/`（= `HARNESS_DIR`）下创建 `steps/`、`history/` 子目录，落盘三个产物 ——

- `paths.json`：路径真值源（`plugin_root`、`working_dir`、`run_ci_script`、`devops_src` 等绝对路径）
- `env.sh`：供后续步骤 `source` 后导出绝对路径（对应硬约束「所有路径从 env.sh 获取」）
- `run-manifest.json`：断点续跑（resume）唯一信任的状态源，防 Agent 跳步

## source env.sh

导出 `HARNESS_DIR`、`${DEVOPS_DST}` 等绝对路径变量，供后续 gate 命令使用。

## gate 0-init — 就绪校验 + 文件初始化

- **就绪校验**：`paths.json` 关键路径为绝对路径、`run_ci_script` 文件存在、三件产物均已落盘。
- **文件初始化**：处理业务配置 `devops_config.yaml`（**可选**，源 = `${DEVOPS_SRC}` = `${CLAUDE_WORKING_DIR}/devops_config.yaml`）——
  - **存在** → cp 到 `${DEVOPS_DST}`，`phase=loop`，进入主循环跑 CI / 修码 / code-review。
  - **不存在** → 视为「该工程无本地 CI 配置」，`next_action=skip` → 直接以 `status=success`（skipped）结束整个 skill：不进入主循环、不跑 CI、不修码、不做 code-review。**不得**报错、**不得**询问、**不得**构造空 yaml 试图继续。退出码 = 0。
- 任一项不满足则 `gate_exit≠0`，主循环不得开始。

## 执行

```bash
bash "${CLAUDE_PLUGIN_ROOT}/skills/local-sandbox-fix/scripts/bash/local-sandbox-fix-init-harness.sh" \
  --plugin-root "${CLAUDE_PLUGIN_ROOT}" \
  --working-dir "${CLAUDE_WORKING_DIR}" \
  --feature-dir "${FEATURE_DIR}"

source "${FEATURE_DIR}/.runs/local-sandbox-fix/env.sh"

bash "${CLAUDE_PLUGIN_ROOT}/skills/local-sandbox-fix/scripts/bash/local-sandbox-fix-gate.sh" \
  --harness-dir "${HARNESS_DIR}" \
  --step "0-init" \
  --record
```

## 完成后

进入主循环（Step 2）：先 resume，再按 `pending_steps` 从 `2-start-ci` 起执行（见 [02-run-and-wait-ci.md](02-run-and-wait-ci.md)）。
