---
name: sdd
description: OmniSpec 全流程开发入口（SDD 范式）。当用户调用 /sdd 时触发，
  将用户功能描述透传给 routing；express/standard/deep 为 workflow agent 选择符，执行由 agent 而非同名 skill 承担。
  触发词：/sdd, 部署omnispec。
---
# sdd

## 用户输入

用户的功能需求描述，原文保存，后续透传：

```text
$ARGUMENTS
```

> **重要**: `$ARGUMENTS` 是用户的功能需求描述（如 "添加用户登录功能"），
> 本 skill 不消费、不修改此参数，仅在最后一步原样传递给 `routing`。
> 如果 `$ARGUMENTS` 为空，在路由转发前询问用户输入功能描述。
>
> 支持可选参数 `--workflow <express|standard|deep>`（或 `--workflow=<...>`），
> 用于显式指定 **workflow 模式**（见下文「workflow 与 agent」）。该参数由 `routing` 解析，本 skill 仅透传。

## 准备：

**SDD环境初始化**： 执行`bash ${CLAUDE_PLUGIN_ROOT}/scripts/bash/init_infra.sh ${CLAUDE_PLUGIN_ROOT} !`pwd` `
根据返回值进行处理：
- 0: 已经准备好了，继续后续步骤
- 1: 继续调用 `omnispec-constitution`技能，最后提交变更（".infra" 目录)，继续后续步骤
- 其他：执行失败，终止后续内容
---

## 步骤 1: 路由转发

如果 `$ARGUMENTS` 为空，使用 `AskUserQuestion` 询问用户：
"请输入您要开发的功能描述"

调用 `routing` 之前，先打印并写入上下文日志：

- `sdd 透传参数: <$ARGUMENTS>`

将 `$ARGUMENTS` 原样传递给 `routing`：

```txt
调用技能 `routing` "$ARGUMENTS"
```

## workflow 与 agent（重要）

- `express`、`standard`、`deep` 是 **workflow 模式标识**，在路由侧用于选择 **对应的 workflow agent**，**不是** skill 名称，也**不应**当作 skill 去调用。
- 三种模式与 **agent** 的对应关系为（agent 定义在 IDE 的 `agents/` 目录下，文件名示例）：
  - `express` → **`express-workflow`** agent
  - `standard` → **`standard-workflow`** agent
  - `deep` → **`deep-workflow`** agent
- 进入某一 workflow 后，由上述 **agent** 编排并驱动后续步骤；业务子步骤里再按需调用各类 **skill**，不要把整条 express/standard/deep 链路误理解为「调用名为 express 的 skill」。
- 与 **`skills/routing/SKILL.md`**、**`agents/complexity-analyzer.md`** 及 **`agents/express-workflow.md` / `standard-workflow.md` / `deep-workflow.md`** 中的「workflow 模式与 agent」约定一致，避免文档之间表述冲突。

## 关键规则

- 始终保持 `$ARGUMENTS` 原样透传到 `routing`
- 若用户携带 `--workflow`，当 `routing` 处于首次执行（无状态文件）或“从头开始”（删除状态文件）分支时使用该参数选择 **workflow agent**（不走复杂度判定）

## 用法说明

### `--workflow` 参数注释

- `--workflow` 可选值仅支持：`express`、`standard`、`deep`（均为 **workflow agent** 选择符，不是 skill）
- 支持两种写法：`--workflow deep` 和 `--workflow=deep`
- 当参数生效时，`routing` 将直接路由到对应的 **workflow agent** 执行，并跳过复杂度判定
- 若参数值非法，`routing` 需立即报错并提示可用取值
- 未传入 `--workflow` 时，保持原有动态判定行为（判定结果同样应映射到某一 **workflow agent**，而非 skill）

### 常用命令示例

```bash
/sdd 添加用户登录功能
/sdd 生成订单管理改造方案
/sdd 支持提供VPN服务化方案设计
/sdd --workflow deep 设计并实现多租户权限系统
/sdd --workflow=express 在 api/user.go 增加 GetProfile 接口
```

### `--workflow` 使用示例（含说明）

```bash
# 指定 deep：路由到 deep-workflow agent，适合跨模块、需架构分析的大改动
/sdd --workflow deep 设计并实现多租户权限系统

# 指定 standard：路由到 standard-workflow agent（完整流程 specify/clarify/design/tasks/analyze/implement）
/sdd --workflow standard 增加订单导出并补齐异常处理

# 指定 express：路由到 express-workflow agent，适合小改动、快速直达
/sdd --workflow=express 在 api/user.go 增加 GetProfile 接口

# 不指定 workflow：按现有规则自动判定
/sdd 优化用户登录体验并补充必要埋点
```
