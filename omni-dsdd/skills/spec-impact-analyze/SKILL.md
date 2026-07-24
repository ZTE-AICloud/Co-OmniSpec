---
name: spec-impact-analyze
description: 需求波及分析：从需求出发分析已有规格与代码知识，判断可复用范围与波及影响，产出结构化上下文供 context.md 使用，不直接写文件。
user-invokable: false
allowed-tools: Read, Glob, Grep, Task, Agent(knowledge-retrieval-agent), Bash(bash, test, mkdir, python3)
---

# 我的技能

围绕单个功能/需求或变更描述，自动完成**需求波及分析**，输出一份可直接用于填充 `context.md` 的结构化内容。

**核心目标**：

- 从用户描述中提取功能目标、用户类型、业务价值和关键概念
- 基于 REQ/SCN/FUNC/API/ENTITY 及 `relations/*.json` 找到相关/受影响的规格
- 复用 `spec-impact-analyze` 的分析结果，补充架构视角、术语映射、约束与假设
- 产出一份结构化的「上下文中间态」，供上层命令按模板写入 `FEATURE_DIR/context.md`

## 行为准则（整个会话有效，不因对话长度放松）

1. ❗ **不直接写入规范文件** — 所有分析结果以结构化对象/Markdown 返回，不直接写入 `FEATURE_DIR/context.md` 或其它规范文档（REQ/SCN/FUNC/API/ENTITY）。**例外**：`FEATURE_DIR/.runs/internal/context.payload.json` 是与上游 specify 的**结构化契约**（非规范文档），`knowledge_retrieval` 字段必须写入其中，供 knowledge-gate 机器校验，此写入不违反本准则。每次输出前自检
2. ❗ **来源引用** — 所有结论（文档关联、术语映射、约束识别）必须引用具体来源（文件名:行号），无引用来源的结论不允许输出，每次输出前自检
3. ❗ **零结果处理** — 未找到相关文档时输出"未找到相关文档，请确认 DOC_DIR 是否正确"，而非基于猜测补充内容，每次输出前自检
4. 不创建分支、不运行脚本（`spec-impact-gate` 门禁脚本除外，见准则 6）
5. 不直接修改现有 REQ/SCN/FUNC/API/ENTITY 文档
6. ❗ **私域知识检索强约束** — 当 Step 2.1 判定知识源**就绪**（含自愈后）时，Step 4.1 **必须**真实派发 `knowledge-retrieval-agent`，并以其返回如实填写 `context.payload.json` 的 `knowledge_retrieval` 字段（`executed:true` + `hits` 数 + `config_hit/vector_built/graph_built/mode`）。**禁止**在知识源就绪时跳过派发或填 `executed:false`。派发后须运行 `spec-impact-gate.sh`（见 Step 4.3），`gate_exit=0` 方可进入 Step 5；`gate_exit=1` 按 `errors` 补齐后重跑（每步最多 2 次）。上游 specify 的 `_gate_step_3` 会对同一字段做二级钳制，子技能无法绕过。

# 使用时机

在以下场景使用本技能：

- 需要在生成功能规范之前，先基于现有反构文档**收集和整理上下文**
- 希望将「上下文收集」与具体命令（如 `/specify`）解耦，由上层命令统一调用本技能
- 需要一份可直接用于 `context.md` 的结构化上下文，而不是散乱的文档列表

## 使用示例

### 基本调用
调用本技能时提供功能描述：

- **输入**：用户需要新增 GSU 会话删除功能，涉及 UPS 同步
- **DOC_DIR**：默认自动检测，或显式传入 `omni-doc`

### 输出示例
返回结构化上下文：
- `context_mode`: `"evidence_first"` 或 `"default"`
- `on_demand.detected`: `true/false`
- 相关反构文档列表（REQ/SCN/FUNC/API/ENTITY）
- 架构分析与术语对齐

## 依赖与环境

