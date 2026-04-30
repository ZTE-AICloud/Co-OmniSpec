# 简单需求按需反构执行阶段

<!-- 阶段3a：简单需求按需反构执行 -->

## 职责
执行简单需求的按需反构流程，调用子 Agent 生成主汇总文档和逐功能独立文档。

## 执行流程

### 0. [ ] 创建阶段3a的子任务的Todo列表
为确保阶段执行过程的透明化和可追踪性，创建阶段3a的子任务的Todo列表：

1. **步骤1 清理上一阶段的上下文，保证本阶段的上下文干净**
2. **步骤2 确认前置条件（阶段2已完成）**
3. **（可选）步骤2.5 相似需求检索（Top-1 历史需求参考）**
4. **步骤2.6 生成波及功能与波及接口清单（为后续扩展提供基础）**
5. **步骤3 调用简单需求反构子 Agent（生成功能文档与接口文档）**
6. **步骤4 更新分支-功能索引（后置钩子）**

### 1. [x] 清理上一阶段的上下文，保证本阶段的上下文干净
- **阶段开始时主动清空上下文**：执行上下文清理，明确说明"开始阶段3a：简单需求按需反构执行。已清空上一阶段的上下文"
- **处理过程中及时清理**：完成每个步骤后，忘掉不必要的中间信息
- **输出精简化**：只输出必要结果，避免冗长的解释性文本

### 2. [ ] 确认前置条件（阶段2已完成）
- **前置条件检查**：
  - 确认阶段2已执行完成（阶段2已验证架构识别结果并设置了 `deep_architecture_result` 变量）
  - 确认阶段1已执行完成，并已获取以下变量：
    - `REPO_ROOT`：仓库根目录（绝对路径）
    - `FEATURE_DIR`：特性目录路径（绝对路径）
    - `BRANCH_NAME`：特性分支名称
  - 若阶段2未执行完成，必须等待阶段2完成后再继续
  - 🔴 `FEATURE_DIR` 必须位于 `{REPO_ROOT}/changes/` 下；若发现落在 `specs/` 或其他目录，必须立即报错并终止流程
  - 🔴 本阶段不依赖 `spec.md`，不得要求先创建或读取 `changes/<feature>/spec.md`
- **验证变量已设置（强制要求）**：
  - 检查 `deep_architecture_result` 变量是否已设置（阶段2中已设置）
  - 若未设置：
    - 输出错误信息：`❌ 错误：架构识别结果变量未设置，无法继续执行反构流程`
    - 输出提示：`请确保阶段2（架构识别）已成功执行完成`
    - **立即终止流程**，不继续执行后续步骤
    - 返回错误状态

### 2.5 [ ] （可选）相似需求检索（Top-1 历史需求参考）

- **目标**：在执行简单需求反构前，基于输入需求与既有需求进行一次 Top-1 相似需求检索，仅作为参考上下文，不改变简单流程的核心产物与路径约束。
- **是否必需**：本步骤为**可选**，可由上层流程通过参数或开关控制是否启用；即便不启用，本阶段仍被视为成功。
- **执行建议**：
  - 输入来源：
    - 新需求信息：可直接基于当前 `arguments` 解析出 `new_requirement` 结构，或复用与复杂流程共享的 `stage1-requirement-understanding.json`
    - 既有需求摘要列表：推荐由前置脚本扫描 `{REPO_ROOT}/omni-doc/on-demand/on-demand-existing-function-analysis-*.md` 生成，并写入 `{FEATURE_DIR}/on-demand/existing-requirements-digest.json`
  - 调用子 Agent：
    - 通过 Task 工具调用 `requirement-similarity-analyzer`
    - 让子 Agent 将结果写入 `{FEATURE_DIR}/on-demand/stage1.5-requirement-similarity.json`（simple 流程专用缓存）
- **降级约束**：
  - 如果本步骤未启用或执行失败，必须视为 `found_similar=false`，并继续执行步骤2.6
  - 不得因为相似需求检索失败而终止简单流程

