# 接口清单扫描

<!-- 阶段3：接口清单扫描 -->

## 职责
扫描指定目录或文件，识别所有潜在的接口定义，生成完整的接口清单。

**单文件接口识别**：子 Agent（interface-recognizer）按本 Skill 内 [references/implementation/interface-recognition.md](../implementation/interface-recognition.md) 执行，输入/输出与步骤以该文档为准。

## 脚本路径说明

本阶段涉及两类脚本路径：

- **本 Skill 捆绑脚本**（使用 `${CLAUDE_SKILL_DIR}/references/scripts/`）：质量闸门、文件校验、覆盖检测等 Python 脚本
- **OmniSpec 项目脚本**（使用 `${DSDD}/scripts/bash/` 或 `${DSDD}/scripts/powershell/`）：bash/PowerShell 包装脚本和工具脚本，由 OmniSpec 项目提供

## 执行流程

### 0. [ ] 创建阶段3的子任务的Todo列表
为确保阶段执行过程的透明化和可追踪性，创建阶段3的子任务的Todo列表：

步骤1. **清理上一阶段的上下文，保证本阶段的上下文干净**
步骤2. **检查缓存状态，确定是否需要执行分析**
步骤2.5. **用户选择扫描方式**（仅在需要执行扫描时）
步骤3. **执行接口清单扫描**（根据所选方式分支执行）
步骤4. **保存批次结果或最终结果到缓存文件**
步骤5. **展示结果并向用户确认**
步骤6. **处理用户确认，更新缓存状态**
步骤7. **执行数量质量闸门校验（强制）**
步骤7.5. **扫描文件覆盖度自动检测（强制：当数量偏低或与预估不符时）**
步骤8. **根据闸门结果执行重扫/重筛策略（强制）**

### 1. [x] 清理上一阶段的上下文，保证本阶段的上下文干净
- **阶段开始时主动清空上下文**：执行上下文清理，明确说明"开始阶段3：接口清单扫描。已清空上一阶段的上下文"
- **批次处理前清理上下文**：处理每个批次前执行无用的批次数据上下文清理，明确说明"开始处理批次X/Y。已清空上一批次的无用的批次数据上下文"
- **批次处理后及时清理**：完成每个批次后忘掉该批的详细信息，防止上下文累积
- **参考增强指南**：详细上下文管理策略请参阅 [增强版Token管理和上下文控制指南](../token-management.md)

### 2. [ ] 检查缓存状态，确定是否需要执行分析
- 读取状态文件：`{REPO_ROOT}/.cache/reverse/interfaces/.cache-status.json`
- 检查字段：`interface_list.confirmed`
- 如果 `confirmed == true`：跳过阶段3，直接进入用户确认步骤
- 如果 `confirmed == false` 或不存在：执行阶段3
- 注意：即使缓存文件存在，只要未确认，就必须执行用户确认步骤
- 检查批次处理状态：如果之前有批次处理失败，从上次中断处继续处理

### 2.5. [ ] 用户选择扫描方式（仅在需要执行扫描时）
- **🔴 进入本步时须向用户说明**（AI Agent 必须输出以下或等价文字）：
  - **交互模式下**：`【接口清单扫描】请选择扫描方式：方式 A（默认，原有接口清单扫描，按文件分批 + SubAgent） 或 方式 B（reverse 调用链扫描）。请输入 A 或 B，直接回车视为 A。`
  - **非交互模式下**：`【接口清单扫描】当前使用默认方式 A（原有接口清单扫描，按文件分批 + SubAgent），无需选择。`
- **🔴 默认方式**：方式A（原有接口清单扫描，按文件分批 + SubAgent），无需用户选择即可继续
- **可选方式**：用户可主动选择方式B（reverse 调用链扫描）
- **执行统一确认机制**：按照 `reverse-shared/references/confirmation-template.md` 中的"过程中确认模板 - 类型1：配置选择确认"执行
  - 默认配置：方式A（原有接口清单扫描，按文件分批 + SubAgent）
  - 交互模式下：显示两种方式供用户选择
    - **方式A（默认）**：结合架构、Few-shot 和用户约束规则，由 AI SubAgent 按文件分批识别
    - **方式B**：基于语法解析与调用链分析，从根函数中识别接口（需前置依赖）
  - **🔴 方式判定优先级**（避免“已设默认 A 仍执行 B”）：
    1. 若存在 `{REPO_ROOT}/.cache/user_input/interface-scan-mode.json` 且其 `mode` 字段为 `"B"` → 使用方式 B（用户显式预选 B）；并读取 `allow_mode_downgrade`（可选，默认 `true`）。
    2. 否则（包括：该文件不存在、该文件 `mode` 为 `"A"`、或文件无效）→ 非交互下使用**默认方式 A**；交互下展示选项由用户选择。
    3. 因此：若希望始终走默认 A，请**勿**在 `.cache/user_input` 下创建或保留 `interface-scan-mode.json` 且内容为 `"mode": "B"`；若有该文件且希望 A，请改为 `"mode": "A"` 或删除该文件。
  - **可选预配置**：若用户希望预选方式 B 且无需交互，可在 `{REPO_ROOT}/.cache/user_input/` 下创建 `interface-scan-mode.json` 并设置：
    - `"mode": "B"`
    - `"allow_mode_downgrade": true|false`（可选，默认 `true`）
    - 语义：
      - `true`：方式 B 不支持/失败时允许自动切换到方式 A
      - `false`：方式 B 不支持/失败时直接报错退出，不允许自动切换
    否则本步检查该文件是否存在且 mode 为 B，否则按默认 A 或交互选择。
  - 将选择结果**仅**写入 `{REPO_ROOT}/.cache/reverse/interfaces/interface-scan-mode.json`（不写入 `.cache/user_input`）：
    ```json
    {"mode": "A" | "B", "confirmed_at": "ISO8601"}
    ```
  - 🔴 **无论交互与否**：非交互模式下使用默认方式 A 时，也须将 `{"mode": "A", "confirmed_at": "<当前 ISO8601>"}` 写入上述缓存文件，以便步骤 3 读取一致。