### 前置条件
- `DOC_DIR` 根目录存在且包含 `specs/` 子目录
- `specs/` 下有 `requirements/`、`scenarios/`、`functions/`、`interfaces/`、`logic_entities/` 目录
- 每个目录下有符合命名规范的文档（REQ-*.md 等）
- `KNOWLEDGE_DIR`（私域知识库根目录，**可选**）：缺失时不阻断反构文档分析，仅 Step 4.1 私域检索降级

### 环境检测

**`DOC_DIR`**：如未提供，技能内部通过 `scripts/*/check-prerequisites.*` 自动检测。

**`KNOWLEDGE_DIR`**（处理方式对标 `CLAUDE_WORKING_DIR`：已注入则沿用，缺失才降级解析）。本技能在 specify 之后执行，`${FEATURE_DIR}/.runs/env.sh` 已含 `export KNOWLEDGE_DIR`，故降级源是 env.sh 而非标记文件：

```bash
# 1. source 上游 specify 落盘的 env.sh（含 KNOWLEDGE_DIR、DOC_DIR 等）
[ -f "${FEATURE_DIR}/.runs/env.sh" ] && source "${FEATURE_DIR}/.runs/env.sh"
# 2. 已注入则沿用（不覆盖）；缺失则回退默认 ${CLAUDE_WORKING_DIR}/omni-doc
export KNOWLEDGE_DIR="${KNOWLEDGE_DIR:-${CLAUDE_WORKING_DIR}/omni-doc}"
```

- `KNOWLEDGE_DIR` 与 `DOC_DIR` **独立**：前者供 Step 4.1 私域知识检索（knowledge-retrieval-agent），后者供 Step 2 反构文档分析（specs/），可指向不同目录。
- `KNOWLEDGE_DIR` 是可选知识源，不强制目录存在；目录缺失时 Step 4.1 走 Fallback（本地 glob/Grep）。

# 指令

## 依赖链声明

数据传递（后续步骤必须引用前序实际产出，禁止重新搜索）：

- **Step 2 的输出**（DOC_DIR 路径）→ **Step 3-5 的输入**：所有后续步骤使用 Step 2 检测到的 DOC_DIR，不重新探测
- **Step 3 的输出**（关键词列表、功能目标、用户类型）→ **Step 4 的输入**：检索步骤直接引用 Step 3 提取的关键词，不重新提取
- **Step 4 的输出**（相关文档列表 + 关联度分数）→ **Step 5 的输入**：构建结果时直接引用 Step 4 筛选出的文档列表，不重新检索
- **Step 2.2 的输出**（evidence_first / default 模式）→ **Step 4.2 的触发条件**：on-demand 证据增强仅在 evidence_first 模式下执行，不得自行切换模式

Checkpoint 计数链：
- Step 3 记录：提取关键词数
- Step 4 引用 Step 3 关键词数，输出：筛选出相关文档数
- Step 5 引用 Step 4 文档数，输出：结构化输出各节完成状态

交叉验证：
- Step 5 构建结果前，检查 Step 4 筛选出的文档数是否为 0；为 0 时按零结果处理，不生成假关联

## 1. 输入

调用本技能时，应提供：

- **功能/需求或变更描述文本**（等价于 `/specify` 中的 `$ARGUMENTS`）
- （可选）**DOC_DIR** 根目录；若未提供，则内部通过与 `scripts/*/check-prerequisites.*` 相同的方式检测，默认 `DOC_DIR = omni-doc`

## 2. 获取文档目录

- 如果调用方未显式提供 `DOC_DIR`，本技能内部需：
    - 判断操作系统（Windows / Linux）
    - 运行：
        - Windows: `scripts/powershell/check-prerequisites.ps1 --json --paths-only`
        - Linux: `scripts/bash/check-prerequisites.sh --json --paths-only`
    - 从 JSON 输出中解析 `DOC_DIR`，并派生以下路径：
        - `DOC_DIR/specs/requirements/` → `REQ-*.md`
        - `DOC_DIR/specs/scenarios/` → `SCN-*.md`
        - `DOC_DIR/specs/functions/` → `FUNC-*.md`
        - `DOC_DIR/specs/interfaces/` → `API-*.md`
        - `DOC_DIR/specs/logic_entities/` → `ENTITY-*.md`
        - `DOC_DIR/specs/relations/requirements.json`
        - `DOC_DIR/specs/relations/scenarios.json`
        - `DOC_DIR/specs/relations/functions.json`
        - `DOC_DIR/specs/relations/interface.json`

