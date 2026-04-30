# 设计文档：`ai-friendly-arch-measure`

## 背景与问题定义

随着 AI 友好架构度量体系的演进，单一职责原则（SRP）仅是众多架构质量指标中的一个。未来还将引入 Token 数统计、模块耦合度、可读性等不同维度的指标，每个指标由独立的 skill 实现（复杂度各异，有些需要 subagent 编排，有些是轻量脚本）。

如果没有统一入口，用户需要记住并逐一调用多个 skill；新增指标时也需要修改调用方的逻辑。该 skill 旨在解决这两个问题：

- 提供**统一的 AI 友好架构度量入口**，屏蔽各指标 skill 的实现差异
- 通过**注册表驱动**实现可扩展性，新增指标 skill 只需注册，无需改动编排逻辑

该 skill 的定位是**跨指标元编排器（meta-orchestrator）**：它不直接实现任何度量逻辑，只负责根据执行参数调度已注册的度量 skill，并聚合所有结果。

## 目标（Goals）

- **统一入口**：提供单一 slash command（`/arch-measure`）覆盖所有 AI 友好架构度量。
- **注册表驱动**：所有度量 skill 的元数据集中在 `metric-registry.json`，编排 skill 本身不感知具体指标。
- **多模式执行**：支持全量（`--all`）、按维度（`--dimension`）、按 skill 名（`--skills`）、默认集（无参数）四种执行模式。
- **聚合报告**：将各度量 skill 的输出结构化聚合为跨维度的统一报告。
- **对扩展开放**：新增度量 skill 时，只需在 `metric-registry.json` 添加一条记录，无需修改编排代码或 SKILL.md。

## 非目标（Non-goals）

- 不负责任何具体指标的度量逻辑（由各叶子 skill 实现）。
- 不感知各度量 skill 内部是否使用 subagent——这是各 skill 的内部实现，对本 skill 透明。
- 不提供 UI 可视化，仅输出结构化 JSON 报告。
- 不负责管理度量 skill 间的数据共享或复用（如两个 skill 都需要模块列表时，各 skill 自行调用 identifier）。

## 触发条件（When to use）

- **完整架构体检**：对代码库进行全维度的 AI 友好性评估
- **按指标单独运行**：在开发过程中针对特定维度（如体积维度）运行
- **CI 集成**：作为统一度量入口嵌入流水线，代替直接调用各 skill

---

## 组件结构

```
agent/skills/ai-friendly-arch-measure/         ← 元编排 skill
├── DESIGN.md                                  ← 本文档
├── SKILL.md                                   ← 技能入口（≤300 行）
├── config/
│   └── metric-registry.json                   ← 核心扩展点：度量 skill 注册表
├── scripts/
│   ├── resolve-skills.py                      ← 根据执行模式从 registry 解析待执行 skill 列表
│   └── aggregate-metrics.py                   ← 聚合所有度量结果，生成 aia_component_summary 格式总报告
└── workflow/
    ├── step01-resolve-skills.md               ← Step 1 执行规范
    ├── step02-execute-skills.md               ← Step 2 执行规范
    └── step03-aggregate-metrics.md            ← Step 3 执行规范

agent/commands/arch-measure.md            ← 用户入口（slash command）

# 运行时生成（在执行工作目录下）
state/
  resolved-skills.json                         ← Step 1 产物
output/
  srp/
    summary.json                               ← SRP skill 产物（aia_metric_fact 格式）
  arch-measure-report.json                     ← 最终聚合报告（aia_component_summary 格式）
```

**Command 与 Skill 的分工**：

| 层 | 文件 | 职责 |
|----|------|------|
| Command | `arch-measure.md` | 用户入口；参数解析；调用 Skill；展示报告摘要 |
| Skill | `ai-friendly-arch-measure/SKILL.md` | 编排逻辑；可被其他 skill/Agent 程序化调用 |

这一分工延续了 OmniSpec2 已有的 command-skill 分离惯例，保证 skill 的可组合性。

---

## metric-registry.json 设计

这是整个系统唯一的扩展点，位于 `config/metric-registry.json`。编排 skill 只读取此文件，不硬编码任何 skill 名或维度信息。

### 结构定义

