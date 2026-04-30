# 实体关系建立

<!-- 阶段4：实体关系建立 -->

## 职责
基于阶段3的输出（实体文档）和实体溯源映射，建立实体与接口、功能之间的完整关系网络。

## 执行流程
### 0. [ ] 创建阶段4的子任务的Todo列表
为确保阶段执行过程的透明化和可追踪性，需要创建阶段4的子任务的Todo列表：

步骤1. **步骤1 清理上一阶段的上下文，保证本阶段的上下文干净**
步骤2. **步骤2 获取仓库根目录和缓存路径**
步骤3. **步骤3 检查缓存状态和依赖验证**
步骤4. **步骤4 建立实体关系网络**
步骤5. **步骤5 展示结果并向用户确认**
步骤6. **步骤6 处理用户确认，更新缓存状态**

### 1. [x] 清理上一阶段的上下文，保证本阶段的上下文干净
- **阶段开始时主动清空上下文**：执行上下文清理，明确说明"开始阶段4：实体关系建立。已清空上一阶段的上下文"
- **执行必要的上下文压缩**：判断当前会话的上下文使用率，这个阶段会读取多个关系文件，需要先把当前会话的上下文进行压缩，再执行后续流程

### 2. [ ] 获取仓库根目录和缓存路径
- 跨平台脚本调用获取 REPO_ROOT：
  - AI Agent直接调用check-prerequisites.sh脚本
  - AI Agent直接调用check-prerequisites.ps1脚本
- 定义缓存目录：`{REPO_ROOT}/.cache/reverse/entities/`
- 定义实体融合输出目录：`{REPO_ROOT}/.cache/reverse/entities/entity-consolidation/`
- 定义关系输出目录：`{REPO_ROOT}/omni-doc/specs/entities/relations/`
- 定义接口反构缓存目录：`{REPO_ROOT}/.cache/reverse/interfaces/`
- 定义功能反构缓存目录：`{REPO_ROOT}/.cache/reverse/functions/`（如果存在）

### 3. [ ] 检查缓存状态和依赖验证
- AI Agent直接读取状态文件 `{REPO_ROOT}/.cache/reverse/entities/.cache-status.json`
- 检查 `entity_relationship_building.confirmed` 字段
- 如果 `confirmed == true`：跳过阶段4，使用缓存结果
- 如果 `confirmed == false` 或不存在：执行阶段4

**依赖验证**：
- 🔴 **强制要求**：必须验证阶段3（实体文档生成）已完成
- 检查实体文档生成的缓存状态文件：`{REPO_ROOT}/.cache/reverse/entities/.cache-status.json`
- 验证 `entity_document_generation.confirmed` 字段为 `true`
- 如果阶段3未完成，给出明确的错误提示，要求用户先完成阶段3
- 验证实体溯源映射文件存在：`{REPO_ROOT}/.cache/reverse/entities/entity-consolidation/entities_lineage.json`
- 如果文件不存在，给出明确的错误提示
- 🔴 **可选依赖验证**：检查功能反构是否已完成（如果已完成，可以建立功能→实体关系）
  - 检查功能反构的缓存状态文件：`{REPO_ROOT}/.cache/reverse/functions/.cache-status.json`（如果存在）
  - 如果功能反构已完成，验证功能-接口关系文件存在：`{REPO_ROOT}/omni-doc/specs/entities/relations/function-interface.json`

### 4. [ ] 建立实体关系网络
为确保阶段执行过程的透明化和可追踪性，创建步骤4的子任务的Todo列表：

4.1. [ ] **4.1 读取实体溯源映射**
4.2. [ ] **4.2 建立接口 → 实体关系**
4.3. [ ] **4.3 建立实体 → 接口关系**
4.4. [ ] **4.4 建立功能 → 实体关系（如果功能反构已完成）**

#### 关系建立执行流程概览
关系建立模式下，主Agent将按照以下流程执行：
1. **读取实体溯源映射**：从阶段2的输出读取实体溯源映射文件
2. **建立接口 → 实体关系**：从实体溯源映射构建接口到实体的映射
3. **建立实体 → 接口关系**：直接从实体溯源数据构建反向关系
4. **建立功能 → 实体关系**：通过接口作为中间节点，构建功能到实体的关系（如果功能反构已完成）