- **方式B 前置依赖**：方式B 执行时（仅当用户显式选择方式 B 时），按以下顺序处理：
- 0. **默认使用Python3.6以上版本并且带齐脚本参数**默认使用python3 执行；带齐脚本参数 --repo-root {REPO_ROOT} --codebase {REPO_ROOT} --output-dir {input_base_dir}
  1. **找到前置依赖生成脚本**（🔴 此步仅检查文件是否存在，不执行脚本）：优先检查路径 `{REPO_ROOT}/.claude/skills/reverse-interfaces/references/scripts/reverse_by_call_chain/prepare_reverse_input.py`，若该文件不存在则检查 `{REPO_ROOT}/claude/skills/reverse-interfaces/references/scripts/reverse_by_call_chain/prepare_reverse_input.py`
  2. **确定 input_base_dir**：默认 `python3 {REPO_ROOT}/.cache/reverse/reverse-input/`，或由 `.cache/user_input/reverse-interface-config.md` 指定
  3. **判断前置依赖是否存在**（三个文件）：
     - `{input_base_dir}/internal/semantics_parser/call_tree_list.json`
     - `{input_base_dir}/internal/syntax_parser/all_methods.json`
     - `{input_base_dir}/internal/syntax_parser/all_functions.json`
  4. **若三个文件均存在**：继续往下执行方式B
  5. **若任一文件不存在**：调用上述脚本生成依赖
  6. **若脚本执行失败，或执行后仍未生成出上述三个文件**：
     - 当 `allow_mode_downgrade=true`：**退回使用方式 A**，并必须：
       - 将 `{REPO_ROOT}/.cache/reverse/interfaces/interface-scan-mode.json` 更新为 `{"mode": "A", "confirmed_at": "<ISO8601>", "fallback_reason": "方式B前置依赖未满足"}`；
       - 向用户输出：`【已退回方式 A】原因：方式 B 前置依赖未满足（prepare_reverse_input 执行失败或三文件未生成）。当前将按方式 A 执行。若需坚持方式 B，请按下方命令手工运行 prepare_reverse_input.py（必须带 --repo-root/--output-dir 等参数）并确保三文件生成后重新执行本阶段：`
     - 当 `allow_mode_downgrade=false`：**直接报错退出当前阶段**，并必须向用户输出：`【方式B执行失败】原因：方式 B 前置依赖未满足（prepare_reverse_input 执行失败或三文件未生成），且已配置禁止降级切换（allow_mode_downgrade=false），本阶段已终止。`
       ```bash
       # 说明：
       # - {REPO_ROOT}：目标项目仓库根目录（绝对路径）
       # - {input_base_dir}：reverse 输入目录（绝对路径），默认 {REPO_ROOT}/.cache/reverse/reverse-input/
       # - {PREPARE_SCRIPT}：脚本绝对路径，优先 python3 {REPO_ROOT}/.claude/skills/reverse-interfaces/references/scripts/reverse_by_call_chain/prepare_reverse_input.py  --repo-root {REPO_ROOT} --codebase {REPO_ROOT} --output-dir {input_base_dir}
       #   不存在则用 python3 {REPO_ROOT}/claude/skills/reverse-interfaces/references/scripts/reverse_by_call_chain/prepare_reverse_input.py --repo-root {REPO_ROOT} --codebase {REPO_ROOT} --output-dir {input_base_dir}
       python3 {PREPARE_SCRIPT} \
         --repo-root {REPO_ROOT} \
         --codebase {REPO_ROOT} \
         --output-dir {input_base_dir}
       ```

### 3. [ ] 执行接口清单扫描（根据所选方式分支执行）
- 读取 `{REPO_ROOT}/.cache/reverse/interfaces/interface-scan-mode.json`，若无或无效则使用**默认方式 A**。
- 读取 `{REPO_ROOT}/.cache/user_input/interface-scan-mode.json` 中的 `allow_mode_downgrade`（缺省 `true`），用于控制方式B失败时是否允许自动切换到方式A。
- **若 mode 为 `A` 或未选择**：执行 **3A. 原有接口清单扫描**（见下方）
- **若 mode 为 `B`**：执行 **3B. reverse 调用链扫描**（见下方）
- **若已设置默认 A 仍执行了方式 B，请排查**：是否存在 `.cache/user_input/interface-scan-mode.json` 且内容为 `"mode": "B"`，若有请删除或改为 `"mode": "A"`。
- **🔴 进入 3A 或 3B 后须立即向用户提示当前执行方式**（AI Agent 必须输出以下之一，且执行过程中关键节点可再次简要提示）：
  - 进入方式 A 时：`【当前执行】方式 A - 原有接口清单扫描（按文件分批 + SubAgent 识别）。`
  - 进入方式 B 时：`【当前执行】方式 B - reverse 调用链扫描（语法/语义解析 + 接口识别）。`

#### 3A. 原有接口清单扫描（方式A，默认）
- **🔴 开始执行前必须输出**：`【当前执行】方式 A - 原有接口清单扫描（按文件分批 + SubAgent 识别）。`
为确保阶段执行过程的透明化和可追踪性，创建步骤3的子任务的Todo列表：

