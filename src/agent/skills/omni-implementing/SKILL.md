---
name: omni-implementing
description: 执行实施计划，通过处理并执行 tasks.md 中定义的所有任务完成实施。
---

# omni-implementing

根据 tasks.md 中的任务分解与 design.md 中的技术计划，按阶段、依赖与 TDD 要求执行实施，并产出任务执行报告。

## 指令

### 1. 设置
   - 判断当前操作系统（Windows 或 Linux）
   - 从仓库根目录运行对应脚本：
     - **Windows**: `.specify/scripts/powershell/check-prerequisites.ps1 --json --require-tasks --include-tasks`
     - **Linux**: `.specify/scripts/bash/check-prerequisites.sh --json --require-tasks --include-tasks`
   - 解析脚本 JSON 输出，获取 **FEATURE_DIR** 和 **AVAILABLE_DOCS** 列表；所有路径使用绝对路径。参数中含单引号时（如 "I'm Groot"）使用转义 `'I'\''m Groot'` 或双引号 `"I'm Groot"`。

### 2. 检查清单状态
（若存在 `FEATURE_DIR/checklists/`） 
   - 扫描 checklists/ 目录中的所有清单文件
   - 对于每个清单, 统计: 
     * 总项目数: 所有匹配 `- [ ]` 或 `- [X]` 或 `- [x]` 的行
     * 已完成项目数: 匹配 `- [X]` 或 `- [x]` 的行
     * 未完成项目数: 匹配 `- [ ]` 的行
   - 创建状态表: 
     ```
     | Checklist | Total | Completed | Incomplete | Status |
     |-----------|-------|-----------|------------|--------|
     | ux.md     | 12    | 12        | 0          | ✓ PASS |
     | test.md   | 8     | 5         | 3          | ✗ FAIL |
     | security.md | 6   | 6         | 0          | ✓ PASS |
     ```
   - 计算总体状态: 
     * **PASS**: 所有清单都有 0 个未完成项目
     * **FAIL**: 一个或多个清单有未完成项目

   - **若有清单未完成**
     * 显示含未完成项数量的表格
     * **停止**并询问："Some checklists are incomplete. Do you want to proceed with implementation anyway? (yes/no)"
     * 等待用户响应后再继续
     * 用户回复 "no" / "wait" / "stop" → 停止；"yes" / "proceed" / "continue" → 进入步骤 3

   - **若所有清单均已完成**
     * 显示所有清单通过的表格
     * 自动进入步骤 3

### 3. 加载与分析实施上下文 
   - **必需**: 读取 tasks.md 获取完整任务列表和执行计划
   - **必需**: 读取 design.md 获取技术栈、架构和文件结构
   - **如果存在**: 读取 data-model.md 获取实体和关系
   - **如果存在**: 读取 contracts/ 获取 API 规范和测试要求
   - **如果存在**: 读取 research.md 获取技术决策和约束
   - **如果存在**: 读取 quickstart.md 获取集成场景

### 4. 项目设置验证
   - **必需**：基于实际项目设置创建或验证忽略文件。

   **检测与创建逻辑** 
   - 检查以下命令是否成功以判断是否为 Git 仓库（若是，则创建/验证 `.gitignore`）： 

     ```sh
     git rev-parse --git-dir 2>/dev/null
     ```
   - 存在 `Dockerfile*` 或 design.md 提及 Docker → 创建/验证 `.dockerignore`
   - 存在 `.eslintrc*` 或 `eslint.config.*` → 创建/验证 `.eslintignore`
   - 存在 `.prettierrc*` → 创建/验证 `.prettierignore`
   - 存在 `.npmrc` 或 `package.json` 且需发布 → 创建/验证 `.npmignore`
   - 存在 Terraform 文件 `*.tf` → 创建/验证 `.terraformignore`
   - 存在 Helm charts → 创建/验证 `.helmignore`

   **若忽略文件已存在**：校验是否包含基本模式，仅追加缺失的关键模式。  
   **若忽略文件不存在**：为检测到的技术创建完整模式集。

   **按技术栈的通用模式**（参考 design.md）：
   - **Node.js/JavaScript**: `node_modules/`, `dist/`, `build/`, `*.log`, `.env*`
   - **Python**: `__pycache__/`, `*.pyc`, `.venv/`, `venv/`, `dist/`, `*.egg-info/`
   - **Java**: `target/`, `*.class`, `*.jar`, `.gradle/`, `build/`
   - **C#/.NET**: `bin/`, `obj/`, `*.user`, `*.suo`, `packages/`
   - **Go**: `*.exe`, `*.test`, `vendor/`, `*.out`
   - **Ruby**: `.bundle/`, `log/`, `tmp/`, `*.gem`, `vendor/bundle/`
   - **PHP**: `vendor/`, `*.log`, `*.cache`, `*.env`
   - **Rust**: `target/`, `debug/`, `release/`, `*.rs.bk`, `*.rlib`, `*.prof*`, `.idea/`, `*.log`, `.env*`
   - **Kotlin**: `build/`, `out/`, `.gradle/`, `.idea/`, `*.class`, `*.jar`, `*.iml`, `*.log`, `.env*`
   - **C++**: `build/`, `bin/`, `obj/`, `out/`, `*.o`, `*.so`, `*.a`, `*.exe`, `*.dll`, `.idea/`, `*.log`, `.env*`
   - **C**: `build/`, `bin/`, `obj/`, `out/`, `*.o`, `*.a`, `*.so`, `*.exe`, `Makefile`, `config.log`, `.idea/`, `*.log`, `.env*`
   - **Swift**: `.build/`, `DerivedData/`, `*.swiftpm/`, `Packages/`
   - **R**: `.Rproj.user/`, `.Rhistory`, `.RData`, `.Ruserdata`, `*.Rproj`, `packrat/`, `renv/`
   - **通用**: `.DS_Store`, `Thumbs.db`, `*.tmp`, `*.swp`, `.vscode/`, `.idea/`

   **工具特定模式**
   - **Docker**: `node_modules/`, `.git/`, `Dockerfile*`, `.dockerignore`, `*.log*`, `.env*`, `coverage/`
   - **ESLint**: `node_modules/`, `dist/`, `build/`, `coverage/`, `*.min.js`
   - **Prettier**: `node_modules/`, `dist/`, `build/`, `coverage/`, `package-lock.json`, `yarn.lock`, `pnpm-lock.yaml`
   - **Terraform**: `.terraform/`, `*.tfstate*`, `*.tfvars`, `.terraform.lock.hcl`
   - **Kubernetes/k8s**：`*.secret.yaml`, `secrets/`, `.kube/`, `kubeconfig*`, `*.key`, `*.crt`

