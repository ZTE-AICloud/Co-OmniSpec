---
name: deep-architecture-identification
description: 按需反构的业务实现——执行深度架构识别分析并按模板生成报告。供 reverse-on-demand 调用。
---

> 本文档为**按需反构**的实现说明，位于本 Skill 的 `references/implementation/`。执行深度架构识别时，子 Agent 按本文档实现分析并生成《深度架构识别报告》。

## 概述

本 Skill 用于在功能反构场景下，对目标代码库执行**深度架构识别分析**，并严格按照 `.omni-infra/templates/logic-architecture-template.md` 模板生成完整的 Markdown 版《深度架构识别报告》，供后续函数反构、接口反构与按需反构使用。

## 输入/输出规格

### 输入参数（由上层 Agent 注入）

- `repo_root`：仓库根目录路径（必填，必须为绝对路径）
- `template_path`：深度架构识别模板路径（可选，默认：`"{REPO_ROOT}/.omni-infra/templates/logic-architecture-template.md"`）
- `output_path`：深度架构识别结果输出路径（可选，默认：`"{REPO_ROOT}/omni-doc/on-demand/logic_architecture.md"`）
- `status_path`：状态文件路径（可选，仅用于读取已有状态，默认：`"{REPO_ROOT}/omni-doc/on-demand/logic_architecture.cache-status.md"`）

### 输出约定

- **主输出文件**：`logic_architecture.md`（默认路径见 `output_path`）
  - 内容必须基于 `template_path` 模板生成，至少覆盖以下章节（保持模板章节顺序与结构）：
    - 项目概览（第 1 章）
    - 架构类型识别（第 2 章）
    - 模块分层结构（第 3 章）
    - 模块边界定义（第 4 章）
    - 模块依赖关系分析（第 5 章）
    - 安全架构（第 7 章，可选）
    - 日志与监控（第 8 章，可选）
    - 测试架构（第 9 章，必填）
- **状态文件**：如 `status_path` 存在，本 Skill 统一由深度架构识别 Agent 写入（Markdown 格式），用于幂等与确认。

## 执行步骤（todos 风格）

### 0. [ ] 创建执行步骤的Todo列表
为确保执行过程的透明化和可追踪性，创建执行步骤的Todo列表：

步骤1. **步骤1.前置与参数校验**
步骤2. **步骤2.读取参考上下文与基础信号**
步骤2.5. **步骤2.5 多语言指纹枚举（必填，Harness 强制）**
步骤3. **步骤3.架构类型识别（对应模板第 1–2 章）**
步骤4. **步骤4.模块分层结构分析（对应模板第 3 章）**
步骤5. **步骤5.模块边界定义（对应模板第 4 章）**
步骤6. **步骤6.模块依赖关系分析（对应模板第 5 章）**
步骤7. **步骤7.安全架构分析（模板第 7 章，可选）**
步骤8. **步骤8.日志与监控分析（模板第 8 章，可选）**
步骤9. **步骤9.测试架构分析（模板第 9 章，必填）**
步骤10. **步骤10.报告装配与模板填充**
步骤11. **步骤11.输出与结果摘要**
步骤12. **步骤12.Token 与性能管理**

### 1. 前置与参数校验

- [ ] **校验必填参数**
  - [ ] 确认 `repo_root` 存在且可访问，并且为绝对路径。
- [ ] **规范化路径**
  - [ ] 若未显式传入 `template_path`，则设为 `"{REPO_ROOT}/.omni-infra/templates/logic-architecture-template.md"`。
  - [ ] 若未显式传入 `output_path`，则设为 `"{REPO_ROOT}/omni-doc/on-demand/logic_architecture.md"`。
  - [ ] 若未显式传入 `status_path`，则设为 `"{REPO_ROOT}/omni-doc/on-demand/logic_architecture.cache-status.md"`。

### 2. 读取参考上下文与基础信号

- [ ] **读取模板文件**
  - [ ] 检查 `template_path` 是否存在且可读。
  - [ ] 加载模板内容（仅存于内存，不修改模板文件）。
- [ ] **读取缓存状态（只读，可选）**
  - [ ] 若 `status_path` 存在，则读取 `deep_architecture_identification` 相关字段，仅用于了解历史执行记录。
