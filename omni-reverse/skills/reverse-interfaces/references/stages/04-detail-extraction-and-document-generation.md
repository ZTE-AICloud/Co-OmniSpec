# 接口详细信息提取与文档生成

<!-- 阶段4：详细信息提取与文档生成 -->

## 职责
基于阶段3接口清单扫描阶段的结果的输出，从代码中提取每个接口的接口信息、功能描述和业务逻辑实体，并直接生成最终文档到output目录。

**单接口详情分析与文档生成**：子 Agent（interface-analyzer）按本 Skill 内 [references/implementation/interface-detail-analysis.md](../implementation/interface-detail-analysis.md) 执行，输入/输出与步骤以该文档为准。

## 脚本路径说明

本阶段涉及两类脚本路径：

- **本 Skill 捆绑脚本**（使用 `${CLAUDE_SKILL_DIR}/references/scripts/`）：文件名校验与修复脚本、全量文档生成校验脚本等 Python 脚本
- **OmniSpec 项目脚本**（使用 `${DSDD}/scripts/bash/` 或 `${DSDD}/scripts/powershell/`）：批次管理、进度跟踪等 bash/PowerShell 工具脚本，由 OmniSpec 项目提供

## 执行流程
### 0. [ ] 创建阶段4的子任务的Todo列表
为确保阶段执行过程的透明化和可追踪性，需要创建阶段4的子任务的Todo列表：

步骤1. **步骤1 清理上一阶段的上下文，保证本阶段的上下文干净**
步骤2. **步骤2 获取仓库根目录和缓存路径**
步骤3. **步骤3 检查缓存状态**
步骤4. **步骤4 执行AI分析所有接口并直接生成文档（接口详细信息提取）**
步骤5. **步骤5 展示结果并向用户确认**
步骤6. **步骤6 处理用户确认，更新缓存状态**

### 1. [x] 清理上一阶段的上下文，保证本阶段的上下文干净
- **阶段开始时主动清空上下文**：执行上下文清理，明确说明"开始阶段4：接口详细信息提取与文档生成。已清空上一阶段的上下文"
- **执行必要的上下文压缩**：判断当前会话的上下文使用率，这个阶段会很耗token，需要先把当前会话的上下文进行压缩，再执行后续流程


### 2. [ ] 获取仓库根目录和缓存路径
- 跨平台脚本调用获取 REPO_ROOT：
  - AI Agent直接调用check-prerequisites.sh脚本
  - AI Agent直接调用check-prerequisites.ps1脚本
- 定义缓存目录：`{REPO_ROOT}/.cache/reverse/interfaces/`
- 定义输出目录：`{REPO_ROOT}/omni-doc/specs/interfaces`

### 3. [ ] 检查缓存状态
- AI Agent直接读取状态文件 `{REPO_ROOT}/.cache/reverse/interfaces/.cache-status.json`
- 检查 `document_generation.confirmed` 字段
- 如果 `confirmed == true`：跳过阶段4，使用缓存结果
- 如果 `confirmed == false` 或不存在：执行阶段4
- 检查接口处理状态：如果有接口处理失败或未完成，从上次中断处继续处理

### 4. [ ] 执行AI分析所有接口并直接生成文档（接口详细信息提取与文档生成）
为确保阶段执行过程的透明化和可追踪性，创建步骤4的子任务的Todo列表：

4.1. [ ] **4.1 获取已处理接口信息**
4.2. [ ] **4.2 创建接口批次文件**
4.3. [ ] **4.3 获取下一个要执行的接口批次**
4.4. [ ] **4.4 更新批次状态为processing（启动前）**
4.5. [ ] **4.5 同时启动多个子agent处理多批次（后台同时运行）**
4.6. [ ] **4.6 收集子agent结果并更新状态**
4.7. [ ] **4.7 检查是否还有未处理的批次**
4.8. [ ] **4.8 继续处理剩余的接口**

