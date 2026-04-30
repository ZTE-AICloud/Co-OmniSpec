# 从接口抽取实体

<!-- 阶段1：从接口抽取实体 -->

## 职责
基于接口反构阶段4的输出（接口聚合文件），从接口聚合文件中识别和提取逻辑实体，记录实体与接口的溯源关系。

## 执行流程
### 0. [ ] 创建阶段1的子任务的Todo列表
为确保阶段执行过程的透明化和可追踪性，需要创建阶段1的子任务的Todo列表：

步骤1. **步骤1 清理上一阶段的上下文，保证本阶段的上下文干净**
步骤2. **步骤2 获取仓库根目录和缓存路径**
步骤3. **步骤3 检查缓存状态和依赖验证**
步骤4. **步骤4 执行AI分析所有接口聚合文件并提取实体（实体抽取）**
步骤5. **步骤5 展示结果并向用户确认**
步骤6. **步骤6 处理用户确认，更新缓存状态**

### 1. [x] 清理上一阶段的上下文，保证本阶段的上下文干净
- **阶段开始时主动清空上下文**：执行上下文清理，明确说明"开始阶段1：从接口抽取实体。已清空上一阶段的上下文"
- **执行必要的上下文压缩**：判断当前会话的上下文使用率，这个阶段会很耗token，需要先把当前会话的上下文进行压缩，再执行后续流程

### 2. [ ] 获取仓库根目录和缓存路径
- 跨平台脚本调用获取 REPO_ROOT：
  - AI Agent直接调用check-prerequisites.sh脚本
  - AI Agent直接调用check-prerequisites.ps1脚本
- 定义缓存目录：`{REPO_ROOT}/.cache/reverse/entities/`
- 定义实体抽取输出目录：`{REPO_ROOT}/.cache/reverse/entities/entity-extraction/`
- 定义接口聚合文件目录：`{REPO_ROOT}/.cache/reverse/interfaces/interface-aggregation/` 或类似路径
- 定义实体文档模板路径：`{REPO_ROOT}/.infra/metamodel/6.entity-template.md`（🔴 抽取输出的每个实体必须严格按此模板结构书写）

### 3. [ ] 检查缓存状态和依赖验证
- AI Agent直接读取状态文件 `{REPO_ROOT}/.cache/reverse/entities/.cache-status.json`
- 检查 `entity_extraction.confirmed` 字段
- 如果 `confirmed == true`：跳过阶段1，使用缓存结果
- 如果 `confirmed == false` 或不存在：执行阶段1

**依赖验证**：
- 🔴 **强制要求**：必须验证接口反构已完成阶段4
- 检查接口反构的缓存状态文件：`{REPO_ROOT}/.cache/reverse/interfaces/.cache-status.json`
- 验证 `document_generation.confirmed` 字段为 `true`
- 如果接口反构未完成，给出明确的错误提示，要求用户先完成接口反构
- 验证接口聚合文件目录存在：`{REPO_ROOT}/.cache/reverse/interfaces/interface-aggregation/` 或类似路径
- 如果接口聚合文件目录不存在，给出明确的错误提示

### 4. [ ] 执行AI分析所有接口聚合文件并提取实体（实体抽取）
为确保阶段执行过程的透明化和可追踪性，创建步骤4的子任务的Todo列表：

4.1. [ ] **4.1 扫描接口聚合文件目录**
4.2. [ ] **4.2 评估数据规模，决定是否分批处理**
4.3. [ ] **4.3 创建文件批次（如果需要）**
4.4. [ ] **4.4 获取下一个要处理的文件批次**
4.5. [ ] **4.5 更新批次状态为processing（启动前）**
4.6. [ ] **4.6 执行AI分析提取实体（批次处理）**
4.7. [ ] **4.7 生成批次结果索引**
4.8. [ ] **4.8 记录溯源信息**
4.9. [ ] **4.9 检查是否还有未处理的批次**
4.10. [ ] **4.10 继续处理剩余的文件**

