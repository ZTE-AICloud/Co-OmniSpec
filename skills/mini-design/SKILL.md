---
name: mini-design
description: 极简SDD生成详设流程，根据输入的方案要求结合代码生成详设文档。由 `/mini-design` 调用本 skill（与技能名同名）。
version: 1.0.0
---

# Mini Design Skill

极简SDD流程，根据输入的方案要求结合代码生成详设文档.

## 触发条件

当用户需要：
- 从自然语言描述创建功能详设文档
- 将需求转化为结构化的设计规范
- 生成可执行的开发计划文档

## 执行步骤

### 0. skill执行开始时间打点记录

开始执行步骤之前，需要进行一些打点记录工作，记录本skill的执行时间到 `start_time`字段：
 - 判断当前操作系统，windows还是linux系统;
 - 针对不同操作系统运行脚本获取配置
   windows: `Get-Date -Format "yyyy-MM-dd HH:mm:ss"`
   linux: `date +"%Y-%m-%d %H:%M:%S"`
 - 将获取的时间记录到 `start_time`

### 1. 分支创建

1. **为分支生成一个简短名称**(2-4个词):
   - 分析功能描述并提取最有意义的关键词
   - 创建一个2-4个词的简短名称, 捕捉功能的核心
   - 尽可能使用动-名词格式(例如, "add-user-auth", "fix-payment-bug")
   - 保留技术术语和缩写(OAuth2、API、JWT等)
   - 保持简洁但足够描述性, 便于快速理解功能
   - 示例:
     - "I want to add user authentication" → "user-auth"
     - "Implement OAuth2 integration for the API" → "oauth2-api-integration"
     - "Create a dashboard for analytics" → "analytics-dashboard"
     - "Fix payment processing timeout bug" → "fix-payment-timeout"

2. 仓库根目录下执行脚本(不要从技能目录下找) 
- 判断当前操作系统，windows还是linux系统;
* windows: `scripts/powershell/mini-create-new-feature.ps1 --json "$ARGUMENTS"`  
* linux: `scripts/bash/mini-create-new-feature.sh --json "$ARGUMENTS"`  
 **使用简短名称参数**并解析其 JSON 输出以获取 BRANCH_NAME 、 SPEC_FILE 、FEATURE_DIR. 所有文件路径必须是绝对路径.

3. **重要说明**:
   - 将第1步创建的2-4词简短名称作为参数附加到
   linux： `scripts/bash/mini-create-new-feature.sh --json "$ARGUMENTS"` 
   windows：`scripts/bash/mini-create-new-feature.sh --json "$ARGUMENTS"` 
    命令, 功能描述作为最终参数.
   - Bash 示例: `--short-name "your-generated-short-name" "功能描述内容"`
   - 对于参数中包含单引号的情况(如 "I'm Groot"), 使用转义语法: 例如 'I'\''m Groot'(或优先使用双引号: "I'm Groot")
   - 你必须且只能运行此脚本一次
   - JSON 输出会显示在终端中 - 请始终参考该输出来获取你要查找的实际内容

### 2. 详设生成
1. 加载上下文，SPEC_FILE 以了解必需的章节.
2. 将上述用户输入作为上下文传递给 `spec-impact-analyze` 技能，并严格遵照技能指引执行。
3. 读取搜集的与用户需求相关文档 FEATURE_DIR/context.md ，查找与用户需求相关的代码, 完成 SPEC_FILE 详设文档编写, 保持章节顺序和标题.

### 3. 检查校验
1. 使用 mini-design-review 子代理评审输出的详设文档。
2. 子代理运行结束后，读取子代理生成的评审文件 FEATURE_DIR/review-result.md 。
3. 如果有评审意见，按照评审意见修改 SPEC_FILE，然后再执行`步骤1 使用 mini-design-review 子代理评审输出的详设文档`。
4. 如果没有评审意见，则执行后续步骤。

### 4. 记录本skill的运行日志信息

执行`runlog-record` skill，请将前面获取到的`start_time`的值作为参数传入`runlog-record` skill

## 输出结果

完成后应告知用户：
- 创建了分支 BRANCH_NAME
- 完成了详设文档 SPEC_FILE
- 提示下一步：使用极简SDD，完成代码开发

## 注意事项

- **不要修改代码**，只需要按照要求输出详设文档
- 始终使用中文回答
- 确保详设文档的章节顺序和标题与模板一致
