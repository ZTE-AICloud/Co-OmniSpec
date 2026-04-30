# 设计文档：`ai-friendly-component-srp-orchestrate`

## 背景与问题定义

在一个中大型代码库（尤其是组件库/模块化仓库）中，**单个模块是否符合单一职责原则（SRP）**往往无法通过抽样评审得出可靠结论。该 skill 旨在提供一条“以代码库为粒度”的全量流水线：

- 自动识别项目内的所有模块（按架构层分类）
- 对每个模块执行 SRP 评估（可并发加速）
- 将所有模块结果聚合成一份整体报告（用脚本完成，节省 token）

该 skill 的定位是 **编排器（orchestrator）**：它不直接实现模块识别与 SRP 判定，而是协调已有 skill 与脚本。

## 目标（Goals）

- **全量覆盖**：对代码库中识别出的所有模块执行 SRP 分析，不漏不重（以 `modules.json` 为权威输入）。
- **可控并发**：step02 以“每批最多 5 个 SubAgent”并发运行，保证性能与资源可控。
- **状态隔离**：所有中间产物写入 `state/`，并且每个 SubAgent 仅写自己的输出文件，避免并发写冲突。
- **可复现聚合**：step03 通过确定性的 Python 脚本汇总统计，不依赖 LLM 输出稳定性。
- **可验证**：每一步都有明确检查点与输出格式约束，便于自动化/手工排错。

## 非目标（Non-goals）

- 不负责定义 SRP 的具体评分模型与违规判定逻辑（由 `ai-friendly-arch-guard-module-single-responsibility` 提供）。
- 不负责模块发现规则的细节与准确性优化（由 `ai-friendly-module-identifier` 提供）。
- 不提供 UI/可视化看板，仅输出结构化 JSON 报告。

## 触发条件（When to use）

当你需要对**整个代码库**进行“模块单一职责原则合规性检查/基线评估/回归对比”时使用该 skill，典型场景：

- 架构治理：识别职责边界模糊、模块耦合过高的区域
- 组件库健康度：为“拆分/合并/重构”提供量化依据
- 质量门禁：在关键分支/版本发布前进行全量扫描

## 输入与输出契约

### 输入

- **`project_path`**：待分析项目根目录**绝对路径**。

### 输出（最终产物）

- **`output/summary.json`**：整体汇总报告，包含：
  - `aggregate`：全量统计（均值、分档分布、各维度均值等）
  - `modules`：每个模块的摘要（名称、路径、分数、违规数、详情文件路径）

## 目录与状态文件规范

该 skill 强制使用以下目录结构以保证状态隔离与可追溯：

```
state/
  modules.json                    # step01 产物：模块清单
  step02-analyze-modules/         # step02 产物：每模块 SRP 分析
    {module_name}.json
output/
  summary.json                    # step03 产物：最终汇总报告
```

约束：

- `state/` 与 `output/` **均相对 skill 工作目录**（通常为 `.claude/skills/ai-friendly-component-srp-orchestrate/` 下）。
- step02 子任务必须通过 `output_path` 写入唯一文件路径，禁止共享文件或追加写。

## 总体执行流程（Workflow）

该 skill 的流水线分为三步：

### Step 01：识别所有模块

**执行者**：SubAgent（调用 `ai-friendly-module-identifier`）

**输入**：`project_path`

**输出**：`state/modules.json`（由 `.claude/skills/ai-friendly-module-identifier/output/modules.json` 复制而来）

**关键动作**：

- 触发模块识别 SubAgent（建议 shallow 扫描深度）
- 等待 SubAgent 完成后，将其输出复制到本 skill 的 `state/modules.json`
- 从 `state/modules.json` 提取模块 `name/path/category` 供 step02 使用

**格式约束**（最小必要字段）：

- `modules`：对象（按架构层分类）
  - 每个模块至少包含：`path`（相对路径）、`name`（目录名）、`files`（文件列表）
- `statistics.total_modules` 应大于 0（若提供）

**SubAgent 返回值（约定）**：

```json
{
  "ok": true,
  "total_modules": 20,
  "state_path": "state/modules.json"
}
```

**验证检查点**：

- `state/modules.json` 存在且可解析
- `modules` 字段存在且为对象
- 至少存在一个架构层分类，且每个模块包含 `path/name/files`

### Step 02：并发执行每模块 SRP 分析（每批最多 5 个）

**执行者**：Main Agent 负责分批调度；每批并发最多 5 个 SubAgent（调用 `ai-friendly-arch-guard-module-single-responsibility`）

