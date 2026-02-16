---
description: 基于可用的设计文档, 为功能特性生成可执行的、按依赖关系排序的 tasks.md 文件.
handoffs:
    - label: 分析一致性
      agent: /omni.analyze
      prompt: 运行项目一致性分析
      send: true
    - label: 实施项目
      agent: /omni.implement
      prompt: 实施项目
      send: true
---

## 用户输入

```text
$ARGUMENTS
```

在继续之前, 你**必须**考虑用户输入(如果不为空).

## 执行流程

使用 [omni-tasking] 技能生成任务列表、制定实施计划
