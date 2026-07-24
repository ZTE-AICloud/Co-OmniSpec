# 阶段1：导入模式与扫描

<!-- 阶段1：根据语言通过大模型识别外部导入方式，扫描并分类 -->

## 职责

1. 识别代码库主要语言（及多语言时的主次）。
2. **通过大模型方式**归纳该语言（或各语言）的“导入/引用”语法，区分如何判断“系统 / 本库 / 外部”。
3. 扫描仓库内目标路径下的源文件，提取所有导入/引用。
4. 对每条导入进行分类：**系统**、**本代码库**、**外部**。
5. 输出结构化清单供阶段2 使用。

## 执行流程

### 0. [ ] 创建阶段1 的 Todo 子项

1. 清理上一阶段上下文（如有）
2. 检查缓存：若 `import_scan.confirmed == true` 且 `import-list.json` 存在，可跳过阶段1
3. 获取 REPO_ROOT（如调用 check-prerequisites）
4. 识别代码库主要语言
5. 用大模型归纳导入方式并区分系统/本库/外部
6. 扫描源文件并提取导入
7. 对每条导入分类（系统 / 本库 / 外部）
8. 保存 `import-list.json` 并更新缓存状态
9. 展示统计并（可选）请用户确认

**等式验收**：
- 步骤 8 完成后：`imports` 数组长度 == 步骤 6 提取的原始导入总数
- 步骤 8 完成后：`stats.total == stats.system + stats.local + stats.external`
- 步骤 9 对话模式确认后：`import_scan.confirmed == true`

### 1. 清理上下文

- 阶段开始时说明：“开始阶段1：导入模式与扫描。已清空上一阶段上下文。”
- 只保留本阶段必要输入与输出，避免冗长中间结果占用上下文。

### 2. 检查缓存

- 读取 `{REPO_ROOT}/.cache/reverse/external-interfaces/.cache-status.json`
- 若 `import_scan.confirmed == true` 且存在 `import-list.json` 且**本次未请求重录**（未显式使用 `--clear-cache` 且用户未在对话中要求重新执行）：跳过阶段1，直接使用该文件进入阶段2
- 若为 `false` 或不存在，或本次明确请求重录：执行阶段1，并覆盖旧的 `import-list.json`

### 3. 获取 REPO_ROOT 与解析参数

- Linux/macOS：调用 `check-prerequisites.sh --paths-only --json`
- Windows：调用 `check-prerequisites.ps1 --paths-only --json`
- 从输出中解析 REPO_ROOT；必要时创建缓存目录 `{REPO_ROOT}/.cache/reverse/external-interfaces/`
- 从 `$ARGUMENTS` 解析：`--path`（扫描目录，默认 `.`）、`--exclude`（可多个，排除模式）、`--interactive` / `--non-interactive` / `--yes`、`--clear-cache`

### 4. 识别代码库主要语言

- 根据用户 `--path` 或默认扫描范围，结合目录结构、常见源文件扩展名（如 .py, .java, .cpp, .go, .js, .ts 等）判断主要语言。
- 若存在多种语言，列出主语言与次要语言，后续优先为主语言定义导入规则。

### 5. 通过大模型归纳“导入方式”并区分系统/本库/外部

- **输入**：当前判定的一种或多种语言。
- **要求**：用自然语言 + 简明规则描述：
  - 该语言中“导入/引用”的语法形式（如 Python：`import x`、`from x import y`；C++：`#include <...>` / `#include "..."`；Java：`import ...`；Go：`import "..."`；JS/TS：`import` / `require()` 等）。
  - 如何区分：
    - **系统**：标准库、操作系统 API、语言内置模块等；
    - **本代码库**：来自本仓库内其他包/目录/模块的符号；
    - **外部**：来自代码库之外的第三方库、SDK、其他项目等。
- **输出**：一段可操作的识别规则（可写入 `import-list.json` 的 `import_patterns` 或单独说明），供后续扫描与分类使用。
- 若多语言，按语言分别说明导入形式与分类规则。

### 6. 扫描源文件并提取导入

- **扫描范围**：在用户 `--path` 指定目录（或默认仓库根）下，按扩展名筛选源文件。
- **应用排除**：排除命中 `--exclude` 模式的文件/目录；并默认排除隐藏目录（如 `.git/`、`.idea/`、`.vscode/`、`.cache/`）以及 `omni-doc/`，不参与扫描。
- 对每种语言，根据上一步的语法规则：
  - 使用 grep/codebase_search/read_file 等方式在**未排除**的文件中查找导入语句；
  - 提取：符号名（或模块/头文件名）、所在文件、行号（可选）。
- 汇总为“原始导入列表”，每条包含：`symbol`（或 module/header）、`source_file`、`language`。
- 可将本次使用的 `path`、`exclude_patterns` 写入 `import-list.json` 以便阶段2 与重录时一致。

### 7. 对每条导入分类（系统 / 本库 / 外部）

- **系统**：标准库、已知系统头文件/模块名（如 `std`、`os`、`java.lang`、`<iostream>` 等），由大模型规则或本地列表判定。
- **本代码库**：模块路径或头文件路径落在仓库内（如相对路径、包名对应本地目录）。
- **外部**：既非系统也非本库，即来自代码库之外的依赖（第三方库、SDK 等）。
- 将分类结果写入每条记录的 `classification` 字段（`system` / `local` / `external`）。
- 统计各分类数量，写入 `import-list.json` 的 `stats`。

### 8. 保存 import-list.json 并更新缓存状态

- 将以下内容写入 `{REPO_ROOT}/.cache/reverse/external-interfaces/import-list.json`：
  - `languages`：语言列表
  - `import_patterns`：各语言的导入形式与分类规则摘要
  - `imports`：每条导入的 symbol、module_or_header、source_file、classification、language
  - `stats`：total / system / local / external 数量
- 更新 `.cache-status.json` 中 `import_scan`：`progress: "completed"`，`confirmed: false`（待用户确认后再置为 true，若流程要求确认）。

### 9. 展示统计并（按运行模式）处理确认

- 展示：总导入数、系统/本库/外部数量、主要语言、若干条“外部”导入示例。
- **对话模式（`--interactive`）**：询问用户：“导入扫描与分类已完成，是否确认并继续阶段2？[Y/n]”，根据用户响应决定是否继续；用户确认后更新 `import_scan.confirmed: true` 并保存，进入阶段2。
- **全自动模式（默认或 `--non-interactive` / `--yes`）**：不再询问，直接视为已确认，更新 `import_scan.confirmed: true` 并保存，进入阶段2。
- 用户拒绝（n/no）时：允许查看详情、重新执行或手动修改 `import-list.json`。

## 输出

- **import-list.json**（位于 `{REPO_ROOT}/.cache/reverse/external-interfaces/`）：包含 `languages`、`import_patterns`、`imports`（含 classification）、`stats`。
- 为阶段2 提供”所有 classification 为 external 的符号”列表，用于后续调用点检索与文档生成。

**等式验收**：
- `imports` 数组长度 == 步骤 6 提取的原始导入总数
- `stats.total == stats.system + stats.local + stats.external`

## 注意事项

- 大模型归纳的规则应简洁可执行，避免歧义。
- 扫描时若仓库很大，可限制深度或按目录分批，控制 Token 与耗时。
- 所有与用户交互使用中文。
