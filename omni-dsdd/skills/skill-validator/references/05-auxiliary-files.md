# 1. 附属文件检查

附属文件是技能的重要组成部分，用于补充技能的功能、提供示例、模板和脚本。良好的附属文件组织能够提高技能的可维护性和易用性。

## 1.1 附属文件结构检查

### 1.1.1 必需文件检查
- [ ] **SKILL.md 为唯一必需文件** [必选项]：确认只有 SKILL.md 是必需的
  - 验证方法：检查技能目录中只有 SKILL.md 是核心文件
  - 其他文件都是可选的附属文件

### 1.1.2 常见附属文件类型

##### 4.1.2.1 template.md 文件
- [ ] **template.md 存在性** [可选项]：检查是否有模板文件
  - 验证方法：检查 `template.md` 或 `templates/` 目录
  - 用途：提供可重复使用的内容模板
  - 典型内容：占位符、变量替换说明、使用说明

- [ ] **template.md 用途明确** [可选项]：模板文件应有明确的使用说明
  - 验证方法：检查模板文件是否有使用说明
  - 错误示例：模板文件无任何说明
  - 正确示例：
    ```markdown
    # 模板说明

    本模板用于生成标准化的代码文件，请替换以下占位符：
    - `{{PROJECT_NAME}}`：项目名称
    - `{{AUTHOR}}`：作者信息
    - `{{DATE}}`：创建日期
    ```

- [ ] **模板占位符清晰** [可选项]：使用清晰的占位符语法
  - 验证方法：检查占位符的一致性和清晰度
  - 常用格式：
    - `{{PLACEHOLDER}}`
    - `$PLACEHOLDER`
    - `PLACEHOLDER`
  - 错误示例：占位符格式不一致
  - 正确示例：统一使用一种占位符格式

##### 4.1.2.2 examples/ 目录
- [ ] **examples/ 目录存在** [可选项]：检查是否有示例目录
  - 验证方法：检查 `examples/` 或 `example/` 目录
  - 用途：提供使用示例和案例

- [ ] **examples/ 有示例文件** [可选项]：目录应包含至少一个示例文件
  - 验证方法：检查目录中是否有文件
  - 错误示例：空目录
  - 正确示例：包含有代表性的示例文件

- [ ] **示例文件有代表性**：示例应覆盖主要使用场景
  - 验证方法：检查示例的多样性和代表性
  - 错误示例：只有单一、简单的示例
  - 正确示例：包含简单、复杂、边界情况的示例

- [ ] **示例文件命名规范** [可选项]：使用描述性的文件名
  - 验证方法：检查示例文件的命名
  - 错误示例：`example1.md`、`example2.md`
  - 正确示例：`basic-usage.md`、`advanced-usage.md`、`edge-case.md`

##### 4.1.2.3 scripts/ 目录
- [ ] **scripts/ 目录存在** [可选项]：检查是否有脚本目录
  - 验证方法：检查 `scripts/` 或 `script/` 目录
  - 用途：存放可执行脚本

- [ ] **脚本文件可执行** [必选项]：脚本文件应具有执行权限
  - 验证方法：检查脚本文件的执行权限（`chmod +x`）
  - 错误示例：Shell 脚本无执行权限
  - 正确示例：Shell 脚本有执行权限

- [ ] **脚本文件有 shebang** [必选项]：脚本开头应有 shebang 行
  - 验证方法：检查脚本文件的第一行
  - 常见 shebang：
    - `#!/bin/bash`：Bash 脚本
    - `#!/usr/bin/env python3`：Python 3 脚本
    - `#!/usr/bin/env node`：Node.js 脚本
  - 错误示例：缺少 shebang 行
  - 正确示例：
    ```bash
    #!/bin/bash
    echo "Hello World"
    ```

- [ ] **脚本文件有说明** [可选项]：复杂脚本应有注释和说明
  - 验证方法：检查脚本文件的注释
  - 错误示例：复杂脚本无任何注释
  - 正确示例：
    ```bash
    #!/bin/bash
    # 脚本说明：部署应用到生产环境
    # 作者：XXX
    # 日期：2026-05-07

    # 1. 运行测试
    npm test
    ```

##### 4.1.2.4 SKILL.md 调用脚本检查