#### 批处理执行流程概览
批处理模式下，主Agent将按照以下流程执行：
1. **扫描接口聚合文件**：扫描接口聚合文件目录，获取所有MD文件
2. **评估数据规模**：根据文件数量决定是否分批处理（文件数量 > 20时，必须分批处理）
3. **创建文件批次**：如果需要分批处理，将文件按每批10个分组
4. **获取待处理批次**：获取下一个待处理的批次
5. **更新批次状态为processing**：在启动处理前，将批次状态标记为"processing"并记录开始时间
6. **执行AI分析**：调用Python脚本处理批次文件，提取实体
7. **生成批次结果索引**：生成轻量级索引文件，不合并大文件
8. **记录溯源信息**：记录实体与接口的对应关系
9. **循环处理**：重复步骤4-8直到所有批次处理完成

#### 🔴 批处理执行流程

**🔴 批处理步骤**：

4.1. **扫描接口聚合文件目录**
   - 🔴 **强制要求**：必须扫描接口聚合文件目录，获取所有MD文件
   - 扫描目录：`{REPO_ROOT}/.cache/reverse/interfaces/interface-aggregation/` 或类似路径
   - 获取所有 `.md` 文件
   - 统计文件总数
   - 🔴 验证文件存在：如果目录不存在或没有文件，给出明确的错误提示

4.2. **评估数据规模，决定是否分批处理**
   - 🔴 **强制要求**：必须根据文件数量决定是否分批处理
   - 如果文件数量 <= 20：执行单批处理模式
   - 如果文件数量 > 20：执行分批处理模式（按每批10个文件划分）
   - 🔴 明确声明："检测到 {file_count} 个接口聚合文件，{处理模式}"

4.3. **创建文件批次（如果需要）**
   - 🔴 **强制要求**：仅在需要分批处理时创建批次文件
   - 🔴 **前置检查**：在创建批次文件之前，必须先检查批次索引文件是否存在：
     - 检查 `{REPO_ROOT}/.cache/reverse/entities/entity-extraction/entities-index.json` 文件是否存在
     - 如果文件存在且有效（包含批次信息），**跳过创建步骤**，直接进入步骤4.4获取批次
     - 如果文件不存在或无效，才执行批次创建
   - 🔴 **批次文件创建**：仅在批次索引文件不存在或无效时才创建批次：
     - 将文件按每批10个分组
     - 生成批次索引文件：`entities-index.json`
     - 批次索引文件格式：
       ```json
       {
         "version": "1.0",
         "total_batches": 15,
         "total_files": 150,
         "batches": [
           {
             "batch_id": 1,
             "source_files": ["interface-aggregation/API-001.md", "interface-aggregation/API-002.md"],
             "status": "pending",
             "timestamp": null
           }
         ]
       }
       ```
   - 🔴 **验证批次文件**：验证批次索引文件已正确生成或已存在
   - 🔴 明确声明："文件批次已就绪，总共 {total_batches} 个批次"（无论是新创建还是已存在）

4.4. **获取下一个要处理的文件批次**
   - 🔴 **强制要求**：必须从批次索引文件中获取待处理批次
   - 🔴 **处理不同场景**：
     - **首次执行场景**：获取状态为"pending"的批次
     - **断点执行场景**：如果存在"processing"状态的批次，优先处理该批次（可能是上次中断的批次）
   - 🔴 **验证批次信息**：
     - 验证批次编号、批次文件列表等关键信息是否存在
     - 验证批次文件是否存在且可访问
     - 如果批次信息不完整，标记为"failed"并记录错误信息

4.5. **更新批次状态为processing（启动前）**
   - 🔴 **强制要求**：主agent负责所有批次状态的统一管理
   - 🔴 **更新状态**：在启动处理之前，主agent必须将批次状态标记为"processing"
   - 更新批次索引文件中的批次状态
   - 记录批次开始处理时间
   - 🔴 明确声明："已标记批次 {batch_id} 为处理中状态"

