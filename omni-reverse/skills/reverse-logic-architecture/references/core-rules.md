# 逻辑架构反构核心规则

## 输出目录

- 规格产物必须写入：`{REPO_ROOT}/omni-doc/specs/logic_architecture/`
- 仅将**机器可读状态**放在：`.cache/reverse/logic_architecture/`

## 执行约束

1. 子 Agent `architecture-identifier` 调用时 **`target_type` 必须为 `logic_architecture`**
2. 禁止将 `architecture.json` 写入 `.cache/reverse/interfaces/`
3. 写入前校验 JSON 可解析；写入后验证文件非空

## 阶段文件

- 阶段说明位于本 Skill 内 `references/stages/`