- [ ] **使用 CLAUDE_SKILL_DIR 变量引用脚本** [必选项]：正确使用变量引用脚本路径
  - 验证方法：检查 bash 注入命令中是否使用了正确的变量语法
  - 变量作用：包含技能的 SKILL.md 文件的目录绝对路径
  - 重要特性：插件技能指向插件内技能的子目录，不是插件根目录
  - 用途：在 bash 注入命令中引用与技能捆绑的脚本或文件，无论当前工作目录如何
  - 错误示例：使用硬编码路径或相对路径
  - 正确示例：
    ```yaml
    ---
    name: codebase-visualizer
    description: Generate an interactive collapsible tree visualization of your codebase
    allowed-tools: Bash(python3 *)
    ---

    Run visualization script from your project root:
    ```bash
    python3 ${CLAUDE_SKILL_DIR}/scripts/visualize.py .
    ```
    ```

- [ ] **脚本路径优先级正确** [必选项]：按正确的优先级查找脚本路径
  - 验证方法：检查技能中是否说明了脚本路径查找逻辑
  - 路径优先级：
    1. 优先：`{REPO_ROOT}/.claude/skills/{skill-name}/referencess/scripts/`
    2. 次选：`{REPO_ROOT}/claude/skills/{skill-name}/referencess/scripts/`
  - 错误示例：只检查一个路径或使用固定路径
  - 正确示例：
    ```markdown
    ## 脚本执行

    脚本按以下优先级查找：
    1. 先检查 `.claude/skills/reverse-interfaces/referencess/scripts/`
    2. 如不存在，再检查 `claude/skills/reverse-interfaces/referencess/scripts/`
    具体为：
    - 前置依赖：`reverse_by_call_chain/prepare_reverse_input.py`
    - 接口识别：`reverse_by_call_chain/run_reverse_identify.py`
    - 结果转换：`reverse_by_call_chain/convert_reverse_interface_checklist.py`
    ```

- [ ] **Bash 工具权限配置正确** [必选项]：调用脚本需要适当的 Bash 工具权限
  - 验证方法：检查 allowed-tools 配置
  - 权限配置推荐：
    1. 调用 python 脚本：`allowed-tools: Bash(python3 *)`
    2. 调用 shell 脚本：`allowed-tools: Bash(sh)`, `allowed-tools: Bash(bash)`
    3. 调用通用命令：`allowed-tools: Bash`
    4. 调用 git 命令：`allowed-tools: Bash(git *)`
  - 错误示例：
    ```yaml
    # 错误：调用脚本但没有指定 Bash 权限
    ---
    name: run-script
    description: Run helper script
    ---
    执行脚本：
    ```bash
    ${CLAUDE_SKILL_DIR}/scripts/helper.py
    ```
  - 正确示例：
    ```yaml
    # 正确：指定了需要的 Bash 权限
    ---
    name: run-script
    description: Run helper script
    allowed-tools: Bash(python3 *)
    ---
    执行脚本：
    ```bash
    ${CLAUDE_SKILL_DIR}/scripts/helper.py
    ```

- [ ] **脚本命令白名单合理** [必选项]：使用精确的命令白名单限制权限
  - 验证方法：检查 Bash 工具的白名单配置
  - 白名单格式：`Bash(command1, command2, ...)` 或 `Bash(command1 *)`
  - 推荐做法：
    1. 列出脚本需要的具体命令
    2. 使用通配符限制命令类型（如 `python3 *`）
    3. 避免过于宽泛的配置
  - 错误示例：
    ```yaml
    # 错误：允许所有 Python 命令
    allowed-tools: Bash(python3)
    ```
  - 正确示例：
    ```yaml
    # 正确：只允许特定的脚本调用
    allowed-tools: Bash(python3 script.py)
    ```

