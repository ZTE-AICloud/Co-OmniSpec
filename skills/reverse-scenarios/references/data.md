---
description: 场景反构的数据交换与缓存规范
parent: reverse-scenarios
target: scenarios
---

## AI Agent ↔ 脚本 数据交换规范（场景反构）

本文件定义场景反构过程中 AI Agent 与脚本之间的数据交换方式、缓存文件命名约定以及目录结构。规范目标是与接口清单反构保持一致风格，便于统一实现与维护。

### 目录结构与路径约定

#### 缓存目录

- 默认缓存目录：`{REPO_ROOT}/.cache/reverse/scenarios/`
- 支持通过环境变量覆盖：
  - `REVERSE_SCENARIO_CACHE_DIR`：若设置，则优先使用该目录

所有缓存文件路径均应为绝对路径。推荐由上层命令在阶段0（缓存状态检查）中统一计算并传递：

- `SCENARIO_CACHE_DIR`：场景缓存目录绝对路径
- `SCENARIO_STATUS_FILE`：`${SCENARIO_CACHE_DIR}/.cache-status.json`

#### 输出目录

- 默认输出目录：`{REPO_ROOT}/omni-doc/specs/scenarios`
  - 由变量 `SCENARIO_OUTPUT_DIR` 表示
  - 在执行前应确保目录已创建（如使用 `mkdir -p` 或 `New-Item -Force`）

### 缓存文件命名约定

所有中间结果文件使用固定文件名，不使用时间戳，便于复用与版本控制：

- `scenario-patterns.json`
  - 场景模式特征（识别出的各种场景模式特征）
- `few-shot-examples.json`
  - Few-shot示例集合（为场景候选抽取提供示例）
- `scenario-types.json`
  - 用户选择的场景类型列表
- `constraints.json`
  - 用户配置的约束规则
- `scenario-candidates.json`
  - 场景候选列表（含来源信息和基础属性）
- `scenario-list.json`
  - 最终场景清单（ID、名称、分类、优先级、文件名等）
- `.cache-status.json`
  - 场景反构状态文件（记录各阶段确认状态与进度）

> 如有需要，也可以在未来引入 `scenario-details.json` 等扩展文件，用于聚合更丰富的场景细节，但不是当前的强制要求。

### 状态文件结构（`.cache-status.json`）

场景反构的状态文件推荐结构如下：

```jsonc
{
  "scenario_patterns": {
    "confirmed": false,
    "progress": "pending",
    "timestamp": null
  },
  "few_shot_examples": {
    "confirmed": false,
    "progress": "pending",
    "timestamp": null
  },
  "scenario_list": {
    "confirmed": false,
    "progress": "pending",
    "timestamp": null
  },
  "document_generation": {
    "confirmed": false,
    "progress": "pending",
    "timestamp": null
  },
  "batch": {
    "stage": null,
    "total_items": 0,
    "batch_size": 0,
    "total_batches": 0,
    "processed_batches": 0,
    "failed_batches": 0
  }
}
```

字段说明：

- `confirmed`：
  - `true`：表示该阶段已执行完成并且用户已明确确认
  - `false`：表示尚未确认或阶段尚未正确完成
- `progress`：
  - `"pending"`：任务尚未开始
  - `"progressing"`：任务进行中
  - `"completed"`：任务完成（通常与 `confirmed=true` 搭配）
  - 可选扩展值（例如 `"completed_with_errors"`），由上层命令定义
- `timestamp`：最近一次状态更新的时间戳（ISO8601 格式）
- `batch`：
  - 记录当前批处理信息，便于在任务中断后恢复
  - `stage`：当前批处理所属阶段（如 `"candidate_extraction"` 或 `"document_generation"`）

> AI Agent 在更新状态文件时应只更新相关字段，避免覆盖其他阶段的信息。

### AI Agent → 脚本：参数与调用方式

#### 通用参数

脚本通常以命令行参数形式接收缓存文件路径和模板路径。推荐的统一参数如下：

- `--scenario-patterns <file>`：场景模式特征文件（可选）
- `--few-shot-examples <file>`：Few-shot示例文件（可选）
- `--scenario-candidates <file>`：场景候选文件（可选）
- `--scenario-list <file>`：场景清单 JSON 文件
- `--template-inventory <file>`：场景清单 Markdown 模板
- `--template-scenario <file>`：单场景 Markdown 模板
- `--output-dir <dir>`：输出目录（通常为 `{REPO_ROOT}/omni-doc/specs/scenarios`）
- `--non-interactive`：非交互模式执行（用于纯脚本执行场景）

