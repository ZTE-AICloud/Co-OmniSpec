---
name: runlog-record
description: 记录 omni skill 执行后的维测数据到 JSON 文件。当需要统一记录 skill 执行结果时、当 omni 工具执行完成后需要生成执行报告时、当需要进行 skill 性能分析时自动触发。适用于 SDD workflow 各阶段结束后手动调用。
argument-hint: "[skill执行的开始时间start_time]"
allowed-tools: Read, Write, Edit, Bash
---

# Skill 执行的维测数据记录

在 **skill 执行结束后**调用，将结构化日志追加写入 **`${FEATURE_DIR}/.runs/metrics/omni-metrics-log.json`**。

## 环境初始化

| 变量 | 含义 |
|------|------|
| `FEATURE_DIR` | 当前特性目录（**必填**，日志唯一落盘根） |
| `CLAUDE_WORKING_DIR` | 用户工作区（可选，Git 辅助解析分支名） |
| `CLAUDE_PLUGIN_ROOT` | 插件根（参考文档路径） |

### Step 0.1 检查变量

```bash
test -n "${FEATURE_DIR:-}" && test -d "${FEATURE_DIR}"
```

- `FEATURE_DIR` 未设置或目录不存在 → **报错终止**，不得继续

```bash
test -n "${CLAUDE_WORKING_DIR:-}" && test -d "${CLAUDE_WORKING_DIR}"
```

- `CLAUDE_WORKING_DIR` 缺失时：`export CLAUDE_WORKING_DIR="$(pwd)"`（**不用** `git rev-parse --show-toplevel`）

**推荐**（SDD workflow 各阶段结束前通常已具备）：

```bash
source "${FEATURE_DIR}/.runs/env.sh"
```

### 路径约定

| 符号 | 展开 |
|------|------|
| Metrics 日志 | `${FEATURE_DIR}/.runs/metrics/omni-metrics-log.json` |
| 特性元数据 | `${FEATURE_DIR}/.runs/paths.json`（可选） |
| 本技能文档 | `${CLAUDE_PLUGIN_ROOT}/skills/runlog-record/SKILL.md` |

目录不存在时，在 **`FEATURE_DIR` 下**创建（禁止写到仓库根或其它 `changes/` 路径）：

```bash
mkdir -p "${FEATURE_DIR}/.runs/metrics"
```

## 概述（职责与输入输出）

### 职责

记录 omni skill 执行后的维测数据，便于性能分析与问题追溯。

### 输入

- **start_time**（必填）：被监控 skill 的开始时间，由调用方传入（如 specify/design 步骤开始时记录的时间戳）
- **上下文字段**（`input` / `output` / `execute_result` / `sdd_step`）：来自**刚结束的上游 skill**，不得编造

### 输出

- 向 `${FEATURE_DIR}/.runs/metrics/omni-metrics-log.json` **追加**一条 JSON 对象（文件整体为 JSON 数组）

## 依赖要求

- `FEATURE_DIR` 已设置且可写
- 对 `${FEATURE_DIR}/.runs/metrics/` 有写入权限
- 支持 JSON 数组 Read / 追加 Write

## 输出格式

```json
{
  "start_time": "",
  "sdd_step": "",
  "feature_desc": "",
  "end_time": "",
  "execute_duration": "",
  "execute_result": "",
  "input": "",
  "output": ""
}
```

## 行为准则

1. **追加不覆盖** — 每次写入前 Read 既有数组，append 后 Write
2. **数据来源透明** — `input` / `output` / `execute_result` 仅来自调用方上下文；无法获取则 `""`
3. **环境依赖** — `FEATURE_DIR` 无效则终止
4. **路径隔离** — 禁止将日志写到 `${CLAUDE_WORKING_DIR}` 根或错误的 `changes/<branch>`（须与当前 `FEATURE_DIR` 一致）

## 解析 `feature_desc` 字段（Step 1.6）

**禁止**用 Git 仓库根推断特性目录：

1. `${FEATURE_DIR}/.runs/paths.json` 的 `branch_name` / `BRANCH_NAME` / `feature_desc`
2. `FEATURE_DIR` 目录 basename（如 `001-TCF-5064840-vpn-service`）
3. 可选：`git -C "${CLAUDE_WORKING_DIR}" branch --show-current`（仅作描述字符串）
4. 仍无法确定 → `feature_desc: ""`

## 执行步骤

请在 **被监控 skill 完全结束后**再调用本技能。

### Step 1: 汇总执行结果

**数据来源规则**（不得自行生成、推测）：

| 字段 | 来源 |
|------|------|
| `input` | 上游 skill 的原始输入 |
| `output` | 上游 skill 的关键输出摘要 |
| `execute_result` | 上游执行状态（success / error 等） |
| `sdd_step` | 被监控 skill 的 `name`（如 `specify`、`design`） |

1. 记录 `end_time`
   - Windows: `Get-Date -Format "yyyy-MM-dd HH:mm:ss"`
   - Linux: `date +"%Y-%m-%d %H:%M:%S"`
2. 由参数 **start_time** 与 `end_time` 计算 `execute_duration`（`10 min 20 sec`）
3. 写入 `input`、`output`、`execute_result`（无则 `""`）
4. 按上文规则写入 `feature_desc`
5. 写入 `sdd_step`（被监控 skill 名称）
6. 将参数 **start_time** 写入 `start_time`

✅ Checkpoint: Step 1 完成 — 各字段已填充

**失败降级**: 时间获取失败 → UTC：`date -u +"%Y-%m-%d %H:%M:%S"`

### Step 2: 追加保存

目标：**`${FEATURE_DIR}/.runs/metrics/omni-metrics-log.json`**

1. `mkdir -p "${FEATURE_DIR}/.runs/metrics"`
2. 文件不存在 → 初始化为 `[]`
3. Read → 解析为数组 → append 本条 → Write（**不得**覆盖历史）

✅ Checkpoint: Step 2 完成 — 已追加到 omni-metrics-log.json

**失败降级**: 写入失败 → 在会话输出完整 JSON 条目；若调用方为 **specify** 等带 gate 的技能，可按其 SKILL 用 Write 补写后再跑 gate

## 使用示例

### 示例 1：SDD 阶段结束（常见）

`specify` / `design` / `tasks` / `analyze` / `implement` 在记录 `start_time` 后，于步骤末尾：

```text
/runlog-record "2026-05-16 10:30:00"
```

须已 `source "${FEATURE_DIR}/.runs/env.sh"` 或等价设置 `FEATURE_DIR`。

### 输出示例

```json
{
  "start_time": "2026-05-16 10:30:00",
  "sdd_step": "specify",
  "feature_desc": "001-TCF-5064840-vpn-service",
  "end_time": "2026-05-16 10:35:20",
  "execute_duration": "5 min 20 sec",
  "execute_result": "success",
  "input": "添加用户登录功能...",
  "output": "spec.md 已生成..."
}
```

## 调用关系

| 方向 | 说明 |
|------|------|
| **上游** | `specify`、`design`、`tasks`、`analyze`、`implement`、`clarify`、`mini-design`、`mini-implement`、`archive`、`checklist` |
| **下游** | 无；仅写本地 JSON |

## 参考

| 项 | 路径 |
|----|------|
| 本技能 | `${CLAUDE_PLUGIN_ROOT}/skills/runlog-record/SKILL.md` |
| 环境导出 | `${FEATURE_DIR}/.runs/env.sh` |