**输入**：`state/modules.json`

**输出**：`state/step02-analyze-modules/{module_name}.json`

**流程要点**：

1. 读取 `state/modules.json`，将所有模块扁平化为列表（保留 `name/path/category`）。
2. 将模块列表按批次切分，每批最多 5 个模块。
3. 对每批次，在**同一条消息**中并发发起最多 5 个子任务调用：
   - 每个子任务必须指定唯一的 `output_path`：
     - `state/step02-analyze-modules/{module_name}.json`
4. 等待本批全部完成后，再发起下一批。

**SubAgent 返回值（约定）**：

```json
{
  "ok": true,
  "module": "commands",
  "output_path": "state/step02-analyze-modules/commands.json"
}
```

**输出格式约束（聚合所依赖的字段）**：

每个模块输出 JSON 至少应包含以下可被聚合脚本读取的字段：

- `module_path`: string（模块相对路径，建议由 SRP skill 输出）
- `metric_result.total_score`: number（0-100）
- `metric_result.confidence`: number（0-1）
- `metric_result.score_detail`（可选，但建议提供）：
  - `directory_single_score`: number（0-100）
  - `module_cohesion_score`: number（0-100）
  - `file_single_score`: number（0-100）
- `violation_info.total_count`: number（>=0）

**验证检查点**：

- `state/step02-analyze-modules/` 目录存在
- 目录下 JSON 文件数量 == 模块总数
- 每个 JSON 文件包含 `metric_result.total_score`、`metric_result.confidence`、`violation_info.total_count`
- `total_score` 在 0-100 范围内
- 不混入非模块文件（脚本会跳过 `processing_summary.json`，但应尽量避免产生）

### Step 03：聚合汇总生成整体报告

**执行者**：脚本 `scripts/aggregate.py`

**输入**：`state/step02-analyze-modules/*.json`

**输出**：`output/summary.json`

**脚本行为（关键细节）**：

- 读取输入目录下全部 `*.json`
- 以文件名 stem 作为 `module_name`
- 跳过 `processing_summary.json`
- 从每个模块 JSON 中抽取：
  - `metric_result.total_score`（默认 0.0）
  - `metric_result.confidence`（默认 0.0）
  - `metric_result.score_detail.{directory_single_score,module_cohesion_score,file_single_score}`（存在则计入均值）
  - `violation_info.total_count`（默认 0）
  - `module_path`（用于模块摘要）
- 计算：
  - `avg_total_score` / `avg_confidence` / `avg_violation_count`
  - `avg_score_detail`（三个维度均值）
  - `score_distribution`（excellent/good/medium/poor 四档）

**分档规则**（脚本内置）：

- `excellent`: score >= 90
- `good`: 70 <= score < 90
- `medium`: 50 <= score < 70
- `poor`: score < 50

**执行命令示例**（信息性）：

```bash
python3 scripts/aggregate.py \
  --input-dir state/step02-analyze-modules \
  --output output/summary.json \
  --project-path "$project_path"
```

**验证检查点**：

- `output/srp/summary.json` 存在
- `execution_ctx.execute_status == "success"`
- `scan_statistics.total_units.modules` 与 step02 实际模块数一致
- `evaluation_details.score_distribution` 四档之和 == `scan_statistics.total_units.modules`
- `core_metrics.total_score` 为 0-100 间有效值
- `modules` 数组长度 == `scan_statistics.total_units.modules`

## `output/srp/summary.json` 结构说明

`scripts/aggregate.py` 输出符合 **`aia_metric_fact`** 格式（详见 `config/data_model.md`）：

- `identity_info.skill_id`: `"ai-friendly-component-srp-orchestrate"`
- `identity_info.arch_dimension`: `"结构可导航性"`
- `execution_ctx.skill_version`: 技能版本号
- `execution_ctx.scan_mode`: `"full"` 或 `"increment"`
- `execution_ctx.execute_status`: `"success"`（失败时脚本 `sys.exit(1)`）
- `execution_ctx.start_time` / `end_time` / `duration_ms`: UTC ISO8601 / 耗时
- `core_metrics.total_score`: 所有模块 total_score 均值（0-100）
- `core_metrics.confidence_score`: 所有模块 confidence 均值（0-1）
- `core_metrics.total_violation_count`: 所有模块违规数之和
- `core_metrics.p0_violation_count` / `p1_violation_count`: 按级别聚合
- `evaluation_details.score_detail`: 各子维度均值（directory_single_score / module_cohesion_score / file_single_score）
- `evaluation_details.score_distribution`: 得分分档（excellent/good/medium/poor 四档）
- `violation_records.level_summary`: 违规级别汇总（P0/P1）
- `violation_records.violation_infos`: 违规详情列表（最多 50 条）
- `scan_statistics.total_units.modules`: 扫描模块总数
- `scan_statistics.violation_units.modules`: 存在违规的模块数
- `scan_statistics.valid_units.modules`: 无违规模块数
- `modules`: 每个模块的摘要（扩展字段，非标准 aia_metric_fact 字段）
  - `module_name`: string（来自文件名）
  - `module_path`: string（来自模块 JSON）
  - `total_score`: number
  - `confidence`: number
  - `violation_count`: number
  - `detail_path`: string（模块 JSON 文件路径）

