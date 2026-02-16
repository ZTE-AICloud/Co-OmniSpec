---
description: 从自然语言功能描述创建或更新功能规范.
handoffs:
  - label: 构建技术计划
    agent: /omni.design
    prompt: 为规范创建计划。我正在构建...
  - label: 澄清规范需求
    agent: /omni.clarify
    prompt: 分析规范的完整性和清晰度
    send: true
---

## 用户输入

```text
$ARGUMENTS
```

在继续之前, 你**必须**考虑用户输入(如果不为空).

## 执行流程

将上述用户输入作为上下文传递给 [omni-specifying] 技能，并严格遵照技能指引执行。