- [ ] **脚本调用有超时控制** [必选项]：长时间运行的脚本应有超时设置
  - 验证方法：检查脚本调用是否有超时控制
  - 超时控制方式：
    1. 使用 `timeout` 命令包装脚本调用
    2. 在脚本内部实现超时检测
    3. 设置合理的超时时间（通常 300 秒 = 5 分钟）
  - 错误示例：长时间脚本无任何超时限制
  - 正确示例：
    ```yaml
    ---
    name: data-processor
    description: Process large data files
    allowed-tools: Bash(python3 *)
    ---

    Run processing script with timeout:
    ```bash
    timeout 300 python3 ${CLAUDE_SKILL_DIR}/scripts/process.py --input data.json --output result.json
    exit_code=$?
    if [ $exit_code -eq 124 ]; then
        echo "错误：脚本执行超时（5分钟）"
        exit 1
    fi
    ```

- [ ] **脚本调用有错误处理** [必选项]：脚本调用应包含错误处理逻辑
  - 验证方法：检查 bash 命令调用是否有错误检测和处理
  - 错误处理方法：
    1. 检查退出码（`$?` 变量）
    2. 使用 `set -e` 在错误时立即退出
    3. 提供有意义的错误信息
    4. 适当的清理和回滚
  - 错误示例：
    ```bash
    # 错误：无错误检测
    python3 ${CLAUDE_SKILL_DIR}/scripts/script.py
    ```
  - 正确示例：
    ```bash
    # 正确：有完整的错误处理
    if ! python3 ${CLAUDE_SKILL_DIR}/scripts/script.py; then
        echo "错误：脚本执行失败"
        cleanup_temp_files
        exit 1
    fi
    ```

- [ ] **脚本调用有日志记录** [可选项]：重要脚本调用应有日志输出
  - 验证方法：检查脚本调用是否有日志记录
  - 日志记录方法：
    1. 记录执行开始和结束
    2. 记录关键步骤和参数
    3. 记录执行时间和结果
    4. 记录错误信息（如有）
  - 错误示例：
    ```bash
    # 错误：无日志输出
    python3 ${CLAUDE_SKILL_DIR}/scripts/script.py
    ```
  - 正确示例：
    ```bash
    # 正确：有完整的日志记录
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] 开始执行脚本"
    echo "脚本路径：${CLAUDE_SKILL_DIR}/scripts/script.py"
    echo "参数：$@"
    python3 ${CLAUDE_SKILL_DIR}/scripts/script.py "$@"
    exit_code=$?
    if [ $exit_code -eq 0 ]; then
        echo "[$(date '+%Y-%m-%d %H:%M:%S')] 执行成功"
    else
        echo "[$(date '+%Y-%m-%d %H:%M:%S')] 执行失败，退出码：$exit_code"
    fi
    ```

- [ ] **多行动态注入使用代码块语法** [必选项]：多行命令使用 ```!` 语法
  - 验证方法：检查多行动态注入的语法
  - 语法要求：
    1. 使用以 ```! ` 开头的围栏代码块
    2. 每行一个命令
    3. 不需要额外的 `` ` 包裹每行
  - 错误示例：
    ```yaml
    # 错误：使用内联多行语法
    Environment: !`echo "line1"; echo "line2"; echo "line3"`
    ```
  - 正确示例：
    ```yaml
    # 正确：使用代码块语法
    ## Environment
    ```!
    node --version
    npm --version
    git status --short
    ```
    ```

- [ ] **shell 字段设置正确** [必选项]：当使用内联 shell 命令时指定正确的 shell
  - 验证方法：检查 shell 字段设置（如有）
  - shell 字段要求：
    1. 支持值：`bash`（默认）、`powershell`
    2. PowerShell 要求：需要 `CLAUDE_CODE_USE_POWERSHELL_TOOL=1` 环境变量
    3. 用途：指定此 skill 中 `!`command` `` 和 ```! ` 块的 shell
  - 错误示例：
    ```yaml
    # 错误：使用不支持的 shell
    ---
    shell: cmd
    ---
    ```
  - 正确示例：
    ```yaml
    # 正确：使用支持的 shell
    ---
    name: windows-deploy
    description: Deploy application on Windows
    shell: powershell
    allowed-tools: Bash(powershell *)
    ---

    Run deployment script:
    ```!
    Get-NodeVersion
    Get-NpmVersion
    git status --short
    ```
    ```

- [ ] **脚本调用与技能内容一致** [必选项]：脚本调用应与技能描述和功能一致
  - 验证方法：检查脚本调用是否与技能的预期行为一致
  - 一致性检查：
    1. 脚本功能与技能描述匹配
    2. 脚本输入输出符合技能预期
    3. 脚本错误处理符合技能文档说明
  - 错误示例：脚本调用与技能描述不符
  - 正确示例：
    ```yaml
    ---
    name: data-processor
    description: 处理数据文件并生成报告
    ---

    处理数据（与描述一致）：
    ```bash
    python3 ${CLAUDE_SKILL_DIR}/scripts/process.py --input data.json --output report.md
    ```
    ```

### 1.1.3 其他附属文件
- [ ] **附属文件命名规范** [可选项]：使用 kebab-case 命名
  - 验证方法：检查文件名格式
  - 错误示例：`MyFile.md`、`my_file.md`、`My File.md`
  - 正确示例：`my-file.md`、`setup-guide.md`、`api-references.md`

- [ ] **附属文件扩展名合理** [可选项]：根据文件类型使用正确的扩展名
  - 验证方法：检查文件扩展名
  - 常见扩展名：
    - Markdown 文件：`.md`
    - Shell 脚本：`.sh`
    - Python 脚本：`.py`
    - JavaScript 文件：`.js`
    - 配置文件：`.yaml`、`.json`、`.toml`
    - 文本文件：`.txt`

## 1.2 文件引用正确性检查

### 1.2.1 引用路径检查
- [ ] **SKILL.md 中引用的附属文件路径正确** [必选项]：确保路径格式正确
  - 验证方法：检查 Markdown 中的文件引用
  - 支持的路径格式：
    - `references/stages/01-stage1.md`：子目录中的文件
    - `./references/stages/01-stage1.md`：显式子目录中的文件
    - `examples/basic-usage.md`：子目录中的文件
    - `../shared/common.md`：上级目录中的文件

- [ ] **相对路径格式正确** [必选项]：使用正确的相对路径语法
  - 验证方法：检查路径分隔符和路径格式
  - 错误示例：
    - `examples\basic-usage.md`（使用反斜杠）
    - `examples//basic-usage.md`（多余斜杠）
  - 正确示例：
    - `examples/basic-usage.md`（使用正斜杠）

