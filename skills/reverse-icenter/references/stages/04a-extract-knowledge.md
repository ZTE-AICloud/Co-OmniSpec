# 阶段4：提取知识（需求 / 场景）

根据传入的`{target}`参数类型，读取 `.cache/icenter/architecture_doc_links/`（架构节点-页面匹配关系分文件目录），按分文件逐个提取{target}要素，最后提取的要素保存到本地。

## 一、目标与产出

| 项目 | 说明 |
|------|------|
| **输入** | `{architecture_doc_links_dir}`（架构节点-页面匹配关系分文件目录） |
| **核心产出** | `{REPO_ROOT}/{OUT_DIR}/` 下按架构节点对应的 `{节点名}.md` |
| **中间产出** | `{extract_progress_path}` |

## 二、关键约束

- **只能用项目提供的脚本，禁止自己生成脚本**
- **除了要求的目录，不允许写别的文件**
- **进度驱动**：仅以 `{extract_progress_path}` 为数据源，完成即标 `[X]`
- **并行发起**：步骤5必须在**同一条消息**中同时批量发起最多 subagents，确保真正并行执行
- **禁止串行**：严禁逐个等待 subagents 返回结果的串行执行方式
- **输出路径**：`{REPO_ROOT}/{OUT_DIR}/{主名}.md`
- **只有当步骤5所有进度结束后，才能往下执行**

## 三、变量定义

执行前统一约定以下变量，后文仅引用变量名，不重复写具体路径。**其中 `{target}` 由上级命令（reverse-icenter 或 reverse）传入。**

| 变量名 | 含义 | 示例值 / 取值规则 |
|--------|------|-------------------|
| `{REPO_ROOT}` | 仓库根目录（由环境/前置步骤提供） | - |
| `{target}` | 本阶段提取目标类型（由上级命令传入） | 可选项 `requirements`、`scenarios` |
| `{CACHE_ICENTER}` | iCenter 缓存根目录 | `.cache/icenter` |
| `{architecture_doc_links_dir}` | 架构节点-页面匹配关系分文件目录（阶段3产出） | `{CACHE_ICENTER}/architecture_doc_links/` |
| `{extract_progress_path}` | 知识提取进度（根据 `{target}` 选择） | `{CACHE_ICENTER}/{target}_extract_progress.md` |
| `{EXTRACTOR_AGENT}` | 本阶段调用的 subAgent 名称（根据 `{target}` 选择） | `{target}-knowledge-extractor`，位置在`.claude/agents/`目录下 |
| `{OUT_DIR}` | 知识提取结果输出目录（根据 `{target}` 选择） | `omni-doc/specs/{target}`|

