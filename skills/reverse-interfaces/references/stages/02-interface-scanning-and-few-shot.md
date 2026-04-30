# 接口模式识别与示例生成

<!-- 阶段2：接口模式识别与示例生成 -->

## 职责
接口模式识别与接口示例生成，为接口清单扫描阶段的正确执行提供支撑

## 执行流程

### 0. [ ] 创建阶段2的子任务的Todo列表
为确保阶段执行过程的透明化和可追踪性，创建阶段2的子任务的Todo列表：

1. **步骤1 清理上一阶段的上下文，保证本阶段的上下文干净**
2. **步骤2 检查缓存状态，确定是否需要执行分析**
3. **步骤3 获取仓库根目录和缓存目录**
4. **步骤4 读取逻辑架构共享产物（architecture.json）**
5. **步骤5 用户确认扫描配置 - 接口类型选择**
6. **步骤6 用户确认扫描配置 - 约束规则配置**
7. **步骤7 用户确认扫描配置 - 配置概览与最终确认**
8. **步骤8 识别接口模式特征**
9. **步骤9 生成Few-shot示例**
10. **步骤10 保存识别结果到缓存文件**
11. **步骤11 展示结果并向用户确认**
12. **步骤12 处理用户确认，更新缓存状态**
13. **步骤13 基于代码行数和识别结果生成接口数量预估（强制）**
14. **步骤14 预估数量交互确认与标识更新（强制）**

### 1. [x] 清理上一阶段的上下文，保证本阶段的上下文干净
- **阶段开始时主动清空上下文**：执行上下文清理，明确说明"开始阶段2：接口模式识别与示例生成。已清空上一阶段的上下文"
- **输出结果精简**：只输出模式特征和统计信息，避免冗余描述

### 2. [ ] 检查缓存状态，确定是否需要执行分析
- 读取状态文件：`{REPO_ROOT}/.cache/reverse/interfaces/.cache-status.json`
- 检查 `few_shot_examples.confirmed` 字段
- 如果两个字段都为 `true`：跳过阶段2，使用缓存结果
- 如果任一字段为 `false` 或不存在：执行阶段2

### 3. [ ] 获取仓库根目录和缓存目录
- 跨平台脚本调用获取 REPO_ROOT
- AI Agent直接调用check-prerequisites.sh脚本
- AI Agent直接调用check-prerequisites.ps1脚本

### 4. [ ] 读取逻辑架构共享产物
- AI Agent 直接读取：`{REPO_ROOT}/omni-doc/specs/logic_architecture/architecture.json`（由 `reverse-logic-architecture` 生成；接口 Skill 不写入此文件）

### 4.5. [ ] 检查用户注入配置文件（如果存在则使用，跳过交互式配置）
#### 检查简化配置文件
- 🔴 **优先检查简化配置文件**：`{REPO_ROOT}/.cache/user_input/interface-config.md`
- 如果简化配置文件存在且有效：
  - 解析配置文件内容：
    - 提取接口类型选择（从"您的选择"行后读取）
    - 提取文件路径过滤（从"文件路径过滤"部分的代码块读取）
    - 提取函数名模式（从"函数名模式"部分的代码块读取）
    - 提取排除模式（从"排除模式"部分的代码块读取）
  - 根据解析结果生成 `interface-types.json` 和 `constraints.json`
  - **跳过步骤5-7（交互式配置）**，直接继续执行步骤8

#### 检查YAML配置文件（向后兼容）
- 如果简化配置文件不存在，检查YAML配置文件：`{REPO_ROOT}/.cache/user_input/interface-identification-rules.yaml`
- 如果YAML配置文件存在且有效：
  - 解析YAML配置文件
  - 提取接口类型和约束规则
  - 生成 `interface-types.json` 和 `constraints.json`
  - **跳过步骤5-7（交互式配置）**，直接继续执行步骤8

#### 如果配置文件不存在
- 继续执行步骤5-7（交互式配置流程）

### 5. [ ] 用户确认扫描配置 - 接口类型选择
- **🔴 前置条件**：仅在配置文件不存在时执行此步骤
- 读取接口类型选择模板：`{REPO_ROOT}/.infra/templates/interface-type-selection-template.md`
- **🔴 执行统一确认机制**：按照 `reverse-shared/references/confirmation-template.md` 中的"过程中确认模板 - 类型1：配置选择确认"执行
  - 默认配置：全选所有接口类型
  - 交互模式下：显示分步向导第一步界面供用户选择接口类型，支持多选操作和全选/取消全选功能
  - 输出文件：`{REPO_ROOT}/.cache/reverse/interfaces/interface-types.json`

### 6. [ ] 用户确认扫描配置 - 约束规则配置
- **🔴 前置条件**：仅在配置文件不存在时执行此步骤
- 读取约束规则配置模板：`{REPO_ROOT}/.infra/templates/constraint-configuration-template.md`
- **🔴 执行统一确认机制**：按照 `reverse-shared/references/confirmation-template.md` 中的"过程中确认模板 - 类型1：配置选择确认"执行
  - 默认配置：空约束规则
  - 交互模式下：显示分步向导第二步界面供用户配置约束规则，支持跳过此步骤（使用默认配置）
  - 输出文件：`{REPO_ROOT}/.cache/reverse/interfaces/constraints.json`（转换成AI Agent可检索的规则）

