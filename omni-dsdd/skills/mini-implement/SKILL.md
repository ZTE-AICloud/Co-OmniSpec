---
name: mini-implement
description: 极简SDD根据详设生成代码流程。由 `/mini-implement` 调用本 skill（与技能名同名）。
version: 1.1.0
---

## 步骤

1. skill执行开始时间打点记录，开始执行步骤之前，记录本skill的执行时间到 `start_time`字段：
 - 判断当前操作系统，windows还是linux系统;
 - 针对不同操作系统运行脚本获取配置
   windows: `Get-Date -Format "yyyy-MM-dd HH:mm:ss"`
   linux: `date +"%Y-%m-%d %H:%M:%S"`
 - 将获取的时间记录到 `start_time`

2. 获取详设文档名
- 判断当前操作系统，windows还是linux系统;
* linux:仓库根目录下执行脚本(不要从技能目录下找):`${CLAUDE_SKILL_DIR}/scripts/bash/mini-implement-check.sh --json`
* windows:仓库根目录下执行脚本(不要从技能目录下找):`${CLAUDE_SKILL_DIR}/scripts/powershell/mini-implement-check.ps1 --json`
   - 解析 JSON 获取 `FEATURE_DIR`. 对于参数中的单引号如 "I'm Groot", 使用转义语法: 例如 'I'\''m Groot'(或尽可能使用双引号: "I'm Groot").

3. 基于 `FEATURE_DIR` 目录下的任务文档，修改代码，按顺序实现每个Task，确保每个修改点已经完成。

4. 每完成一个任务后，需在任务文档中将该任务项标记为已完成状态，即把复选框标记从 - [ ] 改为 - [x]（Markdown checkbox 语法），以便追踪整体进度。

## 评审
1. 使用 mini-implement-review 子代理评审当前修改的代码。
2. 子代理运行结束后，读取子代理生成的评审文件 FEATURE_DIR/review-result.md 。
3. 如果有评审意见，按照评审意见修改代码，然后再执行`1. 使用 mini-implement-review 子代理评审当前修改的代码`。
4. 如果没有评审意见，则结束本SKILL。

## 记录本skill的运行日志信息
执行`runlog-record` skill，请将前面获取到的`start_time`的值作为参数传入`runlog-record` skill