**说明**：命令中涉及路径时，使用 `{REPO_ROOT}/{变量名}` 得到路径（Windows 下将 `/` 换为 `\`）。阶段开始时主 Agent 必须根据上级命令解析得到 `{target}`，并据此确定 `{extract_progress_path}`、`{EXTRACTOR_AGENT}` 与 `{OUT_DIR}`。本阶段读取 `{architecture_doc_links_dir}` 目录下的文件名来生成待处理列表，并将“文件名/路径”传给 subAgent，由 subAgent 自行读取并解析该 JSON 分文件（其中包含架构节点对象与 `matches` 列表，`matches` 每项含 `page_id`（二元数组 `[space_id, page_id]`））。

## 四、执行步骤

### 0. [ ] 创建阶段4的各步骤的 todos

为确保阶段执行过程的透明化和可追踪性，创建阶段4各步骤 todos：

1. **步骤1 清理上一阶段的上下文，保证本阶段的上下文干净**
2. **步骤2 检查缓存状态与前置条件检查**
3. **步骤3 前置条件检查与路径准备**
4. **步骤4 列出待处理分组文件，写入/更新本地进度文件**
5. **步骤5 同时启动多个 subagents 进行知识提取**
6. **步骤6 循环结果检查**
7. **步骤7 收集 subAgent 结果并验证输出**
8. **步骤8 验证最终输出**
9. **步骤9 更新缓存状态**

### 1. [ ] 清理上一阶段的上下文，保证本阶段的上下文干净

- **阶段开始时主动清空上下文**：执行上下文清理，明确说明"开始阶段4：提取知识（目标={target}）。已清空上一阶段的上下文"
- **处理过程中及时清理**：完成每个分析步骤后，忘掉不必要的中间信息
- **输出精简化**：只输出必要结果，避免冗长的解释性文本

### 2. [ ] 检查缓存状态与前置条件检查

- 读取 `{REPO_ROOT}/.cache/icenter/.cache-status.json`
- 检查 `extract_{target}.confirmed` 字段
- 如果 `confirmed == true`：跳过本阶段
- 确认 `{REPO_ROOT}` 已设置
- 确认阶段1、2、3已完成：`page_ids.json`、`page/*.md` 已存在，且 `{architecture_doc_links_dir}` 已生成且目录下存在 `*.json` 分文件
- 校验路径并创建 `{OUT_DIR}`

### 3. [ ] 前置条件检查与路径准备

- 确认 `{REPO_ROOT}` 已设置，获取并归一化 `{REPO_ROOT}`
- 确认阶段1、2、3已完成：`{REPO_ROOT}/{CACHE_ICENTER}/page/*.md` 存在，`{REPO_ROOT}/{architecture_doc_links_dir}` 存在且目录下存在 `*.json` 分文件
- 校验并记录「变量定义」表中的路径变量，含 `{architecture_doc_links_dir}`、`{extract_progress_path}`、`{OUT_DIR}`、`{EXTRACTOR_AGENT}`

### 4. [ ] 列出待处理分组文件，写入/更新本地进度文件 `{extract_progress_path}`

目标：用本地文件 `{REPO_ROOT}/{extract_progress_path}` 持久化管理"待处理列表 + 进度"，避免依赖内存清单或 TODO 列表。

- 列出 `{REPO_ROOT}/{architecture_doc_links_dir}` 目录下的所有 `*.json` 文件，得到"待处理分组文件列表"
- 按文件名稳定排序（如字母序），得到"待处理列表"
- 生成/更新 `{REPO_ROOT}/{extract_progress_path}`，格式为 markdown checklist，使用 `- [ ]` / `- [X]` 标记：
  - 文件第一行写标题：`# extract progress`
  - 其后为 checklist，每项与一个 `*.json` 文件一一对应，每项内容为`{architecture_doc_links_dir}/{文件名}`
  - 若 `{extract_progress_path}` 已存在：对仍存在的文件名，尽量保留其既有 `[X]` 状态；对新出现文件追加为 `[ ]`
- 记录总节点数 Y，用于后续进度汇报（如"已完成 X/Y"）

### 5. [ ] 并行调用多个 subagents 进行知识提取

**执行流程**：
1. 读取 `{extract_progress_path}`，找出前 5 个为 `[ ]` 的分文件文件名
2. **关键：一条消息中同时批量发起所有 subagents (同时最多5个)**
   - 构建一个包含所有Task同时调用的消息
   - 每个Task调用使用相同的subagents_type="{EXTRACTOR_AGENT}"
   - 每个Task调用传递不同的参数（`{repo_root}`, `{architecture_doc_link_filename}`, `{output_file_path}`）
      **subagents 调用参数**：
      - `repo_root`：`{REPO_ROOT}`
      - `architecture_doc_link_filename`：文件名
      - `output_file_path`：`{REPO_ROOT}/{OUT_DIR}/{Prefix}-{主名}.md`
       - `Prefix`根据`{target}`来决定，如果是requirements，那么为`REQ`，如果是scenarios，那么为`SCN`
       - `主名` 建议由 subAgent 从分文件内容中的架构节点 `name` 推导得到
   - **严禁**逐个发起Task调用并等待返回结果
   - **必须确保**所有Task调用在同一时间点发起，以实现真正的并行执行
   - **关键实现**：必须使用单个多工具调用消息，包含所有Task调用，确保它们同时启动
   - **Claude执行要求**：必须在同一个消息中同时发起所有Task调用，不能分别发送多个消息或在循环中逐一发起
3. 等待所有 subagents 返回结果（使用异步等待机制）
4. 根据返回结果更新进度文件：
   - 成功：`{"ok": true, "file": "{文件名}", "count": 12}` → 标为 `[X]`
   - 失败：`{"ok": false, "file": "{文件名}", "error": "错误信息"}` → 保持 `[ ]`
5. 执行上下文压缩（`/compact`）
6. 重复直到所有条目均为 `[X]`



### 6. [ ] 完成条件检查

- 读取 `{extract_progress_path}`：若存在 `[ ]`，返回步骤 5，直到所有checklist均已完成才可进入下一步。
- 列出 `{architecture_doc_links_dir}` 目录下所有 `*.json` 分文件与 `{OUT_DIR}` 下所有输出文件
- 一致性校验：每个架构节点均有对应输出文件

### 7. [ ] 收集 subAgent 结果并验证输出

- 对每个在 `{extract_progress_path}` 中已标记为 `[X]` 的条目（每条目为架构节点名称），检查对应输出是否存在且非空：
  - 路径：`{REPO_ROOT}/{OUT_DIR}/{节点名}.md`，如采用多批写入则应检查同一文件是否已按预期被追加更新
- 若有失败或缺失，记录并可选重试或向用户报告

### 8. [ ] 产出校验

- 确认 `{REPO_ROOT}/{OUT_DIR}/` 下已生成与架构节点对应的文档 `{节点名}.md`
- 若任一步骤执行失败，用中文向用户报告错误

### 9. [ ] 更新缓存状态

- 读取 `{REPO_ROOT}/.cache/icenter/.cache-status.json`
- 更新 `extract_{target}` 部分：设置 `confirmed: true` 和当前时间戳
- 保存更新后的状态文件

### 异步进度更新

- 哪个 subAgent 先完成就先更新其进度
- 不要等待所有 subagents 完成后再统一更新
- 使用原子操作确保进度文件写入安全

### 并行执行保障

- **同时发起**：所有 subagents 必须在同一消息中同时发起，确保并行执行
- **异步收集**：使用异步机制收集所有 subagents 的结果，避免阻塞
- **禁止串行**：严禁任何形式的逐个发起和等待
- **资源利用**：充分利用系统并行能力，提高执行效率
- **执行验证**：执行完成后必须验证所有subagents确实是并行执行的，而非串行执行

**并行执行验证方法**：
- 检查各subagents的启动时间应基本相同（时间差应在毫秒级）
- 检查各subagents的执行日志时间戳，确认没有明显的先后顺序
- 总执行时间应接近单个subAgent的执行时间，而非所有subagents执行时间之和

**强制要求**：
1. 所有Task调用必须在同一个消息中发出（关键：必须是单个消息，不是多个连续消息）
2. 不允许有任何等待或延迟操作（所有Task调用必须同时发起）
3. 必须使用异步方式收集所有结果（不能阻塞等待单个Task完成）
4. 严禁逐个执行Task调用（不能循环逐一发起Task调用）
5. Task调用必须使用并行模式，确保多个subagents能同时运行
6. 必须在发起Task调用前准备好所有参数，避免在调用过程中产生额外延迟
7. 必须验证Task调用确实实现了并行执行，而非串行执行

## 五、输出

1. **按架构节点的知识提取结果**：`{REPO_ROOT}/{OUT_DIR}/` 下与 `{architecture_doc_links_dir}` 中 `*.json` 分文件对应的 `{主名}.md`（由本阶段选定的 **{EXTRACTOR_AGENT}** subAgent 直接生成）。

## 六、依赖关系

- 阶段1（获取子页面 ID）、阶段2（下载文档到本地）、阶段3（架构节点与页面匹配，生成 `.cache/icenter/architecture_doc_links/` 分文件目录）