### 2.6 [ ] 生成波及功能与波及接口清单（为后续扩展提供基础）

- **目标**：在执行简单需求反构前，先分析并生成波及功能清单与波及接口清单（采用与复杂流程一致的格式），为后续扩展能力提供基础。简单流程中，此清单将自动确认（无需用户交互），直接作为后续分析的输入。
- **是否必需**：本步骤为**必需**，用于统一简单流程和复杂流程的输出格式，便于后续扩展（如将来简单流程也支持用户确认）。
- **执行流程**：
  - **前置条件**：需要步骤2已完成，确认 `deep_architecture_result` 已设置
  - **检查缓存**：
    - 检查 `{FEATURE_DIR}/on-demand/stage2-impact-candidates.json` 是否存在
    - 检查 `{FEATURE_DIR}/on-demand/stage2-impact-list.md` 是否存在
    - 如果存在且输入参数未变化（比较 `arguments` 和 `deep_architecture_result`），直接使用缓存结果，跳过后续步骤
  - **理解需求与关键信息提炼**（如缓存不存在）：
    - 从 `arguments` 中提取需求目的/范围、需求场景
    - 提取关键实体/术语/接口路径/模块名/目录线索
    - 若需求文档或 `@` 引用中存在用户提供的术语映射（如“中文术语 -> 英文代码词组”），则将其作为**可选增强输入**增量使用：
      - 保留原始中文关键词
      - 额外提取英文代码词组及常见命名变体（空格分词、驼峰、下划线、连字符）
      - 将扩展结果并入后续检索词集合，提高文档与代码命中率
    - 若不存在术语映射或无法可靠解析，直接回退为原有流程，不报错、不终止
    - 识别变更类型倾向（增/删/改/查）
    - 输出：`{FEATURE_DIR}/on-demand/stage1-requirement-understanding.json`（与复杂流程格式一致）
  - **检索并分析波及功能**（如缓存不存在）：
    - **波及功能分析强制补充步骤**（与复杂流程步骤5一致，🔴 必须遵守）：
      - 对已识别为核心分析范围的目录，先用 `ls` 或递归列出形成完整文件清单，不遗漏同目录成员。
      - 🔴 **不得仅依赖文件名级命中结果**：禁止仅用 `grep -l`、`rg -l` 或等价“只返回文件名”的结果直接收敛波及范围；对命中的核心目录，必须结合完整文件清单逐个复核，并查看匹配行、上下文或计数，避免漏掉同目录下命中但未出现在首轮结果中的文件（如常量定义、默认值文件）。
      - grep 等全文检索须覆盖架构分层与模块边界所暗示的各层路径及需求/架构线索指向的路径，不得在无证据时默认将范围收窄为单一子树。
      - 🔴 **默认使用全文件检索，不按后缀限缩范围**：全文检索默认应覆盖目标目录中的所有文件类型，不得预先用 `*.go`、`*.java`、`*.py`、`*.yaml` 等后缀限制搜索范围；只有在已有充分证据证明某类文件与需求无关时，才允许在说明理由后局部缩小范围。
      - 对配置驱动、部署脚本、启动参数、资源注解、模板、协议、字典、静态资源等场景，必须把脚本、配置和部署目录与源码目录一并纳入全文件检索视野，不得因“先命中源码”而停止。
      - 发现代码引用外部资源（配置、模板、数据或静态资源文件等）后，立即检索该资源所在目录并沿配置/资源依赖向下追溯，纳入候选波及范围。
      - 命中资源引用后，至少补查：引用点、资源定义、同目录相关成员、读取方、消费方、资源驱动逻辑（分发/校验/执行/落库/上报）；若任一项继续命中需求线索，则再向下追一层。
      - 命中全局变量、常量、枚举、静态 map key、注册表键等符号锚点时（即使不是文件路径），也必须继续追溯其定义、赋值、引用和映射关系，不得在入口文件停止。
      - 若需求包含默认值、常量、环境变量、资源注解、参数文件路径等线索，必须额外检查核心模块下的 `util`、`constants`、`config`、`options`、`bootstrap`、`main` 及同目录公共文件，不得因入口文件已命中就停止。
      - 不得只依赖显式调用链；必须并行检查调用链、调度链（消息类型/路由键/handler 映射/registry）、数据链（共享实体/表/状态字段/配置项）、业务阶段链（触发/执行/落库/上报/通知）。
      - 若存在 `deep_architecture_result`，则应根据其中的模块职责、上下游关系和主处理流程对候选范围做架构增强扩散；命中入口、分发、执行或上报模块后，应补搜逻辑架构中前后相邻阶段及协同模块。
      - 经典示例：
        - 消息转发：从消息入口继续追到消息类型枚举/路由键、分发函数、handler map/registry、最终处理函数，以及结果落库/上报出口。
        - 消息转发断链修复：若在 `main.go` 命中 `SUCCL_GIDS` 这类全局变量，必须沿符号定义/赋值/引用继续追到具体处理函数与业务阶段，不得因其不是文件路径而中止。
        - 巡检闭环：从巡检触发入口继续追到执行逻辑、结果落库或状态流转、结果聚合、上报/通知出口；若通过共享表、状态字段、缓存 key 或配置项串接，也视为同一波及链路。
    - 基于关键信息检索候选功能（文档和代码）
    - 若存在术语映射增强结果，则同时使用原始中文词和扩展后的英文代码词组/命名变体进行检索；若不存在，则保持原有检索方式
    - 在支持 LSP 的语言中，优先使用 LSP 工具进行符号级检索
    - **独立执行静态配置/脚本/部署资产检索**：
      - 本步骤为必执行独立子步骤，不得视为源码检索的附属补充而跳过
      - 专门覆盖静态配置、脚本、部署、模板、协议、字典、资源清单等非源码资产
      - 重点目录至少包括：`scripts/`、`deploy/`、`deployment/`、`config/`、`configs/`、`charts/`、`helm/`、`manifests/`、`k8s/`、`resources/`
      - 若需求关键词命中静态资产（如资源注解、环境变量、参数文件路径、模板变量），必须继续检查静态文件本体、同目录相关成员、生成/渲染/发布脚本，以及消费这些配置的执行入口或运行时模块
      - 必须落盘：`{FEATURE_DIR}/on-demand/stage2-static-asset-scan.json`
    - 为每个候选功能项收集证据（文档证据和代码证据）
    - 区分直接波及与间接波及
    - 生成波及功能清单（JSON 和 Markdown 格式）
  - **自动确认清单**（简单流程特性）：
    - 由于简单流程无需用户交互，直接将候选清单作为已确认清单
    - 从 `stage2-impact-candidates.json` 生成 `stage2-impact-confirmed.json`（所有功能默认标记为"保留"状态）
    - 从 `stage2-interface-candidates.json` 生成 `stage2-interface-confirmed.json`（所有接口默认标记为"保留"状态）
  - **输出文件**（必须落盘）：
    - `{FEATURE_DIR}/on-demand/stage1-requirement-understanding.json`：需求理解结果（与复杂流程格式一致）
    - `{FEATURE_DIR}/on-demand/stage1-terminology-map.json`：术语映射增强结果（可选；仅在识别到术语映射时生成）
    - `{FEATURE_DIR}/on-demand/stage2-static-asset-scan.json`：静态配置/脚本/部署资产检索结果
    - `{FEATURE_DIR}/on-demand/stage2-impact-candidates.json`：候选功能清单（JSON格式，与复杂流程格式一致）
    - `{FEATURE_DIR}/on-demand/stage2-impact-list.md`：可读的波及功能清单（Markdown格式，与复杂流程格式一致）
    - `{FEATURE_DIR}/on-demand/stage2-impact-confirmed.json`：已确认功能清单（简单流程中自动确认，与复杂流程格式一致）
    - `{FEATURE_DIR}/on-demand/stage2-interface-candidates.json`：候选接口清单（JSON格式，接口独立文档输入）
    - `{FEATURE_DIR}/on-demand/stage2-interface-list.md`：可读的波及接口清单（Markdown格式）
    - `{FEATURE_DIR}/on-demand/stage2-interface-confirmed.json`：已确认接口清单（简单流程中自动确认）
    - `{FEATURE_DIR}/on-demand/stage2-summary.json`：波及分析摘要
  - **清单格式要求**（与复杂流程保持一致）：
    - `stage2-impact-candidates.json` 中每个功能项应包含：
      - `function_key`：功能唯一标识
      - `function_name`：功能名称
      - `function_description`：功能描述（若未提及则写"未提及"）
      - `impact_type`：波及类型（direct/indirect）
      - `evidence`：证据来源（文档路径/代码路径）
      - `entry_clues`：入口线索（如有）
      - `related_modules`：关联模块（如有）
      - 在支持 LSP 的语言中，代码证据应包含：`code_symbol`、`code_file_path`、`code_range`、`callers`/`callees`（可选）
      - 对非显式调用链场景，建议额外包含：`impact_relation_type`（`call` / `dispatch` / `data_flow` / `business_stage` / `config_binding`）、`relation_anchor`（消息类型/路由键/表名/状态字段/配置 key/事件名）、`business_stage`（trigger / execute / persist / report / notify）
    - `stage2-impact-list.md` 应为可读的 Markdown 格式，包含功能名称、波及类型、证据来源、入口线索等信息
    - `stage2-impact-confirmed.json` 格式与 `stage2-impact-candidates.json` 一致，但增加 `confirmed_status: "保留"` 字段
