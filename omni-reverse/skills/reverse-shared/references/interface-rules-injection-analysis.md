# 接口规则和约束的用户注入机制分析

## 概述

接口反构支持**两种方式**让用户注入接口类型选择和约束规则：
1. **交互式配置**：通过分步向导模板，在运行时交互式选择
2. **配置文件注入**：通过YAML配置文件，提前定义规则和约束

## 方式1：交互式配置（运行时注入）

### 执行时机

在**阶段2：接口扫描与示例生成**的步骤5-7中执行。

### 配置流程

#### 步骤1：接口类型选择（步骤5）

**模板文件**：`{REPO_ROOT}/.omni-infra/templates/interface-type-selection-template.md`

**用户交互**：
```
# 接口类型选择向导 - 步骤1/3

请选择要扫描的接口类型（可多选）：

- [ ] RESTful API (Web服务接口)
- [ ] 消息类接口 (MQ、事件等)
- [ ] 模块间接口 (模块内部调用)
- [ ] 命令行接口 (CLI命令)
- [ ] RPC 接口 (远程过程调用)
- [ ] 函数接口 (普通函数调用)
- [ ] 其他类型接口

[ ] 全选
[ ] 取消全选

请输入您的选择（例如：1,3,5 或直接回车全选）：
```

**输出文件**：`{REPO_ROOT}/.cache/reverse/interfaces/interface-types.json`

**非交互模式**：自动全选所有接口类型

#### 步骤2：约束规则配置（步骤6）

**模板文件**：`{REPO_ROOT}/.omni-infra/templates/constraint-configuration-template.md`

**用户交互**：
```
# 约束规则配置向导 - 步骤2/3

您选择了以下接口类型：
{{selected_interface_types}}

可选的约束规则配置：

### 文件路径过滤（可选）
请输入要包含的文件路径模式（如src/api/*）：
{{include_paths}}

### 函数名模式（可选）
请输入要匹配的函数名模式（如get_*、post_*）：
{{function_patterns}}

### 排除模式（可选）
请输入要排除的文件或函数模式：
{{exclude_patterns}}

[S] 跳过此步骤并使用默认配置，[Enter] 继续配置
```

**输出文件**：`{REPO_ROOT}/.cache/reverse/interfaces/constraints.json`

**非交互模式**：使用空约束规则（默认配置）

#### 步骤3：配置概览与最终确认（步骤7）

**模板文件**：`{REPO_ROOT}/.omni-infra/templates/final-confirmation-template.md`

**用户交互**：
```
# 配置确认向导 - 步骤3/3

## 您的配置概览

### 接口类型
{{selected_interface_types}}

### 约束规则
- 文件路径过滤：{{include_paths_display}}
- 函数名模式：{{function_patterns_display}}
- 排除模式：{{exclude_patterns_display}}

### 扫描范围和预估工作量
基于架构识别结果，关键模块包括：
{{key_modules}}

预估扫描文件总数：{{estimated_files}} 个
预计处理方式：{{processing_mode}}

## 确认操作
请确认以上配置是否正确：

- 输入 `y` 或 `yes` 确认配置并开始扫描
- 输入 `n` 或 `no` 重新配置
- 输入 `1` 返回接口类型选择
- 输入 `2` 返回约束规则配置

确认 [Y/n]:
```

### 配置文件生成

交互式配置完成后，系统会生成两个JSON配置文件：

1. **`interface-types.json`**：包含用户选择的接口类型列表
2. **`constraints.json`**：包含用户配置的约束规则（转换为AI Agent可检索的规则格式）

## 方式2：配置文件注入（提前定义）

### 配置文件位置

**用户配置文件**：`{REPO_ROOT}/.cache/user_input/interface-identification-rules.yaml`（优先使用）

**系统默认模板**：`{REPO_ROOT}/.omni-infra/templates/interface-identification-rules-default.yaml`（备用）

### 配置文件结构

```yaml
version: "1.0"
description: "接口识别规则配置（用户可配置）"

# 接口识别规则和约束信息
identification_rules:
  # 按接口类型配置识别规则
  interface_types:
    # 示例：模块间接口
    module:
      # 约束规则（自然语言描述，AI自动转换）
      constraints:
        - description: "在每个目录下 zenic_xx_plugin.py 文件中，create_、delete_、update_ 开头的函数"
          # AI Agent 会自动理解并转换为检索规则
```

### 支持的接口类型

- `restful`: RESTful API 接口
- `message`: 消息类接口（MQ、事件等）
- `module`: 模块间接口
- `cli`: 命令行接口
- `rpc`: RPC 接口
- `function`: 函数接口
- `other`: 其他类型接口

### 约束规则配置方式

#### 方式1：自然语言描述（推荐）

使用自然语言描述约束规则，AI Agent会自动转换为检索规则：

```yaml
constraints:
  - description: "在每个目录下 zenic_xx_plugin.py 文件中，create_、delete_、update_ 开头的函数"
    # AI Agent 会自动理解并转换为：
    # - 文件路径模式：**/zenic_*_plugin.py
    # - 函数名模式：create_*, delete_*, update_*
```

