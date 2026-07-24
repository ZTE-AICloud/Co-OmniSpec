# 1. 基础结构与层级检查

检查技能的基础结构和层级配置，确保技能能正常加载和识别。

## 1.1 必需文件检查

- [ ] **SKILL.md 文件存在且位置正确** [必选项]：检查 skill 目录根目录下是否存在 SKILL.md 文件
  - 验证方法：使用 `ls -la $ARGUMENTS/SKILL.md` 或检查文件存在性和路径
  - 文件要求：
    - 必须存在于技能目录根目录
    - 路径必须为 `$ARGUMENTS/SKILL.md`
    - 不能位于子目录中
  - 错误示例：
    - 缺少 SKILL.md 文件导致技能无法加载
    - `my-skill/docs/SKILL.md` 或 `my-skill/subdirectory/SKILL.md`（位置错误）
  - 正确示例：`my-skill/SKILL.md`

- [ ] **YAML 前置元数据有效** [必选项]：检查 SKILL.md 是否包含有效的 YAML 前置元数据
  - 验证方法：检查文件开头是否有 `---` 包裹的 YAML 块
  - 错误示例：缺少 `---` 分隔符或 YAML 格式错误
  - 正确示例：
    ```yaml
    ---
    name: my-skill
    description: 技能描述
    ---
    正文内容...
    ```

## 1.2 目录结构检查

- [ ] **技能目录名称规范** [警告]：目录名只能包含小写字母、数字和连字符
  - 验证方法：使用正则 `^[a-z0-9-]+$` 检查目录名
  - 错误示例：`MySkill`、`my_skill`、`my skill`、`my.skill`
  - 正确示例：`my-skill`、`deploy-script`、`api-helper`

- [ ] **目录名长度限制** [必选项]：最大64字符
  - 验证方法：检查目录名长度 <= 64
  - 错误示例：超过64字符的长目录名
  - 正确示例：简洁明了的目录名

- [ ] **无旧格式冲突** [必选项]：检查是否存在与 `.claude/commands/` 的冲突
  - 验证方法：检查是否存在同名的旧命令文件
  - 冲突示例：同时存在 `.claude/commands/deploy.md` 和 `deploy/SKILL.md`
  - 解决方案：优先使用技能格式，移除旧命令文件

- [ ] **附属文件目录结构合理** [可选项]：检查附属文件的组织是否合理 [必选项]:
  - 可选目录：
    - `references/`：存放技能具体实现细节
    - `examples/`：存放使用示例
    - `scripts/`：存放可执行脚本
    - `templates/`：存放模板文件
  - 错误示例：将所有文件堆在根目录下
  - 正确示例：
    ```
    my-skill/
    ├── SKILL.md
    ├── references/               # Markdown 实现文档
    │   ├── stages/              # 阶段实现文档
    │   ├── implementation/      # 具体实现文档
    │   ├── templates/           # 模板文件（JSON/YAML 等）
    │   ├── core-rules.md        # 核心规则
    │   ├── data.md             # 数据规范
    │   └── token-management.md  # Token 管理
    ├── scripts/                 # 可执行脚本
    │   ├── script1.py
    │   └── script2.sh
    ├── examples/
    │   ├── example1.md
    │   └── example2.md
    └── templates/
        └── template.md
    ```

### 1.2.1 references/ 目录检查

- [ ] **references/ 目录存在性检查** [必选项]：检查技能是否包含 references/ 目录
  - 验证方法：检查根目录下是否有 references/ 目录
  - 用途：
    - 存放技能的具体实现细节
    - 提供 AI Agent 执行时的详细指导
    - 包含可执行的脚本和工具
    - 存储配置模板和数据
  - 何时需要：
    - SKILL.md 需要调用脚本或工具
    - 有复杂的分阶段实现逻辑
    - 需要具体的执行步骤和规范
    - 有可重用的配置模板
  - 错误示例：需要具体实现的技能缺乏 references/ 目录
  - 正确示例：包含完整的 references/ 目录

- [ ] **references/ 目录组织合理** [可选项]：检查实现细节的组织结构 [必选项]:
  - 验证方法：检查 references/ 目录下的文件组织
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

### 1.2.2 技能间调用检查

- [ ] **子技能调用规范** [必选项]：检查技能调用其他技能的方式
  - 验证方法：检查是否有调用其他技能的描述
  - 调用方式说明：
    - 通过 /skill-name 直接调用子技能
    - 通过 description 自动触发子技能
    - 在技能内容中说明调用关系
  - 错误示例：技能间调用关系不明确
  - 正确示例：
    ```markdown
    ## 技能依赖

    本技能会调用以下技能：
    - /api-conventions：提供 API 设计规范
    - /code-formatter：格式化生成的代码

    调用方式：Claude 会自动加载这些技能的参考内容
    ```