### 1.2.2 文件存在性检查
- [ ] **引用的文件实际存在** [必选项]：确保所有引用的文件都存在
  - 验证方法：逐个检查引用的文件
  - 错误示例：引用不存在的文件
  - 正确示例：所有引用的文件都实际存在

- [ ] **引用的目录实际存在** [必选项]：确保引用的目录存在
  - 验证方法：检查引用的目录路径
  - 错误示例：引用不存在的目录
  - 正确示例：引用的目录都实际存在

### 1.2.3 循环引用检查
- [ ] **无循环引用** [必选项]：避免文件之间的循环引用
  - 验证方法：构建引用图并检查环路
  - 错误示例：
    - A.md 引用 B.md
    - B.md 引用 A.md
  - 正确示例：单向引用或层次化引用

- [ ] **引用层次合理** [可选项]：建立合理的引用层次结构
  - 验证方法：检查引用的层次性
  - 错误示例：复杂的交叉引用网络
  - 正确示例：清晰的层次化引用结构
    ```
    SKILL.md
    ├── references/
    ├── examples/
    │   ├── basic.md
    │   └── advanced.md
    └── scripts/
        └── setup.sh
    ```

## 1.3 附属文件内容检查

### 1.3.1 references/ 目录内容检查
- [ ] **references/ 目录内容完整** [可选项]：实现细节应包含完整的实现信息
  - 验证方法：检查 references/ 目录下的文件完整性
  - 应包含的文件类型：
    - `stages/`：阶段实现文档（如分阶段执行）
    - `implementation/`：具体实现文档
    - `scripts/`：可执行脚本
    - `templates/`：模板文件
    - `core-rules.md`：核心规则（如有）
    - `data.md`：数据规范（如有）
    - `token-management.md`：Token 管理（如有）
  - 错误示例：内容不完整，缺少关键实现信息
  - 正确示例：内容完整，覆盖主要实现细节

- [ ] **references/ 目录内容有结构** [可选项]：实现细节应有清晰的文件组织
  - 验证方法：检查 references/ 目录的文件组织方式
  - 推荐结构：
    ```
    references/
    ├── stages/                    # 阶段实现文档
    │   ├── 01-stage1.md
    │   ├── 02-stage2.md
    │   └── 03-stage3.md
    ├── implementation/             # 具体实现文档
    │   ├── agent-task-a.md
    │   └── agent-task-b.md
    ├── templates/                 # 模板文件（JSON/YAML 等）
    │   ├── config-template.json
    │   └── output-template.md
    ├── core-rules.md             # 核心规则
    ├── data.md                   # 数据规范
    └── token-management.md        # Token 管理
    ```
  - 错误示例：文件混乱，无清晰分类
  - 正确示例：文件按类型分类，结构清晰

- [ ] **references/ 目录内容有交叉引用** [可选项]：相关实现文档应有交叉引用
  - 验证方法：检查不同文件间的引用关系
  - 交叉引用示例：
    - 示例结构 A：`详见 stages/03-stage3.md`
    - 示例结构 B：`参考 implementation/agent-task-a.md`
    - 示例结构 C：`与 core-rules.md 保持一致`
  - 错误示例：内容孤岛，无任何引用
  - 正确示例：有合理的交叉引用和导航

