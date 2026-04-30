---
description: 需求反构的数据交换与路径规范
parent: reverse-requirements
target: requirements
---

## 路径与输出约定

### 目录与路径排除

- **`--path`**：未指定时默认为仓库根 `.`。
- **`--exclude`**：可多次使用，命中模式的文件/目录不参与发现或列举。
- **默认排除（用于“扫描源码/发现输入文件”）**（与主命令一致）：
  - **所有隐藏目录**：以 `.` 开头的目录（如 `.git/`、`.idea/`、`.vscode/`、`.cache/` 等）。
  - **omni-doc**：`omni-doc/`（仅用于扫描源码时排除）。
- 当从仓库中**搜索**场景文档（`SCN-XXX-*.md`）时：应用 `--path`（默认仓库根）、`--exclude`；默认排除隐藏目录与 `omni-doc/`，**不排除** `.cache/`，以便发现 `.cache/reverse/scenarios/scenario-details/` 下的文件。
- **重要**：internal 产物写入 `.cache/reverse/requirements/internal/`；独立需求文件仍写入 `omni-doc/specs/requirements/`。

### 缓存目录

- 默认：`{REPO_ROOT}/.cache/reverse/requirements/`
- 状态文件：`{REPO_ROOT}/.cache/reverse/requirements/.cache-status.json`
- 变量名：`REQUIREMENTS_CACHE_DIR`、`REQUIREMENTS_STATUS_FILE`

### 输入来源（阶段1）——在工程根目录下搜索场景文档

- **输入获取方式**：在工程根目录（或 `--path` 指定范围）下**搜索**命名形如 `SCN-XXX-场景名称.md` 的文档（例如 `SCN-013-建立实体关系.md`）。
  - 匹配模式：`SCN-*-*.md`（即 `SCN-` 前缀 + 编号/标识 + `-` + 名称 + `.md`）。
  - 搜索时应用 `--exclude` 与默认排除（隐藏目录、`omni-doc/`）；**不排除** `.cache/`，因此 `.cache/reverse/scenarios/scenario-details/` 下的文件会被纳入。
  - 不依赖固定目录或 scenario-list.json；凡命中命名规则的文档均作为输入。
- **单文件命名示例**：`SCN-001-创建端口.md`、`SCN-013-建立实体关系.md`。

#### 场景文档格式（`SCN-XXX-*.md`）

- **文件头部 YAML front matter**：

```yaml
---
id: SCN-001
name: SCN-001-创建端口
brief: 用户通过REST API创建新的网络端口
description: <场景的简要说明>
---
```

- **正文为 Markdown 场景说明**（示例章节）：
  - `# 场景: SCN-001-创建端口`
  - `## 业务背景`
  - `## 触发条件`
  - `## 主要参与者`
  - `## 预期结果`
  - `## 交互流程`（可包含 PlantUML 时序图）
  - `## 关键步骤说明`（以及后续子章节）

阶段1 以**搜索到的全部 SCN-XXX-*.md** 为输入，做场景归类与 EARS 需求抽取。

### 中间产物（阶段1 输出）——internal 放在 .cache/reverse/requirements 下

- **internal 目录**：`{REPO_ROOT}/.cache/reverse/requirements/internal/`
- **需求设计文档**：`{REPO_ROOT}/.cache/reverse/requirements/internal/需求设计.md`
- 阶段1 仅填写或更新该文档中的 **功能需求** 章节

### 阶段2 输入

- **需求设计文档**：`{REPO_ROOT}/.cache/reverse/requirements/internal/需求设计.md`（若不存在可回退到同目录下 `设计文档.md` 等功能需求章节）

### 阶段2 输出目录与命名

- **输出目录**：`{REPO_ROOT}/omni-doc/specs/requirements/`
- **变量名**：`REQUIREMENTS_OUTPUT_DIR`
- **文件命名格式**：`{ID_PREFIX}-{NNN}-{需求简述}.md`
  - `ID_PREFIX`：项目约定，如 `REQ` 或 `INTENT`（与现有 `omni-doc/specs/requirements` 一致）
  - `NNN`：三位数字，从 001 起连续
  - `需求简述`：中文简短描述，建议不超过 20 字，无标点
- **示例**：`REQ-001-计费管理-话单计费.md`、`INTENT-001-模型管理.md`

### 单需求文件内容格式

**模板来源**：单需求文件的格式**不在此处定义**，生成时从 **`.infra/metamodel/1.requirement-template.md`** 读取并按其结构填充。

- 执行需求拆分（阶段2）时，Agent 须先读取该模板文件，再按模板中的 frontmatter 字段与正文结构，将每条需求的 id、name、type、description 及 EARS 内容填入后写出。
- 文件名与 id/name 的对应关系：`{ID_PREFIX}-{NNN}-需求简述.md` 对应 frontmatter 中的 `id: {ID_PREFIX}-{NNN}`、`name: {ID_PREFIX}-{NNN}-需求简述`。

### 状态文件结构（.cache-status.json）

```jsonc
{
  "requirement_analysis": {
    "confirmed": false,
    "progress": "pending",
    "timestamp": null
  },
  "requirement_split": {
    "confirmed": false,
    "progress": "pending",
    "timestamp": null
  }
}
```

- `confirmed`：用户已确认或自动化模式下阶段完成
- `progress`：`pending` | `progressing` | `completed`
- `timestamp`：ISO8601

### 成功标记（可选）

阶段2 全部完成后可创建：`{REPO_ROOT}/.cache/reverse/requirements/internal/requirement_split_success.flag`，用于流水线或后续步骤判断。
