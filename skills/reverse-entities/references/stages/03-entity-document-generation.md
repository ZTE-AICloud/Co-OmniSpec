# 实体文档生成

<!-- 阶段3：实体文档生成 -->

## 职责
基于阶段2的输出（融合后的实体列表），为每个实体生成标准化的实体文档，并生成实体清单文件。

## 执行流程
### 0. [ ] 创建阶段3的子任务的Todo列表
为确保阶段执行过程的透明化和可追踪性，需要创建阶段3的子任务的Todo列表：

步骤1. **步骤1 清理上一阶段的上下文，保证本阶段的上下文干净**
步骤2. **步骤2 获取仓库根目录和缓存路径**
步骤3. **步骤3 检查缓存状态和依赖验证**
步骤4. **步骤4 读取融合后的实体列表并生成文档**
步骤5. **步骤5 展示结果并向用户确认**
步骤6. **步骤6 处理用户确认，更新缓存状态**

### 1. [x] 清理上一阶段的上下文，保证本阶段的上下文干净
- **阶段开始时主动清空上下文**：执行上下文清理，明确说明"开始阶段3：实体文档生成。已清空上一阶段的上下文"
- **执行必要的上下文压缩**：判断当前会话的上下文使用率，这个阶段会生成大量文档，需要先把当前会话的上下文进行压缩，再执行后续流程

### 2. [ ] 获取仓库根目录和缓存路径
- 跨平台脚本调用获取 REPO_ROOT：
  - AI Agent直接调用check-prerequisites.sh脚本
  - AI Agent直接调用check-prerequisites.ps1脚本
- 定义缓存目录：`{REPO_ROOT}/.cache/reverse/entities/`
- 定义实体融合输出目录：`{REPO_ROOT}/.cache/reverse/entities/entity-consolidation/`
- 定义最终输出目录：`{REPO_ROOT}/omni-doc/specs/entities/`
- 定义实体模板路径：`{REPO_ROOT}/.infra/metamodel/6.entity-template.md`

### 3. [ ] 检查缓存状态和依赖验证
- AI Agent直接读取状态文件 `{REPO_ROOT}/.cache/reverse/entities/.cache-status.json`
- 检查 `entity_document_generation.confirmed` 字段
- 如果 `confirmed == true`：跳过阶段3，使用缓存结果
- 如果 `confirmed == false` 或不存在：执行阶段3

**依赖验证**：
- 🔴 **强制要求**：必须验证阶段2（实体融合）已完成
- 检查实体融合的缓存状态文件：`{REPO_ROOT}/.cache/reverse/entities/.cache-status.json`
- 验证 `entity_consolidation.confirmed` 字段为 `true`
- 如果阶段2未完成，给出明确的错误提示，要求用户先完成阶段2
- 验证融合后的实体列表文件存在：`{REPO_ROOT}/.cache/reverse/entities/entity-consolidation/consolidated-entities.json`
- 如果文件不存在，给出明确的错误提示

### 4. [ ] 读取融合后的实体列表并生成文档
为确保阶段执行过程的透明化和可追踪性，创建步骤4的子任务的Todo列表：

4.1. [ ] **4.1 读取融合后的实体列表**
4.2. [ ] **4.2 加载实体模板**
4.3. [ ] **4.3 生成实体文档（基于模板填充）**
4.4. [ ] **4.4 生成实体清单**

#### 文档生成执行流程概览
文档生成模式下，主Agent将按照以下流程执行：
1. **读取融合后的实体列表**：从阶段2的输出读取融合后的实体列表JSON文件
2. **加载实体模板**：读取实体文档模板文件
3. **生成实体文档**：为每个实体生成独立的MD文件，基于模板填充实体信息
4. **生成实体清单**：生成包含统计信息和实体列表表格的清单文件

#### 🔴 文档生成执行流程

**🔴 文档生成步骤**：

4.1. **读取融合后的实体列表**
   - 🔴 **强制要求**：必须读取阶段2生成的融合后的实体列表文件
   - 读取文件：`{REPO_ROOT}/.cache/reverse/entities/entity-consolidation/consolidated-entities.json`
   - 解析JSON文件，获取所有实体信息
   - 🔴 **验证文件存在**：如果文件不存在，给出明确的错误提示
   - 🔴 **验证数据格式**：验证JSON格式正确，包含必要的字段（entity_id, entity_name_cn等）
   - 🔴 **统计信息**：统计实体总数
   - 🔴 明确声明："已读取 {total_entities} 个融合后的实体"

