# 阶段1：获取子页面 ID

<!-- reverse.icenter 阶段1：直接调用 fetch_page_ids.py -->

## 职责

从 iCenter 获取所有子页面 ID，写入 `page_ids.json`。本阶段**直接调用** `fetch_page_ids.py`。

## 前置条件

- `REPO_ROOT` 已设置
- 已执行阶段0（执行前检查）
- 调用脚本时无需考虑鉴权，脚本已内置

## 执行步骤

### 0. [ ] 创建阶段1的子任务 Todo 列表

为确保阶段执行过程的透明化和可追踪性，创建阶段1的子任务 Todo 列表：

1. **步骤1 清理上一阶段的上下文，保证本阶段的上下文干净**
2. **步骤2 检查缓存状态，确定是否需要执行本阶段**
3. **步骤3 确认 REPO_ROOT 并准备调用参数**
4. **步骤4 调用 fetch_page_ids.py 获取所有子页面 ID**
5. **步骤5 验证输出**

### 1. [ ] 清理上一阶段的上下文，保证本阶段的上下文干净

- **阶段开始时主动清空上下文**：执行上下文清理，明确说明「开始阶段1：获取子页面 ID。已清空上一阶段的上下文」
- **处理过程中及时清理**：完成每个分析步骤后，忘掉不必要的中间信息
- **输出精简化**：只输出必要结果，避免冗长的解释性文本

### 2. [ ] 检查缓存状态，确定是否需要执行本阶段

- 读取状态文件：`{REPO_ROOT}/.cache/icenter/.cache-status.json`
- 检查 `fetch_page_ids.confirmed` 字段
- 如果 `confirmed == true`：跳过阶段1，使用缓存结果（如 `page_ids.json` 已存在则视为可跳过）
- 如果 `confirmed == false` 或不存在：执行阶段1

### 3. [ ] 确认 REPO_ROOT 并准备调用参数

- 使用阶段0或 check-prerequisites 输出中的 **REPO_ROOT**（绝对路径）。
- **调用 fetch_page_ids.py 时若不传 `--repo-root`，脚本会报错退出。** 下方命令中的 `{REPO_ROOT}` 必须替换为实际值，且 **`--repo-root` 参数不可省略**。
- `--page-root` 参数的取值来源于 `reverse-icenter`/`reverse --source icenter` 统一解析得到的用户输入：  
  - 在总命令中，用户通过 `--page-root <icenter_root_url1,icenter_root_url2,...>` 传入；  
  - 解析后保存为变量 `ICENTER_ROOT_URLS`，本阶段**直接使用该变量值**，无需再次向用户询问或手工修改命令。

### 4. [ ] 调用 fetch_page_ids.py 获取所有子页面 ID

**必须传入**：
- `--repo-root`，其值为已获取的 **REPO_ROOT**（与脚本路径中的 `{REPO_ROOT}` 一致）；
- `--page-root`，其值为前面统一解析得到的 `ICENTER_ROOT_URLS`（即用户在顶层命令中输入的 `--page-root` 原始字符串）。

- **Linux/macOS**（将 `{REPO_ROOT}` 替换为实际仓库根目录，将 `{ICENTER_ROOT_URLS}` 替换为实际 URL 列表）：
  ```bash
  python ../references/scripts/fetch_page_ids.py \
    --repo-root {REPO_ROOT} \
    --page-root "{ICENTER_ROOT_URLS}"
  ```
- **Windows**（将 `{REPO_ROOT}` 替换为实际仓库根目录，将 `{ICENTER_ROOT_URLS}` 替换为实际 URL 列表；注意 PowerShell 中路径用反斜杠）：
  ```powershell
  python ..\references\scripts\fetch_page_ids.py `
    --repo-root {REPO_ROOT} `
    --page-root "{ICENTER_ROOT_URLS}"
  ```

### 5. [ ] 验证输出

- 确认 `{REPO_ROOT}/.cache/icenter/page_ids.json`
- 若脚本执行失败，用中文向用户报告错误并停止后续阶段

### 5.1 [ ] 更新缓存状态

- 读取状态文件：`{REPO_ROOT}/.cache/icenter/.cache-status.json`
- 更新 `fetch_page_ids` 部分：设置 `confirmed: true` 和当前时间戳
- 保存更新后的状态文件

## 输出

- `{REPO_ROOT}/.cache/icenter/page_ids.json`

## 说明

- 本阶段调用脚本：
  - `../references/scripts/fetch_page_ids.py`
- 根页面列表由用户在顶层命令中通过 `--page-root` 传入，并在阶段 0/总控制流中解析为 `ICENTER_ROOT_URLS` 后传递给脚本，**不再依赖脚本内部默认根页面列表**。
- **常见错误**：
  - 调用时漏传 `--repo-root` 会导致脚本报错（该参数为必填）。务必使用「步骤 3」中的 REPO_ROOT 代入命令；
  - 未在顶层命令中提供 `--page-root`，或未将解析后的 `ICENTER_ROOT_URLS` 传递给本阶段命令，会触发脚本中对 `--page-root` 的参数校验错误。