- [ ] **references/ 目录内容有版本说明** [可选项]：实现细节应说明适用版本
  - 验证方法：检查是否有版本信息
  - 版本信息内容：
    - 实现版本号
    - 适用技能版本
    - 更新日期
    - 变更历史
  - 错误示例：无版本信息
  - 正确示例：
    ```markdown
    # 实现文档

    实现版本：v1.2.0
    适用技能版本：v1.0.0+
    更新日期：2026-05-07

    ## 变更历史

    ### v1.2.0 (2026-05-07)
    - 新增：阶段3的Token预算控制
    - 更新：脚本错误处理

    ### v1.1.0 (2026-04-15)
    - 新增：阶段2的并发控制
    - 更新：模板格式
    ```

### 1.3.2 示例文件内容
- [ ] **示例文件内容完整** [可选项]：示例应该是完整可用的
  - 验证方法：检查示例文件的完整性
  - 错误示例：不完整的示例片段
  - 正确示例：完整的、可运行的示例

- [ ] **示例文件有代表性** [可选项]：示例应覆盖主要使用场景
  - 验证方法：检查示例的多样性
  - 建议包含的示例类型：
    - 基本用法
    - 高级用法
    - 边界情况
    - 常见错误
    - 最佳实践

- [ ] **示例文件有说明** [可选项]：复杂示例应有详细说明
  - 验证方法：检查示例文件的注释和说明
  - 错误示例：复杂示例无任何说明
  - 正确示例：
    ```markdown
    # 高级用法示例

    本示例展示了如何处理复杂的输入场景，包括：
    - 多重参数传递
    - 错误处理
    - 结果验证

    ## 示例代码

    ```python
    # 详细注释的代码示例
    ```
    ```

### 1.3.3 scripts/ 目录脚本文件检查
- [ ] **脚本文件有执行权限** [必选项]：可执行脚本应有执行权限
  - 验证方法：检查文件权限（`ls -l`）
  - 错误示例：Shell 脚本无执行权限（`-rw-r--r--`）
  - 正确示例：Shell 脚本有执行权限（`-rwxr-xr-x`）

- [ ] **脚本文件有错误处理** [必选项]：脚本应包含基本的错误处理
  - 验证方法：检查脚本中的错误处理逻辑
  - 错误示例：脚本无任何错误处理
  - 正确示例：
    ```bash
    #!/bin/bash
    set -e  # 遇到错误时退出

    # 错误处理示例
    if ! command -v git &> /dev/null; then
        echo "错误：git 未安装"
        exit 1
    fi
    ```

- [ ] **脚本文件有日志输出** [可选项]：重要操作应有日志输出
  - 验证方法：检查脚本中的日志语句
  - 错误示例：静默执行，无任何输出
  - 正确示例：
    ```bash
    echo "开始部署..."
    echo "构建应用..."
    echo "部署完成！"
    ```

### 1.3.4 templates/ 目录模板文件检查
- [ ] **模板文件占位符清晰** [可选项]：占位符应清晰易懂
  - 验证方法：检查占位符的命名和格式
  - 错误示例：
    - `{{p}}`：过于简短
    - `{{PLACEHOLDER1}}`：无意义的编号
  - 正确示例：
    - `{{PROJECT_NAME}}`：有意义的名称
    - `{{AUTHOR_EMAIL}}`：清晰的语义

- [ ] **模板文件有使用说明** [可选项]：模板应附带使用说明
  - 验证方法：检查模板文件或相关文档
  - 错误示例：模板无任何说明
  - 正确示例：
    ```markdown
    # 模板使用说明

    本模板用于生成标准化的配置文件。

    ## 占位符说明

    - `{{PROJECT_NAME}}`：项目名称（必需）
    - `{{VERSION}}`：版本号（可选，默认 1.0.0）
    - `{{AUTHOR}}`：作者信息（必需）

    ## 使用方法

    替换占位符后保存为 `config.yaml`
    ```

### 1.3.5 references/ 一致性检查
- [ ] **references/ 与 SKILL.md 一致** [必选项]：实现细节应与 SKILL.md 保持一致
  - 验证方法：对比 references/ 和主文件的内容
  - 一致性检查：
    - 阶段和步骤一致
    - 脚本调用方式一致
    - 数据格式一致
    - 规则和约束一致
  - 错误示例：references/ 与主文件内容矛盾
  - 正确示例：references/ 与主文件内容一致