4.2. **加载实体模板**
   - 🔴 **强制要求**：必须加载实体文档模板
   - 强制使用默认模板：`{REPO_ROOT}/.infra/metamodel/6.entity-template.md`
   - 读取模板文件内容
   - 🔴 **验证模板存在**：如果模板文件不存在，给出明确的错误提示
   - 🔴 **验证模板格式**：验证模板包含以下必备结构（与模板文件完全一致）：YAML frontmatter（id、name、description）、## 实体、## 实体结构（PlantUML 代码块）、## 属性说明（### 属性名 + 类型/用途/取值范围/约束条件）、## 方法说明（### 方法名 + 函数签名/功能描述/输入参数/返回值/调用场景）、## 职责说明
   - 🔴 **生成约束**：后续生成的每个实体文档必须与上述模板的章节标题、层级、顺序一致，不得增删章节或改用其他标题。🔴 **文档中仅允许出现模板**：**## 实体**、**## 实体结构**、**## 属性说明**、**## 方法说明**、**## 职责说明**
   - 🔴 明确声明："已加载实体文档模板：{模板路径}"

4.3. **生成实体文档（基于模板填充）**
   - 🔴 **强制要求**：必须为每个实体生成独立的MD文件
   - 调用实体文档生成脚本：
     - Linux/macOS: `python3 {REPO_ROOT}/.infra/scripts/python/reverse_entities/entity_list_generator.py --repo-root {REPO_ROOT} --input-file {consolidated_entities_file} --template-file {template_file} --output-dir {output_dir} --mode generate-documents`
     - Windows: `python {REPO_ROOT}\.infra\scripts\python\reverse_entities\entity_list_generator.py --repo-root {REPO_ROOT} --input-file {consolidated_entities_file} --template-file {template_file} --output-dir {output_dir} --mode generate-documents`
   - 脚本参数说明：
     - `--repo-root`：仓库根目录
     - `--input-file`：融合后的实体列表JSON文件路径
     - `--template-file`：实体文档模板文件路径
    - `--output-dir`：最终输出目录（`{REPO_ROOT}/omni-doc/specs/entities/`）
     - `--mode`：执行模式（generate-documents表示生成实体文档）
   - 🔴 **文档生成逻辑**：
     - 为每个实体生成独立的MD文件，🔴 **输出内容必须与** `{REPO_ROOT}/.infra/metamodel/6.entity-template.md` **的格式完全一致**（章节标题、层级、顺序、frontmatter 键名均不得更改）
     - 文件命名：`ENTITY-{序号:03d}-{业务名称}.md`
       - 序号从001开始，按实体在列表中的顺序递增
       - 业务名称使用实体的 `entity_name_cn` 字段，去除特殊字符，只保留中文、英文、数字和连字符
     - 基于模板逐节填充，禁止出现模板中不存在的章节或标题；禁止使用「基本属性」「实体基本信息」「业务属性」「关键特性」「关系属性」「使用场景」「技术实现」「风险与注意事项」等，仅允许「## 实体」「## 实体结构」「## 属性说明」「## 方法说明」「## 职责说明」：
       - **Frontmatter部分**（与模板一致）：
         - `id`: `ENTITY-{序号:03d}`（与文件名中的序号保持一致）
         - `name`: `ENTITY-{序号:03d}-{业务名称}`（与文件名保持一致）
         - `description`: 实体的简要描述（从 `responsibility` 字段提取或生成）
       - **## 实体: [ENTITY-XXX-实体名称]**：
         - 使用实体的 `responsibility` 字段作为详细描述
         - 如果 `responsibility` 为空，使用 `entity_name_cn` 和 `entity_type` 生成描述
       - **## 实体结构**：
         - 使用 PlantUML 代码块（` ```plantuml ... ``` `）；若实体数据为 Mermaid，须转换为 PlantUML；属性格式 `+ 类型::属性名`，方法格式 `+ 文件名::函数名()()`，并用 `note right of 实体名称::成员名` 补充说明
         - 若 `class_diagram` 为空，生成占位符说明但保留本节与代码块结构
       - **## 属性说明**：
         - 每个属性使用 `### 属性名`，下列 `- **类型**`、`- **用途**`、`- **取值范围**`（可选）、`- **约束条件**`（可选）；从类图提取或写占位说明
       - **## 方法说明**：
         - 每个方法使用 `### 方法名`，下列 `- **函数签名**`、`- **功能描述**`、`- **输入参数**`、`- **返回值**`、`- **调用场景**`；从类图提取或写占位说明
       - **## 职责说明**：
         - 使用实体的 `responsibility` 字段，补充业务职责、主要功能、设计意图、与其他实体的交互及在系统中的定位
   - 🔴 **输出文件**：
    - 实体文档：`{REPO_ROOT}/omni-doc/specs/entities/ENTITY-{序号:03d}-{业务名称}.md`
     - 每个文件包含一个逻辑实体的完整信息
   - 🔴 **验证生成结果**：
     - 验证所有实体文档已生成
     - 🔴 **验证与模板一致**：抽检生成的文档是否包含且仅包含模板规定的章节（frontmatter、## 实体、## 实体结构、## 属性说明、## 方法说明、## 职责说明），无多余或缺失章节；若出现「基本属性」「实体基本信息」「业务属性」「关键特性」「关系属性」「使用场景」「技术实现」「风险与注意事项」等非模板章节，视为不符合要求
     - 🔴 **自动修复不合规文档**：如果发现某个 `ENTITY-*.md` 文档不满足上述模板结构（例如没有 YAML frontmatter、缺少 `## 实体结构`、包含「基本信息」「业务属性」等旧版章节），必须由 AI Agent 读取该文件内容，将其中已有的业务描述、数据结构、示例代码等信息按如下规则重组后覆盖写回同一路径：
       - 将标题行 `# 实体文档：xxx` 和「基本信息」「业务属性」「技术属性」「关系属性」中的文字，合并整理到模板的 `description` 和 `## 实体` / `## 职责说明` 段落中；
       - 将 JSON 或其它结构描述转换为 PlantUML 类图，放入 `## 实体结构` 代码块中；
       - 将“属性类”信息归并到 `## 属性说明` 下的多个 `### 属性名` 小节中；
       - 将“行为/接口/使用示例”归并到 `## 方法说明` 下，提取函数签名和调用场景；
       - 删除旧版的「基本信息」「业务属性」「技术属性」「关系属性」「使用示例」「元数据」等章节标题，确保最终文档只保留模板规定的章节。
     - 统计生成且通过修复后的文档数量
     - 🔴 明确声明："已生成并校验 {generated_count} 个实体文档，全部符合实体模板格式"

