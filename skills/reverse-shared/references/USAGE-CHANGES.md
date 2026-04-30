# 用户使用变化说明

## 概述

本次优化**对用户使用命令的方式没有变化**，所有原有的命令参数和用法都保持不变。同时，**新增了更灵活的交互模式控制选项**。

## 命令使用方式

### 基本命令格式（无变化）

```bash
# 接口反构命令
reverse --target interfaces --path <path>
```

### 交互模式控制参数（增强）

#### 原有参数（保持不变）

```bash
# 启用交互模式（每个阶段完成后等待用户确认）
reverse --target interfaces --path . --interactive

# 禁用交互模式（全自动，不等待确认）
reverse --target interfaces --path . --non-interactive
reverse --target interfaces --path . --yes
```

#### 新增参数格式（更明确）

```bash
# 明确启用交互模式
reverse --target interfaces --path . --interactive yes

# 明确禁用交互模式
reverse --target interfaces --path . --interactive no
```

## 使用场景对比

### 场景1：首次反构，需要确认每个阶段结果

**之前和现在都可以使用**：
```bash
reverse --target interfaces --path . --interactive
```

**现在也可以使用（更明确）**：
```bash
reverse --target interfaces --path . --interactive yes
```

**执行效果**：
- 阶段1完成后：等待用户确认架构识别结果
- 阶段2完成后：等待用户确认接口类型选择、约束规则配置、Few-shot示例
- 阶段3完成后：等待用户确认接口清单
- 阶段4完成后：等待用户确认文档生成结果

### 场景2：自动化脚本，不需要任何确认

**之前和现在都可以使用**：
```bash
reverse --target interfaces --path . --non-interactive
# 或
reverse --target interfaces --path . --yes
```

**现在也可以使用（更明确）**：
```bash
reverse --target interfaces --path . --interactive no
```

**执行效果**：
- 所有阶段自动确认，不等待用户输入
- 配置选择使用默认值（如全选所有接口类型）
- 批次处理自动继续，不询问是否继续

### 场景3：默认行为（无变化）

**不指定任何交互参数**：
```bash
reverse --target interfaces --path .
```

**执行效果**：
- 默认使用**非交互模式**（全自动）
- 所有确认点自动确认
- 配置使用默认值

## 参数优先级（无变化）

1. `--non-interactive` 或 `--yes`：最高优先级，强制非交互模式
2. `--interactive no`：明确禁用交互模式（新增）
3. `--interactive yes` 或 `--interactive`：启用交互模式
4. 默认：非交互模式（全自动）

## 主要变化总结

### ✅ 保持不变的部分

1. **所有原有参数**：`--interactive`、`--non-interactive`、`--yes` 的行为完全不变
2. **默认行为**：默认仍然是全自动模式（非交互）
3. **命令格式**：基本命令格式没有任何变化
4. **执行流程**：各阶段的执行流程和输出结果没有变化

### ✨ 新增的功能

1. **更明确的参数格式**：支持 `--interactive yes/no` 明确指定
2. **统一的确认机制**：所有确认点使用统一的判断逻辑（对用户透明）

## 推荐使用方式

### 交互式使用（需要确认）

```bash
# 推荐：使用明确的 yes 参数
reverse --target interfaces --path . --interactive yes

# 也可以：使用简写（向后兼容）
reverse --target interfaces --path . --interactive
```

### 自动化使用（不需要确认）

```bash
# 推荐：使用明确的 no 参数
reverse --target interfaces --path . --interactive no

# 也可以：使用原有参数（向后兼容）
reverse --target interfaces --path . --non-interactive
# 或
reverse --target interfaces --path . --yes
```

## 注意事项

1. **向后兼容**：所有原有命令都可以正常使用，无需修改
2. **默认行为**：如果不指定任何交互参数，默认使用非交互模式（全自动）
3. **参数冲突**：如果同时指定 `--interactive` 和 `--non-interactive`，会报错（与之前一致）

