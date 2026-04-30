# 阶段3：架构节点与页面匹配

<!-- reverse.icenter 阶段3：调用 relate_architecture_page.py 将架构节点与文档页面进行向量匹配 -->

## 职责

通过向量嵌入和余弦相似度，将架构节点（`architecture_flattened.json`）与已下载的文档页面进行语义匹配，输出每个架构节点对应的 Top-K 相关页面。本阶段**直接调用** `relate_architecture_page.py`。

## 前置条件

- `REPO_ROOT` 已设置
- 阶段1 已完成：`page_ids.json` 已存在
- 阶段2 已完成：`page/` 目录下已有页面文件
- `architecture_flattened.json` 已存在于 `{REPO_ROOT}/.cache/icenter/`
- 调用脚本时无需考虑鉴权，脚本已内置

## 执行步骤

### 0. [ ] 创建阶段3的子任务 Todo 列表

为确保阶段执行过程的透明化和可追踪性，创建阶段3的子任务 Todo 列表：

1. **步骤1 清理上一阶段的上下文，保证本阶段的上下文干净**
2. **步骤2 检查缓存状态，确定是否需要执行本阶段**
3. **步骤3 调用 relate_architecture_page.py 执行架构-页面匹配**
4. **步骤4 验证输出**

### 1. [ ] 清理上一阶段的上下文，保证本阶段的上下文干净

- **阶段开始时主动清空上下文**：执行上下文清理，明确说明「开始阶段3：架构节点与页面匹配。已清空上一阶段的上下文」
- **处理过程中及时清理**：完成每个分析步骤后，忘掉不必要的中间信息
- **输出精简化**：只输出必要结果，避免冗长的解释性文本

### 2. [ ] 检查缓存状态，确定是否需要执行本阶段

- 读取状态文件：`{REPO_ROOT}/.cache/icenter/.cache-status.json`
- 检查 `relate_architecture_page.confirmed` 字段
- 如果 `confirmed == true`：跳过阶段3，使用缓存结果（如 `architecture_doc_links/` 目录已存在且包含文件则视为可跳过）
- 如果 `confirmed == false` 或不存在：执行阶段3

### 3. [ ] 调用 relate_architecture_page.py 执行架构-页面匹配

**必须传入 `--repo-root`**，其值为已获取的 **REPO_ROOT**。

脚本执行流程：
1. 读取 `page_ids.json`，为每个页面提取内容摘要并生成向量嵌入
2. 读取 `architecture_flattened.json`，为每个架构节点生成向量嵌入
3. 通过余弦相似度计算，为每个架构节点找到 Top-K 最匹配的页面

- **Linux/macOS**：
  ```bash
  python3 ../references/scripts/relate_architecture_page.py --repo-root {REPO_ROOT}
  ```
- **Windows**：
  ```powershell
  python3 ..\references\scripts\relate_architecture_page.py --repo-root {REPO_ROOT}
  ```

### 4. [ ] 验证输出

- 确认 `{REPO_ROOT}/.cache/icenter/architecture_doc_links/` 目录已生成且包含架构节点匹配文件
- 检查目录内容：每个架构节点应有对应的JSON文件，包含 `name`（架构节点）和 `matches`
- 若脚本执行失败，用中文向用户报告错误并停止后续阶段

### 4.1 [ ] 更新缓存状态

- 读取状态文件：`{REPO_ROOT}/.cache/icenter/.cache-status.json`
- 更新 `relate_architecture_page` 部分：设置 `confirmed: true` 和当前时间戳
- 保存更新后的状态文件


## 输出

- `{REPO_ROOT}/.cache/icenter/architecture_doc_links/` 目录，包含每个架构节点的匹配结果JSON文件

## 依赖

- 阶段1（获取子页面 ID）
- 阶段2（下载文档到本地）

## 说明

- 本阶段调用脚本：`../references/scripts/relate_architecture_page.py`
- 依赖已存在的 `page_ids.json` 和 `page/` 目录下的页面文件
- 依赖已存在的 `architecture_flattened.json`（架构节点扁平化数据）
- 使用向量嵌入模型（Qwen3-Embedding-8B）进行语义匹配，API 鉴权已内置于脚本