- [ ] **构建与目录基础扫描（为后续章节提供上下文）**
  - [ ] 样本化列出关键目录树（如 `src/`, `app/`, `services/`, `domain/`, `tests/` 等）。
  - [ ] 搜索并解析构建配置（如 `pom.xml`, `package.json`, `go.mod`, `CMakeLists.txt`, `requirements.txt` 等）。

### 2.5 多语言指纹枚举（必填，Harness 强制）

> ❗ 本步骤是消除"附属语言被忽略"问题的入口。后续步骤 3/4/6 必须基于本步骤的语言清单为每种语言选择分析策略。阶段2 波及检索 Harness 门禁的第 4 项约束（`polyglot_coverage`）会校验本步骤产出，漏报语言或裸 uncovered 将导致 `gate_exit≠0`，阻断阶段3。

- [ ] **枚举仓库全部语言（不得只列主语言）**
  - [ ] 基于文件扩展名统计（覆盖代码扩展名白名单：`.py/.java/.go/.js/.ts/.lua/.sh/.sql/.yaml/.yml/.json/.proto/.c/.cpp/...`）。
  - [ ] 结合构建文件确认技术栈（`go.mod`/`pom.xml`/`package.json`/`requirements.txt`/`CMakeLists.txt` 等）。
  - [ ] **统计每种语言的文件数与代码行数**（用 `find`+`wc -l` 或 `rg --count`），计算占比（文件数占比与行数占比差异大时同时记录）。
  - [ ] **统计全仓文件类型分布**：在 `repo_root` 执行 `find . -type f` 递归统计所有文件后缀（排除 `.git/`、`node_modules/`、`vendor/`、`__pycache__/`、`on-demand/`、`.runs/`），按后缀分组计数，计算各类别文件数与占比；结果写入 `stage2-search-coverage.json` 的 `file_type_stats`（数组，每项含 `extension`、`category`(code|config|doc|data|other)、`file_count`、`percentage`、`associated_language`）。
  - [ ] **分类规则**：
    - `code`：后缀在 `CODE_LANGUAGE_MAP` 中，`associated_language` 填对应语言名
    - `config`：`.yaml`/`.yml`/`.json`/`.toml`/`.properties`/`.ini`/`.env`/`.conf`/`.xml`/`.config`
    - `doc`：`.md`/`.txt`/`.rst`/`.adoc`/`.pdf`
    - `data`：`.csv`/`.db`/`.sqlitedb`
    - `other`：其余所有后缀
  - [ ] `file_type_stats` 字段示例：
    ```json
    "file_type_stats": [
      {"extension": ".java", "category": "code", "file_count": 142, "percentage": "~90%", "associated_language": "Java"},
      {"extension": ".yaml", "category": "config", "file_count": 8, "percentage": "~5%", "associated_language": "YAML"},
      {"extension": ".md", "category": "doc", "file_count": 5, "percentage": "~3%", "associated_language": null},
      {"extension": ".lua", "category": "code", "file_count": 3, "percentage": "~2%", "associated_language": "Lua"}
    ]
    ```
  - [ ] 区分 **primary（主语言，占比最高/承载主体逻辑）** 与 **auxiliary（附属语言，如规则脚本 Lua、运维 Shell、迁移 SQL、协议定义 proto）**，记录每种语言占比、文件后缀、主要作用（承载的业务逻辑/配置/脚本类型）。
  - [ ] Harness 会自动扫盘校验：仓库实际含的（白名单内）语言必须全部声明，**漏报即失败**。
- [ ] **为每种语言判定分析策略**
  - [ ] 判定 LSP 可用性（主语言通常有，附属语言常无）。
  - [ ] 记录 `analysis_method`：`lsp`（有 LSP）、`grep`（无 LSP，按符号模式检索）、`read`（关键文件直读）、`manual`（无法自动分析，需人工说明）。
