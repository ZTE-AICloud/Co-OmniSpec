# 阶段 8：质量审查与收尾

本阶段是逆向分析流程的最后一步，负责跨制品质量保证和文档体系收尾。

> **前置校验说明**：各制品的自闭环校验（ID 唯一性/连续性、覆盖率、Frontmatter 完整性、文件命名一致性）已内嵌到各自阶段的 DoD 步骤中（phase-1/1b、2/2b、3/3b、4、5/5b、6/6b、7），本阶段不再重复。

## 职责范围

1. **跨制品质量审查**：检查制品间引用完整性和内容质量，生成质量报告
2. **关系文件生成**：生成各制品间的关联关系 JSON 文件
3. **清单文件生成**：生成各制品的索引清单文件

**执行顺序**：先质量审查 → 再关系/清单生成（如果质量审查发现严重问题，建议修复后再执行）

---

## 任务 1: 质量审查

### 输入内容
- 所有中间概览文件：`omni-doc/specs-temp/intermediate/`
- 所有规范文件：`omni-doc/specs/`

### 审查项

#### 1. 概览文件存在性
检查以下必需的概览文件是否全部存在：
- `project-entry.md`
- `interface-overview.md`
- `entity-overview.md`
- `function-overview.md`
- `scenario-overview.md`
- `requirement-overview.md`

#### 2. 跨制品引用完整性
验证不同制品之间的 ID 引用链路是否闭合：

| 引用源 | 引用字段 | 目标文件 |
|--------|---------|---------|
| `interface-overview.md` | "逻辑实体"列 | `entity-overview.md` 中的 ENTITY-ID |
| `interface-overview.md` | "功能"列 | `function-overview.md` 中的 FUNC-ID |
| `function-overview.md` | "关联实体" | `entity-overview.md` 中的 ENTITY-ID |
| `scenario-overview.md` | "关联功能" | `function-overview.md` 中的 FUNC-ID |
| `requirement-overview.md` | "关联场景" | `scenario-overview.md` 中的 SCN-ID |

对每条引用：提取源文件中的 ID 列表，在目标文件的列表表格中查找，不存在则记录为引用断裂。

#### 3. 内容质量抽查
随机抽取 3-5 个规范文件（跨制品类型），检查：
- **描述质量**：描述是否具体，是否存在空泛或占位符内容
- **PlantUML 语法**：代码块是否能正常渲染（检查基本语法错误）
- **逻辑合理性**：处理流程、时序图是否有明显的逻辑矛盾

### 输出要求
**输出位置**：`omni-doc/specs-temp/quality_report.md`

**报告格式**：
```markdown
# 规范文档质量报告

生成时间：[时间戳]

## 审查汇总

| 审查项 | 状态 | 问题数 |
|--------|------|--------|
| 概览文件存在性 | ✅/⚠️/❌ | [数量] |
| 跨制品引用完整性 | ✅/⚠️/❌ | [数量] |
| 内容质量抽查 | ✅/⚠️/❌ | [数量] |

**状态说明**：
- ✅ 通过：无问题或仅有轻微问题
- ⚠️ 警告：有中等问题，建议修复但不影响使用
- ❌ 失败：有严重问题，必须修复

## 详细问题列表

### 概览文件存在性问题
- [缺失文件]：[问题描述]
- ...

### 跨制品引用完整性问题
- [引用源文件] → [目标ID]：目标不存在
- ...

### 内容质量问题
- [文件路径]：[问题描述]
- ...

## 建议修复操作

### 引用断裂修复
1. 确认目标制品是否确实缺失（可能是前序阶段遗漏）
2. 如目标存在但 ID 不匹配，修正引用源中的 ID
3. 如目标不存在，从概览或规范中移除该引用

### 内容质量修复
1. 补充空泛或占位符描述
2. 修正 PlantUML 语法错误
3. 修正逻辑矛盾
```

---

## 任务 2: 关系文件生成

从概览文件中提取制品间的关联关系，生成 JSON 文件。

### 输出

#### 2.1 接口→功能关系
**输出位置：** `omni-doc/specs/relations/interface.json`
```json
[
    { "source": "API-XXX", "targets": ["FUNC-001", "FUNC-002"] }
]
```
- `source`: 从 `interface-overview.md` 表格"接口ID"列提取
- `targets`: 从"功能"列提取，无数据则为 `[]`

