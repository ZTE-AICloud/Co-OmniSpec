---
description: 实体清单反构的数据交换规范
parent: reverse-entities
target: entities
---

### AI Agent → 脚本

**方式**：通过命令行参数传递 JSON 文件路径

**参数**：
- `--entity-extraction-result <file>`：实体抽取结果 JSON 文件
- `--consolidated-entities <file>`：融合后的实体列表 JSON 文件
- `--entity-lineage <file>`：实体溯源映射 JSON 文件
- `--interface-aggregation-dir <dir>`：接口聚合文件目录

**文件命名约定**：
- 使用固定文件名（不使用时间戳）：`{CACHE_DIR}/{type}.json`
- 例如：`{REPO_ROOT}/.cache/reverse/entities/.cache-status.json`
- 支持缓存复用：如果文件存在且已确认，直接使用

**示例**：

**Linux (Bash)**：
```bash
# 输出目录统一放到用户工程目录下的 omni-doc/specs/entities 文件夹中
OUTPUT_DIR="$REPO_ROOT/omni-doc/specs/entities"
mkdir -p "$OUTPUT_DIR"

AI Agent调用实体抽取脚本 \
  --repo-root "$REPO_ROOT" \
  --interface-aggregation-dir "$CACHE_DIR/interface-aggregation" \
  --user-terminology "$REPO_ROOT/.cache/user_input/user_terminology.md" \
  --output-dir "$CACHE_DIR/entity-extraction" \
  --non-interactive
```

**Windows (PowerShell)**：
```powershell
# 输出目录统一放到用户工程目录下的 omni-doc/specs/entities 文件夹中
$OutputDir = Join-Path $RepoRoot "omni-doc\specs\entities"
New-Item -ItemType Directory -Path $OutputDir -Force | Out-Null

AI Agent调用实体抽取脚本 `
  -RepoRoot "$RepoRoot" `
  -InterfaceAggregationDir "$CacheDir\interface-aggregation" `
  -UserTerminology "$RepoRoot\.cache\user_input\user_terminology.md" `
  -OutputDir "$CacheDir\entity-extraction" `
  -NonInteractive