- [ ] **落盘到 `stage2-search-coverage.json` 的 `languages` 子结构**
  - [ ] 每项字段：`name`、`role`(primary|auxiliary)、`coverage_status`(covered|degraded)、`analysis_method`(lsp|grep|read|manual)、`file_extensions`（数组，如 `[".java"]`）、`file_count`（文件数）、`lines_of_code`（代码行数，估算）、`estimated_percentage`（占比字符串，如 `"~92%"`）、`primary_role`（主要作用描述，如"业务逻辑/领域模型/控制器"）。
  - [ ] `coverage_status=degraded` 时必须填 `degraded_rationale`（为何降级，如"运维脚本无 LSP，仅按文件读取分析入口"）。
  - [ ] **禁止裸 uncovered**：任何语言要么 `covered` 要么 `degraded`（附理由），不得置为 uncovered 跳过。
  - [ ] **波及声明（auxiliary 必填）**：每个 `role=auxiliary` 语言须填 `impact_status`：
    - `hit`：该附属语言在波及清单 `stage2-impact-candidates.json` 中有命中（波及项须有 `language` 字段或可由 `code_file_path` 推断出该语言）；
    - `no_hit`：检索过但无波及命中，必须附 `no_impact_rationale`（如"本需求不涉及规则脚本改动"）。
    - Harness 会机器校验：声明 hit 但波及清单无该语言命中、或声明 no_hit 但清单命中该语言、或沉默不填，均判 `gate_exit≠0`。
  - [ ] 至少一个 `role=primary`。
  - [ ] 字段示例（含语言构成统计字段）：
    ```json
    "languages": [
      {
        "name": "Java",
        "role": "primary",
        "coverage_status": "covered",
        "analysis_method": "lsp",
        "file_extensions": [".java"],
        "file_count": 142,
        "lines_of_code": 28500,
        "estimated_percentage": "~91%",
        "primary_role": "业务逻辑、领域模型、控制器、服务层"
      },
      {
        "name": "YAML",
        "role": "auxiliary",
        "coverage_status": "covered",
        "analysis_method": "read",
        "impact_status": "no_hit",
        "no_impact_rationale": "本需求不涉及配置变更",
        "file_extensions": [".yaml", ".yml"],
        "file_count": 12,
        "lines_of_code": 2100,
        "estimated_percentage": "~6%",
        "primary_role": "部署配置、CI/CD 流水线、环境参数"
      },
      {
        "name": "Lua",
        "role": "auxiliary",
        "coverage_status": "covered",
        "analysis_method": "grep",
        "impact_status": "hit",
        "file_extensions": [".lua"],
        "file_count": 5,
        "lines_of_code": 950,
        "estimated_percentage": "~3%",
        "primary_role": "规则脚本、热更新逻辑"
      }
    ]
    ```
- [ ] **将语言清单带入后续步骤**：步骤 3/4/6 必须遍历 `languages` 清单逐语言处理，不得只处理 primary。

### 3. 架构类型识别（对应模板第 1–2 章）

- [ ] **收集基础信号**
  - [ ] 分析目录结构与命名模式（如 `domain/`, `application/`, `infrastructure/`, `interfaces/` 等）。
  - [ ] 结合构建文件与依赖信息识别主要技术栈、运行环境与部署方式。
  - [ ] 通过 LSP `workspaceSymbol` / `documentSymbol` 搜索关键符号（如 `*Service`, `*Repository`, `*Controller`，注解 `@Service`, `@Controller` 等）。
  - [ ] ❗ **多语言遍历**：对步骤 2.5 清单中**每种**语言分别收集信号，不得只处理 primary。对 `analysis_method=lsp` 的语言用 LSP 符号搜索；对 `analysis_method=grep/read` 的附属语言（无 LSP），用 `grep` 按该语言约定的符号模式（如 Lua 的 `function`/`local`、Shell 的 `function`/`xxx(){`、SQL 的 `CREATE PROCEDURE`/`CREATE FUNCTION`）检索，并 Read 关键文件确认。
- [ ] **推断架构类型**
  - [ ] 尝试匹配 DDD 分层架构、电信领域组件架构、微服务框架、命令行工具等已知模式。
  - [ ] 若无法明确匹配，则标记为“其他架构类型”，并记录主要特征（如三层 MVC、六边形架构等）。
- [ ] **写入模板对应章节内容**
  - [ ] 在“项目概览”中整理：项目名称（如可推断）、技术栈、架构类型、部署方式、数据库、分析目标。
  - [ ] 在“架构类型识别”中填充主体架构模式与子架构模式（如 Web 框架、API 设计、认证、异步处理等）。

### 4. 模块分层结构分析（对应模板第 3 章）