### 7. [ ] 用户确认扫描配置 - 配置概览与最终确认
- **🔴 前置条件**：仅在配置文件不存在时执行此步骤
- 读取最终确认模板：`{REPO_ROOT}/.infra/templates/final-confirmation-template.md`
- **🔴 执行统一确认机制**：按照 `reverse-shared/references/confirmation-template.md` 中的"过程中确认模板 - 类型1：配置选择确认"执行
  - 交互模式下：显示所有配置项的概览（用户选择的接口类型、配置的约束规则、扫描范围和预估工作量），等待用户最终确认，支持返回修改功能
  - 非交互模式下：自动确认配置，直接继续执行步骤8

#### 生成配置文件
- 根据用户选择的接口类型生成 `{REPO_ROOT}/.cache/reverse/interfaces/interface-types.json` 文件
- 根据用户配置的约束规则转换后生成 `{REPO_ROOT}/.cache/reverse/interfaces/constraints.json` 文件
- 如果用户未配置约束规则，生成空的约束规则文件

### 8. [ ] 识别接口模式特征
#### 关键约束
- 必须在用户指定的路径范围内识别模式
- 所有识别操作都必须在用户指定的路径范围内进行
- 必须应用用户配置的约束规则进行过滤

#### 识别策略（快速识别）
- **Python**：快速识别装饰器（`@app.route`, `@api.route` 等）和函数定义模式
- **Java**：快速识别注解（`@RestController`, `@RequestMapping` 等）和类方法模式
- **JavaScript/TypeScript**：快速识别函数、类方法、导出函数模式
- **Go**：快速识别函数、方法、接口定义模式
- **C/C++**：快速识别头文件中的公共函数声明模式
- **LSP辅助识别**：在支持LSP的语言中，使用Language Server Protocol工具辅助识别符号和定义，提高准确性

#### LSP增强识别策略
1. **符号精确识别**：
   - 使用 `documentSymbol` 识别文件内的精确符号位置
   - 使用 `workspaceSymbol` 在整个工作区中搜索相关符号
   - 结合符号类型信息过滤出接口相关符号

2. **定义上下文获取**：
   - 使用 `goToDefinition` 获取符号的完整定义上下文
   - 使用 `hover` 获取符号的类型信息和文档
   - 使用 `findReferences` 了解符号的使用场景

3. **交叉验证机制**：
   - 将LSP识别结果与grep模式匹配结果交叉验证
   - 优先采用LSP提供的精确位置信息
   - 对于LSP无法识别的模式，回退到传统模式匹配

#### 识别范围
- 在用户指定的路径范围内，优先识别关键模块，快速提取潜在接口模式特征
- 根据用户选择的接口类型进行针对性识别

#### Token管理要求
- 优先使用 `grep` 快速识别接口模式，只在必要时使用 `read_file`
- 在支持LSP的语言中，优先使用LSP工具进行精确识别，减少不必要的文件读取
- 限制读取范围：对于大文件（>1000 行），只读取接口定义相关部分
- 估算token使用量，如果 > 15万tokens，应减少处理范围
- 使用LSP工具时注意控制查询频率，避免过多的LSP请求消耗资源
- LSP后备机制：当LSP工具不可用时，自动回退到传统的模式匹配策略，确保处理连续性

### 9. [ ] 生成Few-shot示例
#### 关键要求
- 必须基于用户配置的约束规则进行few-shot示例生成
- 读取用户配置的约束规则：从 `constraints.json` 文件读取

#### 约束规则过滤
- 对于每个接口类型，如果用户配置了约束规则：
  - 解析约束规则中的文件路径模式
  - 使用 `glob_file_search` 工具根据路径模式过滤文件
  - 解析约束规则中的函数名模式
  - 使用 `grep` 工具根据函数名模式过滤函数
  - 根据约束规则的 `and`/`or` 逻辑组合条件
  - 从扫描结果中筛选出匹配约束规则的接口
- 如果用户未配置约束规则：使用全部扫描结果

#### 示例生成
- 注入识别规则：将模板中提取的识别规则注入到AI提示词中
- 注入约束规则：将用户配置的约束规则（自然语言描述）注入到AI提示词中（如果存在）
- 注入格式要求：将模板中提取的格式定义注入到AI提示词中
- 分析扫描结果（如果应用了约束规则过滤，使用过滤后的结果）
- 结合识别规则和约束规则，识别每种接口类型的典型模式
- 优先使用约束规则匹配的接口作为示例
- 在支持LSP的语言中，使用LSP工具获取更精确的符号信息和定义上下文
- 为每种接口类型生成2-3个典型示例

#### 示例内容要求
- 接口代码片段
- 接口类型标识
- 关键特征（装饰器、注解、命名模式等）
- 识别规则说明（基于模板中的规则）
- 语言特定特征

