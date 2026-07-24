---
name: knowledge-retrieval
description: 私域项目知识检索与知识库构建。支持两种模式：enhance（用户提供知识模型，typed 精细检索）与 baseline（无建模要求，chunk 窗口切片向量 + graphify 图谱兜底）。当需要从项目知识沉淀中获取信息以辅助需求分析、方案设计、编码、测试，或需要构建/刷新知识索引时使用。
when_to_use: |
  检索场景（默认）：
  1. 查阅特定需求/场景/功能/实体/接口（enhance 模式有 ID/类型可锚定）；
  2. 语义查找"和某话题相关的知识"（两模式均可）；
  3. 了解知识结构（仅 enhance）；
  4. 溯源 REQ↔SCN↔FUNC↔ENTITY↔API（仅 enhance 且启用关系）；
  5. 获取某话题在全文档库中的关联上下文子图（图上下文召回，两模式均可）。
  构建场景（build 选项）：
  6. 首次接入或原始知识/文档更新后，需要构建/刷新向量索引与图谱时——加载 reference/build.md 执行。支持 --build（首次）/ --build --update（增量）/ --build --force（强制重建）。
  持久化配置场景：
  7. 想让私域知识库路径在多次 /sdd 间持久生效、免每次传参或 export —— 用 kb-config set 写入 shell 配置（默认 ~/.bashrc）。
allowed-tools: Read, Glob, Grep, Skill, Bash, Task, Agent
argument-hint: "[查询：自然语言描述诉求（默认只读）] --knowledge-dir <dir> [--build [--update|--force]] [--kb-config set <dir> | show | unset]"
---

# Knowledge Retrieval Skill

## 两种操作（与 enhance/baseline 数据模式正交）

本 Skill 有两种操作，**默认是检索**：

### 检索（默认 · 只读 · 无需任何参数）

直接说明检索诉求即可，不带任何标志。Agent 自动 `config-info` 探测 →
按 `mode`（enhance/baseline）走检索工作流。**不写任何产物。**

### 构建（`--build` / `--update` / `--force` · 写产物 · 显式触发）

首次接入或原始知识更新后调用，三态互斥、由用户显式选择：
- `--build`：首次全新构建（向量索引 + graphify 图谱）。
- `--build --update`：增量刷新（向量增量、graphify `--update`）。
- `--build --force`：强制重建（删 graphify-out + 向量 `--force`）。

**触发方式**：用户消息含上述标志，或明确要求"构建/刷新/重建知识库"。Agent 加载
`reference/build.md` 执行编排：装依赖(一次) → 装/检测 graphify → 建向量索引 →
**图谱构建在主线程直接加载并运行 graphify skill（skill 方式，产物自动落盘）**。构建完成后回到检索。

> 「检索 vs 构建」是**做什么**（读 / 写产物）；「enhance vs baseline」是**数据怎么组织**
> （有 / 无知识模型）。二者正交，可任意组合，例如「baseline + 构建」=
> 无模型项目首次建 chunk 索引与图谱。`--build` 是 Skill 触发关键字，不是 CLI 子命令。

### 执行说明

**在项目执行目录下运行**（不要 cd 进 skill 安装目录，否则 CLI 找不到 knowledge.config.yaml）：

```
PYTHONPATH="${CLAUDE_SKILL_DIR}" python -m scripts.cli --pretty <subcommand> [args]
```

CLI 自动从当前目录逐级向上查找 `knowledge.config.yaml`；查找失败可追加 `--config <绝对路径>`。

> ⚠️ 图谱/代码检索**在当前 skill 上下文内直接驱动 graphify CLI**：确认 cwd 为项目根后，**加载 `reference/graph-query.md`按其执行**——它内部完成词表扩充 → 遍历 → 调 `graphify query/path/explain`，从 cwd 的 `./graphify-out/graph.json` 读图。不嵌套调用 graphify skill，省去其构建期上下文。
> 检索**基本只读**；其中图查询会按 `graph-query.md` 写一条**检索路径记录缓存**（`graphify save-result` 回流 + `reflect` 的 LESSONS.md），用于增强后续检索命中，除此之外不写任何产物。需要全量子图时直接 `Read ./graphify-out/graph.json`。
> **构建会写产物**，正文见 `reference/build.md`，仅在构建时按需加载。

