---
description: 接口清单反构的数据交换规范
parent: reverse-interfaces
target: interfaces
---


### AI Agent → 脚本

**方式**：通过命令行参数传递 JSON 文件路径

**参数**：
- `--architecture-result <file>`：架构识别结果 JSON 文件（推荐固定为 `{REPO_ROOT}/omni-doc/specs/logic_architecture/architecture.json`，由 `reverse-logic-architecture` 生成）
- `--few-shot-examples <file>`：Few-shot 示例 JSON 文件
- `--interface-list <file>`：接口清单 JSON 文件
- `--interface-details <file>`：接口详细信息 JSON 文件

**文件命名约定**：
- 使用固定文件名（不使用时间戳）：`{CACHE_DIR}/{type}.json`
- 例如：`{REPO_ROOT}/.cache/reverse/interfaces/.cache-status.json`
- 支持缓存复用：如果文件存在且已确认，直接使用

**示例**：

**Linux (Bash)**：
```bash
# 输出目录统一放到用户工程目录下的omni-doc/specs/interfaces文件夹中
OUTPUT_DIR="$REPO_ROOT/omni-doc/specs/interfaces"
mkdir -p "$OUTPUT_DIR"

AI Agent调用reverse.sh脚本 \
  --target interfaces \
  --interface-list "$CACHE_DIR/interface-list.json" \
  --few-shot-examples "$CACHE_DIR/few-shot-examples.json" \
  --template ./template.md \
  --output-dir "$OUTPUT_DIR" \
  --non-interactive
```

**Windows (PowerShell)**：
```powershell
# 输出目录统一放到用户工程目录下的omni-doc/specs/interfaces文件夹中
$OutputDir = Join-Path $RepoRoot "omni-doc\specs\interfaces"
New-Item -ItemType Directory -Path $OutputDir -Force | Out-Null

AI Agent调用reverse.ps1脚本 `
  -Target interfaces `
  -InterfaceList "$CacheDir\interface-list.json" `
  -FewShotExamples "$CacheDir\few-shot-examples.json" `
  -Template ".\template.md" `
  -OutputDir "$OutputDir" `
  -NonInteractive
```

**输出文件说明**：
- **接口清单文档**：`{REPO_ROOT}/omni-doc/specs/interfaces/接口清单.md`
- **接口详细文档**：每个接口一个文件，`{REPO_ROOT}/omni-doc/specs/interfaces/API_001_{中文业务简要总结}.md`

### 脚本 → AI Agent

**方式**：AI Agent 直接读取 JSON 文件并总结展示

**AI Agent 展示**：
- AI Agent 使用 `read_file` 工具读取 JSON 文件
- AI Agent 基于 JSON 内容总结关键信息，提取统计摘要、分类信息、代表性示例等
- AI Agent 以清晰的 Markdown 格式在对话中展示给用户
- 对于大型数据集，展示摘要和代表性示例，而不是完整列表

**文档生成输出**：
- 脚本生成文档后，输出文档路径和统计信息到 stdout
- AI Agent 读取并展示给用户

### 中间结果文件管理（缓存机制）

**缓存目录位置**：
- 默认：`{REPO_ROOT}/.cache/reverse/`
- 支持通过环境变量指定：`REVERSE_CACHE_DIR`（如果设置，使用该目录）
- 缓存目录在工程目录下，便于版本控制和复用

**逻辑架构共享产物（不在接口缓存目录）**：
- `{REPO_ROOT}/omni-doc/specs/logic_architecture/architecture.json` — 由 `reverse-logic-architecture` 生成，接口阶段**只读**

**接口缓存文件命名**（固定名称，不使用时间戳）：
- `few-shot-examples.json` - Few-shot 示例
- `interface-list.json` - 接口清单
- `.cache-status.json` - 缓存状态文件（记录确认状态）

**接口缓存状态文件格式**（不再包含 `architecture_identification`）：
```json
{
  "few_shot_examples": {
    "confirmed": true,
    "progress": "completed",
    "timestamp": "2024-01-01T00:00:00Z"
  },
  "interface_list": {
    "confirmed": true,
    "progress": "completed",
    "timestamp": "2024-01-01T00:00:00Z"
  },
  "document_generation": {
    "confirmed": true,
    "progress": "completed",
    "timestamp": "2024-01-01T00:00:00Z"
  }
}
```

