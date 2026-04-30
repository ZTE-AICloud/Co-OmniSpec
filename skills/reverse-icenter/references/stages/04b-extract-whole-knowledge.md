# 阶段4b：提取整体知识（系统上下文 / 逻辑架构）

根据传入的`{target}`参数类型，读取 `{related_page_ids}`（整体页面数据），提取{target}要素并保存到本地。

## 一、目标与产出

| 项目 | 说明 |
|------|------|
| **核心产出** | `{REPO_ROOT}/{OUT_DIR}/{target}.md` |
| **中间产出** | 无需进度文件，一次性处理 |

## 二、关键约束

- **只能用项目提供的脚本，禁止自己生成脚本**
- **除了要求的目录，不允许写别的文件**
- **输出路径**：`{REPO_ROOT}/{OUT_DIR}/{target}.md`
- **直接执行**：调用 subAgent 完成整个提取任务，subAgent 自行读取所需文件

## 三、变量定义

执行前统一约定以下变量，后文仅引用变量名，不重复写具体路径。**其中 `{target}` 由上级命令（reverse-icenter 或 reverse）传入。**

| 变量名 | 含义 | 示例值 / 取值规则 |
|--------|------|-------------------|
| `{REPO_ROOT}` | 仓库根目录（由环境/前置步骤提供） | - |
| `{target}` | 本阶段提取目标类型（由上级命令传入） | 可选项 `system-contexts`、`logical-architectures` |
| `{CACHE_ICENTER}` | iCenter 缓存根目录 | `.cache/icenter` |
| `{related_page_ids}` | 代码库相关文件 | `{CACHE_ICENTER}/related_page_ids.json` |
| `{EXTRACTOR_AGENT}` | 本阶段调用的 subAgent 名称（根据 `{target}` 选择） | `{target}-knowledge-extractor`，位置在`.claude/agents/`目录下 |
| `{OUT_DIR}` | 知识提取结果输出目录（根据 `{target}` 选择） | `omni-doc/specs/{target}`|

**说明**：命令中涉及路径时，使用 `{REPO_ROOT}/{变量名}` 得到路径（Windows 下将 `/` 换为 `\`）。阶段开始时主 Agent 必须根据上级命令解析得到 `{target}`，并据此确定 `{EXTRACTOR_AGENT}` 与 `{OUT_DIR}`。本阶段直接调用 subAgent，subAgent 自行读取 `{related_page_ids}` 和 `architecture_flattened.json` 文件并解析处理。

## 四、执行步骤

### 0. [ ] 创建阶段4b的各步骤的 todos

为确保阶段执行过程的透明化和可追踪性，创建阶段4b各步骤 todos：

1. **步骤1 清理上一阶段的上下文，保证本阶段的上下文干净**
2. **步骤2 检查缓存状态与前置条件检查**
3. **步骤3 前置条件检查与路径准备**
4. **步骤4 调用 subAgent 进行整体知识提取**
5. **步骤5 验证输出结果**
6. **步骤6 更新缓存状态**

### 1. [ ] 清理上一阶段的上下文，保证本阶段的上下文干净

- **阶段开始时主动清空上下文**：执行上下文清理，明确说明"开始阶段4b：提取整体知识（目标={target}）。已清空上一阶段的上下文，subAgent将自行读取所需文件"
- **处理过程中及时清理**：完成每个分析步骤后，忘掉不必要的中间信息
- **输出精简化**：只输出必要结果，避免冗长的解释性文本

### 2. [ ] 检查缓存状态与前置条件检查

- 读取 `{REPO_ROOT}/.cache/icenter/.cache-status.json`
- 检查 `extract_{target}.confirmed` 字段
- 如果 `confirmed == true`：跳过本阶段
- 确认 `{REPO_ROOT}` 已设置
- 确认阶段1、2已完成：`page_ids.json` 已存在，且 `{related_page_ids}` 文件已生成
- 确认架构扁平化文件已生成：`architecture_flattened.json` 文件存在
- 校验路径并创建 `{OUT_DIR}`

### 3. [ ] 前置条件检查与路径准备

- 确认 `{REPO_ROOT}` 已设置，获取并归一化 `{REPO_ROOT}`
- 确认阶段1、2已完成：`{REPO_ROOT}/{related_page_ids}` 文件存在
- 确认架构扁平化文件存在：`{REPO_ROOT}/.cache/icenter/architecture_flattened.json` 文件存在
- 校验并记录「变量定义」表中的路径变量，含 `{related_page_ids}`、`{OUT_DIR}`、`{EXTRACTOR_AGENT}`
- 准备 subAgent 自行读取文件的路径信息

### 4. [ ] 调用 subAgent 进行整体知识提取（subAgent自行读取文件）

**执行流程**：
1. 直接调用 subAgent 处理整体知识提取任务
2. subAgent 调用使用 `subagents_type="{EXTRACTOR_AGENT}"`
3. subAgent 自行读取所需文件：
   - `{REPO_ROOT}/{related_page_ids}`（整体页面数据）
   - `{REPO_ROOT}/.cache/icenter/architecture_flattened.json`（架构扁平化数据）
4. 等待 subAgent 返回结果
5. 根据返回结果验证处理结果：
   - 成功：`{"ok": true, "output_file": "{output_file_path}", "count": 12}`
   - 失败：`{"ok": false, "error": "错误信息"}`

**subAgent 调用参数**：
- 无需传递参数，subAgent 自行读取所需文件路径

### 5. [ ] 验证输出结果

- 检查输出文件是否存在且非空：
  - 路径：`{REPO_ROOT}/{OUT_DIR}/{target}.md`
- 验证 subAgent 确实自行读取了所需文件
- 若有失败或缺失，记录并可选重试或向用户报告

### 6. [ ] 更新缓存状态

- 读取 `{REPO_ROOT}/.cache/icenter/.cache-status.json`
- 更新 `extract_{target}` 部分：设置 `confirmed: true` 和当前时间戳
- 记录 subAgent 自行读取文件的完成状态
- 保存更新后的状态文件

## 五、输出

1. **整体知识提取结果**：`{REPO_ROOT}/{OUT_DIR}/{target}.md`（由本阶段选定的 **{EXTRACTOR_AGENT}** subAgent 自行读取文件并直接生成）。

## 六、依赖关系

- 阶段1（获取子页面 ID）、阶段2（下载文档到本地，生成 `{related_page_ids}` 文件）
- 架构扁平化文件（`.cache/icenter/architecture_flattened.json`）