```json
{
  "version": "1.0",
  "dimensions": ["结构可导航性", "体积维度", "耦合维度", "可读性维度"],
  "metrics": [
    {
      "skill_id": "ai-friendly-component-srp-orchestrate",
      "display_name": "模块单一职责",
      "dimension": "结构可导航性",
      "tags": ["default"],
      "enabled": true,
      "description": "检测模块是否遵守单一职责原则，输出 SRP 合规评分",
      "output_path_hint": "output/srp/summary.json"
    },
    {
      "skill_id": "ai-friendly-metric-token-count",
      "display_name": "Token 数统计",
      "dimension": "体积维度",
      "tags": ["default"],
      "enabled": false,
      "description": "统计各模块/文件的 Token 数，评估代码体积对 AI 理解成本的影响",
      "output_path_hint": "output/token/summary.json"
    }
  ]
}
```

### 字段说明

| 字段 | 类型 | 说明 |
|------|------|------|
| `skill_id` | string | 对应 skill 的 `name` 字段，唯一标识，用于调用 |
| `display_name` | string | 人类可读名称，用于报告和日志 |
| `dimension` | string | 所属度量维度，必须是 `dimensions` 列表中的值 |
| `tags` | string[] | 标签，`"default"` 表示无参数时执行 |
| `enabled` | boolean | `false` 表示 skill 尚未实现，跳过执行，结果标记为 `skipped` |
| `description` | string | 说明该指标度量的内容（文档用） |
| `output_path_hint` | string | 建议的输出路径，传给被调用 skill 的 `output_path` 参数 |

### 扩展原则

- 新增指标 skill：在 `metrics` 数组追加一条记录，`enabled: false` 占位声明
- 实现完成后：将 `enabled` 改为 `true`
- 废弃指标：将 `enabled` 改为 `false`，保留记录用于历史追溯（不删除）

---

## 执行模式设计

`resolve-skills.py` 负责将执行参数翻译成待执行 skill 列表，解耦模式逻辑和调度逻辑。

### 四种模式

| 模式 | 参数形式 | 行为 | 示例 |
|------|----------|------|------|
| **默认集** | 无参数 | 执行 `tags` 包含 `"default"` 且 `enabled: true` 的 skill | `/arch-measure` |
| **全量** | `--all` | 执行所有 `enabled: true` 的 skill | `--all` |
| **按维度** | `--dimension <名称>` | 执行指定维度下所有 `enabled: true` 的 skill | `--dimension 结构可导航性` |
| **按 skill** | `--skills <id,...>` | 执行逗号分隔的指定 skill（忽略 `enabled` 状态，强制执行） | `--skills ai-friendly-component-srp-orchestrate` |

### resolve-skills.py 输出

```json
{
  "execute_mode": "default|all|dimension|skills",
  "resolved": [
    {
      "skill_id": "ai-friendly-component-srp-orchestrate",
      "display_name": "模块单一职责",
      "dimension": "结构可导航性",
      "output_path_hint": "output/srp/summary.json"
    }
  ],
  "skipped": [
    {
      "skill_id": "ai-friendly-metric-token-count",
      "reason": "enabled: false"
    }
  ]
}
```

---

## 总体执行流程（Workflow）

```
arch-measure (command)
    │  解析参数（--all / --dimension / --skills / 无参数）
    ▼
ai-friendly-arch-measure (skill)
    │
    ├─ Step 1: 脚本 resolve-skills.py                  [workflow/step01-resolve-skills.md]
    │          输入：config/metric-registry.json + 执行参数
    │          输出：state/resolved-skills.json
    │          作用：确定本次执行的 skill 列表
    │
    ├─ Step 2: 顺序调用各度量 skill                    [workflow/step02-execute-skills.md]
    │   ├─ 调用 ai-friendly-component-srp-orchestrate
    │   │      传入：project_path, output_path=output/srp/summary.json
    │   │      等待完成 → output/srp/summary.json（aia_metric_fact 格式）
    │   ├─ 调用 ai-friendly-metric-token-count（未来）
    │   │      传入：project_path, output_path=output/token/summary.json
    │   │      等待完成 → output/token/summary.json（aia_metric_fact 格式）
    │   └─ ...（按 resolved-skills.json 顺序执行）
    │
    └─ Step 3: 脚本 aggregate-metrics.py               [workflow/step03-aggregate-metrics.md]
               输入：state/resolved-skills.json + output/**/summary.json
               输出：output/arch-measure-report.json（aia_component_summary 格式）
```

### 关于 Step 2 的执行策略

各度量 skill 在逻辑上相互独立，但考虑到以下因素采用**顺序执行**（而非并发）：

