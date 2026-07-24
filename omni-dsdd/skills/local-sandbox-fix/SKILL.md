---
name: local-sandbox-fix
description: 基于 local-sandboxcheck 检查结果自动修复代码并重测。提交前本地 CI 闭环。触发词：local-sandbox-fix、本地沙盒修复、sandbox 自动修复。
version: 1.0.0
---

# Local Sandbox 自动修复

编排「本地沙盒 CI → 失败分析 → 修码 → omni-dsdd:code-review → 重测」闭环，最多 3 轮。详细设计见 [docs/local-sandbox-fix-design.md](docs/local-sandbox-fix-design.md)。

执行主线：**环境初始化 → Step 1 init+gate0 → Step 2 主循环**（gate `2-start-ci`～`7-record-iteration`，最多 3 轮）。

---

## 硬约束

- **工程路径 = CLAUDE_WORKING_DIR**（= `run_local_ci.py` 的 workdir）；禁止 `git rev-parse --show-toplevel`
- **gate_exit≠0 时不得进入下一步**
- gate 2～3 之间禁止修改代码
- 禁止删除文件规避检查
- 所有路径从 `source "${HARNESS_DIR}/env.sh"` 获取
- **禁止**绕过 harness 手工执行 `pytest`、`go test`、`npm test`、`tox` 或 `local-ci`；所有本地 CI/test 只能由 gate `2-start-ci`～`7-record-iteration` 驱动
- `devops_config.yaml` 缺失时，gate `0-init` 会写出 `status=success, skipped=true` 并结束；此时不得补跑任何测试、不得修代码/测试、不得把普通 UT 通过当成本 stage 结果

---

## 环境初始化

进入 Step 1 之前的就绪准备：检查/补全 `CLAUDE_PLUGIN_ROOT`、`CLAUDE_WORKING_DIR`，校验 harness 脚本，**自动从记录文件解析 `FEATURE_DIR`**（未传 `--feature-dir` 时由 harness 读取 `.active-feature` / `changes/*/.runs/.omnispec-state.json` 等记录，解析不到则报错）。详见 [references/stages/00-environment-init.md](references/stages/00-environment-init.md)。

---

## 执行契约与产物

**编排 / 落盘 / 校验分离**：Agent 负责 LLM 修码与 omni-dsdd:code-review；Harness gate 负责 cp、启动 CI、等待、解析 JSON、验 diff、验报告。

| 文件 | 用途 |
|------|------|
| `${FEATURE_DIR}/.runs/local-sandbox-fix/paths.json` | 路径真值源 |
| `${HARNESS_DIR}/env.sh` | source 后导出绝对路径 |
| `${HARNESS_DIR}/run-manifest.json` | 分步门禁、断点续跑 |
| `${HARNESS_DIR}/fix-context.json` | CI 失败时修码上下文 |

契约：[references/harness-contract.json](references/harness-contract.json)

---

## Step 1 — init + gate 0-init

主循环（Step 2）的地基：init 只建地基（目录/路径/状态），gate 0-init 做就绪校验 + **文件初始化**（devops_config 的 cp / 缺失 skip）。本步**不碰业务代码、不跑 CI**。若缺失 `devops_config.yaml`，gate 0-init 已代表本 stage 成功 skip，必须立即停止，不得再执行普通 UT 或自动修复。详见 [references/stages/01-init-and-gate0.md](references/stages/01-init-and-gate0.md)。

---

## Step 2 — 主循环

每轮开始前 **必须** resume：

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/skills/local-sandbox-fix/scripts/python/local_sandbox_fix_harness.py" \
  resume --harness-dir "${HARNESS_DIR}"