- [ ] **基于 LSP 的符号分析**
  - [ ] 使用 `workspaceSymbol` / `documentSymbol` 收集模块相关类型：`*Service`, `*Repository`, `*Controller`, `*Domain`, `*Entity` 等。
  - [ ] 通过 `goToDefinition` / 类型信息分析继承、实现关系与关键注解/装饰器。
  - [ ] ❗ **多语言遍历**：对步骤 2.5 清单中 `analysis_method≠lsp` 的附属语言（Lua/Shell/SQL/proto 等），LSP 不可用，必须回退到 `grep` 符号模式 + `Read` 关键文件的方式收集该语言的模块/单元，**不得因占比小而跳过**。该语言承载的模块（如规则引擎、迁移脚本组、协议定义）也需纳入分层树。
- [ ] **结合构建与目录结构**
  - [ ] 分析各模块在构建文件中的依赖与分组（如 Maven 模块、Node 包、Go module 等）。
  - [ ] 基于目录深度与命名空间推断模块层级（父模块/子模块/兄弟模块）。
- [ ] **构建模块层级树**
  - [ ] 将模块按层/子模块组织为树状结构。
  - [ ] 对关键层（如领域层、应用层、接口层、基础设施层）进行标注。
- [ ] **写入模板对应章节内容**
  - [ ] 使用 ASCII 图描述层级架构图。
  - [ ] 按层级详细说明每个层级的路径、职责、技术、关键组件/文件/模块。

### 5. 模块边界定义（对应模板第 4 章）

- [ ] **识别模块入口点（公共 API）**
  - [ ] 利用 LSP `documentSymbol` / `hover` 找出公共接口类、控制器、服务类、工厂类等。
  - [ ] 标记这些符号所属模块与层级，形成“模块公共 API”清单。
- [ ] **识别模块内部实现**
  - [ ] 区分公共导出与内部实现（依据访问修饰符、导出列表、命名约定等）。
  - [ ] 将内部工具类、私有实现归类为模块内部组成。
- [ ] **抽象模块边界规则**
  - [ ] 基于可见性、访问修饰符与导入关系，总结每个模块的访问约束和依赖方向。
  - [ ] 记录跨模块调用的主要路径，用于后续依赖与影响分析。
- [ ] **写入模板对应章节内容**
  - [ ] 按模块组织公共接口、内部实现与边界规则。

### 6. 模块依赖关系分析（对应模板第 5 章）

- [ ] **构建依赖图**
  - [ ] 使用 LSP `findReferences` / `goToDefinition` 追踪模块间的调用与引用关系。
  - [ ] 将依赖关系归类为 `uses` / `extends` / `implements` / `depends_on` 等类型。
  - [ ] ❗ **跨语言调用边（必填）**：LSP 的引用追不过语言边界，必须用 `grep` 显式补全跨语言调用，否则附属语言会成依赖孤岛。重点检索模式：
    - 进程/脚本调用：`Runtime.exec` / `ProcessBuilder` / `subprocess` / `os/exec` / `child_process`
    - 嵌入式脚本引擎：`ScriptEngine` / `eval(` / `load(` / `dofile` / `require`
    - 原生互操作：JNI / cgo / ctypes / FFI
    - Shell/外部命令：`.sh` 调用、`bash -c`
    - SQL/迁移引用：迁移文件被 ORM/启动流程触发
  - [ ] 找到跨语言调用后，把它作为交互节点画进依赖图（标注跨语言边与目标语言/文件）。
  - [ ] 阶段2波及检索时，调用链追到语言边界处，在 `stage2-call-trace.json` 对应 trace 用 `stopped_reason=non_code_boundary` + `leaf_evidence`（断点文件:行号 + 目标语言）记录，允许在此提前结束（已属 Harness 允许的合法停止原因）。
- [ ] **识别关键特征**
  - [ ] 统计直接依赖与传递依赖，计算依赖深度。
  - [ ] 识别并记录循环依赖（若存在）。
- [ ] **写入模板对应章节内容**
  - [ ] 使用 ASCII 图形式给出依赖关系图。
  - [ ] 在文中汇总依赖统计、依赖深度、循环依赖与依赖类型分布。

### 7. 安全架构分析（模板第 7 章，可选）

- [ ] **判断是否需要安全架构章节**
  - [ ] 若满足任一条件：公网系统 / 有合规要求 / 存在明显安全风险点 / 项目明确要求安全分析，则执行本章；否则在报告中标注为“未适用/未发现”。
- [ ] **分析安全相关机制**
  - [ ] 认证与授权：认证方式（JWT/OAuth2/Session 等）、令牌管理、权限控制策略。
  - [ ] 数据安全：加密方式、传输安全、数据保护机制。
  - [ ] 访问控制：API 保护、权限控制。
  - [ ] 安全漏洞防护：XSS、CSRF、SQL 注入等防护措施。