> **注意**：输出路径为 `output/srp/summary.json`（由 `arch-measure` 注册表的 `output_path_hint` 指定）。

## 并发与一致性设计

- **并发上限**：step02 每批最多 5 个 SubAgent，避免资源峰值与输出拥塞。
- **同消息并发**：同一批次必须在同一条消息中发起多个子任务调用，保证真正并发。
- **写入隔离**：每个 SubAgent 仅写入其专属 `output_path`，不共享状态文件。
- **可恢复性**：
  - 若 step02 中途失败，可通过检查 `state/step02-analyze-modules/` 中缺失的模块输出，按缺失项重新跑对应模块（保持幂等）。
  - step03 可重复执行，输出完全由输入文件决定（确定性）。

## 失败模式与处理策略

- **Step01 失败（模块识别为空/格式错误）**：
  - 直接阻断 step02（无模块可分析或数据不可信）。
  - 优先检查 `state/modules.json` 是否复制成功、JSON 是否包含 `modules` 对象。
- **Step02 局部失败（某些模块无输出/字段缺失）**：
  - 允许重跑缺失模块（以文件存在性为准）。
  - 若字段缺失，聚合脚本会用默认值（0.0/0），但这会污染均值；应将其视为“需要修复 SRP skill 输出”的错误而非容忍。
- **Step03 失败（无 JSON 文件）**：
  - `aggregate.py` 在输入目录没有 JSON 时会退出并返回错误码 1。

## 增量模式设计（v1.1 新增）

### 背景

全量模式适合基线评估，但在 CI 场景中，仅需分析变更模块即可实现门禁。增量模式通过 git diff 识别变更模块，大幅减少分析时间。

### 增量流程

在 step01 和 step02 之间插入 **Step 0.5: 识别变更模块**：

1. **Step 01**：识别全量模块 → `state/modules.json`
2. **Step 0.5**：`scripts/identify-changed-modules.sh` 提取变更模块 → `state/changed-modules.json`
3. **Step 02**：读取 `changed-modules.json`（优先）或 `modules.json`，仅分析变更模块
4. **Step 03**：聚合时检测 `changed-modules.json` 存在性，标注 `analysis_mode: "incremental"`
5. **Step 04**（可选）：`scripts/gate-check.py` 根据阈值判定是否通过门禁

### 关键设计

- **模式透明切换**：通过 `state/changed-modules.json` 存在性自动识别增量模式
- **最小侵入**：step02/step03 核心逻辑不变，仅增加输入源判断
- **可追溯**：`summary.json` 记录 `base_commit`、`target_commit`、`analysis_mode`
- **门禁独立**：step04 可按需启用，阈值通过 `.gate-config.json` 外部化

### 目录结构扩展

```
state/
  changed-modules.json            # step0.5 产物（增量模式）
output/
  gate-result.json                # step04 产物（可选）
.gate-config.json                 # 门禁阈值配置
```

## 可扩展点（Extensions）

- **更丰富的分档/阈值**：可将 `classify_score` 的阈值参数化（例如通过 CLI 参数或配置文件）。
- **输出 Schema 固化**：为 `state/modules.json` 与每模块 SRP 输出定义 JSON Schema，并在 step02/step03 前做校验。
- **额外聚合维度**：按 `category`（架构层）分组输出均值与分布（当前脚本未使用 step01 的分类信息）。

## 验收标准（Definition of Done）

- 输入任意 `project_path`，当 step01 识别到 \(N > 0\) 个模块时：
  - step02 生成 \(N\) 个模块输出文件（1 模块 1 文件）
  - step03 生成 `output/summary.json`，并满足：
    - `aggregate.total_modules == N`
    - `len(modules) == N`
    - `score_distribution` 四档之和 == \(N\)
    - `execute_status == "success"`