#### 批处理执行流程概览
批处理模式下，主Agent将按照以下流程执行：
1. **创建接口批次**：调用批次生成脚本先按 `interface-list.json` 中的 `interface_id` 序号升序排列，再按“批次大小+Token预算”动态分组（不允许重新编号，不允许重复；阶段4必须继承该序号）
2. **获取待处理批次**：调用获取批次脚本获取下一个待处理的批次（最多3个）
3. **更新批次状态为processing**：在启动子Agent前，将所有批次状态标记为"processing"并记录开始时间
4. **并行处理批次**：启动多个interface-analyzer子Agent并行处理不同批次
5. **收集结果并更新状态**：等待所有子Agent完成，收集结果，根据结果批量更新状态为"completed"或"failed"
6. **循环处理**：重复步骤2-5直到所有批次处理完成

#### 🔴 批处理执行流程

**🔴 批处理步骤**：
4.1. **获取已处理接口信息**
   - 🔴 **强制要求**：必须调用进度跟踪脚本获取当前处理进度
   - 🔴 调用进度跟踪脚本获取当前处理进度：
     - Linux/macOS: `${DSDD}/scripts/bash/reverse/interfaces/utils/get_processing_progress.sh {REPO_ROOT}`
     - Windows: `powershell -ExecutionPolicy Bypass -File {REPO_ROOT}\scripts\powershell\reverse\interfaces\utils\Get-ProcessingProgress.ps1 -RepoRoot {REPO_ROOT}`
   - 🔴 分析接口清单文件，确定当前处理状态：
     - 读取 `{REPO_ROOT}/.cache/reverse/interfaces/interface-list.json`
     - 统计各状态接口数量（pending, processing, completed, failed）
     - 确定是否为断点执行场景（存在processing状态的接口）
   - 🔴 根据接口总数决定是否需要批次处理：
     - 如果接口总数 <= 5：执行单批处理模式
     - 如果接口总数 > 5：执行分批处理模式（按动态批次策略划分，默认每批最多2个接口）

4.2. **创建接口批次文件**
   - 🔴 **强制要求**：必须首先检查批次映射文件是否已存在，避免重复创建导致状态丢失
   - 🔴 **前置检查**：在创建批次文件之前，必须先检查批次映射文件是否存在：
     - 检查批次映射文件是否存在（兼容两种命名）：
       - `{REPO_ROOT}/.cache/reverse/interfaces/interface-batch-mapping.json`（旧工具链）
       - `{REPO_ROOT}/.cache/reverse/interfaces/batch-mapping.json`（接口清单扫描阶段生成，推荐）
     - 如果文件存在且有效（包含批次信息），**跳过创建步骤**，直接进入步骤4.3获取批次
     - 如果文件不存在或无效，才执行批次创建
   - 🔴 **批次文件创建**：仅在批次映射文件不存在或无效时才调用批次生成脚本：
     - Linux/macOS: `${DSDD}/scripts/bash/reverse/interfaces/utils/create_interface_batches.sh --repo-root {REPO_ROOT}`
     - Windows: `powershell -ExecutionPolicy Bypass -File {REPO_ROOT}\scripts\powershell\reverse\interfaces\utils\Create-InterfaceBatches.ps1 -RepoRoot {REPO_ROOT}`
     - 脚本会自动检查现有批次文件，如果存在有效的批次文件，会跳过创建并输出提示信息
     - 如需强制重新生成，可以添加 `--force` 参数（Linux/macOS）或 `-Force` 参数（Windows）
   - 🔴 **上下文超限回退策略（新增）**：
     - 若出现 `max_tokens/max_completion_tokens too large`（400）错误，必须强制重建更小批次后重试
     - 建议设置环境变量后重建批次：
       - `INTERFACE_DETAIL_BATCH_SIZE=1`
       - `INTERFACE_DETAIL_MAX_TOKENS=8000`
     - 重建命令示例（Linux/macOS）：
       ```bash
       INTERFACE_DETAIL_BATCH_SIZE=1 INTERFACE_DETAIL_MAX_TOKENS=8000 \
       ${DSDD}/scripts/bash/reverse/interfaces/utils/create_interface_batches.sh --repo-root {REPO_ROOT} --force
       ```
   - 🔴 **验证批次文件**：验证批次文件已正确生成或已存在：
     - 检查批次映射文件存在（`interface-batch-mapping.json` 或 `batch-mapping.json`，脚本会自动回退选择，无需手工复制/重命名）
     - 检查 `{REPO_ROOT}/.cache/reverse/interfaces/interface_detail-batch-status.json` 文件存在
     - 检查至少一个 `interface-batch-details-{n}.json` 文件存在
   - 🔴 明确声明："接口批次文件已就绪，总共 {total_batches} 个批次"（无论是新创建还是已存在）