- [ ] **写入模板对应章节内容**
  - [ ] 按模板章节结构汇总上述信息；如不适用则显式说明原因。

### 8. 日志与监控分析（模板第 8 章，可选）

- [ ] **日志体系**
  - [ ] 分析日志文件位置和结构。
  - [ ] 分析日志配置（handlers、大小限制、备份数量、日志级别等）。
  - [ ] 说明日志内容包含的关键信息。
- [ ] **监控机制（如存在）**
  - [ ] 识别监控采集方式、告警机制与可视化工具。
- [ ] **写入模板对应章节内容**
  - [ ] 在“日志与监控”章节中结构化呈现上述分析结果；如未配置监控，则明确写出当前状态。

### 9. 测试架构分析（模板第 9 章，必填）

- [ ] **测试分层识别**
  - [ ] 分析测试目录结构，识别单元测试、集成测试、端到端测试等。
  - [ ] 建立测试文件与源码文件的对应关系。
  - [ ] 总结测试命名规范与目录组织方式。
- [ ] **测试框架详细分析**
  - [ ] 单元测试框架：识别框架（Jest、pytest、JUnit、Mocha、RSpec 等）、配置文件、框架特性（断言库、异步支持、快照测试等）。
  - [ ] 集成测试框架：识别框架、配置与运行方式。
  - [ ] E2E 测试框架（如存在）：框架名、浏览器支持、无头模式、录制回放等特性。
  - [ ] 性能测试框架（如存在）：工具（JMeter、k6、Artillery、Locust 等）及配置。
  - [ ] 测试运行器：识别运行器（Jest runner、pytest、Maven Surefire 等）、并行执行与测试发现机制。
- [ ] **Mock 机制详细分析**
  - [ ] 识别使用的 Mock 框架/库（Mockito、unittest.mock、sinon、jest.fn、Moq 等）、版本与配置。
  - [ ] 分析接口 Mock、数据库 Mock、外部服务 Mock、文件系统 Mock 等策略。
  - [ ] 识别 Fixture 文件、Factory、Inline Mock 等数据构造方式。
  - [ ] 分析 Stub 与 Spy 的使用场景，以及在项目中 Mock / Stub / Spy 的区分。
- [ ] **测试数据管理分析**
  - [ ] 汇总测试数据来源（Fixture、Factory、Seed 数据、Test Data Builders 等）。
  - [ ] 分析测试数据隔离策略（每个测试独立数据/共享数据/事务回滚等）。
  - [ ] 识别测试数据清理机制（`teardown`、`afterEach`、事务回滚、数据库重置等）。
- [ ] **测试配置与环境分析**
  - [ ] 识别测试配置文件位置与关键配置项。
  - [ ] 分析测试环境变量管理方式。
  - [ ] 分析测试在 CI/CD 中的集成方式与测试报告生成。
- [ ] **测试覆盖率分析**
  - [ ] 识别覆盖率工具（coverage.py、istanbul、JaCoCo 等）、配置与目标。
  - [ ] 记录覆盖率报告生成位置与形式。
- [ ] **测试工具汇总**
  - [ ] 汇总所有使用的测试工具和框架，形成表格或列表写入报告。

### 10. 报告装配与模板填充

- [ ] **章节结构对齐**
  - [ ] 确保报告中已包含模板要求的所有章节，即使部分章节为“未适用/未发现”也需保留。
- [ ] **语言构成与附属语言影响面填充（1.3）**
  - [ ] 从 `stage2-search-coverage.json` 的 `languages` 数组提取每种语言的 `name`、`estimated_percentage`、`file_extensions`、`file_count`、`lines_of_code`、`primary_role`。
  - [ ] 填充 1.1 的"语言构成"字段：`{主语言名称}（~{占比}%） + {附属语言1}（~{占比1}%） + …`。
  - [ ] 填充 1.3 语言构成与附属语言影响面表格：按 languages 顺序逐行填表，每行含语言名称、role、文件后缀、文件数、代码行数、占比、主要作用、分析方式；auxiliary 行额外填「入口」（`{文件路径}:{行号}`）与「被谁调用」（主语言模块/文件:行号 + 调用方式 JNI/subprocess/脚本引擎/命令行/ORM 触发），primary 行两列填 `—`。
  - [ ] 若某语言占比极低（<1%），在"主要作用"中标注"零星脚本/配置片段"，分析方式可标 `manual`。
