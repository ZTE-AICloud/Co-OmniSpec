# 路由转发

> 对应 SKILL.md 步骤 4

如果 `$ARGUMENTS` 为空，使用 `AskUserQuestion` 询问用户：
"请输入您要开发的功能描述"

## 展开 @ 文件引用

如果 `$ARGUMENTS` 包含 `@` 开头的文件引用（格式：`@路径/文件名`），先读取该文件内容，然后用文件内容替换引用。

处理规则：
1. 匹配 `$ARGUMENTS` 中所有 `@路径/文件名` 格式的引用
2. 使用 `Read` 工具读取每个引用对应的文件
3. 将 `$ARGUMENTS` 中的 `@路径/文件名` 替换为文件内容
4. 如果文件不存在或读取失败，报告错误并终止

> **示例**: `/sdd @doc/需求.md` → sdd 读取 `doc/需求.md` 内容后，将完整内容传递给 routing

## 调用 routing

调用 `routing` 之前，先打印并写入上下文日志：

- `sdd 透传参数: <$ARGUMENTS>`
- `sdd 向下游传递知识库路径: KNOWLEDGE_DIR=${KNOWLEDGE_DIR:-${CLAUDE_WORKING_DIR}/omni-doc}`（私域知识检索用，specify 阶段写入 `.runs/env.sh`）
- 若 `FEATURE_CONTEXT_PRESET=true`：额外打印 `sdd 向下游传递特性上下文: FEATURE_DIR=${FEATURE_DIR}, BRANCH_NAME=${BRANCH_NAME}, source=${PRESET_FEATURE_DIR:+cli}${PRESET_FEATURE_DIR:-env}`

将处理后的 `$ARGUMENTS` 传递给 `routing`（**功能描述原样透传**；特性目录/分支名由步骤 3 已赋值的会话变量承载，**不强制**写入 `$ARGUMENTS`）：

```txt
使用 Skill 工具调用 `routing` "$ARGUMENTS"
```

## 完成判据

- `$ARGUMENTS` 非空（空则已通过 AskUserQuestion 取得输入）
- 所有 `@` 文件引用已展开为文件内容（**禁止**重新生成或修改内容，仅替换引用）
- 透传日志已打印：`sdd 透传参数: <$ARGUMENTS>`
- `routing` 已通过 Skill 工具调用