- [ ] **子技能调用避免循环** [警告]：确保技能间没有循环调用
  - 验证方法：分析技能调用关系图
  - 循环调用示例：
    - skill-a 调用 skill-b
    - skill-b 调用 skill-a
  - 影响：
    - 可能导致无限递归
    - 影响性能
    - 消耗上下文配额
  - 错误示例：存在循环调用关系
  - 正确示例：调用关系为有向无环图（DAG）

- [ ] **子技能调用有说明** [必选项]：明确说明技能间的调用关系
  - 验证方法：检查是否有调用关系说明
  - 说明内容：
    - 依赖的技能列表
    - 调用的时机
    - 调用的方式（自动/手动）
    - 调用的目的
  - 错误示例：调用其他技能但无说明
  - 正确示例：
    ```markdown
    ## 技能依赖

    本技能依赖以下技能：

    ### /api-conventions
    - 调用方式：自动加载（Claude 会自动引入）
    - 调用时机：生成 API 接口时
    - 调用目的：遵循项目 API 设计规范

    ### /code-formatter
    - 调用方式：手动调用
    - 调用时机：代码生成完成后
    - 调用目的：格式化生成的代码

    注意：确保这些依赖技能已正确安装和配置
    ```

- [ ] **子技能命名空间正确** [必选项]：如调用插件技能，使用正确的命名空间
  - 验证方法：检查插件技能的调用方式
  - 命名空间格式：`plugin-name:skill-name`
  - 错误示例：
    - 调用插件技能时未使用命名空间
    - 命名空间拼写错误
  - 正确示例：
    ```markdown
    ## 技能依赖

    本技能会调用以下插件技能：
    - my-plugin:deploy-skill：提供部署功能
    - my-plugin:validator-skill：提供验证功能

    注意：需要先安装 my-plugin 插件
    ```

### 1.2.3 附属文件引用规范

- [ ] **附属文件引用格式正确** [必选项]：使用标准的 Markdown 引用格式
  - 验证方法：检查引用的格式
  - 正确格式：
    ```markdown
    - 完整 API 文档：[references/stages/01-stage1.md](references/stages/01-stage1.md)
    - 使用示例：[examples/basic-usage.md](examples/basic-usage.md)
    - 详细说明：参考 [references/](references/) 目录中的相关章节
    - 更多示例：查看 [examples/](examples/) 目录
    ```
  - 错误示例：
    - 引用格式错误
    - 使用绝对路径
    - 引用不存在的文件
  - 正确示例：使用标准的 Markdown 相对路径引用

- [ ] **附属文件引用有说明** [必选项]：每个引用都应有说明用途
  - 验证方法：检查引用是否附带说明
  - 错误示例：孤立的引用，无任何说明
  - 正确示例：
    ```markdown
    ## 补充资源

    - 完整 API 文档：[references/stages/01-stage1.md](references/stages/01-stage1.md)
      - 包含所有 API 接口的详细说明
      - 提供请求/响应示例
      - 说明错误码和处理方式

    - 基础使用示例：[examples/basic-usage.md](examples/basic-usage.md)
      - 展示最基本的调用方式
      - 包含完整的代码示例

    - 高级使用场景：[examples/advanced-usage.md](examples/advanced-usage.md)
      - 展示复杂的集成场景
      - 包含错误处理和最佳实践
    ```

- [ ] **附属文件引用分组合理** [必选项]：按类型或用途分组引用
  - 验证方法：检查引用的组织方式
  - 分组方式：
    - 按文件类型分组（文档/示例/脚本）
    - 按功能分组（API/配置/部署）
    - 按复杂度分组（基础/进阶/高级）
  - 错误示例：引用混乱，无分组
  - 正确示例：
    ```markdown
    ## 补充资源

    ### 实现细节
    - 阶段文档：[references/stages/](references/stages/)
    - 核心规则：[references/core-rules.md](references/core-rules.md)
    - 实现文档：[references/implementation/](references/implementation/)
    - 设计模式：[references/patterns.md](references/patterns.md)

    ### 使用示例
    - 基础示例：[examples/basic.md](examples/basic.md)
    - 高级示例：[examples/advanced.md](examples/advanced.md)

    ### 辅助脚本
    - 设置脚本：[scripts/setup.sh](scripts/setup.sh)
    - 验证脚本：[scripts/validate.py](scripts/validate.py)
    ```