3.1. [ ] **执行前检查**
3.2. [ ] **读取上下文依赖文件并评估数据规模**
3.3. [ ] **调用批次生成脚本自动分批处理（文件数量 > 20时执行）**
3.4. [ ] **同时启动多个子agent一起并发分别处理多个批次**
3.5. [ ] **收集子agent处理结果**
3.6. [ ] **主agent统一管理批次状态**
3.7. [ ] **收集子agent结果并更新状态**
3.8. [ ] **检查是否还有未处理的批次【必须执行的步骤】**
3.9. [ ] **如果还有待处理批次：继续循环处理**
3.10. [ ] **单批扫描流程**（文件数量 <= 20时执行）
3.11. [ ] **扫描完成后检查**
3.12. [ ] **扫描完成后调用脚本自动合并生成最终接口文件interface-list.json**

#### 核心执行流程
AI Agent需要按照以下决策树执行分析：

3.1. **执行前检查**：
   - 🔴 强制验证批次规划已完成（验证批次映射文件interface_scanning-batch-status.json、batch-mapping.json、状态文件和文件列表是否已生成）
   - 阶段开始时明确告知用户当前阶段、扫描范围、预计工作量
   - 🔴 **强制Token预算评估**：评估当前任务的Token预算，确保不超过15万tokens的安全限制

3.2. **读取上下文依赖文件并评估数据规模**：
   - 读取逻辑架构共享产物：`{REPO_ROOT}/omni-doc/specs/logic_architecture/architecture.json`
   - 读取接口类型列表：`interface-types.json`
   - 读取约束规则及转换结果：`constraints.json`、`interface-patterns.json`
   - 读取 Few-shot 示例：`few-shot-examples.json`
   - 验证所有上下文文件存在且可访问
   - 基于以上信息统计需要扫描的文件总数，并写入 `file_list.json`（数组形式，供自动分批使用）
   - 判断处理方式：
     - 文件数量 > 20：执行分批扫描（跳转到 3.3）
     - 文件数量 <= 20：执行单批扫描（跳转到 3.10）

3.3. **调用批次生成脚本自动分批处理（文件数量 > 20时执行）**：
   - 🔴 **强制要求：优先复用已有批次，保证断点续跑，不得重复创建批次**
   - 🔴 **前置检查（与阶段4保持一致的批次管理策略）**：
     - 检查批次映射文件是否已存在（兼容两种命名方式）：
       - 推荐：`{REPO_ROOT}/.cache/reverse/interfaces/batch-mapping.json`（接口清单扫描阶段生成的标准映射文件）
       - 旧格式（如有）：`{REPO_ROOT}/.cache/reverse/interfaces/interface-batch-mapping.json`
     - 同时检查批次状态文件是否存在：
       - `{REPO_ROOT}/.cache/reverse/interfaces/interface_scanning-batch-status.json`
     - 如果**批次映射文件 + 批次状态文件均存在且有效**（包含批次数量、每个批次的基本信息和状态），则：
       - 将当前执行视为“断点续跑场景”
       - 🔴 **禁止重新创建批次**，必须直接跳转到步骤 3.4/3.5 开始按状态继续处理
     - 如果任一文件不存在或无效（例如不包含批次信息、`total_batches` 为 0 等），才允许执行批次创建
   - 🔴 **批次文件创建（仅在确实不存在有效批次时执行）**：
     - 必须调用 `generate_interface_batches` 自动分批，禁止手动创建或伪造批次文件
     - 动态批次规划：
       - 基于用户约束规则和特征筛选获取文件列表
       - 脚本自动创建所有 `batch-details-*.json` 及对应批次映射文件
       - 每个批次记录文件列表、预计 Token、复杂度等信息，映射文件仅保留必要字段
       - 🔴 每个批次预计 Token 不得超过 15 万
     - 初始化批次状态文件 `interface_scanning-batch-status.json`
     - 🔴 **脚本调用方式**：
       - Linux/macOS/Windows（推荐Python版本，跨平台通用）：
         ```bash
         python3 ${DSDD}/scripts/python/generate_interface_batches.py \
           --repo-root {REPO_ROOT} \
           --file-list {file_list_json}
         ```
       - 如需 Bash/PowerShell 包装脚本，可在对应平台调用同名脚本，参数保持一致
  - 🔴 无论是复用已有批次还是创建新批次，AI Agent 都必须明确声明（须含执行方式提示）：
    - "【方式 A】接口清单扫描阶段的批次文件已就绪，总共 {total_batches} 个批次；当前执行模式：{首次扫描|断点续跑}"


3.4. **分轮启动多个子agent并发处理多个批次（分轮执行策略）**
   - 根据 [SKILL.md](../../SKILL.md) 与子 Agent 委派规则，每轮最多启动 2 个 `interface-recognizer` 子 Agent，处理 1–2 个批次
   - 使用批量获取脚本（如 `get-next-batches`）一次获取本轮要处理的批次列表
   - 🔴 **脚本调用方式**：
     - Linux/macOS：
       ```bash
       ${DSDD}/scripts/bash/get-next-batches.sh \
         --repo-root {REPO_ROOT} \
         --batch-count 2
       ```
     - Windows：使用同名 PowerShell 脚本，参数含义与 Bash 版本一致
   - 每个子 Agent 只处理自己负责的一个批次，主 Agent 不参与批次内具体识别逻辑，只负责调度
   - 每轮所有子 Agent 完成后，🔴 必须执行 `/compact`，以"轮次完成"为界清理上下文

