# 实体融合和去重

<!-- 阶段2：实体融合和去重 -->

## 职责
基于阶段1的输出（实体抽取结果），融合重复或相似的实体，通过规则去重、多轮融合迭代和实体价值评估，生成最终的实体列表。

## 执行流程
### 0. [ ] 创建阶段2的子任务的Todo列表
为确保阶段执行过程的透明化和可追踪性，需要创建阶段2的子任务的Todo列表：

步骤1. **步骤1 清理上一阶段的上下文，保证本阶段的上下文干净**
步骤2. **步骤2 获取仓库根目录和缓存路径**
步骤3. **步骤3 检查缓存状态和依赖验证**
步骤4. **步骤4 读取实体文档并执行融合处理**
步骤5. **步骤5 展示结果并向用户确认**
步骤6. **步骤6 处理用户确认，更新缓存状态**

### 1. [x] 清理上一阶段的上下文，保证本阶段的上下文干净
- **阶段开始时主动清空上下文**：执行上下文清理，明确说明"开始阶段2：实体融合和去重。已清空上一阶段的上下文"
- **执行必要的上下文压缩**：判断当前会话的上下文使用率，这个阶段会很耗token，需要先把当前会话的上下文进行压缩，再执行后续流程

### 2. [ ] 获取仓库根目录和缓存路径
- 跨平台脚本调用获取 REPO_ROOT：
  - AI Agent直接调用check-prerequisites.sh脚本
  - AI Agent直接调用check-prerequisites.ps1脚本
- 定义缓存目录：`{REPO_ROOT}/.cache/reverse/entities/`
- 定义实体抽取输出目录：`{REPO_ROOT}/.cache/reverse/entities/entity-extraction/`
- 定义实体融合输出目录：`{REPO_ROOT}/.cache/reverse/entities/entity-consolidation/`

### 3. [ ] 检查缓存状态和依赖验证
- AI Agent直接读取状态文件 `{REPO_ROOT}/.cache/reverse/entities/.cache-status.json`
- 检查 `entity_consolidation.confirmed` 字段
- 如果 `confirmed == true`：跳过阶段2，使用缓存结果
- 如果 `confirmed == false` 或不存在：执行阶段2

**依赖验证**：
- 🔴 **强制要求**：必须验证阶段1（实体抽取）已完成
- 检查实体抽取的缓存状态文件：`{REPO_ROOT}/.cache/reverse/entities/.cache-status.json`
- 验证 `entity_extraction.confirmed` 字段为 `true`
- 如果阶段1未完成，给出明确的错误提示，要求用户先完成阶段1
- 验证实体抽取输出目录存在：`{REPO_ROOT}/.cache/reverse/entities/entity-extraction/`
- 验证批次结果索引文件存在：`{REPO_ROOT}/.cache/reverse/entities/entity-extraction/entities-index.json`
- 如果文件不存在，给出明确的错误提示

### 4. [ ] 读取实体文档并执行融合处理
为确保阶段执行过程的透明化和可追踪性，创建步骤4的子任务的Todo列表：

4.1. [ ] **4.1 读取批次结果索引文件**
4.2. [ ] **4.2 收集所有实体文档**
4.3. [ ] **4.3 步骤0：规则去重（基于entity_id）**
4.4. [ ] **4.4 步骤1-N：多轮融合迭代**
4.5. [ ] **4.5 步骤4：实体价值评估**
4.6. [ ] **4.6 生成融合结果**

#### 融合处理执行流程概览
融合处理模式下，主Agent将按照以下流程执行：
1. **读取批次结果索引**：从阶段1的输出读取批次结果索引文件
2. **收集所有实体**：按需读取批次结果文件，收集所有实体
3. **规则去重**：基于entity_id快速去重
4. **多轮融合迭代**：执行最多3轮融合（基本信息融合、类图整合、收敛检查）
5. **实体价值评估**：过滤低价值实体
6. **生成融合结果**：生成融合后的实体列表和更新的溯源映射

#### 🔴 融合处理执行流程

**🔴 融合处理步骤**：

4.1. **读取批次结果索引文件**
   - 🔴 **强制要求**：必须读取阶段1生成的批次结果索引文件
   - 读取文件：`{REPO_ROOT}/.cache/reverse/entities/entity-extraction/entities-index.json`
   - 解析批次信息，获取所有实体文件列表
   - 🔴 验证文件存在：如果文件不存在，给出明确的错误提示

