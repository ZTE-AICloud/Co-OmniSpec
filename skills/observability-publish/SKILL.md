---
name: observability-publish
description: 从 omni-execution-log.json 聚合生成 omni-observability-result.json，并调用 ssd_step_insert 写入 ssd_step_info。当 changes 下已有执行日志时使用。
argument-hint: "[--dry-run] [--default-branch 分支名] [FEATURE_DIR 或 omni-execution-log.json 路径]"
---

# observability-publish（执行日志 → 可观测性 JSON → 入库）

## 适用场景

- 某特性目录下**已经存在** `omni-execution-log.json`（根为步骤对象数组）。
- 需要生成 **`omni-observability-result.json`**（按 `sdd_step` / `step_name` 取最后一次执行），并**写入数据库**（或仅校验）。

## 用户如何触发（调用本 Skill）

在 Cursor / Claude Code 中任选一种即可：

1. **@ Skill**：在对话里引用本技能（`observability-publish`），并说明特性目录或 `omni-execution-log.json` 的完整路径；若仅校验数据库，写明 **`--dry-run`**（仅对入库步骤生效）。
2. **斜杠命令**（若已加载仓库命令）：执行 **`/observability-publish`**，并按提示补充路径或 `FEATURE_DIR`。
3. **自然语言**：例如：「对 `changes/002-xxx` 执行 observability-publish：生成可观测性 JSON 并入库」。

由 Agent 读取本文件后，**在终端执行下方脚本**，禁止只口述不执行（除非用户环境禁网禁库）。

## 路径约定

- 仓库内脚本目录：`.claude/skills/observability-publish/scripts/python/`（相对仓库根目录）。
- 默认输入：`{FEATURE_DIR}/omni-execution-log.json`。
- 默认输出：`{FEATURE_DIR}/omni-observability-result.json`（由聚合脚本写在**与输入同目录**）。

`FEATURE_DIR` 可为环境变量，或用户给出的 `changes/<feature-id>-...` 绝对/相对路径。

## 执行步骤（必须按序）

### 1. 聚合（清洗 / 按步骤取最后一次）

在**仓库根目录**执行（按实际路径替换）：

```bash
python .claude/skills/observability-publish/scripts/python/omni_build_observability_result.py -i "<FEATURE_DIR>/omni-execution-log.json"
```

可选：

- 指定输出文件：`-o "<FEATURE_DIR>/omni-observability-result.json"`（通常省略，默认即此名）。
- 日志里完全没有 `branch` 时补足根级分支：  
  `--default-branch "<特性目录名或分支名>"`。

成功后应得到 `omni-observability-result.json`，且含 `step_results`、`summary`、`invalid_records`（若有无效行）。

### 2. 入库

未要求试跑时执行：

```bash
python .claude/skills/observability-publish/scripts/python/ssd_step_insert.py -i "<FEATURE_DIR>/omni-observability-result.json"
```

若步骤数据中可能缺 `branch`，且根对象也无 `branch` / `feature_desc`，需传入与上一步相同的  
`--default-branch`。

用户要求**不写库、只校验**时，在**本命令**上加 `--dry-run`：

```bash
python .claude/skills/observability-publish/scripts/python/ssd_step_insert.py -i "<FEATURE_DIR>/omni-observability-result.json" --dry-run
```

注意：`--dry-run` 仅作用于 **ssd_step_insert**；聚合脚本仍会写出 `omni-observability-result.json`。若用户希望连 JSON 都不覆盖，应先备份或改用 `-o` 写到临时路径，再对该路径 dry-run 入库。

## 产出核对

- 终端输出：`已写入: ...` 与 `插入成功，条数: N` 或 `[dry-run] 将插入 N 条`。
- 打开 `omni-observability-result.json` 查看 `summary` 与 `step_results` 是否符合预期。

## 依赖与失败处理

- 聚合脚本仅依赖 Python 标准库。
- 入库依赖 `pymysql` 与 `ssd_step_insert.py` 内 `DB_CONFIG`；连接失败应向用户说明并保留已生成的 JSON。

## 相关文档

- 设计约定：`changes/<feature>/execution-observability-skill-plan.md`（若存在）。