- 各度量 skill 内部可能已有 subagent 并发（如 `srp-orchestrate`），叠加并发会导致资源不可控
- 度量 skill 复杂度差异大（简单 vs 含 subagent），并发收益不稳定
- 顺序执行便于错误定位：某个 skill 失败时可精确知道是哪一步

若后续出现多个轻量 skill 需要加速，可在 registry 中增加 `parallel_group` 字段，同组内并发执行。

---

## 输出规范

### 目录结构（运行时生成）

```
state/
  resolved-skills.json              ← Step 1 产物
output/
  srp/
    summary.json                    ← ai-friendly-component-srp-orchestrate 的输出（aia_metric_fact 格式）
  token/
    summary.json                    ← ai-friendly-metric-token-count 的输出（未来，aia_metric_fact 格式）
  arch-measure-report.json          ← 最终聚合报告（aia_component_summary 格式）
```

### 各度量 skill 的输出格式：aia_metric_fact

每个度量 skill 的 `output/summary.json` 须遵循 `aia_metric_fact` 表结构（详见 `config/data_model.md`）：

```json
{
  "identity_info": {
    "skill_id": "ai-friendly-component-srp-orchestrate",
    "arch_dimension": "结构可导航性"
  },
  "execution_ctx": {
    "skill_version": "v1.0",
    "scan_mode": "full|increment",
    "execute_status": "success|failed",
    "start_time": "ISO8601",
    "end_time": "ISO8601",
    "duration_ms": 12345
  },
  "core_metrics": {
    "total_score": 0.85,
    "confidence_score": 0.80,
    "total_violation_count": 5,
    "p0_violation_count": 0,
    "p1_violation_count": 5
  },
  "evaluation_details": {
    "score_detail": {
      "directory_single_score": 0.85,
      "module_cohesion_score": 0.80,
      "file_single_score": 0.79
    },
    "confidence_detail": {
      "structure_confidence": 0.8,
      "semantic_confidence": 0.75
    }
  },
  "violation_records": {
    "level_summary": { "P0": 0, "P1": 5 },
    "violation_infos": [
      {
        "type": "string",
        "level": "P1",
        "scope_path": "string",
        "resources": [],
        "suggestion": "string"
      }
    ],
    "exempt_infos": []
  },
  "scan_statistics": {
    "total_units": { "modules": 20 },
    "violation_units": { "modules": 3 },
    "valid_units": { "modules": 17 }
  }
}
```

### 最终报告格式：aia_component_summary

`output/arch-measure-report.json` 遵循 `aia_component_summary` 表结构（详见 `config/data_model.md`）：

```json
{
  "identity_info": {
    "project_id": "string",
    "component_id": "string",
    "component_name": "string",
    "component_repo": "/path/to/project",
    "tool_version": "v1.0"
  },
  "scan_result": {
    "total_skill_count": 1,
    "total_score_avg": 0.85,
    "total_violations": 5,
    "p0_total": 0,
    "p1_total": 5,
    "p2_total": 0,
    "scan_time": "ISO8601",
    "statistic_info": {
      "modules": 20,
      "files": 30
    }
  },
  "dimension_data": {
    "arch_dimension_list": ["结构可导航性"],
    "dimension_summary": {
      "结构可导航性": {
        "score": 0.85,
        "status": "success|skipped|failed",
        "skill_count": 1
      }
    }
  },
  "relation_mapping": {
    "skill_id_list": ["ai-friendly-component-srp-orchestrate"],
    "dimension_metric_mapping": {
      "结构可导航性": ["ai-friendly-component-srp-orchestrate"]
    }
  },
  "_meta": {
    "execute_status": "success|partial|failed",
    "execute_mode": "default|all|dimension|skills",
    "overall_grade": "S|A|B|C|D",
    "skipped_skills": ["ai-friendly-metric-token-count"],
    "failed_skills": []
  }
}
```

> `_meta` 为本 skill 私有扩展字段，不在 `aia_component_summary` 标准字段范围内，保留于报告中便于调试和 CI 展示。评级映射：S(≥0.9) / A(≥0.75) / B(≥0.6) / C(≥0.4) / D(<0.4)。

### 对各度量 skill 的输出协议约束（最小必要集）

聚合脚本 `aggregate-metrics.py` 只从各 skill 的 `summary.json` 中读取以下字段：