- [ ] **references/ 内部文件之间一致** [必选项]：references/ 内多个文件应保持一致
  - 验证方法：对比 references/ 内不同文件的内容
  - 一致性检查：
    - 使用相同的术语
    - 遵循相同的规范
    - 阶段顺序正确
    - 数据结构一致
  - 错误示例：不同文件使用不一致的术语或逻辑
  - 正确示例：references/ 内文件之间保持一致

- [ ] **references/ 有更新维护** [可选项]：references/ 文件应保持更新
  - 验证方法：检查 references/ 的更新日期和内容
  - 错误示例：references/ 过时，与当前 SKILL.md 不符
  - 正确示例：references/ 定期更新，内容最新

## 1.4 文件组织最佳实践

### 1.4.1 目录结构组织
- [ ] **目录结构合理** [可选项]：采用清晰的目录层次结构
  - 验证方法：检查目录的组织方式
  - 推荐结构：
    ```
    my-skill/
    ├── SKILL.md              # 主文件
    ├── README.md             # 可选的技能说明
    ├── scripts/             # 可执行脚本
    │   ├── script1.py
    │   └── script2.sh
    ├── references/            # 技能实现细节
    │   ├── stages/          # 阶段实现文档
    │   │   ├── 01-stage1.md
    │   │   ├── 02-stage2.md
    │   │   └── 03-stage3.md
    │   ├── implementation/  # 具体实现文档
    │   ├── templates/       # 模板文件（JSON/YAML 等）
    │   ├── core-rules.md   # 核心规则（可选）
    │   ├── data.md         # 数据规范（可选）
    │   └── token-management.md  # Token 管理（可选）
    ├── CHANGELOG.md          # 可选的变更日志
    ├── examples/             # 使用示例目录
    │   ├── basic-usage.md
    │   └── advanced-usage.md
    └── templates/            # 用户模板目录
        └── template.md

### 1.4.2 文件依赖管理
- [ ] **文件依赖清晰** [必选项]：文件之间的依赖关系应清晰
  - 验证方法：分析文件引用关系
  - 错误示例：隐式的、不明确的依赖关系
  - 正确示例：通过显式的引用建立清晰的依赖关系

### 1.4.3 文档完整性
- [ ] **文档覆盖完整** [可选项]：重要功能都有相应的文档
  - 验证方法：检查技能功能与文档的对应关系
  - 错误示例：某些功能缺少文档说明
  - 正确示例：所有功能都有相应的文档或示例

---

## 📋 附属文件检查清单

完成以下48项检查，在每项完成后标记 `[x]`：

- [ ] SKILL.md 为唯一必需文件
- [ ] template.md 存在性
- [ ] template.md 用途明确
- [ ] 模板占位符清晰
- [ ] examples/ 目录存在
- [ ] examples/ 有示例文件
- [ ] 示例文件有代表性
- [ ] 示例文件命名规范
- [ ] scripts/ 目录存在
- [ ] 脚本文件可执行
- [ ] 脚本文件有 shebang
- [ ] 脚本文件有说明
- [ ] 使用 CLAUDE_SKILL_DIR 变量引用脚本
- [ ] 脚本路径优先级正确
- [ ] Bash 工具权限配置正确
- [ ] 脚本命令白名单合理
- [ ] 脚本调用有超时控制
- [ ] 脚本调用有错误处理
- [ ] 脚本调用有日志记录
- [ ] 多行动态注入使用代码块语法
- [ ] shell 字段设置正确
- [ ] 脚本调用与技能内容一致
- [ ] 附属文件命名规范
- [ ] 附属文件扩展名合理
- [ ] SKILL.md 中引用的附属文件路径正确
- [ ] 相对路径格式正确
- [ ] 引用的文件实际存在
- [ ] 引用的目录实际存在
- [ ] 无循环引用
- [ ] 引用层次合理
- [ ] references/ 目录内容完整
- [ ] references/ 目录内容有结构
- [ ] references/ 目录内容有交叉引用
- [ ] references/ 目录内容有版本说明
- [ ] 示例文件内容完整
- [ ] 示例文件有代表性
- [ ] 示例文件有说明
- [ ] 脚本文件有执行权限
- [ ] 脚本文件有错误处理
- [ ] 脚本文件有日志输出
- [ ] 模板文件占位符清晰
- [ ] 模板文件有使用说明
- [ ] references/ 与 SKILL.md 一致
- [ ] references/ 内部文件之间一致
- [ ] references/ 有更新维护
- [ ] 目录结构合理
- [ ] 文件依赖清晰
- [ ] 文档覆盖完整

### 汇总统计
- 总检查项：48项
- 已完成：0项
- 待完成：48项
- 完成率：0%
