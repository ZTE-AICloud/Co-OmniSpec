# 接口反构配置 - 示例

## 接口类型选择

请选择要扫描的接口类型（可多选，用逗号分隔，留空表示全选）：

支持的接口类型：
- restful: RESTful API 接口
- message: 消息类接口（MQ、事件等）
- module: 模块间接口（模块内部调用）
- cli: 命令行接口（CLI命令）
- rpc: RPC 接口（远程过程调用）
- function: 函数接口（普通函数调用）
- other: 其他类型接口

您的选择：
restful,module

---

## 约束规则配置（可选）

### 文件路径过滤

请输入要包含的文件路径模式（每行一个，支持glob模式，如 `src/api/*` 或 `**/controllers/*.py`）：

```
src/api/*
**/controllers/*.py
plugins/**/*.py
```

### 函数名模式

请输入要匹配的函数名模式（每行一个，支持通配符，如 `get_*`、`post_*`）：

```
get_*
post_*
create_*
delete_*
```

### 排除模式

请输入要排除的文件或函数模式（每行一个，支持glob模式）：

```
**/test/**
**/*_test.py
**/vendor/**
```

