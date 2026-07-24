# 逻辑架构产物校验（接口反构前置）

<!-- 阶段1：校验由 reverse-logic-architecture 产出的 architecture.json -->

## 职责

在接口扫描开始前，**确认**共享逻辑架构产物已存在且可用；本阶段**不生成**架构文件。

## 依赖路径说明

本阶段读取以下外部文件（由 OmniSpec 框架或 `reverse-logic-architecture` 技能生成）：

- `{REPO_ROOT}/omni-doc/specs/logic_architecture/architecture.json`：逻辑架构共享产物
- `{REPO_ROOT}/.cache/reverse/logic_architecture/.cache-status.json`：逻辑架构阶段缓存状态

## 执行流程

### 1. [x] 清理上一阶段的上下文

- 明确说明：「开始阶段1：逻辑架构产物校验。已清空上一阶段的上下文」

### 2. [ ] 校验架构产物路径

- **必读文件**：`{REPO_ROOT}/omni-doc/specs/logic_architecture/architecture.json`
- 校验项：
  - 文件存在且非空
  - 内容为合法 JSON
  - 建议至少包含下列之一（用于判断分析已完成）：`layers`、`key_modules`、`summary`、`architecture_patterns`

### 3. [ ] 失败处理

- 若校验失败：使用**中文**提示用户先执行逻辑架构反构，例如：
  - `reverse --target logic_architecture --path <扫描范围>`
  - 或在全流程中确保编排已先调用 `reverse-logic-architecture`
- **中止**接口反构后续阶段，直至产物可用

### 4. [ ] 成功处理

- 可将架构摘要（非全量 JSON）保留在上下文中，供阶段2（Few-shot）与阶段3（清单扫描）使用
- **禁止**在本阶段调用 `architecture-identifier` 或写入 `architecture.json`

## 与缓存状态的关系

- 接口反构缓存文件 `{REPO_ROOT}/.cache/reverse/interfaces/.cache-status.json`**不包含** `architecture_identification` 段落的维护义务；架构确认状态由 `.cache/reverse/logic_architecture/.cache-status.json` 管理。

## 注意事项

- **`--target all`（全自动）**：因编排保证逻辑架构阶段已先执行，本阶段仍须做存在性与 JSON 合法性检查；失败则中止并报告。
- 旧路径 `.cache/reverse/interfaces/architecture.json` **已废弃**，不得作为读取来源。