### 10. [ ] 保存识别结果到缓存文件
- 获取 REPO_ROOT 实际值
- 使用 `write` 工具保存模式特征文件到 `{REPO_ROOT}/.cache/reverse/interfaces/interface-patterns.json`
- 使用 `write` 工具保存Few-shot示例文件到 `{REPO_ROOT}/.cache/reverse/interfaces/few-shot-examples.json`
- 读取状态文件 `{REPO_ROOT}/.cache/reverse/interfaces/.cache-status.json`
- 更新 `interface_patterns` 和 `few_shot_examples` 部分，设置 `confirmed: false` 和当前时间戳
- 使用 `write` 工具保存更新后的状态文件
- 确保 `{REPO_ROOT}/.cache/reverse/interfaces/interface-types.json` 和 `{REPO_ROOT}/.cache/reverse/interfaces/constraints.json` 文件已生成

### 13. [ ] 基于代码行数和识别结果生成接口数量预估（强制）
- 🔴 **强制要求**：必须执行预估脚本，生成接口类型和数量预估文件，禁止跳过
- 调用脚本：
  - Linux/macOS/Windows（Python跨平台）：
    ```bash
    python3 {REPO_ROOT}/.claude/skills/reverse-interfaces/references/scripts/estimate_interface_counts.py {REPO_ROOT}
    ```
- 读取并验证输出文件：`{REPO_ROOT}/.cache/reverse/interfaces/interface-estimation.json`
- 🔴 **数量基线要求**：预估总数 `estimated_total_interfaces` 不得低于 `ceil(total_code_lines * 0.002)`（代码行数千分之2）
- 如果预估数量低于基线：
  - 标记 `under_estimated=true`
  - 必须要求后续阶段执行扩范围重扫或全文件扫描策略

### 14. [ ] 预估数量交互确认与标识更新（强制）
- 🔴 **强制要求**：必须展示接口类型预估和数量统计，并更新必需标识，未确认不得进入阶段3
- 展示内容：
  - 总代码行数、基线数量、预估总数
  - 按接口类型分组的预估数量
- 交互模式下支持人为调整并确认：
  - 支持调整接口类型启用/禁用、类型权重、目标总量（但不得低于基线）
  - 用户确认后更新 `interface-estimation.json` 中 `mandatory_flags.estimation_confirmed=true`
- 非交互模式：
  - 自动确认并设置 `mandatory_flags.estimation_confirmed=true`

### 11. [ ] 展示结果并向用户确认
- 🔴 强制验证缓存状态：AI Agent直接读取状态文件，验证 `interface_patterns.confirmed == false` 且 `few_shot_examples.confirmed == false`
- 读取JSON文件
- 总结并展示：
  - 识别的文件数量
  - 提取的模式特征数量
  - 按语言分组的统计信息
  - 按模式类型分组的统计信息
  - 代表性模式特征示例
  - 模式类型总数和示例总数
  - 每个模式类型的代表性示例
- **🔴 执行统一确认机制**：按照 `reverse-shared/references/confirmation-template.md` 中的"阶段结束确认模板"执行
  - 阶段名称：接口模式识别与示例生成
  - 询问内容："接口模式特征和Few-shot示例已生成，是否确认结果正确？[Y/n]"
- 🔴 状态双重检查：用户响应后（或自动确认后）AI Agent再次读取状态文件，验证更新成功

### 12. [ ] 处理用户确认，更新缓存状态
- **🔴 执行统一确认机制**：按照 `reverse-shared/references/confirmation-template.md` 中的"阶段结束确认模板"的步骤3执行
  - 状态文件：`{REPO_ROOT}/.cache/reverse/interfaces/.cache-status.json`
  - 状态字段：`interface_patterns` 和 `few_shot_examples`
  - 下一阶段：无（阶段2为最后一个阶段）
- 如果用户拒绝（仅交互模式）：
  - 允许查看详情
  - 或重新执行识别
  - 或手动调整结果

## 输出
1. 接口模式特征（JSON 格式），保存到缓存目录 `{REPO_ROOT}/.cache/reverse/interfaces/interface-patterns.json`，包含识别出的各种接口模式特征，为阶段3提供指导。
2. Few-shot示例集合（JSON格式），保存到缓存目录 `{REPO_ROOT}/.cache/reverse/interfaces/few-shot-examples.json`，作为阶段3接口清单扫描的输入。
3. 接口类型列表（JSON格式），保存到缓存目录 `{REPO_ROOT}/.cache/reverse/interfaces/interface-types.json`，包含用户选择的接口类型，供阶段3使用。
4. 约束规则（JSON格式），保存到缓存目录 `{REPO_ROOT}/.cache/reverse/interfaces/constraints.json`，包含用户配置的约束规则，供阶段3使用。


## 注意事项
- 接口模式特征和Few-shot示例是阶段3的输入，必须确认后才能使用
- 阶段2专注于模式识别，不涉及接口清单生成或复杂的状态管理
- 跨平台支持：所有脚本调用必须同时支持 Linux (bash) 和 Windows (PowerShell)