- **容错处理**：
  - 如果本步骤执行失败，记录错误信息但继续执行步骤3（简单流程的容错特性）
  - 子 Agent 在步骤2中也会执行类似的分析，可以基于子 Agent 的结果补充或修正

### 3. [ ] 调用简单需求反构子 Agent（生成功能文档与接口文档）
- **启动子 Agent**：`simple-on-demand-reverse-agent`
- **输入参数**：
  - `FEATURE_DIR`（使用阶段1中获取的同一个值，必须为绝对路径）
  - `REPO_ROOT`（使用阶段1中获取的值，必须为绝对路径）
  - `arguments`（用户原始输入：`$ARGUMENTS`）
  - `constitution_path`（可选）
  - `deep_architecture_result`（必需：`{REPO_ROOT}/omni-doc/on-demand/logic_architecture.md` 路径，`REPO_ROOT` 为阶段1中获取的值）
- **期望输出**：
  - `{FEATURE_DIR}/on-demand/` 下的按需反构产物（中间过程/缓存）
  - `{REPO_ROOT}/omni-doc/on-demand/on-demand-existing-function-analysis-{BRANCH_NAME}.md`：主汇总文档（优先使用阶段1输出的 `BRANCH_NAME`；缺失时再降级取 `basename(FEATURE_DIR)`）
  - `{REPO_ROOT}/omni-doc/on-demand/functions/{function_key}.md`：逐功能独立分析文档（每个功能一个）
  - `{REPO_ROOT}/omni-doc/on-demand/interfaces/{interface_key}.md`：逐接口独立分析文档（每个接口一个）
  - `{FEATURE_DIR}/on-demand/stage3/function-interface-map.json`：功能-接口映射关系（功能文档引用依据）
  - 每个功能文档必须包含：
    - “接口-代码波及链路（修改点串联）”表格
    - “主处理流程 PlantUML 活动图”
  - 每个接口文档必须包含：
    - “接口使用流程图（PlantUML）”
