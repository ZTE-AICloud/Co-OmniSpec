---
name: reverse-shared
description: 反构流程共用的模板与说明文档. 当其他 reverse-* skill 需要确认模板、配置摘要或规则注入说明时引用.
---

# 反构共用资源 Skill（reverse-shared）

## 概览

本 Skill 存放被多个反构 Skill 共用的文档与模板，不作为独立执行入口。其他 reverse-* skill 在需要时可引用本目录下 `references/` 中的文件。

## 本 Skill 内 references 内容

- [references/confirmation-template.md](references/confirmation-template.md) — 确认步骤模板
- [references/simplified-config-summary.md](references/simplified-config-summary.md) — 简化配置摘要说明
- [references/USAGE-CHANGES.md](references/USAGE-CHANGES.md) — 用法变更说明
- [references/interface-rules-injection-analysis.md](references/interface-rules-injection-analysis.md) — 接口规则注入分析

## 使用方式

- 由 **reverse-interfaces**、**reverse-rules** 等 skill 在阶段文档中按需引用上述文件路径（相对本 repo 的 skill 根或安装后的路径）。
- 不通过 `reverse --target` 直接触发；无独立阶段或 todo。
