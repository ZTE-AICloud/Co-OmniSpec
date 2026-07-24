# 场景模式识别与示例生成

<!-- 阶段1：场景模式识别与示例生成 -->

## 职责
负责识别场景模式特征并生成few-shot示例，为场景清单构建阶段的正确执行提供支撑。

## 执行流程

### 0. [ ] 创建阶段1的子任务的Todo列表
为确保阶段执行过程的透明化和可追踪性，创建阶段1的子任务的Todo列表：

1. **步骤1 清理上一阶段的上下文，保证本阶段的上下文干净**
2. **步骤2 检查缓存状态，确定是否需要执行分析**
3. **步骤2.5 检查用户注入配置（如果存在则使用，跳过AI识别）**
4. **步骤3 获取仓库根目录和缓存目录**
5. **步骤4 用户确认扫描配置（场景类型选择、约束规则配置）**
6. **步骤5 识别场景模式特征**
7. **步骤6 生成Few-shot示例**
8. **步骤7 保存识别结果到缓存文件**
9. **步骤8 展示结果并向用户确认**
10. **步骤9 处理用户确认，更新缓存状态**

### 1. [x] 清理上一阶段的上下文，保证本阶段的上下文干净
- 🔴 **强制Token检查**：阶段开始前必须检查当前上下文大小，如超过10万tokens则强制清空
- 🔴 **强制要求：必须清空上下文**：执行上下文清理，明确说明"开始阶段1：场景模式识别与示例生成。已清空上一阶段的上下文"
- 🔴 **清理验证**：清理后验证上下文已清空，只保留当前阶段必需的状态信息（阶段名称、缓存目录路径、状态文件路径）
- **输出结果精简**：只输出模式特征和统计信息，避免冗余描述

### 2. [ ] 检查缓存状态，确定是否需要执行分析
- 读取状态文件：`{REPO_ROOT}/.cache/reverse/scenarios/.cache-status.json`
- 检查 `scenario_patterns.confirmed` 和 `few_shot_examples.confirmed` 字段
- 如果两个字段都为 `true`：跳过阶段1，使用缓存结果
- 如果任一字段为 `false` 或不存在：继续执行阶段1

### 2.5. [ ] 检查用户注入配置（如果存在则使用，跳过AI识别）
#### 检查配置文件
- 检查用户注入配置文件：`{REPO_ROOT}/.cache/user_input/scenario-identification-rules.yaml`
- 如果配置文件不存在：跳过此步骤，继续执行步骤4-6（用户交互配置和AI识别）
- 如果配置文件存在：执行以下操作

#### 读取和验证配置
- 读取配置文件内容
- 验证YAML格式正确性
- 验证配置字段的有效性（场景类型是否在支持列表中）

#### 检查配置方式
- 检查配置文件中是否存在 `simple_config` 字段（简化配置）
- 检查配置文件中是否存在详细配置字段（`scenario_patterns`、`few_shot_examples`、`constraints`）
- 确定使用的配置方式：
  - 如果同时存在简化配置和详细配置：优先使用详细配置（跳过转换）
  - 如果只存在简化配置：执行自然语言转换
  - 如果只存在详细配置：直接使用（保持向后兼容）
  - 如果都不存在：继续执行步骤4-6（用户交互配置和AI识别）

#### 自然语言转换（如果使用简化配置）
如果检测到 `simple_config` 字段且没有对应的详细配置，执行以下转换：

1. **场景模式特征转换（scenario_descriptions → scenario_patterns）**
   - 读取 `simple_config.scenario_descriptions` 中的自然语言描述
   - 对每个场景描述，AI Agent分析并提取：
     - **代码模式**：从描述中识别可能的函数名、关键字（如"登录"→"login"、"验证"→"authenticate"）
     - **关键特征**：提取业务流程中的关键步骤和特征点
     - **业务领域**：从 `business_domain` 字段获取，或从描述中推断
     - **模式名称**：基于描述生成有意义的模式名称
   - 自动生成 `scenario_patterns` 结构，包含：
     - `pattern_name`：基于描述生成的模式名称
     - `pattern_type`：从 `type` 字段获取
     - `description`：使用原始描述
     - `code_patterns`：从描述中提取的代码模式列表
     - `business_domain`：从配置或描述中获取
     - `key_features`：从描述中提取的关键特征列表
   - 示例转换：
     - 输入："用户登录流程：用户输入用户名和密码，系统验证后创建会话"
     - 输出：
       ```json
       {
         "pattern_name": "用户登录流程",
         "pattern_type": "正向主流程",
         "description": "用户输入用户名和密码，系统验证后创建会话",
         "code_patterns": ["login", "authenticate", "create_session", "username", "password"],
         "business_domain": "用户管理",
         "key_features": ["用户名密码验证", "会话创建"]
       }
       ```