4.6. **执行AI分析提取实体（批次处理）**
   - 🔴 **强制要求**：必须调用Python脚本处理批次文件
   - 调用实体抽取脚本：
     - Linux/macOS: `python3 {REPO_ROOT}/specify/scripts/python/reverse_entities/entity_extractor.py --repo-root {REPO_ROOT} --batch-id {batch_id} --interface-aggregation-dir {interface_aggregation_dir} --user-terminology {user_terminology_file} --output-dir {output_dir}`
     - Windows: `python {REPO_ROOT}\specify\scripts\python\reverse_entities\entity_extractor.py --repo-root {REPO_ROOT} --batch-id {batch_id} --interface-aggregation-dir {interface_aggregation_dir} --user-terminology {user_terminology_file} --output-dir {output_dir}`
   - 脚本参数说明：
     - `--repo-root`：仓库根目录
     - `--batch-id`：批次ID（如果单批处理，可以省略）
     - `--interface-aggregation-dir`：接口聚合文件目录
     - `--user-terminology`：用户术语文件路径（可选）
     - `--output-dir`：输出目录
   - 🔴 **AI分析要求**：
     - 使用提示词模板：`reverse/tools/prompts/entity_extraction_from_interface.md`
     - 对每个接口聚合文件调用AI模型，识别逻辑实体
     - 实体识别包括：
       - 实体标识（entity_id）
       - 业务名称（entity_name_cn）
       - 实体类型（entity_type）
       - 所属领域（domain）
       - 关联文件（related_files）
       - 关键职责（responsibility）
       - 类图（PlantUML 或 Mermaid，生成文档时须可转为 PlantUML）
     - 🔴 **关键提示词要求**：
       - 实体必须满足：有对外接口或对外行为，且有核心规则/状态/依赖交互
       - 排除纯DTO、工具类、常量载体等
     - 🔴 **输出格式（强制与实体模板一致）**：
       - 必须加载并严格遵循实体文档模板：`{REPO_ROOT}/.infra/metamodel/6.entity-template.md`
       - 每个实体在文档中必须按模板完整呈现，结构不可删减、顺序不可打乱。一个 `ENTITIES-xxx.md` 中若有多个实体，则每个实体写为一个完整块，块内结构如下：
         1. **YAML frontmatter**：`id`（ENTITY-XXX）、`name`（ENTITY-XXX-实体名称）、`description`（实体简要描述与详细描述）
         2. **## 实体: [ENTITY-XXX-实体名称]**：实体的详细描述（业务职责、主要功能、设计意图、在系统中的作用）
         3. **## 实体结构**：PlantUML 类图代码块（` ```plantuml ... ``` `），类中属性格式为 `+ 类型::属性名`，方法格式为 `+ 文件名::函数名()()`，并用 `note right of 实体名称::成员名` 补充说明
         4. **## 属性说明**：每个属性一个 `### 属性名`，下列 `- **类型**`、`- **用途**`、`- **取值范围**`（可选）、`- **约束条件**`（可选）
         5. **## 方法说明**：每个方法一个 `### 方法名`，下列 `- **函数签名**`、`- **功能描述**`、`- **输入参数**`、`- **返回值**`、`- **调用场景**`
         6. **## 职责说明**：实体的核心职责、主要处理逻辑、与其他实体的交互、在系统中的定位
       - 禁止使用与模板无关的章节（如「实体概览」「核心执行实体」「执行实体特征分析」等汇总式标题），仅允许模板中规定的标题与层级
   - 🔴 **并发处理**：使用线程池并发处理多个文件（默认最大并发数：20）
   - 🔴 **输出文件**：
     - 实体文档：`{output_dir}/ENTITIES-{原接口文件名}.md`
     - 每个文件包含从对应接口文件中提取的实体列表

4.7. **生成批次结果索引**
   - 🔴 **强制要求**：必须生成轻量级索引文件，不合并大文件
   - 更新批次索引文件，记录批次处理结果：
     - 批次状态：`completed` 或 `failed`
     - 实体文件列表：`entity-extraction/ENTITIES-{原接口文件名}.md`
     - 溯源文件列表：`entity-extraction/lineage/{原接口文件名}.json`
     - 实体数量统计
     - 处理时间戳
   - 🔴 **索引文件格式**：
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