4.2. **收集所有实体文档**
   - 🔴 **强制要求**：必须从批次结果索引中收集所有实体文档
   - 遍历批次结果索引文件中的所有批次
   - 对于每个批次，读取对应的实体文档：
     - 实体文档路径：`{REPO_ROOT}/.cache/reverse/entities/entity-extraction/ENTITIES-{原接口文件名}.md`
   - 解析每个实体文档，提取实体信息
   - 收集所有溯源元数据文件：
     - 溯源文件路径：`{REPO_ROOT}/.cache/reverse/entities/entity-extraction/lineage/{原接口文件名}.json`
   - 🔴 **统计信息**：统计收集到的实体总数、实体文件总数、溯源文件总数
   - 🔴 明确声明："已收集 {total_entities} 个实体，来自 {total_files} 个实体文档文件"

4.3. **步骤0：规则去重（基于entity_id）**
   - 🔴 **强制要求**：必须执行规则去重，快速去除完全相同的实体
   - 调用实体融合脚本执行规则去重：
     - Linux/macOS: `python3 {REPO_ROOT}/specify/scripts/python/reverse_entities/entity_consolidator.py --repo-root {REPO_ROOT} --input-dir {entity_extraction_dir} --output-dir {entity_consolidation_dir} --step rule-dedup`
     - Windows: `python {REPO_ROOT}\specify\scripts\python\reverse_entities\entity_consolidator.py --repo-root {REPO_ROOT} --input-dir {entity_extraction_dir} --output-dir {entity_consolidation_dir} --step rule-dedup`
   - 脚本参数说明：
     - `--repo-root`：仓库根目录
     - `--input-dir`：实体抽取输出目录
     - `--output-dir`：实体融合输出目录
     - `--step`：执行步骤（rule-dedup表示只执行规则去重）
   - 🔴 **规则去重逻辑**：
     - 将所有实体按 `entity_id`（转小写）分组
     - 相同ID的实体合并关联文件列表
     - 保留第一个出现的实体，合并其他实体的文件信息
   - 🔴 **输出结果**：
     - 去重后的实体列表保存到临时文件
     - 统计去重率：`(原始数量 - 去重后数量) / 原始数量 * 100%`
     - 🔴 明确声明："规则去重完成：{原始数量} -> {去重后数量} 个实体 (去重率: {去重率}%)"

4.4. **步骤1-N：多轮融合迭代（默认最多3轮）**
   - 🔴 **强制要求**：必须执行多轮融合迭代，直到收敛或达到最大轮数
   - 每轮迭代包含两个子步骤：
     - **子步骤1：基本信息融合**
     - **子步骤2：类图整合**
   - 每轮迭代后执行收敛检查

   #### 子步骤1：基本信息融合
   - 🔴 **强制要求**：必须调用AI模型进行基本信息融合判断
   - 调用实体融合脚本执行基本信息融合：
     - Linux/macOS: `python3 {REPO_ROOT}/specify/scripts/python/reverse_entities/entity_consolidator.py --repo-root {REPO_ROOT} --input-dir {entity_extraction_dir} --output-dir {entity_consolidation_dir} --step basic-merge --round {round_num}`
     - Windows: `python {REPO_ROOT}\specify\scripts\python\reverse_entities\entity_consolidator.py --repo-root {REPO_ROOT} --input-dir {entity_extraction_dir} --output-dir {entity_consolidation_dir} --step basic-merge --round {round_num}`
   - 🔴 **批次处理**：
     - 将实体分批（每批40个），并发处理（最大并发20）
     - 参考核心规则文档中的批次处理规则
   - 🔴 **AI分析**：
     - 使用提示词模板：`reverse/tools/prompts/entity_consolidation_basic.md`
     - 对每批实体调用AI模型，判断哪些实体应该合并
   - 🔴 **融合判断标准**：
     - **必须合并**：实体标识高度相似、核心职责实质相同、强关联特征组合
     - **可以合并**：职责有包含关系、同一组件的不同方面
     - **不应合并**：职责明显不同、层次不同、独立组件
   - 🔴 **输出结果**：
     - `merged_groups`：需要合并的实体组（每个组包含多个实体ID）
     - `standalone_entities`：保持独立的实体
     - 保存到临时文件，供子步骤2使用

   #### 子步骤2：类图整合
   - 🔴 **强制要求**：必须为合并后的实体组整合类图
   - 调用实体融合脚本执行类图整合：
     - Linux/macOS: `python3 {REPO_ROOT}/specify/scripts/python/reverse_entities/entity_consolidator.py --repo-root {REPO_ROOT} --input-dir {entity_extraction_dir} --output-dir {entity_consolidation_dir} --step class-diagram-merge --round {round_num}`
     - Windows: `python {REPO_ROOT}\specify\scripts\python\reverse_entities\entity_consolidator.py --repo-root {REPO_ROOT} --input-dir {entity_extraction_dir} --output-dir {entity_consolidation_dir} --step class-diagram-merge --round {round_num}`
   - 🔴 **处理逻辑**：
     - 收集合并组中所有源实体的类图
     - 如果只有一个类图，直接使用
     - 如果有多个类图，调用AI模型整合（使用提示词模板 `reverse/tools/prompts/entity_class_diagram_merge.md`）
   - 🔴 **并发处理**：
     - 仅处理合并组，并发处理（最大并发20）
     - 独立实体保持原有类图不变
   - 🔴 **输出结果**：
     - 整合后的类图（Mermaid格式）
     - 合并后的实体列表（包含整合后的类图）

   #### 收敛检查
   - 🔴 **强制要求**：每轮迭代后必须执行收敛检查
   - 比较本轮融合后的实体数量与上一轮的实体数量
   - 如果实体数量没有减少（`len(final_entities) == len(current_entities)`）：
     - 🔴 明确声明："✓ 已收敛，停止迭代"
     - 停止迭代，进入步骤4.5
   - 如果实体数量减少，继续下一轮迭代
   - 🔴 **统计信息**：
     - 记录每轮的融合率：`(1 - 本轮数量 / 上轮数量) * 100%`
     - 记录每轮的处理耗时
     - 🔴 明确声明："第{round_num}轮完成: {上轮数量} -> {本轮数量} 个实体，融合率: {融合率}%，耗时: {耗时}秒"