4.3. **获取下一个要执行的接口批次**
   - 🔴 **强制要求**：必须调用获取批次脚本获取待处理批次
   - 🔴 调用获取批次脚本获取待处理批次（最多3个）：
     - Linux/macOS: `${DSDD}/scripts/bash/reverse/interfaces/utils/get_next_interface_batches.sh --repo-root {REPO_ROOT} --batch-count 3`
     - Windows: `powershell -ExecutionPolicy Bypass -File {REPO_ROOT}\scripts\powershell\reverse\interfaces\utils\Get-NextInterfaceBatches.ps1 -RepoRoot {REPO_ROOT} -BatchCount 3`
   - 🔴 **处理不同场景**：
     - **首次执行场景**：获取状态为"pending"的批次
     - **断点执行场景**：如果存在"processing"状态的批次，优先处理该批次（可能是上次中断的批次）
   - 🔴 **验证批次信息**：
     - 验证批次编号、批次文件路径等关键信息是否存在
     - 验证批次文件是否存在且可访问
     - 如果批次信息不完整，标记为"failed"并记录错误信息

4.4. **更新批次状态为processing（启动前）**
   - 🔴 **强制要求**：主agent负责所有批次状态的统一管理，子agent不参与状态更新
   - 🔴 **批量更新状态**：在批量启动interface-analyzer子agent之前，主agent必须调用批量状态更新脚本将所有批次状态标记为"processing"
   - 🔴 调用批量状态更新脚本将批次状态标记为"processing"：
     - Linux/macOS: `${DSDD}/scripts/bash/reverse/interfaces/utils/update_interface_batches_status.sh --repo-root {REPO_ROOT} --batch-updates '{batch_updates_json}'`
     - Windows: `powershell -ExecutionPolicy Bypass -File {REPO_ROOT}\scripts\powershell\reverse\interfaces\utils\Update-InterfaceBatchesStatus.ps1 -RepoRoot {REPO_ROOT} -BatchUpdates "{batch_updates_json}"`
   - 🔴 **验证要求**：必须验证所有批次状态更新成功，如有更新失败必须报告错误并停止处理
   - 🔴 明确声明："已标记 {batch_count} 个批次为处理中状态"
   - 🔴 记录批次开始处理时间，用于计算处理耗时
   - 🔴 **记录启动的批次列表**：记录本次启动的所有批次编号，用于后续等待验证

4.4.5. **等待子agent完成（强制轮询检查）**
   - 🔴 **强制要求**：必须通过轮询机制等待所有子Agent完成，禁止仅检查文件存在性
   - 🔴 **轮询检查流程**：
     1. 使用批次状态验证脚本验证批次是否真正完成：
        - Linux/macOS: `${DSDD}/scripts/bash/verify-batches-completion.sh --repo-root {REPO_ROOT} --batch-numbers '{batch_numbers_json}' --stage-type interfaces`
        - Windows: `powershell -ExecutionPolicy Bypass -File {REPO_ROOT}\scripts\powershell\verify-batches-completion.ps1 -RepoRoot {REPO_ROOT} -BatchNumbers "{batch_numbers_json}" -StageType interfaces`
     2. 验证通过条件（必须同时满足）：
        - 批次状态文件中的状态为"completed"
        - 输出文件存在且格式正确（接口详情文档）
        - 批次处理时间戳在合理范围内
     3. 如果验证未通过，等待30秒后再次检查（最多等待30分钟）
     4. 如果30分钟内仍有批次未完成，报告超时错误并标记为"failed"
   - 🔴 **禁止行为**：
     - 禁止仅检查文件存在性就认为子Agent完成
     - 禁止在未验证批次状态的情况下继续执行
     - 禁止模拟或创建虚假的结果文件
     - 禁止跳过等待步骤直接进入结果收集
   - 🔴 **等待完成确认**：所有批次验证通过后，明确声明："所有批次已完成验证，可以继续收集结果"