```

**输出文件说明**：
- **实体文档**：每个实体一个文件，`{REPO_ROOT}/omni-doc/specs/entities/ENTITY-{序号:03d}-{业务名称}.md`
- **实体清单**：`{REPO_ROOT}/omni-doc/specs/entities/实体清单.md`

### 脚本 → AI Agent

**方式**：AI Agent 直接读取 JSON 文件并总结展示

**AI Agent 展示**：
- AI Agent 使用 `read_file` 工具读取 JSON 文件
- AI Agent 基于 JSON 内容总结关键信息，提取统计摘要、实体列表、代表性示例等
- AI Agent 以清晰的 Markdown 格式在对话中展示给用户
- 对于大型数据集，展示摘要和代表性示例，而不是完整列表

**文档生成输出**：
- 脚本生成文档后，输出文档路径和统计信息到 stdout
- AI Agent 读取并展示给用户

### 中间结果文件管理（缓存机制）

**缓存目录位置**：
- 默认：`{REPO_ROOT}/.cache/reverse/entities/`
- 支持通过环境变量指定：`REVERSE_CACHE_DIR`（如果设置，使用该目录）
- 缓存目录在工程目录下，便于版本控制和复用

**缓存文件命名**（固定名称，不使用时间戳）：
- `entity-extraction/ENTITIES-{原接口文件名}.md` - 实体抽取结果（按接口文件分组）
- `entity-extraction/entities-index.json` - 批次结果索引文件
- `entity-extraction/lineage/*.json` - 溯源元数据
- `entity-extraction/extraction_stats.json` - 抽取统计信息
- `entity-consolidation/consolidated-entities.json` - 融合后的实体列表
- `entity-consolidation/entities_lineage.json` - 更新的溯源映射
- `entity-consolidation/consolidation_stats.json` - 融合统计信息
- `.cache-status.json` - 缓存状态文件（记录确认状态）

**缓存状态文件格式**：
```json
{
  "version": "1.0",
  "entity_extraction": {
    "confirmed": false,
    "progress": "pending",
    "timestamp": null
  },
  "entity_consolidation": {
    "confirmed": false,
    "progress": "pending",
    "timestamp": null
  },
  "entity_document_generation": {
    "confirmed": false,
    "progress": "pending",
    "timestamp": null
  },
  "entity_relationship_building": {
    "confirmed": false,
    "progress": "pending",
    "timestamp": null
  }
}
```

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
- 或手动删除 `.cache/reverse/entities/` 目录

**文件格式**：
- 所有中间结果使用 JSON 格式（实体文档使用 Markdown 格式）
- 符合设计文档中定义的数据结构

### 数据结构定义

#### 实体基本信息结构
```json
{
  "entity_id": "user_manager",
  "entity_name_cn": "用户管理器",
  "entity_type": "业务服务",
  "domain": "用户管理",
  "related_files": ["src/services/user_service.py", "src/models/user.py"],
  "responsibility": "管理用户相关的业务逻辑，包括用户创建、查询、更新等操作",
  "class_diagram": "```mermaid\nclassDiagram\n...\n```",
  "source_interfaces": ["API-001", "API-002"]
}
```

#### 实体文档结构（基于模板）
```markdown
---
id: ENTITY-001
name: ENTITY-001-用户管理器
description: 管理用户相关的业务逻辑
---

## 实体: ENTITY-001-用户管理器

[实体的详细描述]

## 实体结构

[使用PlantUML类图描述实体的结构]

## 属性说明

[每个属性的详细说明]

## 方法说明

[每个方法的详细说明]

## 职责说明

[详细说明实体的核心职责]
```

#### 批次结果索引文件格式
```json
{
  "version": "1.0",
  "total_batches": 15,
  "total_entities": 45,
  "batches": [
    {
      "batch_id": 1,
      "source_files": ["interface-aggregation/API-001.md", "interface-aggregation/API-002.md"],
      "entity_files": [
        "entity-extraction/ENTITIES-API-001.md",
        "entity-extraction/ENTITIES-API-002.md"
      ],
      "lineage_files": [
        "entity-extraction/lineage/API-001.json",
        "entity-extraction/lineage/API-002.json"
      ],
      "entity_count": 3,
      "status": "completed",
      "timestamp": "2024-01-01T00:00:00Z"
    }
  ]
}
```

#### 实体溯源映射文件格式
```json
{
  "version": "1.0",
  "entities": [
    {
      "entity_id": "ENTITY-001",
      "entity_name_cn": "用户管理器",
      "source_interfaces": ["API-001", "API-002"],
      "source_files": [
        "interface-aggregation/API-001.md",
        "interface-aggregation/API-002.md"
      ],
      "extraction_timestamp": "2024-01-01T00:00:00Z"
    }
  ]
}
```

#### 融合后的实体列表格式
```json
{
  "version": "1.0",
  "total_entities": 30,
  "entities": [
    {
      "entity_id": "ENTITY-001",
      "entity_name_cn": "用户管理器",
      "entity_type": "业务服务",
      "domain": "用户管理",
      "related_files": ["src/services/user_service.py"],
      "responsibility": "管理用户相关的业务逻辑",
      "class_diagram": "```mermaid\nclassDiagram\n...\n```",
      "source_interfaces": ["API-001", "API-002"],
      "merged_from": ["entity-001-original", "entity-002-original"],
      "value_score": 0.85
    }
  ],
  "statistics": {
    "by_type": {
      "业务服务": 15,
      "数据模型": 10,
      "工具类": 5
    },
    "by_domain": {
      "用户管理": 8,
      "订单管理": 7,
      "支付管理": 5
    }
  }
}
```

#### 关系数据结构

**接口 → 实体关系**：
```json
{
  "version": "1.0",
  "relations": [
    {
      "source": "API-001",
      "targets": ["ENTITY-001", "ENTITY-002"]
    }
  ]
}
```

**实体 → 接口关系**：
```json
{
  "version": "1.0",
  "relations": [
    {
      "source": "ENTITY-001",
      "targets": ["API-001", "API-002"]
    }
  ]
}
```

**功能 → 实体关系**：
```json
{
  "version": "1.0",
  "relations": [
    {
      "source": "FUNC-001",
      "targets": ["ENTITY-001", "ENTITY-002"]
    }
  ]
}
```

### AI Agent 展示机制

**展示方式**：
- AI Agent 使用 `read_file` 工具读取 JSON 文件
- AI Agent 基于 JSON 内容总结关键信息并展示

**展示要求**：
- 提取 JSON 中的关键信息：统计摘要、实体列表、代表性示例等
- 使用清晰的 Markdown 格式展示
- 对于大型数据集，展示摘要和代表性示例，而不是完整列表

**示例**：
```bash
# AI Agent 读取 JSON 文件（使用 read_file 工具）
# 文件路径：{REPO_ROOT}/.cache/reverse/entities/.cache-status.json

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