✅ Checkpoint: "Step 2 完成: DOC_DIR = {检测到的路径}, 五类子目录已派生"
失败降级: Glob 探测失败 → 尝试读取 `omni-doc/specs/` 验证有效性 → 仍失败则输出 "DOC_DIR 探测失败，请显式传入 DOC_DIR 参数"

## 2.1 knowledge-retrieval-agent 知识源检查（机器闸门 + 就地自愈）

在 Step 4 调用 `knowledge-retrieval-agent` sub-agent 之前，按**机器闸门**（非主观推断）判定私域知识源状态（**私域知识库根目录 = `${KNOWLEDGE_DIR}`**，已由「环境检测」段解析；**与反构文档库 `${DOC_DIR}` 独立**）。

三态判定（与 `spec-impact-gate` 的 `_check_knowledge_source` 语义一致，供 Step 4.3 门禁复用）：

- **就绪 (`ready`)**：`${KNOWLEDGE_DIR}` 目录存在且非空 **且** 其下 `knowledge.config.yaml` 存在 → Step 4.1 **必须**派发检索。
- **config 缺失 → 就地自愈 (`self_healed`)**：目录存在但 `${KNOWLEDGE_DIR}/knowledge.config.yaml` 缺失 → **不自降级**，从插件模板拷贝补齐（与 `init_omni_infra.sh` 的 `prepare_knowledge_config` 同源）：
  ```bash
  cp "${CLAUDE_PLUGIN_ROOT}/skills/knowledge-retrieval/knowledge.config.yaml" "${KNOWLEDGE_DIR}/knowledge.config.yaml"
  sed -i 's|^raw_knowledge_dir:.*|raw_knowledge_dir: .|' "${KNOWLEDGE_DIR}/knowledge.config.yaml"
  ```
  自愈后视为就绪 → Step 4.1 必须派发检索。
- **合法跳过 (`skip`)**：`${KNOWLEDGE_DIR}` 目录不存在或为空 → 唯一允许跳过 Step 4.1 的路径，Step 4.3 门禁对 `skip` 状态放行。

> ⚠️ 区分：反构文档（REQ/SCN/FUNC/API/ENTITY）检索走 `${DOC_DIR}/specs/`（Step 2）；本步骤仅检查**私域知识检索**（knowledge-retrieval-agent）的配置源 `${KNOWLEDGE_DIR}`，二者可指向不同目录。

> ⚠️ 禁止以"推断知识可能不充分"等主观理由跳过——只有上述三态机器判定中的 `skip` 才是合法跳过路径。`ready`/`self_healed` 均必须派发。

✅ Checkpoint: "Step 2.1 完成: 知识源状态 = {ready/self_healed/skip}, knowledge_dir = {路径}, config = {已存在/已自愈/缺失}"
失败降级: 目录存在但 config 自愈失败（如插件模板缺失）→ 记 `self_heal_failed`，Step 4.3 门禁记 error，按降级处理

## 2.2 可选优先知识源（on-demand）探测

为增强需求边界识别，本技能支持读取 `DOC_DIR/on-demand/` 作为**可选优先知识源**。必须遵循以下兼容策略：

- 若 `DOC_DIR/on-demand/` 存在且可形成最小追溯链路（`requirement -> function -> interface`），进入 `evidence_first` 模式。
- 若目录不存在、文件缺失或链路不足，进入 `default` 模式，继续执行原有分析流程，不得中断。
- 无论哪种模式，最终都要输出统一结构字段，供上层无差别消费。

探测优先级（从高到低）：

1. `DOC_DIR/on-demand/on-demand-existing-function-analysis-*.md`
2. `DOC_DIR/on-demand/relations/*.json`
3. `DOC_DIR/on-demand/functions/*.md`
4. `DOC_DIR/on-demand/interfaces/*.md`
5. `DOC_DIR/on-demand/logic_architecture.md`

