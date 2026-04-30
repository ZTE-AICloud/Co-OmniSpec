# 深度架构识别（深度逻辑架构要素）

## 职责

执行深度架构识别，生成 Markdown 报告 `logic_architecture.md`。

## 执行流程

1. 检查缓存命中：
   - 若 `{REPO_ROOT}/omni-doc/on-demand/logic_architecture.md` 已存在且可读，允许直接复用。
2. 缓存未命中时，调用子 Agent：
   - 使用 `Task` 工具启动 `deep-architecture-identifier`
   - 传入 `repo_root`（绝对路径）
3. 结果校验：
   - 验证 `logic_architecture.md` 已生成且非空
   - 验证 `logic_architecture.cache-status.md` 可读（若存在）
4. 展示摘要并确认（交互模式）/自动确认（非交互模式）

## 输出

- 主产物：`{REPO_ROOT}/omni-doc/on-demand/logic_architecture.md`
- 状态文件：`{REPO_ROOT}/omni-doc/on-demand/logic_architecture.cache-status.md`（可选）