- **清单复用说明**：
  - 子 Agent 在执行步骤2（功能语义检索与波及分析）时，应优先检查步骤2.6已生成的波及功能清单缓存
  - 如果步骤2.6已生成 `stage2-impact-candidates.json` 和 `stage2-impact-confirmed.json`，子 Agent 可以直接复用这些结果，避免重复分析
  - 子 Agent 仍需生成自己的 `stage2-impact-list.json`（用于内部流程），但应确保与步骤2.6生成的清单保持一致
- **反构侧补充说明**：
  - 允许将 `@` 引用文档作为**"需求意图关键词来源"**用于检索知识库候选文档
  - 但 baseline 内容**仍然只允许**来自知识库/存量文档（不把需求意图写入 baseline；未提及则写"未提及"）
  - 子 Agent 必须使用架构识别结果作为额外上下文
- **验证要求**：
  - 子 Agent 调用完成后，必须验证输出文件是否成功生成
  - 必须验证所有 PlantUML 代码块格式：
    - `@startuml` / `@enduml` 成对出现
    - 代码块闭合
    - 图内无明显 Markdown 表格分隔符污染
  - 验证失败则终止流程并报告错误

### 4. [ ] 更新分支-功能索引（后置钩子）

- **目标**：在简单流程的主汇总文档与逐功能文档生成完成后，重建按需反构关系索引文件，便于后续检索与复用。
- **调用脚本**：
  - Bash 版本：`{REPO_ROOT}/scripts/bash/reverse/index/build-on-demand-index.sh`
  - PowerShell 版本：`{REPO_ROOT}/scripts/powershell/reverse/index/build-on-demand-index.ps1`