### 质量闸门与强制标识（新增）

为保证“预估→校验→重扫/重筛”不可跳过，新增以下缓存产物：

- `interface-estimation.json`
  - `total_code_lines`
  - `baseline_min_interfaces`（不低于代码行数千分之2）
  - `estimated_by_type`
  - `estimated_total_interfaces`
  - `mandatory_flags.estimation_generated`
  - `mandatory_flags.estimation_confirmed`
- `interface-quality-report.json`
  - `actual_total_interfaces`
  - `actual_by_type`
  - `status`（`pass|too_few|too_many|invalid_list`）
  - `mandatory_flags.quantity_validation_done`
  - `mandatory_flags.rescan_if_needed_done`
  - `mandatory_flags.full_list_generated`
  - `mandatory_flags.quality_gate_passed`
- `interface-scan-coverage-report.json`（扫描文件覆盖度检测）
  - `file_list_count` / `repo_code_file_count` / `coverage_ratio`
  - `likely_insufficient_coverage` / `recommend_full_file_list_rescan`
  - `apply_full_file_list_done`（是否已写入全量 `file_list.json`）

🔴 执行约束：
- 任一强制标识未通过，禁止进入阶段4
- `interface-list.json` 必须为全量接口清单，不得仅输出示例清单

### 状态字段说明
- `confirmed`: 表示该阶段是否已由用户确认完成
  - `true`: 用户已确认该阶段完成
  - `false`: 用户尚未确认或阶段未完成
- `progress`: 表示该阶段的执行进度状态
  - `"pending"`: 任务尚未开始
  - `"progressing"`: 任务正在进行中
  - `"completed"`: 任务已完成
- `timestamp`: 表示状态最后更新的时间戳

**缓存检查机制**：
1. 每个阶段开始时，检查对应的缓存文件是否存在
2. 如果存在，检查状态文件中的确认状态
3. 如果已确认，直接使用缓存，跳过生成和确认步骤
4. 如果未确认或不存在，执行分析并生成结果
5. 用户确认后，更新状态文件为已确认

**缓存优势**：
- ✅ 避免重复生成：如果用户已确认，直接使用缓存
- ✅ 支持增量处理：可以只重新生成未确认的阶段
- ✅ 版本控制友好：缓存文件在工程目录下，可以纳入版本控制
- ✅ 便于调试：可以查看和修改缓存文件

**清理缓存**：
- 使用 `--clear-cache` 参数清理所有缓存文件
- 或手动删除 `.cache/reverse/` 目录

**文件格式**：
- 所有中间结果使用 JSON 格式
- 符合设计文档中定义的 JSON 结构

### AI Agent 展示机制

**展示方式**：
- AI Agent 使用 `read_file` 工具读取 JSON 文件
- AI Agent 基于 JSON 内容总结关键信息并展示

**展示要求**：
- 提取 JSON 中的关键信息：统计摘要、分类信息、代表性示例等
- 使用清晰的 Markdown 格式展示
- 对于大型数据集，展示摘要和代表性示例，而不是完整列表

**示例**：
```bash
# AI Agent 读取 JSON 文件（使用 read_file 工具）
# 文件路径：{REPO_ROOT}/.cache/reverse/interfaces/.cache-status.json

# 输出到 stdout，AI Agent 读取并展示
```

**输出格式**：
- `--format markdown`（默认）：Markdown 格式，便于 AI Agent 展示
- `--format json`：格式化后的 JSON 格式（使用 jq 或 Python 格式化）
- `--format text`：纯文本格式

**JSON 格式化**：
- 所有展示脚本都会自动格式化 JSON 输出
- 优先使用 `jq` 工具格式化 JSON
- 如果没有 `jq`，会尝试使用 `python3` 或 `python` 的 `json.tool` 模块格式化
- 如果都没有，会输出警告并输出原始 JSON（未格式化）
- 确保用户确认时看到的 JSON 都是格式化的，便于阅读