```

按 `pending_steps` 顺序执行（**gate_exit=0 方可下一步**）：

| 顺序 | gate step | 执行者 | 参考 |
|------|-----------|--------|------|
| 1 | `2-start-ci` | Harness | [02-run-and-wait-ci.md](references/stages/02-run-and-wait-ci.md) |
| 2 | `3-wait-ci` | Harness（阻塞） | 同上 |
| 3 | `4-parse-result` | Harness | [03-analyze-result-and-fix.md](references/stages/03-analyze-result-and-fix.md) |
| — | Agent fix | Agent | [fix-guidelines.md](references/fix-guidelines.md) |
| 4 | `5-fix-verify` | Harness | 同上 |
| — | omni-dsdd:code-review | Agent `Skill("omni-dsdd:code-review")` | [04-code-review-gate.md](references/stages/04-code-review-gate.md) |
| 5 | `6-code-review-gate` | Harness | 同上 |
| 6 | `7-record-iteration` | Harness | [05-retry-and-exit.md](references/stages/05-retry-and-exit.md) |

> devops_config.yaml 的处理已在 Step 1（gate `0-init`）完成，故主循环不含 `1-prepare-config`，首步为 `2-start-ci`。

gate 命令模板：

```bash
bash "${CLAUDE_PLUGIN_ROOT}/skills/local-sandbox-fix/scripts/bash/local-sandbox-fix-gate.sh" \
  --harness-dir "${HARNESS_DIR}" \
  --step "<step-id>" \
  --record
```

解析 gate stdout JSON 的 `next_action`：

- `finalize` → 成功结束
- `fix` → 修码后 gate 5
- `omni-dsdd:code-review` → Skill("omni-dsdd:code-review") 后 gate 6
- `next_iteration` → 回到主循环首步（`2-start-ci`）
- `abort` → 终止并报告 errors

---

## 参考

### Checkpoint 格式

```
✅ Checkpoint local-sandbox-fix: step=<id>, gate_exit=0, iteration=<n>/3, next_action=<action>
```

### 退出码

| code | 含义 |
|------|------|
| 0 | 成功（含 devops_config 缺失时 gate 0-init 直接 skip 成功结束） |
| 1 | init 通用错误 |
| 2 | gate 校验失败（含 gate 0-init 的 devops_config cp 失败） |
| 10 | run.log 120s 无更新 |
| 11 | 90min 全局超时 |
| 12 | CI 进程异常退出 |
| 20 | 超过 3 轮仍未通过 |

### 依赖

- `local-sandboxcheck` — `${RUN_CI_SCRIPT}`
- `omni-dsdd:code-review` — 修码后审查（skill 内修码轮次；express Step 6 已执行过一次）
- `${CLAUDE_WORKING_DIR}/devops_config.yaml` — 业务配置（**可选**；缺失则 skill 跳过本地 CI 并以 success 结束）

---

## express-workflow 集成（Step 7）

由 `agents/express-workflow.md` 在 Step 6 `review` 之后调用。workflow agent **必须**：

1. `source "$FEATURE_DIR/.runs/env.sh"`
2. `workflow-gate.sh --check pre-local-sandbox-fix`
3. `Skill("omni-dsdd:local-sandbox-fix")` — init 显式传入 `--feature-dir "$FEATURE_DIR"`（不传则 harness 自动从记录解析）：

```bash
bash "${CLAUDE_PLUGIN_ROOT}/skills/local-sandbox-fix/scripts/bash/local-sandbox-fix-init-harness.sh" \
  --plugin-root "${CLAUDE_PLUGIN_ROOT}" \
  --working-dir "${CLAUDE_WORKING_DIR}" \
  --feature-dir "${FEATURE_DIR}"
```

4. skill 成功后：
   - `workflow-gate.sh --check local-sandbox-fix-complete`
   - `workflow-update-state.sh --mark-complete local-sandbox-fix --step "Step 7 local-sandbox-fix 完成"`（默认同步 `workflow-progress.md`）

Harness 成功时写入 `${FEATURE_DIR}/.runs/local-sandbox-fix-status.json`，并刷新 express Step 1–7 进度文件。

Workflow 专用门禁：

```bash
bash "${CLAUDE_PLUGIN_ROOT}/skills/local-sandbox-fix/scripts/bash/local-sandbox-fix-workflow-gate.sh" \
  --feature-dir "${FEATURE_DIR}" --check complete
```
