# 1. 前置元数据验证

前置元数据是skill的核心配置部分，直接影响技能的加载、调用和权限控制。

## 1.1 必需/推荐字段检查

### 1.1.1 name 字段

- [ ] **name 字段完整性检查** [必选项]：检查 name 字段的存在性、格式和长度
  - 验证方法：
    - 检查 YAML 中是否有 `name:` 字段
    - 使用正则 `^[a-z0-9-]+$` 检查格式
    - 检查字符串长度 <= 64
  - 完整性要求：
    - 字段必须存在（如省略则使用目录名作为技能名）
    - 只能包含小写字母、数字和连字符
    - 长度不超过64字符
  - 错误示例：
    - 缺少 name 字段
    - `MySkill`、`my_skill`、`my.skill`（格式错误）
    - 超过64字符的过长名称
  - 正确示例：
    ```yaml
    name: my-awesome-skill
    ```
    - `my-skill`、`deploy-helper`、`api-validator`

- [ ] **name 字段最佳实践** [可选项]：建议 name 字段与目录名保持一致
  - 验证方法：比较 name 字段与目录名
  - 最佳实践：保持一致以避免混淆
  - 示例：目录名 `deploy-helper` 对应 `name: deploy-helper`
  - 允许例外：有特殊原因时可以使用不同的名称，但需要在文档中说明

### 1.1.2 description 字段
- [ ] **description 字段存在** [必选项]：强烈建议提供描述字段
  - 验证方法：检查 YAML 中是否有 `description:` 字段
  - 重要性：Claude 依靠此字段判断何时自动调用技能
  - 默认行为：如省略，使用正文第一段作为描述

- [ ] **description 描述清晰** [必选项]：描述应准确反映技能的用途和适用场景
  - 验证方法：检查描述内容是否清晰明确
  - 错误示例：过于模糊的描述如"一个有用的技能"
  - 正确示例：
    ```yaml
    description: 使用可视化图表和类比解释代码。适用于解释代码工作原理、讲解代码库知识或用户提问"这是如何实现的？"等场景。
    ```

- [ ] **description 包含关键词** [必选项]：描述应包含高频场景关键词
  - 验证方法：检查描述中是否包含相关领域的关键词
  - 错误示例：缺少关键词导致自动触发困难
  - 正确示例：包含"解释"、"代码"、"原理"等关键词

- [ ] **description 长度适中** [可选项]：建议100-200字
  - 验证方法：检查描述长度
  - 错误示例：过短（<50字）或过长（>300字）
  - 最佳实践：简洁明了，既提供足够信息又不过于冗长

- [ ] **description 与内容一致** [必选项]：描述应与技能实际内容匹配
  - 验证方法：比较描述与正文内容
  - 错误示例：描述说"部署代码"但实际是"解释代码"
  - 正确示例：描述与功能完全对应

### 1.1.3 argument-hint 字段
- [ ] **argument-hint 存在性** [可选项]：如有参数应提供提示
  - 验证方法：检查技能是否使用变量参数，如有则提供 argument-hint
  - 用途：为用户提供参数提示信息
  - 正确示例：
    ```yaml
    argument-hint: [问题编号]
    ```

- [ ] **argument-hint 格式正确** [可选项]：提示信息应简洁明了
  - 验证方法：检查提示文本是否清晰易懂
  - 错误示例：`参数`（过于简单）
  - 正确示例：`[问题编号]` 或 `[文件路径]`

## 1.2 可选字段合理性检查

### 1.2.1 disable-model-invocation 字段
- [ ] **disable-model-invocation 设置合理** [必选项]：根据技能类型和调用关系正确设置
  - 验证方法：检查技能类型、调用关系与配置的匹配度
  - **被其他 skill 调用的技能（必须 false 或省略）**：
    - 作为子代理预加载的技能
    - 被其他技能通过 Agent 工具调用的技能
    - 提供基础能力的工具类技能
    - 正确示例：
      ```yaml
      # 被其他技能调用的基础技能
      disable-model-invocation: false  # 或不设置，允许自动调用
      ```
    - 错误示例：
      ```yaml
      # 被其他技能调用但禁止自动调用
      disable-model-invocation: true  # 错误！会导致调用失败
      ```

  - **任务类技能（建议 true）**：
    - 部署类技能
    - 提交代码类技能
    - 有副作用的操作
    - 正确示例：
      ```yaml
      disable-model-invocation: true
      ```

  - **参考类技能（建议 false 或省略）**：
    - 代码规范说明
    - 业务领域知识
    - 设计模式解释