3.5. **收集子agent处理结果**
   - 等待当前轮次所有子 Agent 完成处理
   - 收集各批次的 `interface-list-batch-{batch_number}.json` 文件并做格式校验
   - 使用批量状态更新脚本一次性更新本轮已完成批次状态（`completed/failed`）
   - 轮次结束后再次 `/compact`，避免上下文堆积


3.6. **主agent统一管理批次状态**
   - 🔴 批次状态由主 Agent 统一维护，子 Agent 禁止直接修改状态文件
   - 启动子 Agent 前，主 Agent 批量将目标批次标记为 `processing`，记录开始时间及 `batch_numbers` 列表
   - 使用 `verify-batches-completion` 轮询检查所有启动批次是否真正完成：
     - 状态为 `completed`
     - 对应 `interface-list-batch-{batch_number}.json` 存在且格式正确
     - 处理时间戳在合理范围内
   - 轮询策略：未满足条件时每 30 秒重试，最长 30 分钟，超时批次标记为 `failed`
   - 🔴 禁止仅检查文件存在性就认为完成，禁止伪造结果文件或跳过轮询

3.6.5. **等待子agent完成（强制轮询检查）**
   - 按上述轮询规则等待所有目标批次完成
   - 所有目标批次通过验证后，明确声明：“所有批次已完成验证，可以继续收集结果”

3.7. **收集子agent结果并更新状态**
   - 汇总当前轮次所有子 Agent 输出的批次接口清单文件，确认文件存在且结构正确
   - 使用批量状态更新脚本根据结果统一更新批次状态：
     - 成功：标记为 `completed`
     - 失败：标记为 `failed`
   - 清理本轮批次的上下文数据，并声明“已清空当前轮次上下文”
   - 记录批次开始和结束时间，将耗时信息写回状态文件
   - 调用进度脚本获取最新处理进度并向用户报告：
     - “已完成 {completed_batches}/{total_batches} 个批次，进度 {progress_percentage}%，剩余 {pending_batches} 个批次待处理”

3.8. **检查是否还有未处理的批次【必须执行的步骤】**
   - 使用 `get-next-batches` 检查是否还有待处理批次
   - 🔴 **脚本调用方式**：
     - Linux/macOS：
       ```bash
       ${DSDD}/scripts/bash/get-next-batches.sh \
         --repo-root {REPO_ROOT} \
         --batch-count 2
       ```
     - Windows：使用同名 PowerShell 脚本，参数含义与 Bash 版本一致
   - 使用 `get-next-batch --action get-summary` 获取整体进度摘要
   - 执行规则：
     - 首次执行：处理所有待处理批次
     - 断点续跑：从上次中断处继续，直至所有批次处理完成或用户中止

3.9. **如果还有待处理批次：继续循环处理**：
   - 若存在剩余批次：继续按“获取批次 → 标记 processing → 启动子 Agent → 验证 → 更新状态”的循环处理
   - 每轮前后清理无关上下文，并展示剩余批次数和预估处理时间：
     - “已完成 {completed_batches}/{total_batches} 个批次，进度 {progress_percentage}%，剩余 {pending_batches} 个批次待处理，预计还需要 {estimated_remaining_time}”
   - 当剩余批次数 > 10 时，🔴 必须询问用户是否继续处理：
     - 用户回复 `n/no`：记录后暂停处理
     - 用户回复 `y/yes/回车`：继续执行下一轮
     - 用户未回复：继续等待，禁止自动继续
   - 🔴 严禁跳过未处理批次或创建空结果文件模拟完成
   - 所有批次完成后：
     - 更新整体状态为 `completed`
     - 使用进度脚本获取最终进度，并输出“接口清单扫描已完成！总共处理了 {total_batches} 个批次，完成率 100%”

3.10. **单批扫描流程**（文件数量 <= 20时执行）：
   - 处理前检查当前上下文大小，>10 万则强制清空
   - 创建一个包含全部目标文件的“虚拟批次”，状态标记为 `processing`
   - 启动单个 `interface-recognizer` 子 Agent 处理该批次，等待其完成
   - 验证结果文件完整性和正确性，根据结果将批次状态标记为 `completed` 或 `failed`
   - 对超大文件进行分段/截断读取，并在处理过程中监控 Token（超过 15 万即报错并停止）
   - 处理结束后再次检查 Token 并清理无关上下文

3.11. **扫描完成后检查**：
   - 获取仓库根目录
   - 确认所有由子 Agent 生成的批次接口清单文件已保存在缓存目录中
   - 校验 `batch-mapping.json` 与状态文件中批次信息的一致性和完整性
   - 确认没有仍处于 `pending/processing` 的批次

3.12. **扫描完成后调用脚本自动合并生成最终接口文件interface-list.json**：
   - 使用统一的合并脚本（跨平台，仅依赖 Python）对所有批次结果进行合并：
     ```bash
     python3 ${DSDD}/scripts/python/merge_interface_results.py {REPO_ROOT}
     ```
   - 脚本会在 `{REPO_ROOT}/.cache/reverse/interfaces/` 目录下：
     - 按批次顺序读取 `interface-list-batch-{batch_number}.json`
    - **统一重排 `interface_id` 为全局连续编号**（`API_001`、`API_002`...，不按接口类型分段编号）
    - 合并时按业务特征去重，确保编号不重复且连续
     - 自动生成按类型、模块、业务领域等维度的统计信息
     - 生成最终接口清单文件 `interface-list.json`，整体结构与本节给出的模板示意保持一致
  - 🔴 **重要**：主流程禁止手工拼装或修改 `interface-list.json`，必须通过上述脚本生成；`interface_id` 的最终连续编号由合并脚本统一生成
   - 🔴 **全量清单要求**：`interface-list.json` 必须包含全部接口（`interfaces` 全量数组），禁止仅输出示例子集

