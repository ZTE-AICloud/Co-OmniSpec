---
name: scenario-recognition
description: 场景反构的业务实现——从单文件识别业务场景。供 reverse-scenarios 阶段3 调用。
---

> 本文档为**场景反构**的实现说明，位于本 Skill 的 `references/implementation/`。执行场景清单扫描时，子 Agent 按本文档实现单文件场景识别。

# 场景识别Skill（默认）

## Overview

这是一个通用的场景识别skill，用于从单个代码文件中识别业务场景。该skill接收一个目标文件路径（`file_path`），分析该目标文件中的所有代码，识别出文件中定义的所有业务场景（正向主流程、异常场景、边界场景等）。该skill结合LSP工具、模式匹配、Few-shot示例和业务语义分析等多种方式，能够从目标文件中准确识别各种类型的业务场景。

## 输入参数

Skill接收以下输入参数：

- **file_path** (必需): **目标文件路径**（绝对路径），这是要被识别业务场景的源代码文件。Skill将从这个文件中识别所有业务场景，包括：
  - 正向主流程场景（如用户登录、订单创建等）
  - 异常场景（如登录失败、订单取消等）
  - 边界场景（如空值处理、边界值验证等）
  - 测试用例场景（如单元测试、集成测试等）
- **scenario_types_file** (必需): scenario-types.json文件路径，包含需要识别的场景类型列表
- **constraints_file** (可选): constraints.json文件路径，包含用户配置的约束规则
- **scenario_patterns_file** (必需): scenario-patterns.json文件路径，包含场景模式特征
- **few_shot_examples_file** (必需): few-shot-examples.json文件路径，包含Few-shot示例集合
- **output_file** (必需): 临时输出文件路径（绝对路径），Skill将识别到的场景写入此文件

## 输出格式

🔴 **重要变更**：Skill不再返回场景数组，而是直接写入文件，以减少与SubAgent的交互内容，避免上下文超限。

### 文件输出格式

Skill将识别到的场景直接写入`output_file`指定的临时文件，文件内容为JSON数组格式：

```json
[
  {
    "scenario_name": "用户登录场景",
    "business_name": "用户通过用户名密码登录系统",
    "business_domain": "用户管理",
    "scenario_type": "正向主流程",
    "priority": "high",
    "source_files": ["/path/to/auth.py"],
    "entry_points": ["login", "authenticate"],
    "description": "用户输入用户名和密码，系统验证后允许用户登录",
    "confidence": 0.95,
    "tags": ["authentication", "login"],
    "related_interfaces": []
  }
]
```

### Skill返回格式（极简JSON）

Skill执行完成后，向SubAgent返回极简状态JSON，不包含场景数据：

**成功时**：
```json
{"ok": true, "count": 5}
```

**失败时**：
```json
{"ok": false, "error": "文件读取失败"}
```

**注意**：
- 如果文件中没有识别到场景，写入空数组 `[]`，返回 `{"ok": true, "count": 0}`
- `scenario_id` 由调用方（subagent）统一生成，skill不需要生成
- `source_files` 应只包含当前文件路径
- 所有字段都是必需的，如果无法确定某个字段的值，应使用合理的默认值
- 🔴 **强制要求**：必须确保输出文件已成功写入，如果写入失败，返回 `{"ok": false, "error": "文件写入失败"}`

## When to Use This Skill

在以下情况下使用此skill：
- 需要从代码文件中识别业务场景
- 项目没有定制化的场景识别需求
- 需要通用的场景识别能力

## Workflow

### 步骤1：读取规则和特征文件

🔴 **目的**：读取识别规则和特征文件，这些文件将用于在目标文件（`file_path`）中识别业务场景。

1. 读取 `scenario_types_file`，获取需要识别的场景类型列表（用于判断目标文件中的场景属于哪种类型）
2. 读取 `scenario_patterns_file`，获取场景模式特征（用于在目标文件中匹配场景模式）
3. 读取 `few_shot_examples_file`，获取Few-shot示例（用于提高在目标文件中识别场景的准确性）
4. 如果提供了 `constraints_file`，读取约束规则（用于过滤目标文件中不符合条件的场景候选）

### 步骤2：分析目标文件

🔴 **明确目标**：从`file_path`指定的目标文件中识别所有业务场景。目标文件是输入的源代码文件，Skill需要分析该文件中的所有代码，找出符合业务场景模式的函数、测试用例、业务流程等。

1. **文件类型判断**：根据`file_path`的文件扩展名判断编程语言（如`.py`、`.js`、`.java`、`.go`等）

2. **LSP工具使用**（如果支持）：
   - 🔴 **目标**：在目标文件（`file_path`）中识别场景相关的符号
   - 使用 `documentSymbol` 获取目标文件内的所有符号信息（函数、类、测试用例等）
   - 从符号列表中筛选出场景相关符号（如测试函数、业务流程函数等）
   - 使用 `hover` 获取每个场景符号的文档和类型信息
   - 使用 `findReferences` 了解场景符号的调用关系