- [ ] **布尔值格式正确** [必选项]：使用 true/false 而非 yes/no
  - 验证方法：检查布尔值格式
  - 错误示例：`disable-model-invocation: yes`
  - 正确示例：`disable-model-invocation: true`

### 1.2.2 user-invocable 字段
- [ ] **user-invocable 设置合理** [必选项]：根据技能用途正确设置
  - 验证方法：检查技能是否需要用户手动触发
  - 后台技能（建议 false）：
    - 纯知识类内容
    - 背景信息提供
    - 不需要用户手动执行的技能

  - 常规技能（建议 true 或省略）：
    - 需要用户明确触发的操作
    - 交互式技能

### 1.2.3 model 字段
- [ ] **model 字段值有效** [必选项]：使用当前支持的模型名称
  - 验证方法：检查模型名称是否在支持列表中
  - 支持的模型：`sonnet`、`opus`、`haiku`
  - 错误示例：`model: gpt4`、`model: claude-3`
  - 正确示例：
    ```yaml
    model: sonnet
    ```

- [ ] **model 字段必要性** [可选项]：仅在需要覆盖默认配置时使用
  - 验证方法：检查是否有特殊需求
  - 最佳实践：通常不需要指定，使用会话默认配置

### 1.2.4 effort 字段
- [ ] **effort 字段值有效** [必选项]：使用有效的努力级别
  - 验证方法：检查 effort 值是否在支持列表中
  - 支持的值：`low`、`medium`、`high`、`xhigh`、`max`（可用级别取决于模型）
  - 错误示例：`effort: high-level`、`effort: 1`
  - 正确示例：
    ```yaml
    effort: high
    ```

### 1.2.5 when_to_use 字段
- [ ] **when_to_use 字段存在性** [可选项]：当技能需要额外的触发上下文时提供
  - 验证方法：检查技能是否有需要额外说明的触发场景
  - 用途：关于 Claude 何时应该调用该 skill 的额外上下文，例如触发短语或示例请求
  - 正确示例：
    ```yaml
    when_to_use: Use when user asks "how do I deploy", mentions "production deployment", or needs to push changes to servers.
    ```

- [ ] **when_to_use 内容清晰** [必选项]：提供具体的触发场景和示例请求
  - 验证方法：检查 when_to_use 内容是否包含具体的触发短语或示例
  - 错误示例：`when_to_use: 部署应用`（过于简单）
  - 正确示例：
    ```yaml
    when_to_use: Use when user mentions "deploy", "production", "push to server", or asks about deployment process.
    ```

- [ ] **when_to_use 与 description 配合** [必选项]：与 description 组合不超过字符限制
  - 验证方法：检查 description + when_to_use 组合文本长度
  - 限制：组合文本被限制为 1,536 个字符
  - 错误示例：description 和 when_to_use 过长导致截断
  - 正确示例：前置关键用例，保持简洁

### 1.2.6 arguments 字段
- [ ] **arguments 字段存在性** [必选项]：当技能使用命名参数时提供
  - 验证方法：检查技能内容中是否使用了命名参数占位符（如 `$name`）
  - 用途：定义用于 skill 内容中 `$name` 替换的命名位置参数
  - 正确示例：
    ```yaml
    arguments: [issue, branch]
    ```

- [ ] **arguments 格式正确** [必选项]：使用空格分隔的字符串或 YAML 列表
  - 验证方法：检查 arguments 的格式
  - 支持格式：
    ```yaml
    # 空格分隔
    arguments: issue branch

    # YAML 列表
    arguments:
      - issue
      - branch
    ```
  - 错误示例：使用逗号分隔或其他错误格式
  - 正确示例：使用推荐的两种格式之一

- [ ] **arguments 与内容匹配** [必选项]：参数名称与正文中的占位符对应
  - 验证方法：检查 arguments 定义的名称在正文中都有对应的 `$name` 占位符
  - 错误示例：
    ```yaml
    arguments: [issue, branch]
    # 正文中没有使用 $issue 或 $branch 占位符
    ```
  - 正确示例：
    ```yaml
    arguments: [issue, branch]
    # Fix GitHub issue $issue on branch $branch following our coding standards.
    ```