#### 🔴 关系建立执行流程

**🔴 关系建立步骤**：

4.1. **读取实体溯源映射**
   - 🔴 **强制要求**：必须读取阶段2生成的实体溯源映射文件
   - 读取文件：`{REPO_ROOT}/.cache/reverse/entities/entity-consolidation/entities_lineage.json`
   - 解析JSON文件，获取实体与接口的对应关系
   - 🔴 **验证文件存在**：如果文件不存在，给出明确的错误提示
   - 🔴 **验证数据格式**：验证JSON格式正确，包含必要的字段（entity_id, source_interfaces等）
   - 🔴 **统计信息**：统计实体总数、接口总数、关系总数
   - 🔴 明确声明："已读取实体溯源映射，包含 {total_entities} 个实体，{total_interfaces} 个接口，{total_relations} 条关系"

4.2. **建立接口 → 实体关系**
   - 🔴 **强制要求**：必须建立接口到实体的关系
   - 调用实体关系构建脚本：
     - Linux/macOS: `python3 {REPO_ROOT}/.infra/scripts/python/reverse_entities/entity_relationship_builder.py --repo-root {REPO_ROOT} --entity-lineage {entity_lineage_file} --interfaces-dir {interfaces_dir} --output {output_dir}/interface-entity.json --relation-type interface-to-entity`
     - Windows: `python {REPO_ROOT}\.infra\scripts\python\reverse_entities\entity_relationship_builder.py --repo-root {REPO_ROOT} --entity-lineage {entity_lineage_file} --interfaces-dir {interfaces_dir} --output {output_dir}\interface-entity.json --relation-type interface-to-entity`
   - 脚本参数说明：
     - `--repo-root`：仓库根目录
     - `--entity-lineage`：实体溯源映射文件路径
     - `--interfaces-dir`：接口文档目录（可选，用于验证接口ID）
     - `--output`：输出文件路径（`{REPO_ROOT}/omni-doc/specs/entities/relations/interface-entity.json`）
     - `--relation-type`：关系类型（interface-to-entity表示接口→实体）
   - 🔴 **关系构建逻辑**：
     - 从实体溯源映射中提取每个实体的 `source_interfaces` 字段
     - 构建接口到实体的映射：`{interface_id: [entity_id1, entity_id2, ...]}`
     - 对于每个接口ID，收集所有关联的实体ID
     - 去重并排序实体ID列表
     - 生成关系列表：`[{source: "API-001", targets: ["ENTITY-001", "ENTITY-002"]}, ...]`
   - 🔴 **输出文件**：
     - 接口 → 实体关系：`{REPO_ROOT}/omni-doc/specs/entities/relations/interface-entity.json`
     - 文件格式：JSON数组，每个元素包含 `source`（接口ID）和 `targets`（实体ID列表）
   - 🔴 **验证生成结果**：
     - 验证关系文件已生成
     - 验证文件格式正确
     - 统计关系数量
     - 🔴 明确声明："已建立接口 → 实体关系，共 {relation_count} 条关系"

4.3. **建立实体 → 接口关系**
   - 🔴 **强制要求**：必须建立实体到接口的反向关系
   - 调用实体关系构建脚本：
     - Linux/macOS: `python3 {REPO_ROOT}/.infra/scripts/python/reverse_entities/entity_relationship_builder.py --repo-root {REPO_ROOT} --entity-lineage {entity_lineage_file} --output {output_dir}/entity-interface.json --relation-type entity-to-interface`
     - Windows: `python {REPO_ROOT}\.infra\scripts\python\reverse_entities\entity_relationship_builder.py --repo-root {REPO_ROOT} --entity-lineage {entity_lineage_file} --output {output_dir}\entity-interface.json --relation-type entity-to-interface`
   - 脚本参数说明：
     - `--repo-root`：仓库根目录
     - `--entity-lineage`：实体溯源映射文件路径
     - `--output`：输出文件路径（`{REPO_ROOT}/omni-doc/specs/entities/relations/entity-interface.json`）
     - `--relation-type`：关系类型（entity-to-interface表示实体→接口）
   - 🔴 **关系构建逻辑**：
     - 直接从实体溯源映射数据构建
     - 对于每个实体，提取其 `source_interfaces` 字段
     - 清理和标准化接口ID（转大写、去空格）
     - 去重并排序接口ID列表
     - 生成关系列表：`[{source: "ENTITY-001", targets: ["API-001", "API-002"]}, ...]`
   - 🔴 **输出文件**：
     - 实体 → 接口关系：`{REPO_ROOT}/omni-doc/specs/entities/relations/entity-interface.json`
     - 文件格式：JSON数组，每个元素包含 `source`（实体ID）和 `targets`（接口ID列表）
   - 🔴 **验证生成结果**：
     - 验证关系文件已生成
     - 验证文件格式正确
     - 统计关系数量
     - 🔴 明确声明："已建立实体 → 接口关系，共 {relation_count} 条关系"