3. **模式匹配**：
   - 🔴 **目标**：在目标文件（`file_path`）中匹配场景模式
   - 读取目标文件的代码内容
   - 根据场景模式特征匹配代码模式（如测试用例模式、业务流程模式等）
   - 识别测试用例（如`test_*`、`*Test`等测试函数）
   - 识别业务流程函数（如包含业务逻辑的函数）

4. **业务语义提取**：
   - 🔴 **目标**：从目标文件（`file_path`）中提取场景的业务含义
   - 分析目标文件中的函数名、类名、注释，提取业务含义
   - 分析目标文件中的函数调用链，理解业务流程
   - 结合目标文件的路径和模块名称，理解业务上下文

### 步骤3：场景识别和分类

🔴 **明确目标**：从步骤2的分析结果中，识别出目标文件（`file_path`）中的所有业务场景，并对每个场景进行分类和特征提取。

1. **场景候选识别**：
   - 🔴 **目标**：从目标文件（`file_path`）中筛选出所有场景候选
   - 结合LSP在目标文件中识别出的符号和模式匹配在目标文件中找到的模式
   - 参考Few-shot示例，判断目标文件中的哪些函数/测试用例符合业务场景定义
   - 应用约束规则，过滤目标文件中不符合条件的候选
   - 🔴 **输出**：目标文件中的场景候选列表（每个候选包含函数名、位置、类型等信息）

2. **场景分类**：
   - 🔴 **目标**：对目标文件（`file_path`）中识别出的每个场景候选进行分类
   - 根据场景类型列表，判断目标文件中的每个场景候选属于哪种类型
   - 确定场景类型（正向主流程、异常场景、边界场景等）
   - 🔴 **输出**：每个场景候选的场景类型

3. **业务语义优化**：
   - 🔴 **目标**：为目标文件（`file_path`）中的每个场景生成业务语义化的名称和描述
   - 将目标文件中技术性的函数名转换为更具业务语义的场景名称
   - 例如：目标文件中的`login()` → "用户登录流程"
   - 例如：目标文件中的`create_order()` → "订单创建流程"
   - 🔴 **输出**：每个场景的业务名称、业务描述等

4. **场景特征提取**：
   - 🔴 **目标**：从目标文件（`file_path`）中提取每个场景的完整特征信息
   - 识别业务领域（从目标文件的模块名、包名推断）
   - 确定优先级（根据场景类型和业务重要性）
   - 提取入口函数（从目标文件中场景函数的主入口点提取）
   - 识别相关接口（如果可能，从目标文件中场景调用的接口识别）
   - 🔴 **输出**：每个场景的完整特征信息（业务领域、优先级、入口函数、相关接口等）

### 步骤4：生成场景对象并写入文件

🔴 **明确目标**：将从目标文件（`file_path`）中识别出的所有业务场景，转换为符合输出格式的场景对象。

对目标文件中识别到的每个场景，生成符合输出格式的场景对象：

- **scenario_name**: 业务场景名称（业务语义化的名称）
- **business_name**: 业务描述（更详细的业务说明）
- **business_domain**: 业务领域（如"用户管理"、"订单处理"等）
- **scenario_type**: 场景类型（从scenario_types中匹配）
- **priority**: 优先级（high/medium/low）
- **source_files**: 源文件列表（当前文件）
- **entry_points**: 入口函数列表
- **description**: 场景描述
- **confidence**: 识别置信度（0.0-1.0）
- **tags**: 标签列表
- **related_interfaces**: 相关接口ID列表（如果能够识别）

### 步骤5：写入输出文件

🔴 **明确目标**：将从目标文件（`file_path`）中识别出的所有业务场景写入输出文件。

🔴 **强制要求**：将目标文件中识别到的所有场景写入`output_file`指定的临时文件。

1. **确保输出目录存在**：如果输出文件的目录不存在，必须创建目录
2. **写入JSON文件**：将场景数组序列化为JSON格式，写入到`output_file`
3. **文件格式验证**：确保写入的JSON格式正确，可以被SubAgent正确读取
4. **错误处理**：如果文件写入失败，返回 `{"ok": false, "error": "文件写入失败"}`

**文件写入要求**：
- 使用UTF-8编码
- JSON格式，缩进2个空格
- 如果识别到0个场景，写入空数组 `[]`
- 确保文件写入成功后再返回状态

## LSP增强识别支持

### LSP支持的语言

- **Python**: 使用Python Language Server
- **JavaScript/TypeScript**: 使用TypeScript Language Server
- **Java**: 使用Eclipse JDT Language Server
- **Go**: 使用gopls
- **C/C++**: 使用clangd

### LSP工具使用策略

1. **符号精确识别**：
   - 🔴 **目标**：在目标文件（`file_path`）中识别场景相关的符号
   - 使用 `documentSymbol` 识别目标文件内的精确符号位置
   - 使用 `workspaceSymbol` 在整个工作区中搜索相关符号（但主要关注目标文件）
   - 结合符号类型信息过滤出目标文件中的场景相关符号（函数、类、测试用例等）