#### 2.2 功能→实体关系
**输出位置：** `omni-doc/specs/relations/functions.json`
```json
[
    { "source": "FUNC-XXX", "targets": ["ENTITY-001", "ENTITY-002"] }
]
```
- `targets`: 从 `function-overview.md` 功能详情的"关联实体"行提取

#### 2.3 场景→功能关系
**输出位置：** `omni-doc/specs/relations/scenarios.json`
```json
[
    { "source": "SCN-XXX", "targets": ["FUNC-001", "FUNC-002"] }
]
```
- `targets`: 从 `scenario-overview.md` 场景详情的"关联功能"行提取，无数据则为 `[]`

#### 2.4 需求→场景关系
**输出位置：** `omni-doc/specs/relations/requirements.json`
```json
[
    { "source": "REQ-XXX", "targets": ["SCN-001", "SCN-002"] }
]
```
- `targets`: 从 `requirement-overview.md` 需求详情的"关联场景"行提取，无数据则为 `[]`

---

## 任务 3: 概览文件归档

将中间概览文件从临时目录移动到对应的制品目录下，作为该制品的索引文件。

### 移动规则

| 源文件（`omni-doc/specs-temp/intermediate/`） | 目标位置 |
|----------------------------------------------|---------|
| `interface-overview.md` | `omni-doc/specs/interfaces/interface-overview.md` |
| `entity-overview.md` | `omni-doc/specs/entities/entity-overview.md` |
| `function-overview.md` | `omni-doc/specs/functions/function-overview.md` |
| `scenario-overview.md` | `omni-doc/specs/scenarios/scenario-overview.md` |
| `requirement-overview.md` | `omni-doc/specs/requirements/requirement-overview.md` |
| `project-entry.md` | `omni-doc/specs/project-entry.md` |

### 执行方式
使用 `mv` 移动文件（非复制），移动后 `omni-doc/specs-temp/intermediate/` 目录应为空或仅剩非概览中间产物。

---

## 任务 4: 生成反构摘要

所有任务执行完毕后，生成反构输出摘要，输出到 `omni-doc/specs/SUMMARY.md` 并向用户展示。

### 数据采集

1. **制品统计**：从各概览文件的列表表格中统计行数
2. **工程规模**：使用 shell 命令统计被分析代码库的规模
   - 文件数：`find <项目根> -type f -name "*.py" -o -name "*.java" -o -name "*.go" ... | wc -l`（按实际语言调整）
   - 代码行数：`wc -l` 或 `cloc`（如可用）
   - 主要语言：从 `project-entry.md` 中提取
3. **耗时统计**：从 `omni-doc/specs-temp/task_process.md` 的进度记录推算，或根据实际执行会话数估算

### 输出格式

**输出位置**：`omni-doc/specs/SUMMARY.md`

```markdown
# 反构输出摘要

## 工程概况

| 指标 | 值 |
|------|-----|
| 项目名称 | [项目名] |
| 主要语言 | [语言] |
| 源文件数 | [数量] |
| 代码行数 | [数量] |

## 制品统计

| 制品类型 | 数量 | 输出目录 |
|---------|------|---------|
| 接口 | [N] | `specs/interfaces/` |
| 逻辑实体 | [N] | `specs/entities/` |
| 业务功能 | [N] | `specs/functions/` |
| 业务场景 | [N] | `specs/scenarios/` |
| 系统需求 | [N] | `specs/requirements/` |
| 关系文件 | 4 | `specs/relations/` |
| 架构文档 | 1 | `specs/logic_architecture.md` |
| 上下文文档 | 1 | `specs/context.md` |
| **合计规范文件** | **[总数]** | |

## 引用链路

```
需求(REQ) → 场景(SCN) → 功能(FUNC) → 实体(ENTITY)
                                    ↑
                            接口(API) ─┘
```

## 执行信息

| 指标 | 值 |
|------|-----|
| 执行会话数 | [N] |
| 总耗时(估算) | [时长] |
| 质量审查状态 | ✅/⚠️/❌ |
| 引用完整性 | [通过数]/[总检查数] |
```

---

## 注意事项
- JSON 文件保持良好的格式化（缩进 2 个空格）
- targets 无数据时填写空数组 `[]`
- 确保文件编码为 UTF-8
