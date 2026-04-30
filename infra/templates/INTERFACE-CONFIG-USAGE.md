# 接口反构配置使用说明（简化版）

## 概述

接口反构现在支持**简化版配置文件**，使用类似交互式向导的Markdown格式，比YAML格式更简单直观。

## 配置文件位置

**简化版配置**（推荐）：`{REPO_ROOT}/.cache/user_input/interface-config.md`

**YAML配置**（高级，向后兼容）：`{REPO_ROOT}/.cache/user_input/interface-identification-rules.yaml`

## 简化版配置格式

### 配置文件结构

```markdown
# 接口反构配置（简化版）

## 接口类型选择

您的选择：restful,module,cli

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

### 配置示例

完整示例请参考：`.specify/templates/interface-config-simple-example.md`

## 使用步骤

### 步骤1：创建或编辑配置文件

```bash
# 系统安装时会自动生成模板文件
# 如果不存在，可以手动创建：
cp .specify/templates/interface-config-simple.md .cache/user_input/interface-config.md
```

### 步骤2：填写接口类型

在配置文件中找到"您的选择"行，填写接口类型代码（用逗号分隔）：

```markdown
您的选择：restful,module,cli
```

**支持的接口类型**：
- `restful`: RESTful API 接口
- `message`: 消息类接口
- `module`: 模块间接口
- `cli`: 命令行接口
- `rpc`: RPC 接口
- `function`: 函数接口
- `other`: 其他类型接口

**留空表示全选**：如果"您的选择"行留空或删除，系统会全选所有接口类型。

### 步骤3：配置约束规则（可选）

#### 文件路径过滤

在"文件路径过滤"部分的代码块中填写要包含的文件路径模式：

```markdown
### 文件路径过滤

```
src/api/*
**/controllers/*.py
plugins/**/*.py
```
```

**支持glob模式**：
- `src/api/*`: 匹配 `src/api/` 目录下的所有文件
- `**/controllers/*.py`: 匹配任意目录下的 `controllers` 子目录中的 `.py` 文件
- `plugins/**/*.py`: 匹配 `plugins` 目录及其子目录下的所有 `.py` 文件

#### 函数名模式

在"函数名模式"部分的代码块中填写要匹配的函数名模式：

```markdown
### 函数名模式

```
get_*
post_*
create_*
delete_*
```
```

**支持通配符**：
- `get_*`: 匹配以 `get_` 开头的函数名
- `*_handler`: 匹配以 `_handler` 结尾的函数名
- `*_api_*`: 匹配包含 `_api_` 的函数名

#### 排除模式

在"排除模式"部分的代码块中填写要排除的文件或函数模式：

```markdown
### 排除模式

```
**/test/**
**/*_test.py
**/vendor/**
```
```

### 步骤4：运行反构命令

```bash
reverse --target interfaces --path <your-path>
```

系统会自动：
1. 检测配置文件是否存在
2. 如果存在，解析配置文件并跳过交互式配置步骤
3. 如果不存在，使用交互式配置流程

## 配置文件优先级

1. **简化版配置**（`interface-config.md`）：最高优先级
2. **YAML配置**（`interface-identification-rules.yaml`）：如果简化版不存在
3. **交互式配置**：如果配置文件都不存在

## 配置示例

### 示例1：只选择接口类型，不配置约束

```markdown
# 接口反构配置（简化版）

## 接口类型选择

您的选择：restful,module

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

### 示例2：完整配置

```markdown
# 接口反构配置（简化版）

## 接口类型选择

您的选择：restful,module,cli

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

## 与交互式配置的对比

### 交互式配置

- **优点**：直观、适合临时调整
- **缺点**：每次执行都需要配置

### 简化版配置文件

- **优点**：
  - ✅ 简单直观，类似交互式向导的风格
  - ✅ 可复用，适合团队共享
  - ✅ 支持版本控制
  - ✅ 无需复杂的YAML结构
- **缺点**：需要提前准备配置文件

## 与YAML配置的对比

### YAML配置（高级）

```yaml
identification_rules:
  interface_types:
    module:
      constraints:
        - description: "在每个目录下 zenic_xx_plugin.py 文件中，create_、delete_、update_ 开头的函数"
```

**特点**：
- 支持自然语言描述的约束规则（AI自动转换）
- 支持更复杂的配置结构
- 适合高级用户

### 简化版配置（推荐）

```markdown
您的选择：module

### 文件路径过滤

```
**/zenic_*_plugin.py
```

### 函数名模式

```
create_*
delete_*
update_*
```
```

**特点**：
- ✅ 更简单直观
- ✅ 直接填写，无需理解YAML结构
- ✅ 类似交互式向导的风格
- ✅ 适合大多数用户

## 常见问题

### Q1: 简化版配置和YAML配置有什么区别？

**A**: 
- **简化版配置**：使用Markdown格式，直接填写接口类型和约束规则，简单直观
- **YAML配置**：使用YAML格式，支持自然语言描述的约束规则（AI自动转换），适合高级用户
- 两种格式可以共存，简化版配置优先级更高

### Q2: 如果同时存在两种配置文件会怎样？

**A**: 系统会优先使用简化版配置（`interface-config.md`），忽略YAML配置。

### Q3: 约束规则可以不配置吗？

**A**: 可以。如果某个约束规则不需要，可以：
- 留空代码块
- 删除对应部分
- 不填写任何内容

### Q4: 配置文件格式有严格要求吗？

**A**: 
- 接口类型选择：必须在"您的选择："行后填写
- 约束规则：必须在对应的代码块中填写（三个反引号之间）
- 其他部分可以自由添加注释或说明

### Q5: 如何从交互式配置切换到配置文件？

**A**: 
1. 运行一次交互式配置，查看生成的 `interface-types.json` 和 `constraints.json`
2. 根据这些文件的内容，填写到 `interface-config.md` 中
3. 下次执行时，系统会自动使用配置文件

## 迁移指南

### 从YAML配置迁移到简化版配置

1. **读取YAML配置中的接口类型**：
   ```yaml
   # 从 YAML 中提取
   interface_types:
     - restful
     - module
   ```

2. **转换为简化版格式**：
   ```markdown
   您的选择：restful,module
   ```

3. **提取约束规则**：
   - 从YAML的 `constraints` 部分提取文件路径、函数名模式等
   - 填写到简化版配置的对应代码块中

### 从交互式配置迁移到配置文件

1. **查看生成的JSON文件**：
   - `interface-types.json`: 查看选择的接口类型
   - `constraints.json`: 查看配置的约束规则

2. **填写到配置文件**：
   - 根据JSON内容填写到 `interface-config.md`

## 注意事项

1. **配置文件位置**：必须放在 `.cache/user_input/` 目录下
2. **文件格式**：使用Markdown格式，注意代码块的格式（三个反引号）
3. **接口类型代码**：必须使用小写，用逗号分隔
4. **路径模式**：支持glob模式，每行一个模式
5. **向后兼容**：如果配置文件不存在，完全按照交互式流程执行