#### 方式2：结构化配置（高级）

直接提供结构化的约束规则：

```yaml
constraints:
  - description: "特定目录下的插件文件"
    include_patterns:
      - "**/zenic_*_plugin.py"
    function_patterns:
      - "create_*"
      - "delete_*"
      - "update_*"
    exclude_patterns:
      - "**/test/**"
```

### 配置文件使用流程

1. **安装时自动生成模板**：
   - 系统安装时会在 `.cache/user_input/` 目录下生成 `interface-identification-rules.yaml` 模板文件

2. **用户编辑配置**：
   - 用户根据项目需求编辑配置文件
   - 只配置需要反构的接口类型
   - 可选：添加约束规则（自然语言或结构化）

3. **系统检测和使用**：
   - 如果配置文件存在且有效，系统会优先使用配置文件
   - 如果配置文件不存在，使用交互式配置流程
   - 如果配置文件部分缺失，只执行缺失部分的交互式配置

## 两种方式的优先级和组合

### 优先级顺序

1. **用户配置文件**（`.cache/user_input/interface-identification-rules.yaml`）：最高优先级
2. **交互式配置**（运行时选择）：如果配置文件不存在
3. **系统默认配置**：如果以上都不存在

### 组合使用场景

#### 场景1：完全使用配置文件

```yaml
# .cache/user_input/interface-identification-rules.yaml
identification_rules:
  interface_types:
    module:
      constraints:
        - description: "只识别插件文件中的接口"
```

**执行效果**：
- 跳过交互式配置步骤5-7
- 直接使用配置文件中的接口类型和约束规则
- 生成 `interface-types.json` 和 `constraints.json`

#### 场景2：完全使用交互式配置

**不创建配置文件**（或删除现有配置文件）

**执行效果**：
- 执行交互式配置步骤5-7
- 用户通过向导选择接口类型和配置约束规则
- 生成 `interface-types.json` 和 `constraints.json`

#### 场景3：混合使用

**配置文件只定义接口类型，约束规则通过交互式配置**

```yaml
# .cache/user_input/interface-identification-rules.yaml
identification_rules:
  interface_types:
    - module
    - restful
  # 不配置 constraints，通过交互式配置
```

**执行效果**：
- 使用配置文件中的接口类型（跳过步骤5）
- 执行交互式约束规则配置（步骤6）
- 执行配置概览确认（步骤7）

## 约束规则的转换机制

### 自然语言 → 检索规则

AI Agent会将自然语言描述的约束规则转换为结构化的检索规则：

**输入（自然语言）**：
```
"在每个目录下 zenic_xx_plugin.py 文件中，create_、delete_、update_ 开头的函数"
```

**输出（检索规则）**：
```json
{
  "include_patterns": ["**/zenic_*_plugin.py"],
  "function_patterns": ["create_*", "delete_*", "update_*"]
}
```

### 约束规则的应用

约束规则在以下阶段应用：

1. **阶段2：接口模式识别**（步骤8）
   - 应用约束规则过滤文件
   - 应用约束规则过滤函数

2. **阶段3：接口清单扫描**
   - 使用约束规则指导接口识别
   - 只识别符合约束规则的接口

## 配置文件示例

### 简化配置示例

```yaml
version: "1.0"
description: "接口识别规则配置"

identification_rules:
  interface_types:
    module:
      constraints:
        - description: "只识别插件文件中的接口"
        - description: "排除测试文件"
```

### 完整配置示例

```yaml
version: "1.0"
description: "接口识别规则配置"

identification_rules:
  interface_types:
    module:
      constraints:
        - description: "特定目录下的插件文件"
          include_patterns:
            - "**/zenic_*_plugin.py"
          function_patterns:
            - "create_*"
            - "delete_*"
            - "update_*"
          exclude_patterns:
            - "**/test/**"
            - "**/*_test.py"
```

## 总结

### 用户注入方式对比

| 方式 | 配置文件位置 | 使用时机 | 优点 | 缺点 |
|------|------------|---------|------|------|
| **交互式配置** | 运行时生成 | 执行阶段2时 | 直观、灵活、适合临时调整 | 每次执行都需要配置 |
| **配置文件注入** | `.cache/user_input/interface-identification-rules.yaml` | 执行前定义 | 可复用、适合团队共享、支持版本控制 | 需要提前准备配置文件 |

### 推荐使用场景

1. **首次使用或探索阶段**：使用交互式配置
2. **项目稳定后**：使用配置文件注入，便于团队共享和版本控制
3. **CI/CD自动化**：使用配置文件注入，确保一致性

### 关键特性

1. **自然语言支持**：约束规则可以使用自然语言描述，AI自动转换
2. **灵活组合**：可以混合使用配置文件和交互式配置
3. **向后兼容**：如果配置文件不存在，完全按照交互式流程执行
4. **智能转换**：AI Agent自动将自然语言约束转换为检索规则

## 相关文档

- [确认步骤模板](confirmation-template.md)
- [简化配置摘要说明](simplified-config-summary.md)
- [用法变更说明](usage-changes.md)
- [接口规则注入分析](interface-rules-injection-analysis.md)

