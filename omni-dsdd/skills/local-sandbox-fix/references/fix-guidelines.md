# 修码约束（local-sandbox-fix）

## 输入

1. `${HARNESS_DIR}/fix-context.json` — Harness gate `4-parse-result` 生成
2. 失败检查项的 `check_log` 本地日志文件（绝对路径）

## 分析优先级

1. 读 `failed_checks[].check_log` 定位编译/UT 失败根因
2. KW / Coverity / Lizard → 解压 `meta.measure_path`：
   ```bash
   tar -xzf "${MEASURE_PATH}" -C /tmp/measure && find /tmp/measure -type f
   ```
3. 参考 `${SANDBOXCHECK_DIR}/execution_outputs/git_summary.txt`（若存在）

## 修码规则

- **禁止**删除源文件规避检查
- 仅修改与失败项相关的最小范围代码
- Git 操作统一：`git -C "${CLAUDE_WORKING_DIR}" ...`
- 修码完成后须存在未提交变更（由 gate `5-fix-verify` 机读验证）

## 完成后

执行 `Skill("code-review")` 同步等待，再跑 gate `6-code-review-gate`。