- [ ] **文件类型组成填充（1.4）**
  - [ ] 从 `stage2-search-coverage.json` 的 `file_type_stats` 数组提取每种后缀的 `extension`、`category`、`file_count`、`percentage`、`associated_language`。
  - [ ] 填充 1.4 文件类型组成表格：按 `code`（代码类）优先、`config`（配置类）、`doc`（文档类）、`data`（数据类）、`other`（其他）分组排列，每行含后缀、类别、文件数、占比、关联语言（本节只统计后缀分布，语言的语义信息以 1.3 为准）。
  - [ ] "关联语言"列：对 `category=code` 的行填对应语言名称（来自 `languages` 声明或 `CODE_LANGUAGE_MAP`），其余类别填 `—`。
  - [ ] 验证：表格文件数之和应约等于仓库实际非排除文件总数（允许 ±1% 舍入误差）；若差异超过 5% 需说明原因（如生成文件、临时文件未计入）。
- [ ] **配置文件影响分析填充（1.5 配置文件影响分析）**
  - [ ] 从 `stage2-static-asset-scan.json` 的 `config_files` 数组读取每个已解析的配置文件（`parse_status=parsed`）。
  - [ ] 按后缀分组（YAML / JSON / XML / properties-ini / 其他），每组一张子表格。
  - [ ] 每行填：配置文件名、相对路径、`extracted_keys`（关键配置项，若过多可截取 top 10 并标注"等"）、`structure_summary`（配置用途）、`consumer_refs`（消费者模块/函数，追溯到代码文件:行号；无消费者填 `—` 并在"说明"列注明原因）、关联波及功能（从 `stage2-impact-candidates.json` 匹配，填 `function_key`；无关联填 `—`）。
  - [ ] 在"说明"列对以下情况加标注：含变量引用（如 `${VAR}`/`{{template}}`）标注"含变量引用"；含敏感配置标注"含敏感配置"；消费者为空且原因为"纯基础设施配置"标注"纯基础设施配置"。
  - [ ] 若某后缀组配置文件数量多（如 10+ 个 properties 文件），可合并为一行，格式为"{后缀} 配置文件 ×{N}"，详细清单指向 `stage2-static-asset-scan.json`。
  - [ ] 验证：`stage2-static-asset-scan.json` 中有 `parse_status≠parsed` 的文件须在对应行标注原因；消费者链路（consumer_refs）应能追溯到波及清单中的功能或模块。
- [ ] **占位符替换**
  - [ ] 替换模板中的所有占位符（如 `{项目名称}`、`{路径}` 等），避免留下未填充内容。
- [ ] **格式检查**
  - [ ] 保持模板的章节顺序和 Markdown 格式（标题层级、列表、代码块等）不被破坏。

### 11. 输出与结果摘要

- [ ] **准备输出目录**
  - [ ] 确保 `output_path` 所在目录存在，不存在则创建。
- [ ] **写入 Markdown 结果**
  - [ ] 将装配好的报告内容写入 `output_path`。
- [ ] **结构校验**
  - [ ] 再次快速检查生成的 Markdown：章节是否齐全、是否存在明显未替换占位符。
- [ ] **生成概要摘要**
  - [ ] 汇总架构类型、主要技术栈、模块数量/层级数量、是否存在循环依赖、是否完成安全/日志/测试架构分析等关键信息。
- [ ] **向上层 Agent 返回**
  - [ ] 返回执行状态（成功/失败）、`output_path` 以及概要摘要，供主流程写入缓存状态与报告。

### 12. Token 与性能管理

- [ ] **优先使用 LSP 工具**
  - [ ] 尽量通过 LSP 获取结构化符号与依赖信息，避免读取完整源文件。
  - [ ] ❗ **例外**：本条仅适用于有 LSP 的语言。对步骤 2.5 中 `analysis_method=grep/read` 的附属语言（无 LSP），`grep` + `Read` 是唯一可靠手段，**不受"避免读全文"约束**——否则附属语言无法被分析而再次被忽略。
- [ ] **分批处理大仓库**
  - [ ] 对大目录按模块/层级分批扫描，避免一次性加载全部文件。
- [ ] **精确限定范围**
  - [ ] 调用 LSP 时总是带上精确的文件路径、符号名或模式，降低无关结果数量。