```json
{
  "identity_info": {
    "skill_id": "...",
    "arch_dimension": "..."
  },
  "execution_ctx": {
    "execute_status": "success|failed"
  },
  "core_metrics": {
    "total_score": 0.0,
    "total_violation_count": 0,
    "p0_violation_count": 0,
    "p1_violation_count": 0
  },
  "scan_statistics": {
    "total_units": {}
  }
}
```

其余字段（`evaluation_details`、`violation_records` 详情等）由各 skill 自行定义，聚合脚本不感知。

---

## 失败模式与处理策略

| 失败场景 | 处理策略 |
|----------|----------|
| `resolve-skills.py` 执行失败 | 阻断整个流程，报告 registry 解析错误 |
| 某个度量 skill 执行失败 | **容错继续**：记录 `_meta.failed_skills`，继续执行其余 skill，最终 `_meta.execute_status: "partial"` |
| 所有 skill 均失败 | `_meta.execute_status: "failed"`，不运行聚合脚本 |
| 某 skill 输出缺少 `core_metrics.total_score` | 聚合时该 skill 评分标记为 `null`，不计入 `scan_result.total_score_avg` |
| `aggregate-metrics.py` 执行失败 | 各 skill 的原始 `summary.json` 仍存在，可手动查阅，报告生成失败不影响原始数据 |

**容错继续**的设计依据：各度量指标相互独立，一个指标失败不应导致其他已完成的度量结果丢失。

---

## 可扩展点（Extensions）

### 近期可扩展点

1. **新增度量 skill**：只需在 `config/metric-registry.json` 追加记录，无需修改 SKILL.md
2. **调整维度权重**：在 registry 的 dimension 级别增加 `weight` 字段，聚合脚本读取加权均值
3. **新增执行模式（如按 tag）**：只需修改 `resolve-skills.py`，SKILL.md 无感知

### 中期可扩展点

4. **skill 间依赖（共享前置数据）**：在 registry 增加 `depends_on` 字段，`resolve-skills.py` 按拓��顺序排列执行��列
5. **并发执行分组**：在 registry 增加 `parallel_group` 字段，同组��� skill 并发执行（适合轻量 skill）
6. **增量模式透传**：将 `base_commit`/`target_commit` 参数透传给支持增量模式的度量 skill

### 已知约束

- 各度量 skill 的 `output_path` 参数命名需统一（当前 SRP skill 已支持此参数）
- 新增 skill 若不支持 `output_path` 参数，需先改造该 skill 再注册

---

## 验收标准（Definition of Done）

**Step 1（resolve-skills.py）**：
- `state/resolved-skills.json` 存在且可解析
- `resolved` 列表中的 `skill_id` 均在 registry 中存在
- `--dimension` 参数传入非法值时返回清晰错误信息

**Step 2（skill 调用）**：
- 每个 resolved skill 执行完毕后，`output_path_hint` 对应文件存在
- 某 skill 失败时，其余 skill 正常继续执行

**Step 3（aggregate-metrics.py）**：
- `output/arch-measure-report.json` 存在且可解析，格式符合 `aia_component_summary`
- `dimension_data.arch_dimension_list` 中的维度集合与 `resolved-skills.json` 中的维度一致
- `scan_result.total_score_avg` 仅计算 `execution_ctx.execute_status: "success"` 的 skill

**端到端**：
- 新增一条 `enabled: false` 的 registry 记录，运行结果中该 skill 出现在 `skipped_skills`
- 将已有记录的 `enabled` 改为 `true`，该 skill 在默认模式下被执行

---

## 与现有 skill 的关系

```
ai-friendly-arch-measure (本 skill，元编排层)
    │
    ├─ 调用 → ai-friendly-component-srp-orchestrate (SRP 指标编排层)
    │              │
    │              ├─ 调用 → ai-friendly-module-identifier (叶子 skill)
    │              └─ 调用 → ai-friendly-arch-guard-module-single-responsibility (叶子 skill)
    │
    └─ 调用 → ai-friendly-metric-token-count (未来，叶子或编排 skill)
```

本 skill 只与各"指标编排 skill"或"指标叶子 skill"交互，不直接调用 `module-identifier` 等基础 skill（这是各指标 skill 的内部实现细节）。

---

## 波及分析与变更设计

### 背景

引入 `aia_metric_fact` / `aia_component_summary` 数据模型后，已有 skill 的输出结构需要适配。本节描述波及范围和变更方案。

### 波及 skill：`ai-friendly-component-srp-orchestrate`