#### 3B. reverse 调用链扫描（方式B）
- **🔴 禁止调用 call-chain-analyzer**：本阶段（接口清单扫描）的方式 B **不得**使用 Task 工具启动 `call-chain-analyzer` 或任何其他子 Agent。`call-chain-analyzer` 仅用于**功能反构**的调用链分析，与接口反构无关。方式 B 必须**在本流程内**按下方 3B.1～3B.3 依次执行脚本（prepare_reverse_input.py → reverse_syntax_parser identify → convert_reverse_interface_checklist.py），由主 Agent 直接调用脚本完成。
- **🔴 开始执行前必须输出**：`【当前执行】方式 B - reverse 调用链扫描（语法/语义解析 + 接口识别）。`
- **🔴 脚本路径解析**：以下所有脚本路径优先使用 `{REPO_ROOT}/.claude/skills/reverse-interfaces/references/scripts/...`（安装到目标项目后的路径）；若该路径下文件不存在（例如在 OmniSpec 源码仓库或未执行 install 的目标中），则使用 `{REPO_ROOT}/claude/skills/reverse-interfaces/references/scripts/...`。执行命令前须将 `{REPO_ROOT}`、`{input_base_dir}` 替换为实际绝对路径。
当使用方式B时，执行以下流程：

##### 3B.0. 方式B“不可中断执行”协议（新增，必须遵守）
- **目标**：方式B整体可能运行数分钟到更久，为避免前台中断/会话切换/工具超时导致进程被终止，本协议要求将关键长步骤以“可恢复的后台守护方式”运行，并把必要状态落盘。
- **强制要求**：
  - **进入方式B后，主 Agent 不得因为任何非错误原因提前结束本阶段**；不得在脚本未完成时进入后续步骤或进入用户确认步骤。
  - **建议后台运行 + 轮询完成**：对长步骤（尤其是 3B.2）应优先使用后台运行方式，并持续轮询直到确认进程退出并获得退出码。
  - **状态落盘**：必须写入以下两个文件（若目录不存在需先创建）：
    - `{REPO_ROOT}/.cache/reverse/interfaces/mode-b-identify.pid`：记录 3B.2 的进程 PID（若以后台运行方式启动）
    - `{REPO_ROOT}/.cache/reverse/interfaces/mode-b-identify.log`：记录 3B.2 的标准输出/错误输出日志（建议使用行缓冲）
- **恢复检查（被打断后必须先做）**：
  1. 若存在 `mode-b-identify.pid`，先检查该 PID 是否仍在运行；若仍在运行则继续等待并轮询日志，不得重跑。
  2. 若 PID 不存在或已不在运行：
     - 若 `interface_functions_checklist.json` 已存在且非空，视为 3B.2 已完成，可进入 3B.3；
     - 否则视为 3B.2 未完成或失败，需要重新执行 3B.2（或在确认前置依赖缺失时退回方式A）。

3B.1. **确定路径与依赖**（按顺序执行,使用python3执行，脚本需要带齐参数 --repo-root {REPO_ROOT} --codebase {REPO_ROOT} --output-dir {input_base_dir}）
   - **步骤 1：找到前置依赖生成脚本**（🔴 此步仅检查文件是否存在，不执行脚本）
     - 优先检查路径：`{REPO_ROOT}/.claude/skills/reverse-interfaces/references/scripts/reverse_by_call_chain/prepare_reverse_input.py`
     - 若该文件不存在则检查：`{REPO_ROOT}/claude/skills/reverse-interfaces/references/scripts/reverse_by_call_chain/prepare_reverse_input.py`
     - 将找到的脚本绝对路径记为 `PREPARE_SCRIPT`，后续步骤 5 中使用
     - 若两者均不存在：
       - `allow_mode_downgrade=true`：直接退回方式 A（须更新缓存为 mode A 并向用户输出“已退回方式 A”及原因，同 2.5 步骤 6）
       - `allow_mode_downgrade=false`：直接报错退出当前阶段，并输出禁止降级切换原因
   - **步骤 2：确定 input_base_dir**
     - 默认：`{REPO_ROOT}/.cache/reverse/reverse-input/`
     - 若存在 `{REPO_ROOT}/.cache/user_input/reverse-interface-config.md`，从中解析 `input_base_dir`
   - **步骤 2.1：确保 input_base_dir 目录存在**
     - 若 `input_base_dir` 不存在则创建该目录（含所有父目录）。
     - 执行方式：在确定 `input_base_dir` 后立即执行 `mkdir -p "{input_base_dir}"`（Bash）或等效操作，再进入步骤 3；避免仅“确定路径”却不创建导致后续检查或脚本写入失败。
   - **步骤 3：判断前置依赖是否存在**（三个文件）：
     - `{input_base_dir}/internal/semantics_parser/call_tree_list.json`
     - `{input_base_dir}/internal/syntax_parser/all_methods.json`
     - `{input_base_dir}/internal/syntax_parser/all_functions.json`
   - **步骤 4：若三个文件均存在** → 继续执行 3B.2
   - **步骤 5：若任一文件不存在** → 使用步骤 1 已确定的 `PREPARE_SCRIPT` 绝对路径调用脚本生成：
     ```bash
     python3 {PREPARE_SCRIPT} \
       --repo-root {REPO_ROOT} \
       --codebase {REPO_ROOT} \
       --output-dir {input_base_dir}
     ```
     其中 `{PREPARE_SCRIPT}` 为步骤 1 中已确定的脚本绝对路径。
     - 脚本会依次执行：语言检测 → 语法解析 → 语义解析（调用链生成）
   - **步骤 6：脚本执行后再次校验**
     - 若脚本执行失败（非零退出码）：
       - `allow_mode_downgrade=true`：退回方式 A（须更新缓存为 mode A 并输出“已退回方式 A”原因，同上 2.5 步骤 6）。
       - `allow_mode_downgrade=false`：报错退出当前阶段。
     - 若脚本执行成功，但三个文件仍未全部生成：
       - `allow_mode_downgrade=true`：退回方式 A 并更新缓存与提示。
       - `allow_mode_downgrade=false`：报错退出当前阶段。
     - 若三个文件均已生成：继续执行 3B.2