### 5. 解析 tasks.md 结构并提取
   - **任务阶段**：设置、测试、核心、集成、完善
   - **任务依赖**：顺序与并行规则
   - **任务详情**：ID、描述、文件路径、并行标记 [P]
   - **执行流程**：顺序与依赖要求

### 6. 按任务计划执行实施
   - **分阶段**：完成当前阶段后再进入下一阶段
   - **依赖**：顺序任务按序执行，带 [P] 的并行任务可一并执行
   - **TDD**：在对应实施任务前执行测试任务
   - **同文件协调**：影响同一文件的任务须顺序执行
   - **检查点**：每阶段完成后验证再继续

### 7. 实施执行规则
   - **设置**：初始化项目结构、依赖、配置
   - **测试先行**：按需为合约、实体、集成场景编写测试
   - **核心开发**：模型、服务、CLI、端点
   - **集成**：数据库、中间件、日志、外部服务
   - **收尾**：单元测试、性能与文档

### 8. 进度与错误处理
   - 每完成一项任务即报告进度
   - 非并行任务失败则停止；并行任务 [P] 中失败的单独报告，其余继续
   - 错误信息需包含调试上下文；无法继续时给出下一步建议
   - **重要**：已完成任务须在 tasks.md 中标记为 `- [X]`。

### 9. 完成验证与任务状态分析
   - **重新读取 tasks.md**：获取最新状态，统计已完成（`- [X]`）与未完成（`- [ ]`）任务。

   - **任务完成度验证**
     * 对已标记完成的任务做实际校验：
       - 验证所有必需任务已完成
       - 检查实施功能是否与原始规范匹配
       - 验证测试通过且覆盖率满足要求
       - 确认实施遵循技术计划
     * 校验不通过的任务改回未完成。

   - **未完成任务分析**
     * 评估每个未完成任务是否可执行：
       - 检查依赖项(其他任务、外部服务、工具)是否满足
       - 检查所需文件或资源是否存在
       - 检查权限或配置问题
     * 归类阻塞原因：等待依赖、缺少资源、环境限制、需求问题、其他。

   - **任务执行处理**
     * **可执行**：询问用户是否继续；同意则按依赖执行，拒绝则记入报告。
     * **无法执行**：生成分析报告（任务 ID、原因、阻塞说明、解决建议）。

### 10. 生成最终报告
   - **任务执行报告**（需包含）：
       ```
       ## 任务执行最终报告
       ### 总体统计
       - 总任务数: X
       - 已完成: Y (Z%)
       - 未完成: W (V%)
         - 可执行: A
         - 无法完成: B

       ### 已完成任务列表
       [列出所有已完成的任务ID和描述]

       ### 可执行的未完成任务列表
       [列出可以继续执行的任务ID和描述]

       ### 无法完成的任务分析
       [列出无法完成的任务, 包含:
        - 任务ID和描述
        - 阻塞原因(等待依赖/缺少资源/环境限制/需求问题/其他)
        - 详细说明
        - 解决建议]
       ```
   - **下一步建议**
     - 全部完成 → 报告成功
     - 存在可执行未完成任务 → 建议继续执行
     - 存在无法完成的任务 → 建议用户排查并解决阻塞后再执行

**注意**：本技能假定 tasks.md 中已有完整任务分解。若任务不完整或缺失，请先通过相应命令重新生成任务列表。