---

# 阶段 0 · 能力探测（检索操作下，每次会话第一件事，必做，构建操作下可跳过）

先用一条命令摸清模式与各检索器/产物状态，后续所有门控都基于它：

```
PYTHONPATH="${CLAUDE_SKILL_DIR}" python -m scripts.cli --pretty config-info
```

返回示例：

```json
{
  "config_path": "/proj/knowledge.config.yaml",
  "mode": "baseline",
  "raw_knowledge_dir": "./raw_knowledge",
  "vector_enabled": true,
  "vector_index_exists": false,
  "graph_enabled": true,
  "graph_path": "/proj/graphify-out/graph.json",
  "graph_exists": false
}
```

**第一门控 · 模式路由（`mode`）**：

- `mode = "enhance"` → 有知识模型。走**完整工作流**（阶段 1 理解模型 → typed 渐进检索），全原语可用。
- `mode = "baseline"` → 无知识模型。**跳过阶段 1**（无模型可理解），使用 `vector-search`（chunk 级）+ **加载 `reference/graph-query.md` 并按其执行 graphify 查询（query/path/explain）** 双路召回；typed 类原语不可用（调用会返回 `unavailable_in_baseline_mode`）。

**第二门控 · 产物就绪**：

- `vector_enabled=true` 但 `vector_index_exists=false` → 向量索引未构建。**提示用户运行 build 选项**（见下文「构建（build）选项」），不要自动代跑。
- `graph_enabled=true` 但 `graph_exists=false` → 图谱未构建。同样提示走 build 选项。
- 二者就绪后正常检索。

探测一次，记住结论（模式 + 各产物状态），整个流程据此选路。

---

# 构建（--build）选项 —— 按需加载

当用户消息含 `--build`，或 `config-info` 显示 `vector_index_exists=false` /
`graph_exists=false`、或用户要求"构建/刷新知识库/重建索引"时，**加载并按
`reference/build.md` 执行**：

```
读取 ${CLAUDE_SKILL_DIR}/reference/build.md，按其中分步流程执行构建。
```

build 选项会：检测系统并一键安装 graphify（用 `scripts/` 下的安装脚本）；按 `mode` 决定构建内容（enhance 建属性级索引、baseline 建 chunk 索引）；两模式都构建 graphify 图谱（**图谱构建在主线程直接加载并运行 graphify skill**）。**构建会写产物，不属于只读检索**，仅在此显式触发。构建完成后回到检索工作流。

---

# 检索工作流（按阶段执行）

检索效果差，多半是"没搞清要找什么、知识长什么样就直接搜"。**先探测能力 → 再立意图 → 渐进检索**，全程锚定核心意图。enhance 与 baseline 的差异见每阶段标注。

## 阶段 1 · 理解知识模型（仅 enhance；baseline 跳过）

- `list-entity-types`：有哪些知识类型、数量、用途。
- 对意图相关类型 `describe-entity-type <type_id>`：看属性 schema、哪些 `searchable`、枚举/必填。
- 需要时 `list-searchable-attributes`：确认向量检索实际生效在哪些属性（`effective=true` 才生效）。

产出直接喂给阶段 3 的收窄参数。若意图概念在模型里无对应类型/属性，如实说明，不硬搜。

> **baseline 模式**：本阶段全部跳过——没有 schema 可理解。直接进入阶段 2。

## 阶段 2 · 明确检索意图

写明核心意图（找什么、支撑哪个研发活动）、涉及类型（enhance 用 type_id 锚定；baseline 用自然语言话题）、已知锚点（ID / 名称 / 仅话题语义）、子目标拆解。每步回头校验是否仍服务核心意图。

## 阶段 3 · 快速建立背景

- **enhance**
  - **有 ID** → `get-instance` / `get-attribute`
  - **有名称** → `fuzzy‑search`
  - **图谱可用** → **加载 `reference/graph-query.md` 并按其执行 graphify 查询（query/path/explain）**