- [ ] **参数顺序正确** [必选项]：参数按顺序映射到位置
  - 验证方法：检查 arguments 中的顺序与调用时的参数位置对应
  - 映射规则：名称按顺序映射到参数位置（$0, $1, $2...）
  - 错误示例：顺序混乱导致参数值错位
  - 正确示例：
    ```yaml
    arguments: [issue, branch]
    # /fix-issue 123 feature-branch
    # $issue 映射到 123，$branch 映射到 feature-branch
    ```

### 1.2.7 paths 字段
- [ ] **paths 字段存在性** [必选项]：当技能需要限定激活文件时提供
  - 验证方法：检查技能是否只应在特定文件被处理时激活
  - 用途：Glob 模式，限制何时激活此 skill
  - 正确示例：
    ```yaml
    paths: src/**/*.ts test/**/*.ts
    ```

- [ ] **paths 格式正确** [必选项]：使用逗号分隔或 YAML 列表格式
  - 验证方法：检查 paths 的格式和 Glob 模式
  - 支持格式：
    ```yaml
    # 逗号分隔
    paths: src/**/*.ts, test/**/*.ts

    # YAML 列表
    paths:
      - src/**/*.ts
      - test/**/*.ts
    ```
  - 错误示例：使用无效的 Glob 模式
  - 正确示例：使用标准的 Glob 模式语法

- [ ] **paths 模式合理** [必选项]：Glob 模式与技能目标文件匹配
  - 验证方法：验证 Glob 模式能正确匹配目标文件
  - 常用 Glob 模式：
    - `*.js`：所有 JS 文件
    - `src/**/*.py`：src 目录下所有 Python 文件（递归）
    - `**/*.ts`：所有 TypeScript 文件
  - 错误示例：模式过于宽泛或不匹配目标文件
  - 正确示例：模式精准覆盖技能相关的文件类型和目录

- [ ] **paths 与技能适用性一致** [必选项]：paths 限制不应影响技能核心功能
  - 验证方法：检查 paths 限制是否合理，不会导致技能在需要时无法激活
  - 错误示例：paths 限制过窄，导致技能在应该激活时不激活
  - 正确示例：paths 范围合理，既限定适用范围又不影响正常使用

### 1.2.8 shell 字段
- [ ] **shell 字段存在性** [必选项]：当技能使用内联 shell 命令时考虑设置
  - 验证方法：检查技能内容中是否包含 `!`command` `` 或 ```! ` 块
  - 用途：指定此 skill 中 `!`command` `` 和 ```! ` 块的 shell
  - 支持值：`bash`（默认）、`powershell`
  - 正确示例：
    ```yaml
    shell: powershell
    ```

- [ ] **shell 字段值有效** [必选项]：使用支持的 shell 类型
  - 验证方法：检查 shell 字段值是否在支持列表中
  - 支持的值：`bash`（默认）、`powershell`
  - PowerShell 要求：需要 `CLAUDE_CODE_USE_POWERSHELL_TOOL=1` 环境变量
  - 错误示例：`shell: cmd`、`shell: zsh`
  - 正确示例：
    ```yaml
    shell: powershell  # Windows 环境
    ```

- [ ] **shell 配置与平台匹配** [必选项]：shell 类型应与目标平台匹配
  - 验证方法：检查技能是否在特定平台使用
  - 最佳实践：跨平台技能使用默认 bash，Windows 专用技能使用 powershell
  - 错误示例：在跨平台技能中指定 powershell
  - 正确示例：根据平台需求合理设置 shell

### 1.2.9 context 和 agent 字段
- [ ] **context 设置合理性** [必选项]：仅在需要子代理时设置
  - 验证方法：检查是否真的需要隔离执行环境
  - 使用场景：
    - 长时间运行的任务
    - 高复杂度任务
    - 需要隔离上下文的任务

- [ ] **context: fork 时指定 agent** [必选项]：必须同时指定 agent 类型
  - 验证方法：检查 context: fork 时是否有 agent 字段
  - 错误示例：
    ```yaml
    context: fork
    # 缺少 agent 字段
    ```
  - 正确示例：
    ```yaml
    context: fork
    agent: Explore
    ```