4.4. **建立功能 → 实体关系（如果功能反构已完成）**
   - 🔴 **条件检查**：检查功能反构是否已完成
   - 检查功能反构的缓存状态文件：`{REPO_ROOT}/.cache/reverse/functions/.cache-status.json`（如果存在）
   - 如果功能反构未完成或不存在，跳过此步骤，明确声明："功能反构未完成，跳过功能 → 实体关系建立"
   - 如果功能反构已完成，执行以下步骤：
     - 🔴 **强制要求**：必须读取功能-接口关系和接口-实体关系
     - 验证功能-接口关系文件存在：`{REPO_ROOT}/omni-doc/specs/entities/relations/function-interface.json`
     - 验证接口-实体关系文件存在：`{REPO_ROOT}/omni-doc/specs/entities/relations/interface-entity.json`（步骤4.2的输出）
     - 调用实体关系构建脚本：
       - Linux/macOS: `python3 {REPO_ROOT}/.infra/scripts/python/reverse_entities/entity_relationship_builder.py --repo-root {REPO_ROOT} --function-interface-relations {function_interface_file} --interface-entity-relations {interface_entity_file} --output {output_dir}/function-entity.json --relation-type function-to-entity`
       - Windows: `python {REPO_ROOT}\.infra\scripts\python\reverse_entities\entity_relationship_builder.py --repo-root {REPO_ROOT} --function-interface-relations {function_interface_file} --interface-entity-relations {interface_entity_file} --output {output_dir}\function-entity.json --relation-type function-to-entity`
     - 脚本参数说明：
       - `--repo-root`：仓库根目录
       - `--function-interface-relations`：功能-接口关系文件路径
       - `--interface-entity-relations`：接口-实体关系文件路径
       - `--output`：输出文件路径（`{REPO_ROOT}/omni-doc/specs/entities/relations/function-entity.json`）
       - `--relation-type`：关系类型（function-to-entity表示功能→实体）
     - 🔴 **关系构建逻辑**：
       - 构建接口到实体的映射：从接口-实体关系文件中提取 `{api_id: [entity_id1, entity_id2, ...]}`
       - 构建功能到实体的映射：
         - 对于每个功能，从功能-接口关系文件中获取其关联的接口ID列表
         - 通过接口ID查找对应的实体ID列表
         - 合并所有关联的实体ID（去重）
         - 生成关系列表：`[{source: "FUNC-001", targets: ["ENTITY-001", "ENTITY-002"]}, ...]`
     - 🔴 **输出文件**：
       - 功能 → 实体关系：`{REPO_ROOT}/omni-doc/specs/entities/relations/function-entity.json`
       - 文件格式：JSON数组，每个元素包含 `source`（功能ID）和 `targets`（实体ID列表）
     - 🔴 **验证生成结果**：
       - 验证关系文件已生成
       - 验证文件格式正确
       - 统计关系数量
       - 🔴 明确声明："已建立功能 → 实体关系，共 {relation_count} 条关系"

### 5. [ ] 展示结果并向用户确认
- 获取仓库根目录
- 🔴 强制验证输出目录：检查关系文件是否已生成到 `{REPO_ROOT}/omni-doc/specs/entities/relations/`
- 🔴 强制验证缓存状态：AI Agent直接读取状态文件，验证 `entity_relationship_building.confirmed == false`
- 读取生成的关系文件：
  - `interface-entity.json`
  - `entity-interface.json`
  - `function-entity.json`（如果存在）