4.5. **分轮启动多个子agent处理多批次（分轮执行策略）**
   - 🔴 **分轮执行策略（核心机制）**：
     - 根据 [SKILL.md](../../SKILL.md) 与子 Agent 委派规则，每轮最多启动 2 个 `interface-analyzer` 子 Agent，避免上下文超限
     - 采用分轮执行模式：轮次1启动Agent1+Agent2 → 等待完成 → /compact，轮次2启动Agent3+Agent4 → 等待完成 → /compact
     - 每轮处理最多2个批次，确保上下文可控
   - 🔴 **强制要求**：必须并行启动多个interface-analyzer子Agent处理不同批次
   - 🔴 **并行启动方式**：
     - 为了提高处理效率，同时启动多个interface-analyzer子Agent处理不同的批次
     - 🔴 **强制要求**：必须使用明确的并行启动指令，确保多个子Agent同时启动
     - 🔴 **并发数限制**：每轮最多同时启动2个子Agent，避免上下文超限
     - 示例：请同时启动2个interface-analyzer子Agent来分别处理以下批次文件：
       - `interface-batch-details-1.json`
       - `interface-batch-details-2.json`
   - 🔴 **上下文管理**：
     - 主agent负责协调所有子agent的执行
     - 每个子agent独立处理自己的批次数据
     - 主agent不直接参与批次内的具体接口识别工作
     - 🔴 **分轮执行流程**：
       - 轮次1：启动Agent1处理interface-batch-details-1.json + Agent2处理interface-batch-details-2.json → 等待完成 → /compact
       - 轮次2：启动Agent3处理interface-batch-details-3.json + Agent4处理interface-batch-details-4.json → 等待完成 → /compact
       - 依此类推，直到所有批次处理完成