- **baseline**
  - **主题定位**
    - `vector‑search "<话题>" --top‑k 5`
      - **粒度**：chunk 级
      - **返回**：切片 + 文件名 + `location`
      - **用途**：先看话题落在哪些文档
  - **图谱可用** → **加载 `reference/graph-query.md` 并按其执行 graphify 查询（query/path/explain）**
  - **查看库中已有文档** → `list-documents`（全量列出相对路径 + 文件名）
  - **已知大概文件名** → `fuzzy‑search "<名称>"` 匹配文件名/路径 → 返回 `source_file`

**要求：图谱可用情况下，请务必使用 graphify 查询（query/path/explain）进行信息检索**
## 阶段 4 · 渐进式深入

- **enhance**
  - **向量检索收窄** → `vector‑search` 配合 `--type-ids` / `--attributes`
  - **精确取值** → `fuzzy‑search`、`get-instance --attributes`、`get-attribute`
  - **图谱回连**
    1. 用 `graphify`查询 返回子图的 **`label` / `source_file`**，以 `fuzzy‑search` 反查为 KB 实例 ID
    2. 再调用 `get‑instance` 取完整信息

- **baseline**
  - **多轮向量收敛**
    - 调整 `--top‑k` / `--min‑score`（无类型/属性时可收窄），命中切片即视为主要证据
  - **回连方式**
    - 原语只返回：切片正文、`source_file`、`location`
    - **若切片不足以支撑结论** → 用 `Read` 打开对应 `source_file` 的 `location` 区段读取上下文（按需，不要默认全文读取）
  - **图谱回连** → `graphify`查询 返回子图的 `source_file` 与切片在文件维度对齐；需要全量子图时 `Read ./graphify-out/graph.json`

- **每轮判断**
  1. 信息是否足以支撑核心意图？
  2. 仍缺哪块内容？

## 阶段 5 · 兜底降级（成本最高，前面都不够才用）

- **enhance**
  - `list‑instances <type_id>`（必要时可不加 filter）全量列出实例，按元数据逐条打分 → 高分项再 `get‑instance` 深取

- **baseline**
  - `list‑documents` 全量列出文档 → 按文件名/路径逐条打分挑选高分项 → `Read` 对应 `source_file` 确认
  - 或调大 `vector‑search --top‑k`（建议 15–20）
  - 或重新 加载 `reference/graph-query.md` 并按其执行 graphify 查询（query/path/explain），换话题词重试
  - **仍找不到** → 如实告知，绝不编造

---

# 可选参数与渐进式收窄

## vector-search

`vector-search <query> [--type-ids ...] [--attributes ...] [--top-k N] [--min-score F]`

- `--type-ids` / `--attributes`：**仅 enhance 生效**，把语义检索限定到类型/属性，最有效的提精手段。baseline 下忽略这两个参数。
- `--top-k`：背景探查用小值（3–5），兜底补全调大（15–20）。
- `--min-score`：背景探查可不设；要高确定性结论时设较高阈值（0.7+）。

**enhance 渐进范例**：`vector-search "支付重试" --top-k 5`（不限类型看落点）→ 收窄 `vector-search "支付失败重试策略" --type-ids requirement --attributes 需求陈述 --top-k 8 --min-score 0.6`。

**baseline 范例**：`vector-search "支付失败重试策略" --top-k 5` → 看命中切片的 `source_file`/`location` → 不够则 `vector-search ... --top-k 15` 或 `Read` 源文件区段。

返回顶层含 `"mode"`：`enhance` 的 hit 形如 `{id,type,attribute,score,snippet}`；`baseline` 的 hit 形如 `{source_file,location,score,snippet}`。

## 其他（仅 enhance）

`fuzzy-search`、`get-instance --attributes`、`get-attribute`、`list-instances --filter`：用法同前，baseline 下均不可用。

---

# 门控小结

- **mode=baseline** → 跳过阶段 1，typed 原语返回 `unavailable_in_baseline_mode`，使用 `vector-search`(chunk) + 加载 `reference/graph-query.md` 并按其执行 graphify 查询（query/path/explain）。
- **vector/graph 产物缺失** → 提示用户走 build 选项，不自动代跑；用其它可用原语先尽力完成，不中断。
- **graph_enabled=true 且 graph_exists=true** → 加载 `reference/graph-query.md` 并按其执行 graphify 查询（query/path/explain）（graphify 内部完成词表扩展 + 遍历 + 回流）。拿到返回的精简子图后在主线程做回连（enhance：`fuzzy-search`→`get-instance`；baseline：直接 `Read` 源文件）；需全量子图时 `Read ./graphify-out/graph.json`。