4.5. **步骤4：实体价值评估**
   - 🔴 **强制要求**：必须执行实体价值评估，过滤低价值实体
   - 调用实体融合脚本执行价值评估：
     - Linux/macOS: `python3 {REPO_ROOT}/specify/scripts/python/reverse_entities/entity_consolidator.py --repo-root {REPO_ROOT} --input-dir {entity_extraction_dir} --output-dir {entity_consolidation_dir} --step value-evaluation`
     - Windows: `python {REPO_ROOT}\specify\scripts\python\reverse_entities\entity_consolidator.py --repo-root {REPO_ROOT} --input-dir {entity_extraction_dir} --output-dir {entity_consolidation_dir} --step value-evaluation`
   - 🔴 **批次处理**：
     - 分批评估（每批30个），并发处理（最大并发20）
     - 参考核心规则文档中的批次处理规则
   - 🔴 **AI分析**：
     - 使用提示词模板：`reverse/tools/prompts/entity_value_evaluation.md`
     - 对每批实体调用AI模型评估实体价值
   - 🔴 **评估标准**：
     - 实体是否有明确的业务价值
     - 实体是否被接口使用
     - 实体是否有核心规则/状态/依赖交互
   - 🔴 **输出结果**：
     - 保留有价值的实体列表
     - 为每个实体记录价值评分（value_score）
     - 统计过滤掉的低价值实体数量
     - 🔴 明确声明："实体价值评估完成：{评估前数量} -> {评估后数量} 个实体，过滤了 {过滤数量} 个低价值实体"

4.6. **生成融合结果**
   - 🔴 **强制要求**：必须生成融合后的实体列表和更新的溯源映射
   - 调用实体融合脚本生成最终结果：
     - Linux/macOS: `python3 {REPO_ROOT}/specify/scripts/python/reverse_entities/entity_consolidator.py --repo-root {REPO_ROOT} --input-dir {entity_extraction_dir} --output-dir {entity_consolidation_dir} --step generate-result`
     - Windows: `python {REPO_ROOT}\specify\scripts\python\reverse_entities\entity_consolidator.py --repo-root {REPO_ROOT} --input-dir {entity_extraction_dir} --output-dir {entity_consolidation_dir} --step generate-result`
   - 🔴 **生成文件**：
     - **融合后的实体列表**：
       - 文件路径：`{REPO_ROOT}/.cache/reverse/entities/entity-consolidation/consolidated-entities.json`
       - 格式：JSON文件，包含所有融合后的实体信息
       - 包含字段：entity_id, entity_name_cn, entity_type, domain, related_files, responsibility, class_diagram, source_interfaces, merged_from, value_score
     - **更新的溯源映射**：
       - 文件路径：`{REPO_ROOT}/.cache/reverse/entities/entity-consolidation/entities_lineage.json`
       - 格式：JSON文件，记录实体与接口的对应关系
       - 包含字段：entity_id, entity_name_cn, source_interfaces, source_files, extraction_timestamp
     - **融合统计信息**：
       - 文件路径：`{REPO_ROOT}/.cache/reverse/entities/entity-consolidation/consolidation_stats.json`
       - 格式：JSON文件，包含融合过程的统计信息
       - 包含字段：原始数量、规则去重后数量、融合后数量、价值评估后数量、最终数量、按类型统计、按领域统计、融合轮数、总耗时
   - 🔴 **验证生成结果**：
     - 验证所有文件已正确生成
     - 验证文件格式正确
     - 统计最终实体数量
     - 🔴 明确声明："融合结果已生成：最终保留 {最终数量} 个实体"