4.6. **收集子agent结果并更新状态**
   - 🔴 **等待子agent处理完成**：主agent等待当前轮次所有并行启动的interface-analyzer子agent完成接口识别任务
   - 🔴 **收集处理结果**：
     - 收集当前轮次每个子agent生成的接口详情文档：
      - 文件路径：`{REPO_ROOT}/omni-doc/specs/interfaces/{接口ID}_{中文业务简要总结}.md`
       - 例如：`API_001_事务创建调度回调接口.md`
    - 🔴 **批次明细 to-do + 范围锁定（新增，必须遵守）**：
      - 在启动该轮次所有 `interface-analyzer` 子agent之前，主agent必须从本轮涉及的每个 `interface-batch-details-{batch_number}.json` 中提取出“该批次要扫描的完整 `interface_id` 集合”；
      - 为每个 `batch_number` 创建可追踪的 to-do（或等价记录），内容至少包含：`batch_number` 与“本批次的全部 interface_id 列表”；
      - 子agent只能处理这些 interface_id 对应的接口；重试时**必须使用同一个批次明细文件**，禁止为了省事缩减接口集合或替换为新的批次明细文件（否则系统不可用）。
   - 🔴 **验证处理结果**：
     - 检查生成的接口详情文档是否存在且格式正确
     - 验证接口数据的完整性
     - 统计处理成功的批次数量
     - 如果某个子agent处理失败，记录错误信息
    - 🔴 **根据结果批量更新状态（带批次全生成闸门）**：
      - 在调用批量状态更新脚本把某个 `batch_number` 标记为 `completed` 之前，主agent必须先对该 `batch_number` 执行批次级全生成校验（`ensure_interface_batch_docs_generated.py`），确认本批次下每个 `interface_id` 的详情文档都已生成；
      - 若校验返回缺失（退出码为 `2`），则不得把该 `batch_number` 标记为 `completed`，必须保持为 `pending` 并触发“重试同批次”（不允许缩减批次明细接口集合，不允许替换批次文件）。
   - 🔴 **强制/compact机制**：
     - 当前轮次所有批次处理完成后，必须执行/compact指令压缩上下文
     - 明确声明："当前轮次已完成，执行/compact压缩上下文，释放上下文空间"
     - 这是防止上下文超限的关键步骤，每轮完成后必须执行
     - **处理成功**：如果子agent成功完成任务，将对应批次状态标记为"completed"
     - **处理失败**：如果子agent处理失败，将对应批次状态标记为"failed"
     - 批量状态更新脚本调用：
       - Linux/macOS: `${DSDD}/scripts/bash/reverse/interfaces/utils/update_interface_batches_status.sh --repo-root {REPO_ROOT} --batch-updates '{batch_updates_json}'`
       - Windows: `powershell -ExecutionPolicy Bypass -File {REPO_ROOT}\scripts\powershell\reverse\interfaces\utils\Update-InterfaceBatchesStatus.ps1 -RepoRoot {REPO_ROOT} -BatchUpdates "{batch_updates_json}"`
     - 批量更新可以显著减少状态更新时间，提高整体处理效率
   - 🔴 **批次处理后清理上下文**：
     - 清理内容：忘记当前批次的所有处理数据和分析结果
     - 明确声明："已完成 {batch_count} 个批次的处理。已清空当前批次的上下文"
   - 🔴 **计算批次处理耗时**：
     - 记录批次开始和结束时间，计算处理时长
     - 更新批次处理时间到批次状态文件
   - 🔴 **强制要求**：必须调用进度跟踪脚本获取更新后的处理进度
   - 🔴 向用户报告当前进度："已完成 {completed_batches}/{total_batches} 个批次的处理，进度 {progress_percentage}%，剩余 {pending_batches} 个批次待处理"
  - 🔴 **文件名强制校验与修复（新增，必须执行）**：
    - 每轮批次完成后，必须先调用文件名校验脚本，修复不符合规范的详情文档文件名：
      ```bash
      python3 {REPO_ROOT}/.claude/skills/reverse-interfaces/references/scripts/validate_and_fix_interface_doc_filenames.py {REPO_ROOT}
      ```
    - 规范：`{接口ID}_{中文业务简要总结}.md`
    - 不符合规范的文件必须自动重命名，禁止跳过（否则下游系统可能崩溃）

    - 🔴 **批次级别文件全生成校验（新增，必须执行）**：
      - 对本轮涉及的每个 `batch_number` 逐个执行批次级校验脚本：
       ```bash
       python3 {REPO_ROOT}/.claude/skills/reverse-interfaces/references/scripts/ensure_interface_batch_docs_generated.py {REPO_ROOT} --batch-number {batch_number}
       ```
     - 判定规则：
       - 退出码 `0`：该批次全部接口详情文档已生成，允许继续处理结果收集与状态更新；
       - 退出码 `2`：该批次存在缺失文档；
         - 主agent必须等待脚本回写接口 `processing_status=pending` 并将该批次状态重置为 `pending`；
         - **必须重新启动同一个 `batch_number` 对应的 `interface-analyzer` 子agent**（不允许缩减批次明细接口集合，不允许更换批次文件，不允许减少扫描范围）；
         - 直到该批次校验通过（退出码 `0`）才允许进入下一批次。
     - 🔴 阻断规则：若任一 `batch_number` 校验未通过，主agent必须继续重试该缺失 `batch_number`，直到所有相关 `batch_number` 都校验通过；否则禁止进入“下一批次/下一轮完成推进”。

   - 🔴 **全量文档强制校验（新增，必须执行）**：
     - 每轮批次完成后，必须调用全量校验脚本核对详情文档是否覆盖 `interface-list.json` 中全部接口：
       ```bash
       python3 {REPO_ROOT}/.claude/skills/reverse-interfaces/references/scripts/ensure_all_interface_docs_generated.py {REPO_ROOT}
       ```
     - 若返回“存在缺失”（退出码2）：
       - 视为“尚未完成”，禁止结束阶段
       - 脚本会自动把缺失接口状态和关联批次状态重置为 `pending`
       - 主流程必须继续执行后续批次，直到校验通过

