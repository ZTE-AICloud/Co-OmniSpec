---
description: 通过提出最多 5 个高度针对性的澄清问题, 识别当前功能规范中未充分说明的领域, 并将答案编码回规范中.
handoffs:
  - label: 构建技术计划
    agent: /omni.design
    prompt: 为规范创建计划。我正在构建...
---

# 规范澄清命令

## 用户输入

```text
$ARGUMENTS
```

在继续之前, 你**必须**考虑用户输入(如果不为空).

## 执行流程

使用 omni-clarifying 技能澄清规范模糊性.