推荐模式判定规则：

- 同时存在 `relations/branch-function.json` 与 `relations/function-interface.json` 且可解析：优先 `evidence_first`。
- 向后兼容：若缺少 `branch-function.json` 但存在 `relations/requirement-function.json`，仍可进入 `evidence_first`。
- 仅存在部分 on-demand 文件但无法形成链路：`default` + 记录 `fallback_reason`。

✅ Checkpoint: "Step 2.2 完成: 模式 = {evidence_first/default}, {N} 个 on-demand 文件已探测"
失败降级: relations/*.json 解析失败 → 记录 JSON 解析错误，切换为 default 模式

## 3. 解析功能/变更描述

从输入描述中提取：

- **功能目标**：系统要达成的能力或效果
- **用户类型 / 角色**：如 GSU、PFU、运维人员等
- **业务价值**：为什么要做这件事
- **关键概念与数据对象**：例如「会话删除」「UPSeid」「ACK」「LDB 同步」等
- **关键词列表**：用于后续检索和匹配（不必原样写入 `context.md`）

## 4. 检索反构文档与基础关联

4.1 和 4.2 相互独立，根据各自前置条件独立判断是否执行：

- **Step 4.1**：当 Step 2.1 判定知识源 `ready`/`self_healed` 时**必须执行**（不得以 Step 4.2 是否执行为由跳过）；仅 `skip` 状态合法跳过
- **Step 4.2**：当 on-demand 存在（evidence_first 模式）时执行

两者可并存（同时满足条件时均执行），也可单独执行。**但 4.1 的执行/跳过只由 Step 2.1 机器闸门决定，与 4.2 完全独立。**

✅ Checkpoint: "Step 4 完成: 4.1={executed:true, hits:M, config_hit:bool} | 4.1={skipped, reason:知识源skip}, 4.2={执行/跳过}"

## 4.1 knowledge-retrieval-agent 检索（知识源就绪时无条件派发）

**触发条件（机器闸门，非主观判断）**：仅当 Step 2.1 判定为 `skip`（目录不存在/为空）时跳过本步；`ready`/`self_healed` **必须无条件派发**，禁止以"推断不充分"为由跳过。

委托 `knowledge-retrieval-agent` sub-agent 执行检索（隔离其厚重上下文），在 prompt 中**显式传入**（subagent 上下文从空白开始，不继承本会话历史）：
- **检索意图文本** = 功能/需求或变更描述原文（等价于 `/specify` 的 `$ARGUMENTS`）
- **已提取要素** = Step 3(解析功能/变更描述) 产出的功能目标 / 用户类型 / 关键概念 / 关键词列表
  （直接引用 Step 3 实际产出，禁止让 sub-agent 重新提取）
- **DOC_DIR** = Step 2 检测到的反构文档目录（默认 `${CLAUDE_WORKING_DIR}/omni-doc`，用于 specs/ 反构文档）
- **KNOWLEDGE_DIR** = 私域知识库根目录（已由「环境检测」段解析，与 DOC_DIR 独立）
- **`@knowledge` 检索路径** = **`${KNOWLEDGE_DIR}`**（私域知识检索根目录）
- **检索配置** = **`${KNOWLEDGE_DIR}/knowledge.config.yaml`**（由 sdd 工程初始化脚本 `init_omni_infra.sh` 的 `prepare_knowledge_config` 步骤在工程初始化时自动生成；sub-agent 在该目录下运行，CLI 自动级联查找配置）
- **额外要求**：要求 sub-agent 在返回里**如实标注** `config_hit`（config 是否命中）、`vector_built`（向量索引是否已构建）、`graph_built`（图谱是否已构建）、`mode`（`enhance`/`baseline`，来源 `config-info`），用于区分「真零结果」与「产物未构建导致的中途降级」

sub-agent 返回带来源（`source_file:location` / 实例 ID）的结构化结果后：
- 直接用于 Step 5 构建，引用其命中文档列表与关联度判断；
- 满足行为准则 2（来源引用）：所有结论沿用 sub-agent 返回的 `source_file/location`；
- 满足交叉验证：若返回命中数为 0，按**真零结果**处理（`executed:true, hits:0`），**不得**当作跳过，不得生成假关联。

**❗ 强制留痕（写入 payload）**：派发完成后（含真零结果），必须把检索结论写入 `FEATURE_DIR/.runs/internal/context.payload.json` 的 `knowledge_retrieval` 字段（完整 schema 见 Step 5 第 7 节）。合法跳过（Step 2.1 = `skip`）时写 `executed:false` + 非空 `skip_reason`。**未写该字段或写了 `executed:false` 而知识源就绪，Step 4.3 门禁必拦。**

> ⚠️ 派发 prompt 只放"这一次检索需要的东西"——意图 + Step 3 要素 + DOC_DIR(反构) + KNOWLEDGE_DIR/@knowledge 路径(私域检索)，
> 不要把本会话的历史、前序 Step 的完整叙述粘进去。

✅ Checkpoint: "Step 4.1 完成: executed=true, 筛选出 {M} 个相关文档, config_hit={bool}, vector_built={bool}, graph_built={bool}, mode={enhance/baseline}"
失败降级: 文档数为 0 → 按真零结果处理（`hits:0`），不生成假关联；产物未构建 → 如实标注并降级，仍记 `executed:true`

## 4.2 on-demand 证据增强（evidence_first 模式）

在 `evidence_first` 模式下，除原有文档检索外，额外执行：

- 读取 `relations/*.json` 构建边界基线：
  - `branch-function.json` 作为功能白名单来源（兼容读取 `requirement-function.json`）。
  - `branch-interface.json` 作为接口白名单来源（兼容读取 `requirement-interface.json`）。
  - `function-interface.json` 作为功能-接口追溯链路来源。
- 读取 `functions/*.md` 与 `interfaces/*.md` 提取：
  - 明确的变更点（新增字段、响应变化、关键流程变化）。
  - 风险提示与证据不足项（用于澄清候选）。
- 读取 `on-demand-existing-function-analysis-*.md` 作为需求级摘要与波及统计补充。

边界控制规则：

- 白名单（in-scope）：在 `relations` 中被 branch（或兼容 requirement）指向的 function/interface。
- 黑名单（out-of-scope）：未在 `relations` 中出现且无直接证据链支撑的对象。
- 灰名单（needs-clarification-candidate）：有摘要提及但证据不完整的对象。

✅ Checkpoint: "Step 4.2 完成: 白名单 {N} 项, 黑名单 {M} 项, 灰名单 {K} 项"
失败降级: relations 文件全部不存在 → 输出 default 模式结果

## 4.3 私域知识检索门禁（必须执行）

Step 4.1/4.2 完成后、进入 Step 5 之前，**必须**运行 `spec-impact-gate` 做机器校验（一级钳制）。该门禁用机器闸门替代主观判断，堵住"知识源就绪却跳过 knowledge-retrieval-agent"。

- **Linux / macOS / Git Bash**：
  ```bash
  bash "${CLAUDE_PLUGIN_ROOT}/skills/spec-impact-analyze/scripts/bash/spec-impact-gate.sh" \
    --feature-dir "$FEATURE_DIR" --record
  ```
- **Windows (pwsh)**：
  ```powershell
  & "${CLAUDE_PLUGIN_ROOT}/skills/spec-impact-analyze/scripts/powershell/spec-impact-gate.ps1" \
    --feature-dir "$FEATURE_DIR" --record
  ```

门禁语义（`gate_exit`）：
- `0`：知识源状态与 `context.payload.json` 的 `knowledge_retrieval` 字段一致（就绪→已派发；skip→已标注跳过）→ 进入 Step 5
- `1`：以下任一 → **不得**进入 Step 5，按 JSON `errors` 补齐后重跑（每步最多 2 次）：
  - 知识源就绪（`ready`/`self_healed`）但 payload 缺 `knowledge_retrieval` 字段
  - `executed:false` 而知识源就绪（即"偷懒跳过"）
  - `executed:true` 但 `hits/config_hit/vector_built/graph_built/mode` 字段缺失或类型错误（无法区分真零结果 vs 中途降级）
  - `executed:false` 但 `skip_reason` 为空
- config 缺失时门禁自动就地自愈（拷贝插件模板 + `raw_knowledge_dir: .`），自愈后视为就绪。

> 上游 specify 的 `_gate_step_3` 会对同一 `knowledge_retrieval` 字段做**二级钳制**——即使本门禁被绕过，specify 阶段仍会拦下不合规 payload。两级门禁互为兜底。

✅ Checkpoint: "Step 4.3 完成: gate_exit=0, knowledge_source={ready/self_healed/skip}, executed={bool}, hits={M}"
失败降级: `gate_exit=1` → 读 `errors` 补齐 payload 或补派 sub-agent，重跑门禁；最多 2 次仍失败则输出降级 payload（`degraded:true`）并继续 Step 5，不得静默跳过

## 5. 构建用于 `context.md` 的结构化结果

1. **功能描述**：
    - 原始输入描述
    - 提炼后的功能目标
    - 用户类型 / 角色
    - 业务价值与动机

2. **相关反构文档**：
    - **反构文档层级关系概览**：按「需求(REQ) → 场景(SCN) → 功能(FUNC) → 接口(API)/逻辑实体(ENTITY)」四层填写本功能的主干链路；用表格列出每层涉及的文档 ID、名称/角色、以及该层驱动的下一层文档（下游），体现“谁驱动谁、谁调用谁”，而非纯文件列表。
    - **需求文档（REQ）**：
        - 相关 REQ-XXX 文件名列表（不含目录）
        - 每个 REQ 与本功能/变更的关系说明与建议变更类型
    - **场景文档（SCN）**：
        - 相关 SCN-XXX 文件名列表
        - 每个场景在本次功能中的角色（扩展/复用/新增）
    - **功能文档（FUNC）**：
        - 相关 FUNC-XXX 文件名列表
        - 每个功能与接口/实体的关键关系与变更建议
    - **接口文档（API）**：
        - 相关 API-XXX 文件名列表
        - 每个接口的消息类型标识符、代码文件路径、与本功能/变更的关系、变更建议
    - **逻辑实体文档（ENTITY）**：
        - 相关 ENTITY-XXX 文件名列表
        - 每个实体在本功能中的作用（请求/响应/内部消息等）与变更建议
    - **代码映射简表**：
        - 代码文件 ↔ API / FUNC / ENTITY 的主要映射关系（用于后续实现阶段参考）

3. **架构分析与设计参考**：
    - 可复用的需求模式（引用现有 REQ 编号 + 简述模式）
    - 可扩展的场景模式（引用现有 SCN 编号 + 简述扩展点）
    - 针对本次功能/变更**需要新增**的需求/场景/功能/接口/实体建议（概要级，不写详细规范）

4. **术语对齐**：
    - 用户术语 → 系统术语映射表（例如：「GSU 会话删除请求」 → `ENTITY-054`，ACK → `ENTITY-055`）
    - 重要的术语差异点说明（同一概念多种叫法时的统一规则）

5. **约束与假设**：
    - 技术约束：性能、时延、可靠性等（引用现有文档或架构约束）
    - 业务规则：从相关 REQ/SCN/FUNC 中抽取的关键业务逻辑约束
    - 显式假设：在缺乏信息时做出的合理假设，供上层命令在规范中引用

6. **on-demand 扩展结构（统一输出，允许为空）**：
    - `context_mode`: `evidence_first` 或 `default`
    - `on_demand.detected`: `true/false`
    - `on_demand.fallback_reason`: 未命中时说明原因（目录不存在/链路不足/文件缺失）
    - `on_demand.scope`:
      - `requirement_id`
      - `direct_functions[]`
      - `indirect_functions[]`
      - `interfaces[]`
    - `on_demand.traceability[]`: `requirement -> function -> interface` 链路
    - `on_demand.contract_deltas[]`:
      - `interface_id`
      - `request_added[]`
      - `response_added[]`
      - `response_modified[]`
    - `on_demand.risks[]`
    - `on_demand.evidence_gaps[]`

7. **私域知识检索留痕（`knowledge_retrieval`，必须写入 `context.payload.json`）**：
    - `executed`: `bool` — Step 4.1 是否真实派发了 knowledge-retrieval-agent（知识源就绪时必须 `true`；仅 Step 2.1 = `skip` 时可为 `false`）
    - `hits`: `int` — 命中相关文档/实例数（真零结果记 `0`，不得省略）
    - `config_hit`: `bool` — sub-agent 标注的 config 是否命中（来源 `config-info`）
    - `vector_built`: `bool` — 向量索引是否已构建（区分"真零结果"与"索引未构建的中途降级"）
    - `graph_built`: `bool` — 图谱是否已构建
    - `mode`: `"enhance"` | `"baseline"` — 检索模式（来源 `config-info`）
    - `skip_reason`: `string|null` — `executed:false` 时必须非空，说明合法跳过原因（目录缺失/为空）

> 该字段是 Step 4.3 门禁与上游 specify `_gate_step_3` 二级钳制的机器契约，字段缺失或不合规会被门禁拦截。

> 输出应以「总结与归纳」为主，而不是简单复制文档原文或罗列文件名。

✅ Checkpoint: "Step 6 完成: 功能描述 ✓, 反构文档 ✓, 架构分析 ✓, 术语对齐 ✓, 约束假设 ✓, on-demand扩展 ✓, knowledge_retrieval ✓ (共7节)")"
失败降级: 某节内容为空 → 该节输出 "（未识别到相关内容）"，不得跳过或留空

## 6. 输出约定

调用本技能时，应返回一个**结构化对象**（或等价的 Markdown 结构），其字段尽量与 `context-template.md` 对齐，方便上层命令直接：

- 必须包含 `context_mode` 与 `on_demand.detected` 字段，供上层决定是否启用边界锁定策略。
- 必须包含 `knowledge_retrieval` 字段（完整 schema 见 Step 5 第 7 节），供 Step 4.3 门禁与上游 specify 二级钳制校验。
- 在 `default` 模式下，`on_demand.*` 字段可为空数组/空对象，但字段应保留。

上层命令（如 `/specify`）只负责：

- 调用本技能获取上下文结构
- 按模板写入 `FEATURE_DIR/context.md`

## Decision Gate

Signal candidates（仅作为调查起点，不能直接升级为结论）：
- 关键词命中 → 仅启动文档检索，不能断言"该文档与此需求相关"
- on-demand 目录存在 → 仅启动 evidence_first 模式探测，不能断言"evidence_first 链路完整"
- 关联度分数 > 0.6 → 仅作为候选筛选阈值，不能断言"文档是核心依赖"

强结论的 Required Evidence：

| Claim Type | Required Evidence |
|------------|-------------------|
| `relational`（文档关联判断）| Read 工具确认的文档 frontmatter + 关键词命中的具体行号 |
| `structural`（模式识别）| Read 工具确认的多个文档原文，不能仅基于 Glob 探测推断 |
| `behavioral`（功能范围判断）| evidence_first 模式下 Read 的 relations/*.json 解析结果 + functions/*.md 内容 |

Counter-evidence 检查：
- 文档关联判断必须检查：文档是否有更新？是否在另一个不相关分支中被修改？
- 白名单/黑名单边界判断必须检查：是否存在灰名单对象需要澄清？
- 证据不足时：降级为 `tentative`，在 `on_demand.evidence_gaps[]` 中列出

Completeness ceiling：
- 仅 Glob 探测到文件存在 → completeness = unresolved，不得输出强关联结论
- Read 了文件但未解析 relations/*.json → completeness = partial，结论降级为 tentative
- 完整 evidence_first 链路 + Read 确认 → completeness = complete，可输出 accepted 结论