4.7. **检查是否还有未处理的批次**
   - 🔴 **强制要求**：必须严格按照指导文件要求调用脚本检查是否还有待处理批次
   - 🔴 调用获取批次脚本检查是否还有待处理批次：
       - 使用新的批量获取脚本获取多个待处理批次：
       - Linux/macOS: `${DSDD}/scripts/bash/reverse/interfaces/utils/get_next_interface_batches.sh --repo-root {REPO_ROOT} --batch-count 3`
       - Windows: `powershell -ExecutionPolicy Bypass -File {REPO_ROOT}\scripts\powershell\reverse\interfaces\utils\Get-NextInterfaceBatches.ps1 -RepoRoot {REPO_ROOT} -BatchCount 3`
   - 🔴 **强制要求**：必须调用进度跟踪脚本获取当前处理进度
   - 🔴 调用进度跟踪脚本获取当前处理进度：
     - Linux/macOS: `${DSDD}/scripts/bash/reverse/interfaces/utils/get_processing_progress.sh {REPO_ROOT}`
     - Windows: `powershell -ExecutionPolicy Bypass -File {REPO_ROOT}\scripts\powershell\reverse\interfaces\utils\Get-ProcessingProgress.ps1 -RepoRoot {REPO_ROOT}`
   - 🔴 **处理要求**：必须严格按照以下规则处理剩余批次
   - 🔴 **处理不同执行场景**：
     - **首次执行场景**：处理所有待处理批次
     - **断点执行场景**：从上次中断处继续处理所有待处理批次
  - 🔴 **不可协调约束（新增）**：
    - 不允许以“已生成若干示例文档”判定完成
    - 只有当 `ensure_all_interface_docs_generated.py` 返回全量通过时，才允许结束循环

4.8. **继续处理剩余的接口**
   - 🔴 如果还有待处理批次：继续循环处理
     - 清理上一批次无关的上下文信息，为了保证token不超限，必须清理无用的上下文数据
     - 显示剩余批次数和预估处理时间
     - 🔴 向用户报告当前进度："已完成 {completed_batches}/{total_batches} 个批次的处理，进度 {progress_percentage}%，剩余 {pending_batches} 个批次待处理，预计还需要 {estimated_remaining_time}"
     - 🔴 **执行统一确认机制**（当剩余批次数 > 3时）：按照 `reverse-shared/references/confirmation-template.md` 中的"过程中确认模板 - 类型2：是否继续处理确认"执行
       - 询问内容："检测到还有 {remaining_batches} 个批次未处理，预计需要 {estimated_time} 完成，是否继续处理？[Y/n]"
       - 非交互模式下：自动继续处理所有剩余批次
     - 🔴 **非交互模式强制不中断（新增，必须遵守）**：
       - 禁止因为“耗时过长/达到时间预算/已生成部分核心文件/已生成若干示例/Token 警告/模型提示资源不足”等任何原因而提前停止；
       - 以“全量校验通过”为唯一完成条件：只要 `ensure_all_interface_docs_generated.py` / 最终数量门禁未通过，就必须继续处理剩余批次；
       - 任何 400 token 超限等错误视为可恢复：必须通过重建更小批次（例如 `INTERFACE_DETAIL_BATCH_SIZE=1`）并重试同一批次，而不是停止。
   - 🔴 **严禁跳过**：严禁在任何情况下跳过未处理的批次
   - 🔴 **必须实际处理**：必须实际处理每个批次的数据，不能批量创建空批次文件或跳过任何批次
   - 🔴 如果所有批次已完成：跳出循环
    - 跳出前必须再次执行全量文档校验脚本，确认无缺失文档
    - 若存在缺失，必须回到批次处理循环，继续生成缺失文档
     - 更新整体状态为 "completed"
     - 🔴 **强制要求**：必须调用进度跟踪脚本获取最终处理进度
     - 🔴 调用进度跟踪脚本获取最终处理进度：
       - Linux/macOS: `${DSDD}/scripts/bash/reverse/interfaces/utils/get_processing_progress.sh {REPO_ROOT}`
       - Windows: `powershell -ExecutionPolicy Bypass -File {REPO_ROOT}\scripts\powershell\reverse\interfaces\utils\Get-ProcessingProgress.ps1 -RepoRoot {REPO_ROOT}`
     - 🔴 最终进度报告："接口详细信息提取与文档生成已完成！总共处理了 {total_interfaces} 个接口，完成率 100%"