> 实际脚本可以根据需要精简或扩展这些参数，但应保持命名风格与接口反构一致（`--kebab-case`）。

#### Linux（Bash）示例

```bash
#!/usr/bin/env bash
set -e
set -u
set -o pipefail

REPO_ROOT="/path/to/repo"          # 由 AI Agent 传入
SCENARIO_CACHE_DIR="$REPO_ROOT/.cache/reverse/scenarios"
SCENARIO_OUTPUT_DIR="$REPO_ROOT/omni-doc/specs/scenarios"

mkdir -p "$SCENARIO_OUTPUT_DIR"

omni-scenarios.sh \
  --scenario-list "$SCENARIO_CACHE_DIR/scenario-list.json" \
  --template-inventory "$REPO_ROOT/.infra/templates/default/reverse-scenario-inventory-template.md" \
  --template-scenario "$REPO_ROOT/.infra/templates/default/reverse-scenario-detail-template.md" \
  --output-dir "$SCENARIO_OUTPUT_DIR" \
  --non-interactive
```

#### Windows（PowerShell）示例

```powershell
#!/usr/bin/env pwsh
$ErrorActionPreference = 'Stop'

$RepoRoot = "C:\path\to\repo"      # 由 AI Agent 传入
$CacheDir = Join-Path $RepoRoot ".cache\reverse\scenarios"
$OutputDir = Join-Path $RepoRoot "omni-doc\scenarios"

New-Item -ItemType Directory -Path $OutputDir -Force | Out-Null

omni-scenarios.ps1 `
  -ScenarioList "$CacheDir\scenario-list.json" `
  -TemplateInventory "$RepoRoot\.infra\templates\default\reverse-scenario-inventory-template.md" `
  -TemplateScenario "$RepoRoot\.infra\templates\default\reverse-scenario-detail-template.md" `
  -OutputDir "$OutputDir" `
  -NonInteractive
```

### 脚本 → AI Agent：结果读取与展示

#### 读取 JSON 结果

脚本或其他工具生成的 JSON 结果文件（例如 `scenario-list.json`）由 AI Agent 读取并以 Markdown 形式展示给用户。推荐流程：

1. AI Agent 使用 `read_file` 工具读取 JSON 文件
2. 基于 JSON 内容提取关键信息：
   - 场景总数
   - 按领域/类型的统计
   - 若干代表性场景条目
3. 使用中文对结果进行总结与解释，避免一次性输出过长列表

#### 文档生成输出

- 文稿类输出文件：
  - 场景清单文档：`{SCENARIO_OUTPUT_DIR}/scenario-list.md`
  - 单场景文档：`{SCENARIO_OUTPUT_DIR}/SCN-XXX-*.md`
- 脚本应在 stdout 中输出：
  - 实际生成的文件数量
  - 输出目录路径
  - 可能的告警或错误提示
- AI Agent 读取这些输出后，应：
  - 用中文向用户总结结果
  - 在必要时展示部分代表性内容或路径

### 缓存检查与复用机制

1. 每个阶段开始前：
   - 检查对应产物文件是否存在
   - 检查 `.cache-status.json` 中的 `confirmed` 状态
2. 若已确认且文件存在：
   - 直接使用缓存，跳过重新生成
3. 若未确认或文件缺失：
   - 正常执行分析与生成流程
   - 完成后更新状态文件并写入最新时间戳

### 缓存清理

为了支持从零开始重跑或清理由于中断导致的残留缓存，推荐：

- 通过参数支持整体清理：
  - 例如 CLI 参数：`--clear-cache`
  - 或单独脚本：`clean-scenario-cache.sh` / `Clean-ScenarioCache.ps1`
- 清理策略可包括：
  - 删除 `{SCENARIO_CACHE_DIR}` 下的所有 JSON 文件
  - 或仅删除 `.cache-status.json`，保留中间结果用于调试

### Token 与大文件处理（与接口反构规则对齐）

- 对于体量较大的 JSON/Markdown 文件：
  - AI Agent 仅按需读取部分内容（例如前若干条场景），避免一次性加载全部
  - 在进行批量展示或分析前，先评估文件大小和预估 Token 消耗
- 在批量处理场景清单时：
  - 单批处理的场景数量应控制在 5–10 个
  - 每批处理前后清理上下文，只保留必要的元信息（批次号、输出目录等）

---

**注意**：本数据规范文件与 `reverse-scenarios.md` 中描述的整体流程相互补充。实现时应统一遵守路径、文件命名和状态管理约定，避免在不同脚本和 Agent 之间引入不一致的约定。