- 总结并展示：
  - 接口 → 实体关系数量
  - 实体 → 接口关系数量
  - 功能 → 实体关系数量（如果已建立）
  - 关系网络统计信息：
    - 涉及的接口总数
    - 涉及的实体总数
    - 涉及的功能总数（如果功能反构已完成）
  - 代表性关系示例（展示2-3个关系示例）
  - 关系文件输出目录
- 询问用户："实体关系建立已完成，是否确认结果？[Y/n]"
- 🔴 状态双重检查：用户响应后AI Agent再次读取状态文件，验证更新成功

### 6. [ ] 处理用户确认，更新缓存状态
#### 用户确认（Y/yes/回车或非交互模式）
- 读取状态文件 `{REPO_ROOT}/.cache/reverse/entities/.cache-status.json`
- 更新 `entity_relationship_building` 部分，设置 `confirmed: true` 和当前时间戳
- 使用 `write` 工具保存更新后的状态文件
- 明确说明阶段4已完成，清空上下文
- 自动结束整个实体反构流程

#### 用户拒绝（n/no）
- 允许查看详情或重新生成
- 保持 `confirmed: false` 状态，等待用户进一步指令

## AI Agent上下文管理要求
- **阶段开始时主动清空上下文**：请先执行上下文清理，然后明确说明"开始阶段4：实体关系建立。已清空上一阶段的上下文"
- **关系建立后清理上下文**：关系建立完成后，清理当前处理的所有数据和分析结果，明确声明："已完成实体关系建立。已清空当前处理的上下文"

## 🔴 实体关系建立要求
请参考 [核心规则文档](../core-rules.md) 中的分批处理规则和Token管理规则。

## 输入
- **实体溯源映射**（必需）：
  - 位置：`{REPO_ROOT}/.cache/reverse/entities/entity-consolidation/entities_lineage.json`
  - 格式：JSON文件，记录实体与接口的对应关系
- **接口文档目录**（可选）：
  - 位置：`{REPO_ROOT}/omni-doc/specs/entities/interfaces/` 或 `{REPO_ROOT}/.cache/reverse/interfaces/interface-aggregation/`
  - 用途：验证接口ID的有效性
- **功能-接口关系文件**（可选，如果功能反构已完成）：
  - 位置：`{REPO_ROOT}/omni-doc/specs/entities/relations/function-interface.json`
  - 格式：JSON文件，记录功能与接口的对应关系

## 输出
- **接口 → 实体关系**：
  - 位置：`{REPO_ROOT}/omni-doc/specs/entities/relations/interface-entity.json`
  - 格式：JSON数组，每个元素包含 `source`（接口ID）和 `targets`（实体ID列表）
- **实体 → 接口关系**：
  - 位置：`{REPO_ROOT}/omni-doc/specs/entities/relations/entity-interface.json`
  - 格式：JSON数组，每个元素包含 `source`（实体ID）和 `targets`（接口ID列表）
- **功能 → 实体关系**（如果功能反构已完成）：
  - 位置：`{REPO_ROOT}/omni-doc/specs/entities/relations/function-entity.json`
  - 格式：JSON数组，每个元素包含 `source`（功能ID）和 `targets`（实体ID列表）

## 注意事项
- AI Agent必须在阶段4完成后暂停，等待用户确认后才能结束整个流程
- 实体关系建立是流程的最后一步，必须确认后才算完成
- 用户确认后，AI Agent应该自动结束整个实体反构流程
- **关系建立要求**：
  - 接口 → 实体关系必须建立（必需）
  - 实体 → 接口关系必须建立（必需）
  - 功能 → 实体关系可选（仅在功能反构已完成时建立）
  - 关系文件格式必须统一，使用标准JSON格式
- **依赖关系**：
  - 接口 → 实体关系和实体 → 接口关系可以独立建立
  - 功能 → 实体关系依赖于功能反构的输出，如果功能反构未完成，应跳过此步骤
- 跨平台支持：所有脚本调用必须同时支持Linux(bash)和Windows(PowerShell)
- **🔴 脚本使用违规严重警告**：
  - 严禁手动修改关系文件跳过处理步骤
  - 严禁批量创建空关系文件模拟处理完成
  - 严禁跳过用户确认机制自动处理所有剩余步骤
  - 违规行为将导致处理状态不一致，影响断点续执行功能

