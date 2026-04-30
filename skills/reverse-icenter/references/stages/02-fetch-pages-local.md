# 阶段2：下载文档到本地

<!-- reverse.icenter 阶段2：直接调用 fetch_pages_local.py -->

## 职责

根据 `page_ids.json` 将 iCenter 页面拉取到本地 `page/` 目录。本阶段**直接调用** `fetch_pages_local.py`。

## 前置条件

- `REPO_ROOT` 已设置
- 阶段1 已完成：`page_ids.json` 已存在
- 调用脚本时无需考虑鉴权，脚本已内置

## 执行步骤

### 0. [ ] 创建阶段2的子任务 Todo 列表

为确保阶段执行过程的透明化和可追踪性，创建阶段2的子任务 Todo 列表：

1. **步骤1 清理上一阶段的上下文，保证本阶段的上下文干净**
2. **步骤2 检查缓存状态，确定是否需要执行本阶段**
3. **步骤3 调用 fetch_pages_local.py 拉取页面到本地**
4. **步骤4 验证输出**

### 1. [ ] 清理上一阶段的上下文，保证本阶段的上下文干净

- **阶段开始时主动清空上下文**：执行上下文清理，明确说明「开始阶段2：下载文档到本地。已清空上一阶段的上下文」
- **处理过程中及时清理**：完成每个分析步骤后，忘掉不必要的中间信息
- **输出精简化**：只输出必要结果，避免冗长的解释性文本

### 2. [ ] 检查缓存状态，确定是否需要执行本阶段

- 读取状态文件：`{REPO_ROOT}/.cache/icenter/.cache-status.json`
- 检查 `fetch_pages_local.confirmed` 字段
- 如果 `confirmed == true`：跳过阶段2，使用缓存结果（如 `page/` 下已有页面文件则视为可跳过）
- 如果 `confirmed == false` 或不存在：执行阶段2

### 3. [ ] 调用 fetch_pages_local.py 拉取页面到本地

**必须传入 `--repo-root`**，其值为已获取的 **REPO_ROOT**。

- **Linux/macOS**：
  ```bash
  python3 ../references/scripts/fetch_pages_local.py \
    --repo-root {REPO_ROOT}
  ```
- **Windows**：
  ```powershell
  python3 ..\references\scripts\fetch_pages_local.py --repo-root {REPO_ROOT}
  ```

脚本固定读取 `{REPO_ROOT}/.cache/icenter/page_ids.json`。

### 4. [ ] 验证输出

- 确认 `{REPO_ROOT}/.cache/icenter/page/` 下已生成若干 `{space_id}-{page_id}.md` 文件
- 若脚本执行失败，用中文向用户报告错误并停止后续阶段

### 4.1 [ ] 更新缓存状态

- 读取状态文件：`{REPO_ROOT}/.cache/icenter/.cache-status.json`
- 更新 `fetch_pages_local` 部分：设置 `confirmed: true` 和当前时间戳
- 保存更新后的状态文件


## 输出

- `{REPO_ROOT}/.cache/icenter/page/{space_id}-{page_id}.md`

## 依赖

- 阶段1（获取子页面 ID）

## 说明

- 本阶段调用脚本：`../references/scripts/fetch_pages_local.py`
- 依赖已存在的 `page_ids.json`