2. **约束规则转换（constraint_descriptions → constraints）**
   - 读取 `simple_config.constraint_descriptions` 中的自然语言描述
   - 对每个约束描述，AI Agent分析并提取：
     - **文件路径模式**：
       - 识别"只识别XX模块"→生成 `include_patterns`（如"**/user/**/*.py"）
       - 识别"排除XX文件"→生成 `exclude_patterns`（如"**/test_*.py"）
     - **关键字列表**：
       - 识别"包含XX关键字"→生成 `include_keywords`（如["login", "register"]）
     - **作用域**：
       - 识别"XX模块"→生成 `scope`（如"user_management"）
   - 自动生成 `constraints` 结构
   - 示例转换：
     - 输入："只识别用户管理模块的场景，排除测试文件"
     - 输出：
       ```json
       {
         "description": "只识别用户管理模块的场景，排除测试文件",
         "scope": "user_management",
         "include_patterns": ["**/user/**/*.py", "**/auth/**/*.py"],
         "exclude_patterns": ["**/test_*.py", "**/*_test.py", "**/tests/**/*.py"]
       }
       ```

3. **Few-shot示例生成（基于转换后的场景模式特征）**
   - 基于转换后的 `scenario_patterns`，在代码库中搜索匹配的场景代码
   - 使用 `code_patterns` 和 `key_features` 作为搜索条件
   - 为每种场景类型生成2-3个典型示例
   - 自动生成 `few_shot_examples` 结构

#### 处理配置内容（按优先级）
**优先级顺序**：详细配置 > 简化配置（转换后） > 缓存结果 > AI自动识别

1. **场景类型列表（scenario_types）**
   - 如果提供了 `scenario_types`（在详细配置或 `simple_config` 中）：
     - 直接使用配置的场景类型列表
     - 生成 `{REPO_ROOT}/.cache/reverse/scenarios/scenario-types.json` 文件
     - 跳过步骤4中的场景类型选择交互
   - 如果未提供：继续执行步骤4，使用交互式选择

2. **场景模式特征（scenario_patterns）**
   - 如果提供了详细配置的 `scenario_patterns`：
     - 直接使用配置的场景模式特征
     - 将配置内容转换为JSON格式
     - 生成 `{REPO_ROOT}/.cache/reverse/scenarios/scenario-patterns.json` 文件
     - 跳过步骤5（AI模式识别）
   - 如果提供了 `simple_config.scenario_descriptions`（且没有详细配置）：
     - 执行自然语言转换（见上方"自然语言转换"部分）
     - 将转换后的场景模式特征保存到 `{REPO_ROOT}/.cache/reverse/scenarios/scenario-patterns.json` 文件
     - 跳过步骤5（AI模式识别）
   - 如果都未提供：继续执行步骤5，使用AI自动识别

3. **Few-shot示例（few_shot_examples）**
   - 如果提供了详细配置的 `few_shot_examples`：
     - 直接使用配置的Few-shot示例
     - 将配置内容转换为JSON格式
     - 生成 `{REPO_ROOT}/.cache/reverse/scenarios/few-shot-examples.json` 文件
     - 跳过步骤6（AI示例生成）
   - 如果提供了 `simple_config.scenario_descriptions`（且没有详细配置）：
     - 基于转换后的场景模式特征，在代码库中搜索匹配的场景代码
     - 自动生成Few-shot示例
     - 保存到 `{REPO_ROOT}/.cache/reverse/scenarios/few-shot-examples.json` 文件
     - 跳过步骤6（AI示例生成）
   - 如果都未提供：继续执行步骤6，使用AI自动生成

4. **约束规则（constraints）**
   - 如果提供了详细配置的 `constraints`：
     - 直接使用配置的约束规则
     - 将配置内容转换为JSON格式
     - 生成 `{REPO_ROOT}/.cache/reverse/scenarios/constraints.json` 文件
     - 跳过步骤4中的约束规则配置交互
   - 如果提供了 `simple_config.constraint_descriptions`（且没有详细配置）：
     - 执行自然语言转换（见上方"自然语言转换"部分）
     - 将转换后的约束规则保存到 `{REPO_ROOT}/.cache/reverse/scenarios/constraints.json` 文件
     - 跳过步骤4中的约束规则配置交互
   - 如果都未提供：继续执行步骤4，使用交互式配置