## 1.3 文件命名规范

- [ ] **使用 kebab-case 命名**：所有文件名使用小写字母和连字符
  - 验证方法：检查文件名符合 `^[a-z0-9-.]+$` 模式
  - 错误示例：`MyFile.md`、`my_file.md`、`My File.md`
  - 正确示例：`my-file.md`、`setup-script.sh`

- [ ] **无特殊字符** [必选项]：文件名不应包含空格、中文等特殊字符
  - 验证方法：检查文件名只包含字母、数字、连字符、点和下划线
  - 错误示例：`我的文件.md`、`file name.md`、`file@name.md`
  - 正确示例：`my-file.md`、`file_name.md`

- [ ] **SKILL.md 文件名完全匹配** [必选项]：必须使用确切的 SKILL.md 文件名
  - 验证方法：检查文件名是否为 "SKILL.md"（区分大小写）
  - 错误示例：`skill.md`、`Skill.md`、`SKILL.MD`
  - 正确示例：`SKILL.md`

- [ ] **附属文件扩展名合理** [必选项]：根据文件类型使用正确的扩展名
  - Markdown 文件：`.md`
  - Shell 脚本：`.sh`
  - Python 脚本：`.py`
  - JavaScript 文件：`.js`
  - 错误示例：`script.txt`、`markdown.md.md`
  - 正确示例：`api-references.md`、`setup.sh`、`helper.py`

## 1.4 技能层级检查

- [ ] **技能层级识别**：识别技能的存放层级 [必选项]:
  - 验证方法：根据路径识别技能层级
  - 层级分类：
    - 企业级：通过托管设置配置
    - 个人级：`~/.claude/skills/`
    - 项目级：`.claude/skills/`
    - 插件级：`<plugin>/skills/`
    - 附加目录：通过 --add-dir 添加
  - 错误示例：放在不支持的位置
  - 正确示例：放在支持的层级位置

- [ ] **技能优先级有说明**：说明技能的优先级关系 [必选项]:
  - 验证方法：检查是否有优先级说明
  - 优先级顺序：企业级 > 个人级 > 项目级
  - 错误示例：同名技能无优先级说明
  - 正确示例：
    ```markdown
    ## 技能层级

    本技能存放位置：个人级（~/.claude/skills/）
    优先级：高于项目级技能，低于企业级技能

    如存在同名冲突，优先级更高的技能会优先生效。
    ```

## 1.5 嵌套目录检查

- [ ] **嵌套目录技能说明**：如为嵌套目录技能，应有说明 [必选项]:
  - 验证方法：检查是否在嵌套目录中
  - 适用场景：
    - 单体仓库（monorepo）
    - 每个子包拥有独立技能
  - 错误示例：嵌套目录技能无说明
  - 正确示例：
    ```markdown
    ## 技能位置

    本技能位于 packages/frontend/.claude/skills/ 目录
    适用于：packages/frontend/ 子包的开发工作
    自动触发：编辑 packages/frontend/ 中的文件时
    ```

- [ ] **嵌套目录路径合理**：确保嵌套目录路径结构合理 [必选项]:
  - 验证方法：检查目录层次深度
  - 建议：避免过深的嵌套层次（建议不超过 3 层）
  - 错误示例：过深的嵌套层次
  - 正确示例：合理的嵌套层次

---

## 📋 基础结构与层级检查清单

完成以下23项检查，在每项完成后标记 `[x]`：

- [ ] SKILL.md 文件存在且位置正确
- [ ] YAML 前置元数据有效
- [ ] 技能目录名称规范
- [ ] 目录名长度限制
- [ ] 无旧格式冲突
- [ ] 附属文件目录结构合理
- [ ] references/ 目录存在性检查
- [ ] references/ 目录组织合理
- [ ] 子技能调用规范
- [ ] 子技能调用避免循环
- [ ] 子技能调用有说明
- [ ] 子技能命名空间正确
- [ ] 附属文件引用格式正确
- [ ] 附属文件引用有说明
- [ ] 附属文件引用分组合理
- [ ] 使用 kebab-case 命名
- [ ] 无特殊字符
- [ ] SKILL.md 文件名完全匹配
- [ ] 附属文件扩展名合理
- [ ] 技能层级识别
- [ ] 技能优先级有说明
- [ ] 嵌套目录技能说明
- [ ] 嵌套目录路径合理

### 汇总统计
- 总检查项：23项
- 已完成：0项
- 待完成：23项
- 完成率：0%