### 5. [ ] 展示结果并向用户确认
- 获取仓库根目录
- 🔴 强制验证输出目录：检查融合结果是否已生成到 `{REPO_ROOT}/.cache/reverse/entities/entity-consolidation/`
- 🔴 强制验证缓存状态：AI Agent直接读取状态文件，验证 `entity_consolidation.confirmed == false`
- 读取融合后的实体列表文件：`consolidated-entities.json`
- 读取融合统计信息文件：`consolidation_stats.json`
- 总结并展示：
  - 原始实体总数
  - 规则去重后的实体数量
  - 融合后的实体数量
  - 价值评估后的最终实体数量
  - 按类型分组的统计信息
  - 按领域分组的统计信息
  - 融合轮数和总耗时
  - 代表性实体示例（展示2-3个融合后的实体基本信息）
- 询问用户："实体融合和去重已完成，是否确认结果？[Y/n]"
- 🔴 状态双重检查：用户响应后AI Agent再次读取状态文件，验证更新成功

### 6. [ ] 处理用户确认，更新缓存状态
#### 用户确认（Y/yes/回车或非交互模式）
- 读取状态文件 `{REPO_ROOT}/.cache/reverse/entities/.cache-status.json`
- 更新 `entity_consolidation` 部分，设置 `confirmed: true` 和当前时间戳
- 使用 `write` 工具保存更新后的状态文件
- 明确说明阶段2已完成，清空上下文
- 自动进入下一阶段（阶段3：实体文档生成）

#### 用户拒绝（n/no）
- 允许查看详情或重新生成
- 保持 `confirmed: false` 状态，等待用户进一步指令

## AI Agent上下文管理要求
- **阶段开始时主动清空上下文**：请先执行上下文清理，然后明确说明"开始阶段2：实体融合和去重。已清空上一阶段的上下文"
- **融合处理后清理上下文**：融合处理完成后，清理当前处理的所有数据和分析结果，明确声明："已完成实体融合处理。已清空当前处理的上下文"

## 🔴 实体融合要求
请参考 [核心规则文档](../core-rules.md) 中的分批处理规则和Token管理规则。

## 输入
- **实体文档目录**（必需）：
  - 位置：`{REPO_ROOT}/.cache/reverse/entities/entity-extraction/`
  - 格式：Markdown文件，包含从接口文件中提取的实体列表
  - 文件格式：`ENTITIES-{原接口文件名}.md`
- **批次结果索引**（必需）：
  - 位置：`{REPO_ROOT}/.cache/reverse/entities/entity-extraction/entities-index.json`
  - 格式：JSON文件，包含批次信息和实体文件列表
- **溯源映射文件**（必需）：
  - 位置：`{REPO_ROOT}/.cache/reverse/entities/entity-extraction/lineage/*.json`
  - 格式：JSON文件，记录实体与接口的映射关系

## 输出
- **融合后的实体列表**：
  - 位置：`{REPO_ROOT}/.cache/reverse/entities/entity-consolidation/consolidated-entities.json`
  - 格式：JSON文件，包含所有融合后的实体信息
- **更新的溯源映射**：
  - 位置：`{REPO_ROOT}/.cache/reverse/entities/entity-consolidation/entities_lineage.json`
  - 格式：JSON文件，记录实体与接口的对应关系（已更新融合信息）
- **融合统计信息**：
  - 位置：`{REPO_ROOT}/.cache/reverse/entities/entity-consolidation/consolidation_stats.json`
  - 格式：JSON文件，包含融合过程的统计信息

## 注意事项
- AI Agent必须在阶段2完成后暂停，等待用户确认后才能进入下一阶段
- 实体融合是流程的关键步骤，必须确认后才算完成
- 用户确认后，AI Agent应该自动进入阶段3（实体文档生成）
- **批次处理用户确认**：当实体数量较多时，AI Agent必须在处理过程中适时询问用户是否继续，不得擅自跳过未处理的批次
- 跨平台支持：所有脚本调用必须同时支持Linux(bash)和Windows(PowerShell)
- **🔴 脚本使用违规严重警告**：
  - 严禁手动修改融合结果文件跳过处理步骤
  - 严禁批量创建空融合文件模拟处理完成
  - 严禁跳过用户确认机制自动处理所有剩余步骤
  - 违规行为将导致处理状态不一致，影响断点续执行功能