#### 更新缓存状态
- 如果所有必需内容（scenario_patterns 和 few_shot_examples）都已从配置中获取或转换得到：
  - 更新状态文件中的 `scenario_patterns` 和 `few_shot_examples` 部分
  - 设置 `confirmed: true` 和当前时间戳
  - 明确说明："已使用用户注入配置（或已从简化配置转换），跳过AI识别步骤"
  - 如果使用了简化配置转换，说明："已从自然语言描述转换为结构化规则"
  - 跳转到步骤8（展示结果并确认）
- 如果只提供了部分内容：
  - 更新已提供内容对应的状态字段
  - 继续执行缺失内容的步骤（步骤4/5/6）

#### 配置转换说明

**详细配置转换**（如果使用详细配置）：
- 将YAML配置转换为对应的JSON格式，确保与缓存JSON文件格式兼容
- 场景模式特征格式：`scenario_patterns.json` 应包含 `patterns` 数组，每个模式包含 `pattern_name`、`pattern_type`、`description`、`code_patterns`、`business_domain`、`key_features` 等字段
- Few-shot示例格式：`few-shot-examples.json` 应包含 `few_shot_examples` 对象，按场景类型组织，每个示例包含 `scenario_name`、`scenario_type`、`business_domain`、`code_snippet`、`key_features`、`description`、`entry_points` 等字段
- 约束规则格式：`constraints.json` 应包含 `constraints` 数组，每个约束包含 `description`、`scope`、`include_patterns`、`exclude_patterns`、`include_keywords` 等字段

**简化配置转换**（如果使用简化配置）：
- AI Agent分析自然语言描述，提取关键信息并转换为结构化格式
- 场景模式特征转换：
  - 从 `scenario_descriptions` 中提取业务描述、代码模式、关键特征
  - 使用代码库搜索验证提取的代码模式是否存在
  - 生成符合 `scenario_patterns.json` 格式的结构
- 约束规则转换：
  - 从 `constraint_descriptions` 中提取文件路径模式、关键字、作用域
  - 将自然语言描述转换为glob模式（如"用户管理模块"→"**/user/**/*.py"）
  - 生成符合 `constraints.json` 格式的结构
- Few-shot示例生成：
  - 基于转换后的场景模式特征，在代码库中搜索匹配的代码片段
  - 使用 `code_patterns` 和 `key_features` 作为搜索条件
  - 生成符合 `few-shot-examples.json` 格式的结构

### 3. [ ] 获取仓库根目录和缓存目录
- 跨平台脚本调用获取 REPO_ROOT
- AI Agent直接调用check-prerequisites.sh脚本
- AI Agent直接调用check-prerequisites.ps1脚本

### 4. [ ] 用户确认扫描配置（场景类型选择、约束规则配置）
#### 检查是否已从用户注入配置获取
- 如果步骤2.5中已从用户注入配置获取了 `scenario_types` 和 `constraints`：跳过此步骤
- 如果步骤2.5中只获取了部分内容：只执行缺失部分的交互配置
- 如果步骤2.5中未获取任何内容：执行完整的交互配置

#### 场景类型选择（如果未从配置获取）
- 读取场景类型选择模板：`{REPO_ROOT}/.omni-infra/templates/scenario-type-selection-template.md`（如果不存在，使用默认场景类型列表）
- 显示分步向导供用户选择场景类型
- 支持的场景类型包括：正向主流程、异常场景、边界场景、批处理场景、集成场景、工作流场景等
- 根据用户选择生成 `{REPO_ROOT}/.cache/reverse/scenarios/scenario-types.json` 文件

#### 约束规则配置（如果未从配置获取）
- 读取约束规则配置模板：`{REPO_ROOT}/.omni-infra/templates/constraint-configuration-template.md`（如果存在）
- 显示分步向导供用户配置约束规则
- 支持跳过此步骤（使用默认配置）
- 根据用户配置生成 `{REPO_ROOT}/.cache/reverse/scenarios/constraints.json` 文件

### 5. [ ] 识别场景模式特征
#### 检查是否已从用户注入配置获取
- 如果步骤2.5中已从用户注入配置获取了 `scenario_patterns`：跳过此步骤
- 如果步骤2.5中未获取：执行以下AI识别流程