- **调用参数要求**：
  - 必须传入 `--repo-root`，值为当前 `REPO_ROOT`（绝对路径）
  - 如需 dry-run 或调试，可按脚本 `--help` 说明增加参数（由上层流程控制）
- **执行约束**：
  - 🔴 **后置钩子**：只能在步骤3成功生成 `{REPO_ROOT}/omni-doc/on-demand/on-demand-existing-function-analysis-{BRANCH_NAME}.md` 之后调用
  - 🔴 **失败不阻塞主流程**：
    - 如果索引构建脚本执行失败，必须记录 warning（包括命令、返回码、stderr 摘要）
    - 不得因为索引重建失败而判定本阶段整体失败
  - 建议由上层流程对索引构建结果进行人工抽查验证

## 输出
- `{FEATURE_DIR}/on-demand/`：按需反构产物（中间过程/缓存）
- `{REPO_ROOT}/omni-doc/on-demand/on-demand-existing-function-analysis-{BRANCH_NAME}.md`：主汇总文档（优先使用阶段1输出的 `BRANCH_NAME`；缺失时再降级取 `basename(FEATURE_DIR)`）
- `{REPO_ROOT}/omni-doc/on-demand/functions/{function_key}.md`：逐功能独立分析文档（每个功能一个）
- `{REPO_ROOT}/omni-doc/on-demand/interfaces/{interface_key}.md`：逐接口独立分析文档（每个接口一个）

## 注意事项
- **⚠️ 关键约束**：所有子 Agent 调用都必须使用**阶段1中获取并保存的同一个 `REPO_ROOT`（阶段1）和 `FEATURE_DIR`（阶段1）变量值**（绝对路径），不得让子 Agent 自行计算或创建目录路径，以确保所有输出都写入正确的目标目录
- **⚠️ 执行顺序约束**：本阶段必须在阶段2执行完成后才能开始执行，不得在阶段2完成前执行
- **依赖架构识别结果**：本阶段依赖阶段2的架构识别结果（`{REPO_ROOT}/omni-doc/on-demand/logic_architecture.md`）
- **🔴 重要**：AI Agent 在执行所有步骤时，必须使用中文进行说明和输出
- 跨平台支持：所有脚本调用必须同时支持 Linux (bash) 和 Windows (PowerShell)