2. **定义上下文获取**：
   - 🔴 **目标**：获取目标文件（`file_path`）中场景符号的完整定义上下文
   - 使用 `goToDefinition` 获取目标文件中符号的完整定义上下文
   - 使用 `hover` 获取目标文件中符号的类型信息和文档
   - 使用 `findReferences` 了解目标文件中符号的使用场景和调用链

3. **交叉验证机制**：
   - 将LSP在目标文件中识别出的结果与模式匹配在目标文件中找到的结果交叉验证
   - 优先采用LSP提供的精确位置信息
   - 对于LSP无法识别的模式，回退到传统模式匹配方式分析目标文件

### LSP使用要求

- **优先使用**：在支持LSP的语言中，对目标文件（`file_path`）优先使用LSP工具进行精确识别，减少不必要的文件读取
- **Token管理**：对目标文件使用LSP工具时注意控制查询频率，避免过多的LSP请求消耗资源
- **后备机制**：当LSP工具不可用时，自动回退到传统的模式匹配策略分析目标文件，确保处理连续性
- **精确指定**：每次调用LSP工具时必须明确指定目标文件路径（`file_path`）、函数名等精确信息

## Token管理要求

### 核心原则

- 🔴 **强制Token检查点**：
  - 处理目标文件（`file_path`）前必须检查当前上下文大小，如超过10万tokens则强制清空
  - 处理目标文件完成后必须检查当前上下文大小，如超过15万tokens则报错
- 🔴 **优先使用LSP工具**：对目标文件（`file_path`）使用LSP工具获取结构化信息，避免读取完整文件内容
- 🔴 **精确指定信息**：调用LSP工具时必须明确指定目标文件路径（`file_path`）、函数名等精确信息
- 🔴 **限制文件读取**：如果目标文件很大，只读取目标文件中场景相关部分及其上下文（上下各50行）

### 具体要求

- **场景描述提取**：从目标文件（`file_path`）中优先从文档字符串、注释和测试用例中获取信息，避免分析完整实现代码
- **业务流程识别**：从目标文件中使用LSP工具精准获取函数调用链，避免读取完整函数体
- **业务实体识别**：从目标文件中按需追踪相关类定义，避免加载整个模块
- 🔴 **强制要求：上下文清理**：处理完目标文件（`file_path`）后立即清理上下文，防止Token累积
- 🔴 **清理验证**：清理后验证上下文已清空，只保留必要的状态信息

## 错误处理

- 🔴 **目标文件错误**：如果目标文件（`file_path`）不存在或无法读取，写入空数组 `[]` 到输出文件，返回 `{"ok": false, "error": "目标文件不存在或无法读取: {file_path}"}`
- 如果规则文件缺失，使用默认规则继续处理目标文件，但记录警告
- 如果LSP工具不可用，自动回退到模式匹配方式分析目标文件
- 如果识别目标文件过程中出现错误，记录错误但继续处理目标文件中的其他场景
- 如果输出文件写入失败，返回 `{"ok": false, "error": "文件写入失败"}`
- 🔴 **强制要求**：所有错误情况都必须写入输出文件（即使是空数组），确保SubAgent可以读取文件判断处理状态

## 质量保证

- 验证生成的场景对象结构完整性
- 确保所有必需字段都有值
- 验证场景类型在允许的类型列表中
- 确保置信度在合理范围内（0.0-1.0）

## 示例

### 输入示例

```json
{
  "file_path": "/path/to/project/src/auth/login.py",  // 目标文件：要识别业务场景的源代码文件
  "scenario_types_file": "/path/to/.cache/reverse/scenarios/scenario-types.json",
  "constraints_file": "/path/to/.cache/reverse/scenarios/constraints.json",
  "scenario_patterns_file": "/path/to/.cache/reverse/scenarios/scenario-patterns.json",
  "few_shot_examples_file": "/path/to/.cache/reverse/scenarios/few-shot-examples.json",
  "output_file": "/path/to/.cache/reverse/scenarios/temp/scenario-1-0.json"
}
```

**说明**：`file_path` 是目标文件路径，Skill将从这个文件中识别所有业务场景。

### 输出文件示例

Skill将从目标文件（`file_path`）中识别到的场景写入`output_file`指定的文件：

```json
[
  {
    "scenario_name": "用户登录场景",
    "business_name": "用户通过用户名密码登录系统",
    "business_domain": "用户管理",
    "scenario_type": "正向主流程",
    "priority": "high",
    "source_files": ["/path/to/project/src/auth/login.py"],
    "entry_points": ["login", "authenticate"],
    "description": "用户输入用户名和密码，系统验证后允许用户登录",
    "confidence": 0.95,
    "tags": ["authentication", "login"],
    "related_interfaces": []
  }
]
```

### Skill返回示例

Skill执行完成后，向SubAgent返回极简状态JSON：

**成功时**：
```json
{"ok": true, "count": 1}
```

**失败时**：
```json
{"ok": false, "error": "文件读取失败"}
```