4.8. **记录溯源信息**
   - 🔴 **强制要求**：必须记录实体与接口的对应关系
   - 对每个处理的接口聚合文件，生成溯源元数据文件：
     - 文件路径：`{output_dir}/lineage/{原接口文件名}.json`
     - 文件格式：
       ```json
       {
         "source_file": "interface-aggregation/API-001.md",
         "entities": [
           {
             "entity_id": "user_manager",
             "entity_name_cn": "用户管理器",
             "source_interfaces": ["API-001", "API-002"]
           }
         ],
         "extraction_timestamp": "2024-01-01T00:00:00Z"
       }
       ```
   - 🔴 **溯源映射要求**：
     - 记录每个实体来源于哪些接口（接口ID列表）
     - 记录实体与接口文件的对应关系
     - 后续用于建立实体与接口、功能之间的关系

4.9. **检查是否还有未处理的批次**
   - 🔴 **强制要求**：必须调用进度跟踪脚本获取当前处理进度
   - 读取批次索引文件，统计各状态批次数量（pending, processing, completed, failed）
   - 🔴 **强制用户确认机制**：当剩余批次数 > 3时，必须询问用户是否继续处理
   - 🔴 向用户报告当前进度："已完成 {completed_batches}/{total_batches} 个批次的处理，进度 {progress_percentage}%，剩余 {pending_batches} 个批次待处理"
   - 🔴 **处理不同执行场景**：
     - **首次执行场景**：处理所有待处理批次
     - **断点执行场景**：从上次中断处继续处理所有待处理批次

4.10. **继续处理剩余的文件**
   - 🔴 如果还有待处理批次：继续循环处理
     - 清理上一批次无关的上下文信息，为了保证token不超限，必须清理无用的上下文数据
     - 显示剩余批次数和预估处理时间
     - 🔴 向用户报告当前进度："已完成 {completed_batches}/{total_batches} 个批次的处理，进度 {progress_percentage}%，剩余 {pending_batches} 个批次待处理，预计还需要 {estimated_remaining_time}"
     - 🔴 **强制用户确认机制**：当剩余批次数 > 3时，必须询问用户是否继续处理
       - 询问用户："检测到还有 {remaining_batches} 个批次未处理，预计需要 {estimated_time} 完成，是否继续处理？[Y/n]"
       - 如果用户回复 "n" 或 "no"：记录用户选择并暂停处理，等待进一步指令
       - 如果用户回复 "y"、"yes" 或回车：继续处理下一批次
       - 如果用户未回复：继续等待用户确认，不得自动继续
   - 🔴 **严禁跳过**：严禁在任何情况下跳过未处理的批次
   - 🔴 **必须实际处理**：必须实际处理每个批次的数据，不能批量创建空批次文件或跳过任何批次
   - 🔴 如果所有批次已完成：跳出循环
     - 更新整体状态为 "completed"
     - 🔴 **强制要求**：必须调用进度跟踪脚本获取最终处理进度
     - 🔴 最终进度报告："实体抽取已完成！总共处理了 {total_files} 个接口聚合文件，提取了 {total_entities} 个实体，完成率 100%"
     - 生成统计信息文件：`{output_dir}/extraction_stats.json`
       ```json
       {
         "version": "1.0",
         "total_files": 150,
         "total_entities": 45,
         "by_type": {
           "业务服务": 20,
           "数据模型": 15,
           "工具类": 10
         },
         "by_domain": {
           "用户管理": 15,
           "订单管理": 12,
           "支付管理": 8
         },
         "extraction_timestamp": "2024-01-01T00:00:00Z"
       }
       ```

### 5. [ ] 展示结果并向用户确认
- 获取仓库根目录
- 🔴 强制验证输出目录：检查实体文档是否已生成到 `{REPO_ROOT}/.cache/reverse/entities/entity-extraction/`
- 🔴 强制验证缓存状态：AI Agent直接读取状态文件，验证 `entity_extraction.confirmed == false`
- 读取批次结果索引文件：`entities-index.json`
- 总结并展示：
  - 处理的接口聚合文件总数
  - 提取的实体总数
  - 按类型分组的统计信息
  - 按领域分组的统计信息
  - 代表性实体示例（展示2-3个实体的基本信息）
  - 批次处理统计信息
