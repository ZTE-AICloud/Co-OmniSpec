# Workflow 完成摘要

> **加载时机**：仅在 Final（`workflow-gate.sh --check workflow-complete` 通过后）输出用户可见摘要前 Read 本文档。  
> Step 0–N 执行过程中**不要** Read，避免占用 token。

## 模式差异一览

| 特性 | express | standard | deep | expert |
| ------ | --------- | ---------- | ------ | ------ |
| 阶段数 | 7 | 8 | 9 | 7 |
| clarify | 无 | 有（自动决策推荐选项） | 有（自动决策推荐选项） | 无 |
| brainstorming | 无 | 无 | 无 | 有（用户批准设计稿） |
| brainstorming-sdd-bridge | 无 | 无 | 无 | 有（转强结构 SDD 接口） |
| reverse | 无 | 无 | 有（no_state_write） | 无 |
| specify 自动收敛 | 有（5 次） | 无 | 无 | 无（由桥接阶段生成 specify 接口） |
| design 自动收敛 | 有（5 次） | 无 | 无 | 无（跳过 design stage，仅保留 design.md 接口） |
| analyze auto_fix_unlimited | 无 | 有 | 有 | 无 |
| review 并行 | 有 | 有 | 有 | 有 |

## 最终摘要模板

按 `$FLOW_MODE` 选用对应模板；须含 implement 与 review 完成信息。

### Express 模式

```txt
[Express 模式] workflow 执行完成
分支: … | specify/design/implement/review: ✅
制品: context.md, spec.md, research.md, design.md, data-model.md, quickstart.md, tasks.md | 任务: N/M
```

### Standard 模式

```txt
[Standard 模式] workflow 执行完成

分支: <分支名>
AI 验证结果:
  - specify: ✅ 通过 (score: XX/100)
  - clarify: ✅ 通过 (score: XX/100)
  - design: ✅ 通过 (一致性: 无问题, 质量: XX/100)
制品路径:
  - spec.md: <路径>
  - design.md: <路径>
  - tasks.md: <路径>
任务统计: 总计 N 个任务, 已完成 M 个
关键决策: (列出 clarify 阶段自动采纳的主要澄清项，注明自动决策模式)
```

### Expert 模式

```txt
[Expert 模式] workflow 执行完成

分支: <分支名>
AI 验证结果:
  - brainstorming: ✅ 完成（交互式设计已批准）
  - brainstorming-sdd-bridge: ✅ 通过（已生成 spec.md/design.md/context.md/checklist/eval/state）
  - specify 接口制品: ✅ 已由桥接生成 (score: XX/100)
  - design.md 接口: ✅ 已由桥接生成（未执行 design stage）
  - local-sandbox-fix: ✅ 通过
制品路径:
  - *-design.md: <brainstorming 产出路径>
  - spec.md: <路径>
  - context.md: <路径>
  - design.md: <路径>
  - tasks.md: <路径>
任务统计: 总计 N 个任务, 已完成 M 个
关键决策: (列出 brainstorming 阶段确认的主要设计决策)
```

### Deep 模式

```txt
[Deep 模式] workflow 执行完成

分支: <分支名>
AI 验证结果:
  - reverse: ✅ 通过
  - specify: ✅ 通过 (score: XX/100)
  - clarify: ✅ 通过 (score: XX/100)
  - design: ✅ 通过 (一致性: 无问题, 质量: XX/100)
制品路径:
  - reverse: omni-doc/on-demand/logic_architecture.md, omni-doc/on-demand/functions/ 等
  - spec.md: <路径>
  - design.md: <路径>
  - tasks.md: <路径>
任务统计: 总计 N 个任务, 已完成 M 个
关键决策: (列出 clarify 阶段自动采纳的主要澄清项，注明自动决策模式)
```
