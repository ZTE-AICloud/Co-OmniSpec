---
description: 执行实施规划工作流, 使用计划模板生成设计制品.
handoffs:
  - label: 创建任务
    agent: /omni.tasks
    prompt: 将计划分解为任务
    send: true
  - label: 创建检查清单
    agent: /omni.checklist
    prompt: 为需求创建质量检查清单
    send: true
---

# omni.design

## 用户输入

```text
$ARGUMENTS
```

在继续之前, 你**必须**考虑用户输入(如果不为空).

## 执行流程

将上述用户输入作为上下文传递给 omni-designing 技能，并严格遵照技能指引执行。