- [ ] **agent 类型有效** [必选项]：使用支持的代理类型
  - 验证方法：检查 agent 类型是否在支持列表中
  - 常用类型：
    - `Explore`：探索代码库
    - `Plan`：设计实现方案
    - `general-purpose`：通用任务
    - `omni-dsdd:*`：特定的 Omni 代理
  - 错误示例：`agent: CustomAgent`
  - 正确示例：
    ```yaml
    agent: Explore
    ```

### 1.2.10 hooks 字段
- [ ] **hooks 配置语法正确** [必选项]：确保钩子配置格式正确
  - 验证方法：检查 YAML 语法
  - 常用钩子类型：`pre`、`post`、`error`
  - 正确示例：
    ```yaml
    hooks:
      pre: validate-input
      post: cleanup
      error: handle-error
    ```

## 1.3 元数据最佳实践

### 1.3.1 字段值格式
- [ ] **无多余空格或引号** [必选项]：字段值应简洁明了
  - 验证方法：检查字段值周围是否有多余空格或不必要的引号
  - 错误示例：
    ```yaml
    name:  "my-skill"  
    description: ' 技能描述 '
    ```
  - 正确示例：
    ```yaml
    name: my-skill
    description: 技能描述
    ```

- [ ] **布尔值格式正确** [必选项]：使用标准的 YAML 布尔值
  - 验证方法：检查布尔值是否使用 true/false
  - 错误示例：`yes`、`no`、`ON`、`OFF`、`1`、`0`
  - 正确示例：`true`、`false`

### 1.3.2 列表格式
- [ ] **列表格式正确** [必选项]：使用逗号分隔或 YAML 数组格式
  - 验证方法：检查列表语法
  - 支持的格式：
    ```yaml
    # 逗号分隔
    allowed-tools: Read, Grep, Glob

    # YAML 数组
    allowed-tools:
      - Read
      - Grep
      - Glob
    ```
  - 错误示例：混合使用不同格式
  - 正确示例：保持格式一致性

### 1.3.3 字段顺序
- [ ] **字段顺序合理** [可选项]：建议按照重要性排列字段
  - 推荐顺序：
    1. name（必需）
    2. description（推荐）
    3. argument-hint（如有）
    4. 其他可选字段

### 1.3.4 注释和文档
- [ ] **复杂配置有注释** [可选项]：对于复杂的元数据配置提供注释
  - 验证方法：检查 YAML 中是否使用了 `#` 注释
  - 正确示例：
    ```yaml
    # 禁用模型自动调用，仅允许用户手动触发
    disable-model-invocation: true

    # 指定使用 Opus 模型以获得更高的推理能力
    model: opus
    ```

---

## 📋 前置元数据验证检查清单

完成以下38项检查，在每项完成后标记 `[x]`：

- [ ] name 字段完整性检查
- [ ] name 字段最佳实践
- [ ] description 字段存在
- [ ] description 描述清晰
- [ ] description 包含关键词
- [ ] description 长度适中
- [ ] description 与内容一致
- [ ] argument-hint 存在性
- [ ] argument-hint 格式正确
- [ ] disable-model-invocation 设置合理
- [ ] 被其他 skill 调用的技能不能设置 true
- [ ] 布尔值格式正确
- [ ] user-invocable 设置合理
- [ ] model 字段值有效
- [ ] model 字段必要性
- [ ] effort 字段值有效
- [ ] when_to_use 字段存在性
- [ ] when_to_use 内容清晰
- [ ] when_to_use 与 description 配合
- [ ] arguments 字段存在性
- [ ] arguments 格式正确
- [ ] arguments 与内容匹配
- [ ] 参数顺序正确
- [ ] paths 字段存在性
- [ ] paths 格式正确
- [ ] paths 模式合理
- [ ] paths 与技能适用性一致
- [ ] shell 字段存在性
- [ ] shell 字段值有效
- [ ] shell 配置与平台匹配
- [ ] context 设置合理性
- [ ] context: fork 时指定 agent
- [ ] agent 类型有效
- [ ] hooks 配置语法正确
- [ ] 无多余空格或引号
- [ ] 布尔值格式正确
- [ ] 列表格式正确
- [ ] 字段顺序合理
- [ ] 复杂配置有注释

### 汇总统计
- 总检查项：38 项
- 已完成：0 项
- 待完成：38 项
- 完成率：0%