3B.2. **调用接口识别**
   - **🔴🔴 强制阻塞要求：本步骤的脚本执行时间可能较长（数分钟甚至更久），AI Agent 必须完整等待脚本执行结束（即进程退出并返回退出码）后，才能执行任何后续步骤（包括 3B.3 及之后的所有步骤）。严禁在脚本尚未执行完成时提前进入下一步骤、跳过本步、或假设本步已完成。**
   - **🔴🔴 不可中断执行要求（关键补强）**：
     - 若以“前台阻塞”方式运行脚本，任何前台中断都可能导致进程被终止；因此 **推荐** 以“后台守护 + 日志落盘 + PID 落盘”的方式运行。
     - 无论采用前台或后台方式，**完成判定必须以“进程退出 + 退出码 + 输出文件校验”三者同时满足为准**；仅看到日志输出或文件生成片段均不得进入 3B.3。
   - **执行中提示**：开始本步前可再次输出 `【方式 B】正在执行：调用链扫描 → 接口识别。此步骤耗时较长，请耐心等待脚本执行完成。`
   - **🔴 脚本路径解析**：与 3B.1 步骤 1 相同方式，优先 `{REPO_ROOT}/.claude/skills/reverse-interfaces/references/scripts/reverse_by_call_chain/run_reverse_identify.py`，不存在则用 `{REPO_ROOT}/claude/skills/reverse-interfaces/references/scripts/reverse_by_call_chain/run_reverse_identify.py`。将找到的脚本绝对路径记为 `IDENTIFY_SCRIPT`。
   - **🔴 执行命令（推荐：后台守护方式）**：
     - 确保目录存在：
       - `mkdir -p "{REPO_ROOT}/.cache/reverse/interfaces/"`
     - 使用行缓冲将输出写入日志，并将 PID 写入文件（Bash 示例）：
       ```bash
       ( stdbuf -oL -eL python3 {IDENTIFY_SCRIPT} \
         --repo-root {REPO_ROOT} \
         --input-base-dir {input_base_dir} \
         2>&1 | tee "{REPO_ROOT}/.cache/reverse/interfaces/mode-b-identify.log" ) & \
       echo $! > "{REPO_ROOT}/.cache/reverse/interfaces/mode-b-identify.pid"
       ```
     - **轮询等待**：循环检查 `mode-b-identify.pid` 对应进程是否仍在运行；运行中则持续等待并可读取日志增量；当进程退出后，再进行“退出码与输出文件校验”。
   - **🔴 执行命令（可选：前台阻塞方式，仅在明确不需要后台守护时使用）**（必须传入所有必选参数 `--repo-root` 和 `--input-base-dir`，将 `{REPO_ROOT}` 和 `{input_base_dir}` 替换为实际绝对路径后执行）：
     ```bash
     python3 {IDENTIFY_SCRIPT} \
       --repo-root {REPO_ROOT} \
       --input-base-dir {input_base_dir}
     ```
   - **🔴 执行完成判定**：必须同时满足以下条件才视为本步完成：
     1. 脚本进程已退出（已获得退出码）
     2. 退出码为 0（执行成功）
     3. 预期输出文件 `interface_functions_checklist.json` 已存在且非空
     - 若退出码非 0：视为本步失败，向用户报告错误信息，不得继续后续步骤
     - 若脚本仍在运行中（未获得退出码）：继续等待，严禁提前进入 3B.3
   - 该脚本内部会调用 `{scripts/python}/reverse_syntax_parser/main.py --step identify`（优先 `.claude/skills/reverse-interfaces/references/scripts/`，否则 `claude/skills/reverse-interfaces/references/scripts/`），即复用 reverse_syntax_parser 的接口识别实现；完成后会**强制校验** `interface_functions_checklist.json` 是否存在且非空，若校验失败必须视为本步失败，不得继续后续阶段
   - 输出目录：`{input_base_dir}/internal/interface_identification/`
   - 预期输出文件：`{input_base_dir}/internal/interface_identification/interface_functions_checklist.json`