### 5. [ ] 展示结果并向用户确认
- 获取仓库根目录
- 🔴 强制验证输出目录：检查文档是否已生成到 `{REPO_ROOT}/omni-doc/specs/interfaces/`
- 🔴 强制验证缓存状态：AI Agent直接读取状态文件，验证 `document_generation.confirmed == false`
- 读取生成的文档列表
- **🔴 生成汇总接口清单**：
  - 调用接口清单生成脚本创建汇总文档：
    - Linux/macOS: `${DSDD}/scripts/bash/reverse/interfaces/utils/generate_interface_inventory.sh --repo-root {REPO_ROOT}`
    - Windows: `powershell -ExecutionPolicy Bypass -File {REPO_ROOT}\scripts\powershell\reverse\interfaces\utils\Generate-InterfaceInventory.ps1 -RepoRoot {REPO_ROOT}`
  - 🔴 **最后阶段数量门禁（新增，必须执行）**：
    - 在生成 `omni-doc/specs/interfaces/接口清单.md` 之前，再次读取全量校验结果（由前述 `ensure_all_interface_docs_generated.py` 生成的退出码/报告决定）：
      - 比对 `interface-list.json` 的 `expected_interface_count` 与实际生成的 `generated_docs_count`
      - 若 `count_match == false` 或存在缺失文档（退出码=2）：必须回到批次循环继续生成，禁止生成 `接口清单.md`
    - 只有当 `count_match == true`（并且缺失数为 0）时，才允许继续生成 `接口清单.md`
  - 🔴 质量门禁：脚本内部会在生成 `接口清单.md` 之前再次执行 `validate_and_fix_interface_doc_filenames.py`
  - 🔴 不通过（重命名/回写后仍不合规）则直接报错退出，禁止生成 `接口清单.md`
  - 脚本将按照模板查找顺序查找并读取接口清单模板文件（优先使用项目特定模板，如果不存在则使用默认模板）
  - 脚本将收集所有已生成的接口详情文档信息
  - 脚本将根据模板生成汇总接口清单文档：`{REPO_ROOT}/omni-doc/specs/interfaces/接口清单.md`
  - 脚本将实施写入重试机制确保跨平台兼容性和正确性
- 总结并展示：
  - 接口总数
  - 生成的文档列表
  - 按类型分组的统计信息
  - 按层级分组的统计信息
  - 代表性接口示例
  - 元数据：提取时间、来源等
  - 生成的文档列表
- **🔴 执行统一确认机制**：按照 `reverse-shared/references/confirmation-template.md` 中的"阶段结束确认模板"执行
  - 阶段名称：接口详细信息提取与文档生成
  - 询问内容："接口详细信息已提取并生成文档完成，是否确认结果？[Y/n]"
- 🔴 状态双重检查：用户响应后（或自动确认后）AI Agent再次读取状态文件，验证更新成功

### 6. [ ] 处理用户确认，更新缓存状态
- **🔴 执行统一确认机制**：按照 `reverse-shared/references/confirmation-template.md` 中的"阶段结束确认模板"的步骤3执行
  - 状态文件：`{REPO_ROOT}/.cache/reverse/interfaces/.cache-status.json`
  - 状态字段：`document_generation`
  - 下一阶段：无（阶段4为最后一个阶段，自动结束整个流程）
- 如果用户拒绝（仅交互模式）：
  - 允许查看详情或重新生成


## AI Agent上下文管理要求
- **阶段开始时主动清空上下文**：请先执行上下文清理，然后明确说明"开始阶段4：接口详细信息提取与文档生成。已清空上一阶段的上下文"
- **参考增强指南**：详细上下文管理策略请参阅 [增强版Token管理和上下文控制指南](../token-management.md)

## 🔴 接口处理要求
请参考 [核心规则文档](../core-rules.md) 中的分批处理规则。

## 🔴 全量文档生成强制要求（新增）
- `interface-list.json` 中每个接口都必须生成对应详情文档，禁止仅生成示例文档
- 必须先通过脚本 `references/scripts/validate_and_fix_interface_doc_filenames.py` 做文件名校验与自动修复
- 必须通过脚本 `references/scripts/ensure_all_interface_docs_generated.py` 做全量校验
- 校验不通过时必须继续分批生成，直至全部完成；该要求不可协商，不得跳过


### 接口状态字段说明
在接口清单文件 `{REPO_ROOT}/.cache/reverse/interfaces/interface-list.json` 中，每个接口对象必须使用以下标准化的状态字段：