4.4. **生成实体清单**
   - 🔴 **强制要求**：必须生成实体清单文件
   - 调用实体清单生成脚本：
     - Linux/macOS: `python3 {REPO_ROOT}/.infra/scripts/python/reverse_entities/entity_list_generator.py --repo-root {REPO_ROOT} --entity-dir {output_dir} --output {output_dir}/实体清单.md --mode generate-list`
     - Windows: `python {REPO_ROOT}\.infra\scripts\python\reverse_entities\entity_list_generator.py --repo-root {REPO_ROOT} --entity-dir {output_dir} --output {output_dir}\实体清单.md --mode generate-list`
   - 脚本参数说明：
     - `--repo-root`：仓库根目录
    - `--entity-dir`：实体文档目录（`{REPO_ROOT}/omni-doc/specs/entities/`）
    - `--output`：输出文件路径（`{REPO_ROOT}/omni-doc/specs/entities/实体清单.md`）
     - `--mode`：执行模式（generate-list表示生成实体清单）
   - 🔴 **清单生成逻辑**：
     - 扫描实体文档目录，读取所有 `ENTITY-*.md` 文件
     - 解析每个实体文档，提取实体信息：
       - 实体标识（entity_id）
       - 业务名称（entity_name_cn）
       - 实体类型（entity_type）
       - 所属领域（domain）
       - 关联文件（related_files）
       - 实体文件路径
     - 生成统计信息：
       - **按实体类型统计**：
         - 统计每种实体类型的数量
         - 生成表格：| 实体类型 | 数量 |
       - **按所属领域统计**：
         - 统计每个领域的实体数量
         - 生成表格：| 所属领域 | 数量 |
     - 生成实体列表表格：
       - 表头：| 序号 | 实体标识 | 业务名称 | 实体类型 | 所属领域 | 关联文件 | 实体文件 |
       - 为每个实体生成一行，包含所有关键信息
       - 实体文件列包含文件链接（Markdown链接格式）
   - 🔴 **输出文件**：
    - 实体清单：`{REPO_ROOT}/omni-doc/specs/entities/实体清单.md`
     - 文件格式：Markdown格式，包含统计信息和实体列表表格
   - 🔴 **验证生成结果**：
     - 验证清单文件已生成
     - 验证文件格式正确（包含统计信息和实体列表表格）
     - 验证统计信息准确（与实体文档数量一致）
     - 🔴 明确声明："已生成实体清单文件，包含 {total_entities} 个实体"

