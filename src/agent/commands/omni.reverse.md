---
description: 从现有代码库逆向生成完整规范文档, 包含项目入口分析、接口识别、实体提取、功能分析、架构梳理、场景归纳、需求抽象、上下文建模和文档生成.
handoffs:
  - label: 创建项目章程
    agent: /omni.constitution
    prompt: 基于逆向分析结果创建或更新项目章程
    send: true
---

# omni.reverse

## 用户输入

```text
$ARGUMENTS
```

在继续之前, 你**必须**考虑用户输入(如果不为空).

## 执行流程

将上述用户输入作为上下文传递给 omni-reversing 技能，并严格遵照技能指引执行。