3B.3. **转换为 interface-list.json**（🔴 必选，不得跳过）
   - **🔴 脚本路径解析**：与 3B.1 步骤 1 相同方式，优先 `{REPO_ROOT}/.claude/skills/reverse-interfaces/references/scripts/reverse_by_call_chain/convert_reverse_interface_checklist.py`，不存在则用 `{REPO_ROOT}/claude/skills/reverse-interfaces/references/scripts/reverse_by_call_chain/convert_reverse_interface_checklist.py`。将找到的脚本绝对路径记为 `CONVERT_SCRIPT`。
   - **🔴 执行命令**（必须传入所有必选参数，将 `{REPO_ROOT}` 和 `{input_base_dir}` 替换为实际绝对路径后执行）：
     ```bash
     python3 {CONVERT_SCRIPT} \
       --repo-root {REPO_ROOT} \
       --input {input_base_dir}/internal/interface_identification/interface_functions_checklist.json \
       --output {REPO_ROOT}/.cache/reverse/interfaces/interface-list.json
     ```
   - 确保 `{REPO_ROOT}/.cache/reverse/interfaces/` 目录存在（转换脚本会按需创建；也可先执行 `mkdir -p "{REPO_ROOT}/.cache/reverse/interfaces/"`）
   - 转换后的 `interface-list.json` 与方式A输出格式一致。
   - **3B.3.1 校验**：执行 3B.3 后**必须**检查 `{REPO_ROOT}/.cache/reverse/interfaces/interface-list.json` 是否存在且非空。若不存在则不得进入步骤5，须向用户输出错误说明并检查：3B.2 是否已生成 `interface_functions_checklist.json`、3B.3 转换命令是否返回退出码 0，必要时重新执行 3B.3 直至该文件生成成功。

3B.4. **方式B 完成后**
   - 仅当 3B.3.1 校验通过（`interface-list.json` 已存在）后，方可进入步骤5。
   - 跳过步骤4中的批次验证（方式B无批次文件）
   - 直接进入步骤5展示结果并向用户确认


### 4. [ ] 保存批次结果或最终结果到缓存文件

#### 关键验证步骤
- **方式A**：如果进行了分批处理，必须首先验证所有子agent均已成功完成处理
  - 🔴 AI Agent直接读取批次状态文件，计算未处理批次数
  - 如果未处理批次数 > 0：绝对禁止创建最终文件
  - 如果未处理批次数 == 0：验证通过，可以继续执行
- **方式B**：转换脚本已直接生成 `interface-list.json`，无需批次验证
- 🔴 **保存前Token检查**：检查当前上下文大小，如超过15万tokens则强制清空后再保存



### 5. [ ] 展示结果并向用户确认
- **🔴 关键要求**：
  - **无论缓存是否存在，只要 `interface_list.confirmed == false`，就必须执行此步骤**
  - **即使 `interface-list.json` 文件已存在，只要未确认，就必须展示并等待用户确认**
  - **这是强制步骤，AI Agent 不能跳过，不能自动继续到阶段4**
- 获取仓库根目录
- 🔴 强制验证缓存状态：AI Agent直接读取状态文件，验证 `interface_list.confirmed == false`
- 读取JSON文件：`{REPO_ROOT}/.cache/reverse/interfaces/interface-list.json`
- 总结并展示：
  - 接口总数
  - 按接口类型分组统计
  - 按层级/业务领域/语言分组统计
  - 详细接口列表（按接口类型分组展示）
  - 元数据：扫描时间、来源、扫描范围等
- **🔴 执行统一确认机制**：按照 `reverse-shared/references/confirmation-template.md` 中的"阶段结束确认模板"执行
  - 阶段名称：接口清单扫描
  - 询问内容："接口清单已生成，是否确认清单正确？[Y/n]"


### 6. [ ] 处理用户确认，更新缓存状态
- **🔴 关键要求**：
  - **交互模式下：只有用户明确回复后，才能执行后续操作**
  - **交互模式下：如果用户未回复，AI Agent 必须继续等待，不能自动继续**
  - **非交互模式下：自动确认并继续**
  - **这是强制步骤，AI Agent 不能跳过**
- **🔴 执行统一确认机制**：按照 `reverse-shared/references/confirmation-template.md` 中的"阶段结束确认模板"的步骤3执行
  - 状态文件：`{REPO_ROOT}/.cache/reverse/interfaces/.cache-status.json`
  - 状态字段：`interface_list`
  - 下一阶段：阶段4（详细信息提取与文档生成）
  - **说明**：类型分类已在阶段3中完成（接口清单已包含 `interface_type` 字段），不需要单独的类型分类阶段
- 如果用户拒绝（仅交互模式）：
  - 允许调整、排除或补充接口
  - **🔴 禁止行为**：
    - ❌ 在交互模式下，未获得用户明确回复的情况下更新状态文件
    - ❌ 在交互模式下，假设用户已确认，自动继续到阶段4
    - ❌ 跳过用户确认步骤，直接继续执行

### 7. [ ] 执行数量质量闸门校验（强制）
- 🔴 **强制要求**：必须执行数量质量闸门校验，未通过不得进入阶段4
- 调用脚本：
  - Linux/macOS/Windows（Python跨平台）：
    ```bash
    python3 {REPO_ROOT}/.claude/skills/reverse-interfaces/references/scripts/validate_interface_quality_gate.py {REPO_ROOT}
    ```
- 读取输出报告：`{REPO_ROOT}/.cache/reverse/interfaces/interface-quality-report.json`
- 必查项：
  - 实际数量与预估数量是否“基本一致”
  - `full_list_generated == true`（确认是全量清单而非示例）
  - `mandatory_flags.quality_gate_passed == true`

### 7.5. [ ] 扫描文件覆盖度自动检测（强制）
- 🔴 **触发条件**（满足任一即必须执行本步骤）：
  - 步骤7 质量闸门报告状态为 `too_few`；或
  - `interface-list.json` 中接口总数明显低于 `interface-estimation.json` 中的 `estimated_total_interfaces`（与质量闸门口径一致）
- 🔴 **目的**：自动判断缺口是否主要由 **`file_list.json` 覆盖文件过少**（相对仓库全部可扫代码文件）导致，而非单纯识别规则失效。
- 调用脚本（仅检测，默认不写文件）：
  ```bash
  python3 {REPO_ROOT}/.claude/skills/reverse-interfaces/references/scripts/detect_interface_scan_coverage.py {REPO_ROOT}
  ```