### 5. [ ] 展示结果并向用户确认
- 获取仓库根目录
- 🔴 强制验证输出目录：检查实体文档是否已生成到 `{REPO_ROOT}/omni-doc/specs/entities/`
- 🔴 强制验证缓存状态：AI Agent直接读取状态文件，验证 `entity_document_generation.confirmed == false`
- 读取实体清单文件：`{REPO_ROOT}/omni-doc/specs/entities/实体清单.md`
- 统计生成的实体文档数量
- 总结并展示：
  - 生成的实体文档总数
  - 按类型分组的统计信息
  - 按领域分组的统计信息
  - 代表性实体示例（展示2-3个实体的基本信息，包括实体ID、名称、类型、领域）
  - 实体文档输出目录
  - 实体清单文件路径
- 询问用户："实体文档生成已完成，是否确认结果？[Y/n]"
- 🔴 状态双重检查：用户响应后AI Agent再次读取状态文件，验证更新成功

### 6. [ ] 处理用户确认，更新缓存状态
#### 用户确认（Y/yes/回车或非交互模式）
- 读取状态文件 `{REPO_ROOT}/.cache/reverse/entities/.cache-status.json`
- 更新 `entity_document_generation` 部分，设置 `confirmed: true` 和当前时间戳
- 使用 `write` 工具保存更新后的状态文件
- 明确说明阶段3已完成，清空上下文
- 自动进入下一阶段（阶段4：实体关系建立）

#### 用户拒绝（n/no）
- 允许查看详情或重新生成
- 保持 `confirmed: false` 状态，等待用户进一步指令

## AI Agent上下文管理要求
- **阶段开始时主动清空上下文**：请先执行上下文清理，然后明确说明"开始阶段3：实体文档生成。已清空上一阶段的上下文"
- **文档生成后清理上下文**：文档生成完成后，清理当前处理的所有数据和分析结果，明确声明："已完成实体文档生成。已清空当前处理的上下文"

## 🔴 实体文档生成要求
请参考 [核心规则文档](../core-rules.md) 中的分批处理规则和Token管理规则。

## 输入
- **融合后的实体列表**（必需）：
  - 位置：`{REPO_ROOT}/.cache/reverse/entities/entity-consolidation/consolidated-entities.json`
  - 格式：JSON文件，包含所有融合后的实体信息
- **实体模板**（必需）：
  - 强制使用：`{REPO_ROOT}/.infra/metamodel/6.entity-template.md`
  - 格式：Markdown文件，包含实体文档的模板结构

## 输出
- **最终实体文档目录**：
  - 位置：`{REPO_ROOT}/omni-doc/specs/entities/`
  - 文件格式：`ENTITY-{序号:03d}-{业务名称}.md`
  - 每个文件包含一个逻辑实体的完整信息
- **实体清单**：
  - 位置：`{REPO_ROOT}/omni-doc/specs/entities/实体清单.md`
  - 格式：Markdown文件，包含统计信息和实体列表表格

## 注意事项
- AI Agent必须在阶段3完成后暂停，等待用户确认后才能进入下一阶段
- 实体文档生成是流程的关键步骤，必须确认后才算完成
- 用户确认后，AI Agent应该自动进入阶段4（实体关系建立）
- **文档生成要求**：
  - 🔴 **输出路径**：实体文档必须生成到 `{REPO_ROOT}/omni-doc/entities/`，不得使用 `output/entities/`
  - 🔴 实体文档必须严格按 `{REPO_ROOT}/.infra/metamodel/6.entity-template.md` 生成：仅包含「## 实体」「## 实体结构」「## 属性说明」「## 方法说明」「## 职责说明」五节及 frontmatter；禁止使用「基本属性」「实体基本信息」「业务属性」「关键特性」「关系属性」「使用场景」「技术实现」「风险与注意事项」等非模板章节
  - 实体序号必须连续，从001开始
  - 实体文件名必须与文档中的id和name字段保持一致（格式 `ENTITY-{序号:03d}-{业务名称}.md`，如 ENTITY-001-Node.md）
  - 类图须以 PlantUML 代码块呈现在「## 实体结构」下；若源数据为 Mermaid，须转换为 PlantUML
- 跨平台支持：所有脚本调用必须同时支持Linux(bash)和Windows(PowerShell)
- **🔴 脚本使用违规严重警告**：
  - 严禁手动修改实体文档跳过生成步骤
  - 严禁批量创建空实体文件模拟处理完成
  - 严禁跳过用户确认机制自动处理所有剩余步骤
  - 违规行为将导致处理状态不一致，影响断点续执行功能

