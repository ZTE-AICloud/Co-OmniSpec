# 深度逻辑架构反构核心规则

## 输出规则

1. 只生成以下核心文件：
   - `{REPO_ROOT}/omni-doc/on-demand/logic_architecture.md`
2. 可选状态文件：
   - `{REPO_ROOT}/omni-doc/on-demand/logic_architecture.cache-status.md`

## 执行规则

1. 必须通过子 Agent `deep-architecture-identifier` 执行识别。
2. 输出必须为 Markdown，且符合 `logic-architecture-template.md` 章节结构。
3. 若主产物缺失或为空，视为失败，不得进入后续阶段。