#### 必须使用的状态字段
1. **processing_status**（必填）：接口处理状态字段，**必须使用此确切字段名**
   - 可选值：`"pending"`, `"processing"`, `"completed"`, `"failed"`
   - 含义：
     - `"pending"`：接口待处理（初始状态）
     - `"processing"`：接口正在处理中
     - `"completed"`：接口处理完成
     - `"failed"`：接口处理失败

2. **processed_at**（可选）：接口处理完成时间戳
   - 格式：ISO 8601标准格式（例如：`"2026-01-12T10:30:00Z"`）
   - 仅在接口状态为`"completed"`或`"failed"`时添加

3. **processing_time**（可选）：接口处理耗时（秒）
   - 类型：数值型
   - 仅在接口处理完成时添加

#### 状态字段更新规范
- **必须使用标准工具**：更新接口状态时必须使用提供的标准脚本工具：
  - Linux/macOS: `${DSDD}/scripts/bash/reverse/interfaces/utils/update_interface_status.sh`
  - Windows: `{REPO_ROOT}\scripts\powershell\reverse\interfaces\utils\Update-InterfaceStatus.ps1`
  - Python脚本: `.omni-infra/scripts/python/reverse_interfaces/update_interface_status.py`（OmniSpec 源码树内同文件位于 `scripts/python/reverse_interfaces/update_interface_status.py`）

- **禁止手动更新**：严禁手动编辑接口清单文件来更新状态，必须使用标准工具

- **字段命名强制要求**：**必须使用`processing_status`作为状态字段名，禁止使用其他名称如`status`、`state`等**

#### 示例格式
```json
{
  "interface_id": "API_001",
  "name": "getUserInfo",
  "interface_type": "RESTful API",
  "source_file": "/path/to/controllers/user.controller.js",
  "path_method": "/api/users/{id} GET",
  // ... 其他原有字段 ...
  "processing_status": "pending"
}
```

处理中的接口示例：
```json
{
  "interface_id": "API_001",
  "name": "getUserInfo",
  "interface_type": "RESTful API",
  "source_file": "/path/to/controllers/user.controller.js",
  "path_method": "/api/users/{id} GET",
  // ... 其他原有字段 ...
  "processing_status": "processing",
  "processed_at": "2026-01-12T10:30:00Z"
}
```

处理完成的接口示例：
```json
{
  "interface_id": "API_001",
  "name": "getUserInfo",
  "interface_type": "RESTful API",
  "source_file": "/path/to/controllers/user.controller.js",
  "path_method": "/api/users/{id} GET",
  // ... 其他原有字段 ...
  "processing_status": "completed",
  "processed_at": "2026-01-12T10:30:15Z",
  "processing_time": 15.5
}
```

## 输出
最终文档输出（omni-doc 目录）：
- 接口清单文档：`{REPO_ROOT}/omni-doc/specs/interfaces/接口清单.md`
- 接口详情文档：每个接口一个文件，`{REPO_ROOT}/omni-doc/specs/interfaces/{接口ID}_{中文业务简要总结}.md`
  - 规范示例：`API_001_事务创建调度回调接口.md`
- 接口状态信息：直接更新到 `{REPO_ROOT}/.cache/reverse/interfaces/interface-list.json` 文件中，包含每个接口的处理状态信息

## 注意事项
- AI Agent必须在阶段4完成后暂停，等待用户确认后才能结束整个流程
- 文档生成是流程的最终输出，必须确认后才算完成
- 用户确认后，AI Agent应该自动结束整个流程
- **接口处理用户确认**：当接口数量较多时，AI Agent必须在处理过程中适时询问用户是否继续，不得擅自跳过未处理的接口
- 跨平台支持：所有脚本调用必须同时支持Linux(bash)和Windows(PowerShell)
- **🔴 子agent使用要求：如果有多个批次要处理，为了提升处理效率，必须同时启动多个interface-analyzer子agent同时分别处理不同批次文件**
- **🔴 脚本使用违规严重警告**：
  - 严禁手动修改接口状态文件跳过处理步骤
  - 严禁批量创建空接口文件模拟处理完成
  - 严禁跳过用户确认机制自动处理所有剩余接口
  - 违规行为将导致处理状态不一致，影响断点续执行功能