---

# 原语清单

## 能力探测（阶段 0）
- **config-info**：返回 `mode` 与各检索器/产物状态。每次会话先跑。

## 持久化配置（运维类，不依赖 config.yaml / KB 产物）
- **kb-config set `<绝对路径>` [--shell-file `<file>`]**：把私域知识库路径持久化写入 shell 配置（默认 `~/.bashrc`），
  避免每次 `/sdd` 手动传 `--knowledge-dir` 或 export。已存在则改值、不存在则追加；相对路径自动转绝对路径；幂等。
- **kb-config show [--shell-file `<file>`]**：查看 shell 配置里的持久化值 与 当前进程实际生效值，并报告是否一致。
- **kb-config unset [--shell-file `<file>`]**：从 shell 配置删除该持久化行（不存在则返回 noop）。
- **优先级**：`--knowledge-dir`(CLI) > `KNOWLEDGE_DIR`(env / `~/.bashrc`) > 默认 `omni-doc`，与 sdd 全链路一致。
- **生效**：修改 shell 配置后需**新开终端**或 `source ~/.bashrc`；当前已运行的 Claude Code 会话不会自动刷新环境变量。
- **探测顺序**：`--shell-file` > `$BASH_RC` > `~/.bashrc`。

## 结构类（阶段 1，仅 enhance）
- **list-entity-types** / **describe-entity-type `<type_id>`** / **list-searchable-attributes**

## 精确类（仅 enhance）
- **list-instances `<type_id>` [--filter JSON]** / **get-instance `<id>` [--attributes ...]** / **get-attribute `<id> <attr>`**

## 精确类（仅 baseline）
- **list-documents**：枚举 raw_knowledge_dir 下可检索的文档（相对路径 + 文件名）。
  对等 enhance 的 list-instances，用于兜底遍历与精确定位前的全量浏览。取细节用 `Read <source_file>`。

## 语义/定位类（两模式，按 mode 行为不同）
- **vector-search**：enhance 属性级、baseline chunk 级，返回含 `mode`。
- **fuzzy-search**：**enhance** 模糊匹配实例名（返回 id/type/name）；
  **baseline** 模糊匹配文件名/路径（返回 source_file/name）。返回含 `mode`。

## 图谱类（两模式，受 graph 门控）
- 加载 `reference/graph-query.md` 并按其执行 graphify 查询（query/path/explain）：
  图上下文召回，ID 不互通，然后进行回连
  （enhance 用 fuzzy-search，baseline 用 Read 源文件）；全量子图见 `./graphify-out/graph.json`。

---

# 组合式用法

- **enhance · "支付整体设计牵扯哪些需求/功能"**：config-info 确认 enhance + graph 就绪 → list/describe entity types → 加载 `reference/graph-query.md` 并按其执行 graphify 查询（query/path/explain）（传入 "支付 退款 重试 牵扯哪些需求和功能"）→ 按返回子图的 source_file/label 用 fuzzy-search 回连 → get-instance。
- **baseline · "项目里支付是怎么设计的"**：config-info 确认 baseline + 产物就绪 → `vector-search "支付 退款 重试 设计" --top-k 8` 看命中切片 → 加载 `reference/graph-query.md` 并按其执行 graphify 查询（query/path/explain）（传入 "支付设计"）查关联面 → 必要时 `Read` 高分切片对应 source_file 区段确认。

- **未构建**：config-info 显示 `vector_index_exists=false` → 提示用户"知识索引未构建，请触发 build 选项构建" → 用户同意后加载 reference/build.md 执行。

---

# 运维类（人工用，详见 reference/build.md）
- `build-vector-index [--force]`：构建向量索引（两模式通用，按 config mode 自动选属性级/chunk 级；初次构建和增量构建均走此命令）。
- `stats` / `validate`：查看 KB 状况与一致性。
- 图谱重建：经 build 选项编排与执行；
  `--update` 增量、`--force` 删 graphify-out 后全新重建。