#### AI识别流程
- 在用户指定的路径范围内，基于代码库本身进行场景模式识别
- 应用用户配置的约束规则进行过滤（从 `constraints.json` 读取）
- 识别业务逻辑模式（状态机、工作流、异常处理等）和函数调用模式
- 识别测试用例结构，推断业务场景
- 根据用户选择的场景类型进行针对性识别（从 `scenario-types.json` 读取）

### 6. [ ] 生成Few-shot示例
#### 检查是否已从用户注入配置获取
- 如果步骤2.5中已从用户注入配置获取了 `few_shot_examples`：跳过此步骤
- 如果步骤2.5中未获取：执行以下AI生成流程

#### AI生成流程
- 基于用户配置的约束规则和识别结果生成few-shot示例
- 从 `constraints.json` 读取约束规则
- 从 `scenario-patterns.json` 读取已识别的模式特征（如果步骤5已执行）
- 为每种场景类型生成2-3个典型示例
- 示例包含场景代码片段、场景类型标识、关键特征、识别规则说明等

### 7. [ ] 保存识别结果到缓存文件
- 保存模式特征文件到 `{REPO_ROOT}/.cache/reverse/scenarios/scenario-patterns.json`
- 保存Few-shot示例文件到 `{REPO_ROOT}/.cache/reverse/scenarios/few-shot-examples.json`
- 更新状态文件中的 `scenario_patterns` 和 `few_shot_examples` 部分，设置 `confirmed: false`

### 8. [ ] 展示结果并向用户确认
- 读取JSON文件并总结展示：识别的场景模式数量、模式特征数量、按场景类型和业务领域分组的统计信息、代表性示例等
- 询问用户："场景模式特征和Few-shot示例已生成，是否确认结果正确？[Y/n]"

### 9. [ ] 处理用户确认，更新缓存状态
#### 用户确认（Y/yes/回车或非交互模式）
- 🔴 **保存前Token检查**：检查当前上下文大小，如超过15万tokens则强制清空后再保存
- 更新状态文件中的 `scenario_patterns` 和 `few_shot_examples` 部分，设置 `confirmed: true` 和当前时间戳
- 🔴 **强制要求：必须清空上下文**：明确说明阶段1已完成，清空上下文
- 🔴 **清理验证**：清理后验证上下文已清空，只保留必要的状态信息

#### 用户拒绝（n/no）
- 允许查看详情、重新执行识别或手动调整结果

## 输出
1. 场景模式特征（JSON 格式），保存到缓存目录 `{REPO_ROOT}/.cache/reverse/scenarios/scenario-patterns.json`，包含识别出的各种场景模式特征，为后续场景候选抽取和清单构建提供指导。
2. Few-shot示例集合（JSON格式），保存到缓存目录 `{REPO_ROOT}/.cache/reverse/scenarios/few-shot-examples.json`，作为后续场景候选抽取流程的输入（通常在接口清单扫描或其他子流程中使用）。
3. 场景类型列表（JSON格式），保存到缓存目录 `{REPO_ROOT}/.cache/reverse/scenarios/scenario-types.json`，包含用户选择的场景类型，供后续场景处理流程使用。
4. 约束规则（JSON格式），保存到缓存目录 `{REPO_ROOT}/.cache/reverse/scenarios/constraints.json`，包含用户配置的约束规则，供后续场景处理流程使用。

## 注意事项
- **用户注入配置优先级**：如果 `{REPO_ROOT}/.cache/user_input/scenario-identification-rules.yaml` 存在，优先使用用户注入的配置，跳过相应的AI识别步骤
- **灵活组合**：用户可以只配置部分内容（如只配置场景类型），让AI识别模式和生成示例
- **配置验证**：使用用户注入配置前，必须验证YAML格式和字段有效性
- **向后兼容**：如果没有用户注入配置，完全按照原有流程执行（交互式配置 + AI识别）
- 场景模式特征和Few-shot示例是后续场景清单构建的重要输入，必须确认后才能使用
- 阶段1专注于模式识别，不涉及场景清单生成或复杂的状态管理
- 跨平台支持：所有脚本调用必须同时支持 Linux (bash) 和 Windows (PowerShell)
- 本阶段是独立的场景反构流程，只基于用户注入的规则和代码库本身进行场景模式识别，不依赖其他要素的反构输出

