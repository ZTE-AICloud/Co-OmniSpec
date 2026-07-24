# 简化配置文件格式说明

## 改进概述

为了简化用户配置，新增了**简化版配置文件格式**，使用类似 `constraint-configuration-template.md` 的Markdown风格，比YAML格式更简单直观。

## 配置文件格式对比

### 旧格式（YAML，复杂）

```yaml
version: "1.0"
description: "接口识别规则配置（用户可配置）"

identification_rules:
  interface_types:
    module:
      constraints:
        - description: "在每个目录下 zenic_xx_plugin.py 文件中，create_、delete_、update_ 开头的函数"
```

**问题**：
- ❌ 需要理解YAML结构
- ❌ 嵌套层级深
- ❌ 约束规则需要用自然语言描述，不够直观

### 新格式（Markdown，简化）

```markdown
# 接口反构配置

## 接口类型选择

您的选择：
restful,module,cli

---

## 约束规则配置（可选）

### 文件路径过滤

```
src/api/*
**/controllers/*.py
```

### 函数名模式

```
get_*
post_*
```

### 排除模式

```
**/test/**
**/*_test.py
```
```

**优势**：
- ✅ 简单直观，类似交互式向导的风格
- ✅ 直接填写，无需理解复杂结构
- ✅ 约束规则直接填写模式，无需自然语言描述
- ✅ 易于编辑和维护

## 配置文件位置和优先级

### 配置文件位置

1. **简化版配置**（推荐）：`{REPO_ROOT}/.cache/user_input/interface-config.md`
2. **YAML配置**（高级，向后兼容）：`{REPO_ROOT}/.cache/user_input/interface-identification-rules.yaml`

### 优先级

1. **简化版配置**（`interface-config.md`）：最高优先级
2. **YAML配置**（`interface-identification-rules.yaml`）：如果简化版不存在
3. **交互式配置**：如果配置文件都不存在

## 使用方式

### 方式1：使用简化版配置（推荐）

1. **编辑配置文件**：
   ```bash
   # 系统安装时会自动生成模板
   # 编辑 .cache/user_input/interface-config.md
   ```

2. **填写配置**：
   ```markdown
   您的选择：restful,module
   
   ### 文件路径过滤
   ```
   src/api/*
   ```
   ```

3. **运行命令**：
   ```bash
   reverse --target interfaces --path .
   ```

### 方式2：使用YAML配置（高级）

继续使用原有的YAML格式，完全向后兼容。

### 方式3：交互式配置

不创建配置文件，使用交互式向导。

## 配置解析逻辑

### 简化版配置解析

AI Agent解析 `interface-config.md` 时：

1. **提取接口类型**：
   - 查找"您的选择："行
   - 读取该行后的内容（如 `restful,module,cli`）
   - 解析为接口类型列表

2. **提取文件路径过滤**：
   - 查找"文件路径过滤"部分
   - 读取代码块中的内容（三个反引号之间）
   - 每行一个路径模式

3. **提取函数名模式**：
   - 查找"函数名模式"部分
   - 读取代码块中的内容
   - 每行一个函数名模式

4. **提取排除模式**：
   - 查找"排除模式"部分
   - 读取代码块中的内容
   - 每行一个排除模式

5. **生成JSON配置**：
   - 生成 `interface-types.json`
   - 生成 `constraints.json`

## 配置示例

### 最小配置（只选择接口类型）

```markdown
# 接口反构配置

## 接口类型选择

您的选择：
restful,module

---

## 约束规则配置（可选）

### 文件路径过滤

```

### 函数名模式

```

### 排除模式

```
```

```

### 完整配置

```markdown
# 接口反构配置

## 接口类型选择

您的选择：
restful,module,cli

---

## 约束规则配置（可选）

### 文件路径过滤

```
src/api/*
**/controllers/*.py
plugins/**/*.py
```

### 函数名模式

```
get_*
post_*
create_*
delete_*
```

### 排除模式

```
**/test/**
**/*_test.py
**/vendor/**
```
```

## 实施细节

### 阶段2文档更新

在 `02-interface-scanning-and-few-shot.md` 中新增步骤4.5：
- 检查简化配置文件（`interface-config.md`）
- 如果存在，解析并跳过交互式配置步骤5-7
- 如果不存在，检查YAML配置文件
- 如果都不存在，执行交互式配置

### 安装脚本更新

在 `build/install.sh` 中：
- 优先生成简化版配置模板（`interface-config.md`）
- 同时生成YAML配置模板（向后兼容）
- 更新README说明文档

## 优势总结

1. **简单直观**：类似交互式向导的风格，用户容易理解
2. **直接填写**：无需理解YAML结构，直接在代码块中填写模式
3. **易于维护**：Markdown格式，易于编辑和版本控制
4. **向后兼容**：保留YAML配置支持，不影响现有用户
5. **灵活组合**：可以只配置接口类型，约束规则通过交互式配置

## 迁移建议

### 从YAML配置迁移

1. 读取YAML中的接口类型列表
2. 转换为简化格式：`您的选择：restful,module`
3. 提取约束规则，填写到对应的代码块中

### 从交互式配置迁移

1. 查看生成的 `interface-types.json` 和 `constraints.json`
2. 根据JSON内容填写到 `interface-config.md`

## 相关文档

- [确认步骤模板](confirmation-template.md)
- [简化配置摘要说明](simplified-config-summary.md)
- [用法变更说明](usage-changes.md)
- [接口规则注入分析](interface-rules-injection-analysis.md)