#### 当前输出结构 vs. aia_metric_fact 字段映射

| 当前 `output/summary.json` 字段 | aia_metric_fact 字段 | 变更类型 |
|-------------------------------|----------------------|---------|
| `skill_id` | `identity_info.skill_id` | 重构：移入 `identity_info` |
| —（无）| `identity_info.arch_dimension` | **新增**：固定值 `"结构可导航性"` |
| `rule_version` | `execution_ctx.skill_version` | 重命名 + 重构：移入 `execution_ctx` |
| `execute_status` | `execution_ctx.execute_status` | 重构：移入 `execution_ctx` |
| `analysis_mode` | `execution_ctx.scan_mode`（`"full"/"incremental"` → `"full"/"increment"`） | 重命名 + 值规范化 + 重构 |
| `start_time` | `execution_ctx.start_time` | 重构：移入 `execution_ctx` |
| `end_time` | `execution_ctx.end_time` | 重构：移入 `execution_ctx` |
| `duration_ms` | `execution_ctx.duration_ms` | 重构：移入 `execution_ctx` |
| `aggregate.avg_total_score` | `core_metrics.total_score` | 重命名 + 重构：移入 `core_metrics` |
| `aggregate.avg_confidence` | `core_metrics.confidence_score` | 重命名 + 重构 |
| `aggregate.avg_violation_count` | `core_metrics.total_violation_count` | 重命名 + 重构 |
| —（无）| `core_metrics.p0_violation_count` | **新增**：从各模块 JSON 的 `violation_info` 按级别聚合 |
| —（无）| `core_metrics.p1_violation_count` | **新增**：同上 |
| `aggregate.avg_score_detail` | `evaluation_details.score_detail` | 重构：移入 `evaluation_details` |
| —（无）| `evaluation_details.confidence_detail` | **新增（可选）**：暂可省略或填空对象 |
| —（无）| `violation_records` | **新增**：汇总各模块的违规记录（`level_summary` 必填，`violation_infos` 可截断保留 Top-N） |
| `aggregate.total_modules` | `scan_statistics.total_units.modules` | 重构：移入 `scan_statistics.total_units` |
| —（无）| `scan_statistics.violation_units.modules` | **新增**：统计 `violation_count > 0` 的模块数 |
| —（无）| `scan_statistics.valid_units.modules` | **新增**：`total_units.modules - violation_units.modules` |
| `modules`（模块明细列表）| 不在 aia_metric_fact 标准字段范围内 | **保留**：作为扩展字段，聚合脚本不感知 |
| `base_commit` / `target_commit` | 不在 aia_metric_fact 范围内 | **保留**：作为扩展字段，放入顶层或 `execution_ctx` 扩展位 |

#### 变更范围

| 文件 | 变更类型 | 变更内容 |
|------|---------|---------|
| `scripts/aggregate.py` | **必须修改** | 输出结构从平铺重构为 `aia_metric_fact` 嵌套格式；新增 p0/p1 按级别聚合；新增 `scan_statistics` 违规/有效单元统计 |
| `SKILL.md` §最终输出 | **必须修改** | 更���� `output/summary.json` 字段说明以反映新结构 |
| `workflow/step03-aggregate-results.md` | **必须修改** | 更新字段说明和示例 |
| `DESIGN.md` | **必须修改**（本文档）| 已在本次更新 |

#### 不需变更

- `workflow/step01-identify-modules.md`、`step02-analyze-modules.md`：仅涉及中间产物，不影响最终输出格式。
- `scripts/gate-check.py`：读取 `output/summary.json` 的 `aggregate.*` 字段，需评估是否同步更新字段路径（建议在 `gate-check.py` 中同步适配新字段路径，作为独立小变更）。
- `ai-friendly-arch-guard-module-single-responsibility`（叶子 skill）：其单模块输出格式由自身定义，本次变更不涉及。

#### 兼容策略

`aggregate.py` 输出结构切换为 `aia_metric_fact` 后为**破坏性变更**（breaking change）。建议：
- 同步更新本 skill（`arch-measure`）的 `aggregate-metrics.py`，使其读取新字段路径 `core_metrics.total_score`（而非旧的 `aggregate.avg_total_score`）。
- `gate-check.py` 中若硬编码了 `aggregate.*` 路径，需同步修改。
- 不保留向后兼容的旧字段（避免双写膨胀），在变更时一次性迁移。