- 询问用户："实体抽取已完成，是否确认结果？[Y/n]"
- 🔴 状态双重检查：用户响应后AI Agent再次读取状态文件，验证更新成功

### 6. [ ] 处理用户确认，更新缓存状态
#### 用户确认（Y/yes/回车或非交互模式）
- 读取状态文件 `{REPO_ROOT}/.cache/reverse/entities/.cache-status.json`
- 更新 `entity_extraction` 部分，设置 `confirmed: true` 和当前时间戳
- 使用 `write` 工具保存更新后的状态文件
- 明确说明阶段1已完成，清空上下文
- 自动进入下一阶段（阶段2：实体融合和去重）

#### 用户拒绝（n/no）
- 允许查看详情或重新生成
- 保持 `confirmed: false` 状态，等待用户进一步指令

## AI Agent上下文管理要求
- **阶段开始时主动清空上下文**：请先执行上下文清理，然后明确说明"开始阶段1：从接口抽取实体。已清空上一阶段的上下文"
- **批次处理后清理上下文**：每个批次处理完成后，清理当前批次的所有处理数据和分析结果，明确声明："已完成批次 {batch_id} 的处理。已清空当前批次的上下文"

## 🔴 实体抽取要求
请参考 [核心规则文档](../core-rules.md) 中的分批处理规则和Token管理规则。

## 输入
- **接口聚合文件目录**（必需）：
  - 位置：`{REPO_ROOT}/.cache/reverse/interfaces/interface-aggregation/` 或类似路径
  - 格式：Markdown文件，包含接口的详细信息
- **实体文档模板**（必需，用于约束输出格式）：
  - 位置：`{REPO_ROOT}/.infra/metamodel/6.entity-template.md`
  - 格式：Markdown模板，规定每个实体的 frontmatter、## 实体、## 实体结构、## 属性说明、## 方法说明、## 职责说明；抽取生成的 ENTITIES-*.md 中每个实体块必须与该模板结构一致
- **用户术语文件**（可选）：
  - 位置：`{REPO_ROOT}/.cache/user_input/user_terminology.md`
  - 格式：Markdown文件，包含用户定义的规范术语

## 输出
- **实体文档目录**：
  - 位置：`{REPO_ROOT}/.cache/reverse/entities/entity-extraction/`
  - 文件格式：`ENTITIES-{原接口文件名}.md`
  - 每个文件包含从对应接口文件中提取的实体列表；🔴 **每个实体的书写必须严格遵循** `{REPO_ROOT}/.infra/metamodel/6.entity-template.md` **的章节与结构**（frontmatter、## 实体、## 实体结构、## 属性说明、## 方法说明、## 职责说明），不得使用模板外的章节标题或汇总式报告结构
- **批次结果索引**：
  - 位置：`{REPO_ROOT}/.cache/reverse/entities/entity-extraction/entities-index.json`
  - 格式：JSON文件，包含批次信息和实体文件列表
- **溯源元数据**：
  - 位置：`{REPO_ROOT}/.cache/reverse/entities/entity-extraction/lineage/*.json`
  - 格式：JSON文件，记录实体与接口的映射关系
- **统计信息**：
  - 位置：`{REPO_ROOT}/.cache/reverse/entities/entity-extraction/extraction_stats.json`
  - 格式：JSON文件，包含实体统计信息

## 注意事项
- AI Agent必须在阶段1完成后暂停，等待用户确认后才能进入下一阶段
- 实体抽取是流程的第一步，必须确认后才算完成
- 用户确认后，AI Agent应该自动进入阶段2（实体融合和去重）
- **批次处理用户确认**：当批次数量较多时，AI Agent必须在处理过程中适时询问用户是否继续，不得擅自跳过未处理的批次
- 跨平台支持：所有脚本调用必须同时支持Linux(bash)和Windows(PowerShell)
- **🔴 脚本使用违规严重警告**：
  - 严禁手动修改批次索引文件跳过处理步骤
  - 严禁批量创建空实体文件模拟处理完成
  - 严禁跳过用户确认机制自动处理所有剩余批次
  - 违规行为将导致处理状态不一致，影响断点续执行功能