- 读取报告：`{REPO_ROOT}/.cache/reverse/interfaces/interface-scan-coverage-report.json`
- 关注字段：
  - `likely_insufficient_coverage` / `recommend_full_file_list_rescan`
  - `file_list_count`、`repo_code_file_count`、`coverage_ratio`
  - `actual_total_interfaces`、`estimated_total_interfaces`
- 🔴 **当 `recommend_full_file_list_rescan == true` 时**：
  - **交互模式（含半自动/可对话场景）**：
    - 必须向用户展示上述分析摘要；
    - **必须**询问是否执行「全量扩展 `file_list.json` + 强制重建扫描批次 + 重新执行接口清单扫描」；
    - 仅当用户明确确认后，才执行扩展与重扫（不可默认替用户选“否”跳过）。
  - **非交互模式（全自动 `--non-interactive` / `--yes` 等）**：
    - 必须自动执行全量文件列表扩展并重扫，不得因无用户回复而中止恢复流程：
      ```bash
      python3 {REPO_ROOT}/.claude/skills/reverse-interfaces/references/scripts/detect_interface_scan_coverage.py {REPO_ROOT} --apply-full-file-list
      ```
    - 随后必须调用 `generate_interface_batches`（或等价 Python 脚本）**带 `--force`（或文档规定的强制重建参数）** 重建 `batch-mapping.json` / `batch-details-*`，再按阶段3批次流程重新识别并合并 `interface-list.json`。
- 🔴 **脚本退出码**：为 `2` 时表示「疑似覆盖不足且数量偏低、需按上款处理」；若已带 `--apply-full-file-list` 并成功写入全量列表，脚本会以 `0` 退出，但主流程仍须继续「重建批次 + 重扫」直至质量闸门通过。

### 8. [ ] 根据闸门结果执行重扫/重筛策略（强制）
- 当报告状态为 `too_few`：
  - 必须先完成步骤 **7.5** 的覆盖度检测与用户选择/自动全量扩展（如适用），再触发扩范围重扫；若仍不足，必须开启全文件扫描（与 7.5 全量 `file_list` 一致）
  - 交互模式下给出建议并允许用户指定新策略/路径/类型
- 当报告状态为 `too_many`：
  - 必须执行接口类型分析与组合筛选，再次生成清单
  - 交互模式下支持用户注入筛选规则
- 当报告状态为 `invalid_list`：
  - 必须重新生成全量 `interface-list.json`，禁止带示例化清单进入下一阶段
- 🔴 **阻断规则**：若上述处理未完成，或质量闸门标识未通过，禁止进入阶段4


## 🔴 批次处理要求
请参考 [核心规则文档](../core-rules.md) 中的分批处理规则。

## 输出
1. 接口清单（JSON格式），保存到缓存目录 `{REPO_ROOT}/.cache/reverse/interfaces/interface-list.json`，包含所有识别出的接口定义。
2. **方式A**：批次接口清单文件（JSON格式），保存到缓存目录 `{REPO_ROOT}/.cache/reverse/interfaces/interface-list-batch-{batch_number}.json`，由interface-recognizer子agent生成。
3. **方式A**：批次映射文件、批次详细文件、批次状态文件（`batch-mapping.json`、`batch-details-{n}.json`、`interface_scanning-batch-status.json`）。
4. **方式B**：无批次文件，直接由转换脚本生成 `interface-list.json`；reverse_syntax_parser 原始输出位于 `{input_base_dir}/internal/interface_identification/`。



**文件状态说明：**
- `files` 字段使用对象数组格式，每个对象包含：
  - `path`: 文件路径（相对路径）
  - `status`: 处理状态，可选值：
    - `"pending"`: 待处理（初始状态）
    - `"processing"`: 处理中
    - `"completed"`: 已完成
    - `"failed"`: 处理失败
- 脚本支持自动查找下一个未处理的文件（跳过"completed"和"failed"状态的文件）
- 脚本兼容旧格式（字符串数组），自动识别并转换


## 🔴 关键注意事项
- **🔴 强制要求**：AI Agent 必须在阶段 3 完成后暂停，等待用户确认后才能继续阶段 4（无论缓存是否存在，只要 `interface_list.confirmed == false`，就必须展示结果并等待用户确认）
- 接口清单已包含类型分类信息（`interface_type` 字段），是详细信息提取的输入，必须确认后才能使用
- **用户确认后，AI Agent 应该自动继续执行阶段 4（详细信息提取与文档生成），不需要等待额外的用户指令**
- **🔴 用户确认步骤是强制步骤，不能跳过，不能省略**
- **🔴 接口清单生成必须严格按照"接口清单JSON模板定义"中的结构生成，确保与阶段4的输入要求一致**
- **🔴 子agent使用要求：如果有多个批次要处理，采用分轮执行策略，每轮最多启动2个interface-recognizer子agent同时分别处理不同批次文件，每轮完成后必须/compact**
- **🔴 状态管理要求**：主agent负责所有批次状态的统一管理，包括状态更新、统计信息维护等
- 跨平台支持：所有脚本调用必须同时支持Linux(bash)和Windows(PowerShell)
- **🔴 脚本使用违规严重警告**：
  - 严禁手动修改接口状态文件跳过处理步骤
  - 严禁批量创建空接口文件模拟处理完成
  - 严禁跳过用户确认机制自动处理所有剩余接口
  - 违规行为将导致处理状态不一致，影响断点续执行功能

