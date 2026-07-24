---
name: skill-craft
description: |
  Evaluates, repairs, creates, and audits Claude Skills using an 8-module quality framework with weighted scoring.
  Performs structural scanning, anti-pattern detection, completeness verification, discovery validation, and decision-gate checks.
  Use when checking Skill quality ("check skill", "skill 质量", "评估这个 skill", "review skill", "skill 好不好",
  "skill 总是不触发", "skill 输出不稳定"), fixing Skill defects ("fix skill", "修复 skill"),
  creating new Skills ("创建 skill", "新建 skill"), or auditing multi-Skill route conflicts ("审计 skill", "系统审计").
  Also triggers on: "evaluate skill", "audit skill system", "skill quality report", "grade this skill".
  Do not use for general code review, non-Skill documentation, Skill design concept discussions without a concrete target, or runtime debugging.
tools:
  - Read
  - Grep
  - Glob
  - Bash
  - Edit
  - Write
---

# Skill Craft — Evaluate / Fix / Create / Audit

> 按用户语言响应（Respond in the user's language）

## 触发条件

**check 模式**（同时满足）:
- 用户提供了现有**单个** Skill 目录路径（含 SKILL.md）
- 用户意图是评估/检查/审计/打分/review
- 问题现象信号（优先匹配）: "skill 总是不触发" "skill 输出不稳定" "skill 质量怎么样"

**fix 模式**（同时满足）:
- 用户提供了现有 Skill 目录路径（含 SKILL.md）
- 用户意图是修复/修/调整/更新/fix/repair

**create 模式**（同时满足）:
- 用户要求创建/生成/新建一个 Skill
- 用户描述了 Skill 的用途或领域

**audit 模式**（同时满足）:
- 用户提供了包含**多个** Skill 的父目录路径
- 或用户明确要求"系统级审计""全局检查""路由冲突检查"
- 目录下存在 ≥2 个 SKILL.md

**不触发**:
- 讨论 Skill 设计概念但无具体目标（"Skill 应该怎么写？"）
- 引用 Skill 路径但无操作意图（"这个 Skill 在哪？"）
- 非 Skill 类文件的代码审计（用 code-audit）

**歧义处理**:
- 无法判断模式时询问: "您是要 check（单个评估）、fix（评估+修复）、create（从零创建）、还是 audit（多 Skill 系统审计）？"

**默认**:
- 单个 Skill 路径 + 无明确修复词 → check
- 单个 Skill 路径 + "修/改/更新/修复" → fix
- 无现有目录 + "创建/生成/新建" → create
- 多 Skill 父目录 → audit

---

## 行为准则

以下规则在整个会话期间有效，不因对话长度而放松：

1. ❗ **每个发现/修改必须引用来源**（文件路径 + 章节/行号）— 适用所有模式。每次输出前自检此条。
2. ❗ **评分基于检查清单客观打分**（按清单定义的 0/1/2 或 Pass/Partial/Fail），不凭印象 — check/fix 模式。每次输出前自检此条。
3. ❗ **禁止单边修复** — fix 模式：改文档必须同步改实现，改实现必须同步改文档。每次修改前自检此条。
4. ❗ **强结论必须通过 Decision Gate** — 触发信号只能启动调查，不能直接生成结论；证据不足时输出 `tentative` / `unresolved` — 适用 check/fix/audit/create 所有模式。每次输出前自检此条。

其他准则:
- 评估的是 Skill 本身的结构质量，不是 Skill 所服务领域的专业深度
- fix 模式：修复范围仅限审计发现，不可"顺便优化"审计未提及的内容
- create 模式：生成内容基于用户需求描述，不可添加用户未要求的领域知识

---

## 工具优先级（不可自行降级）

| 操作 | 首选工具 | 降级条件 | 降级工具 |
|------|---------|---------|---------|
| 读取文件 | Read | Read 返回错误 | Bash cat |
| 查找文件 | Glob | Glob 返回 0 且路径确认存在 | Bash ls -R |
| 搜索关键词 | Grep | Grep 连续 2 次失败 | Bash grep |
| 修改已有文件 | Edit | Edit 失败（如 old_string 不唯一） | 调整 old_string 范围后重试 Edit |
| 创建新文件 | Write | — | — |

- 单次超时 ≠ 工具不可用，必须重试 1 次
- 降级必须标注: "⚠️ 降级: [原因]"
- 不可用 Bash sed/awk 替代 Edit

---

## 输出约束

禁止输出:
- "让我来分析一下..." / "首先我们需要..." 等开场白
- 工具调用前后的重复描述（直接调用，不说"我将使用 Read 工具读取..."）
- 已知信息的复述（用户刚说的路径、文件刚读的内容）
- 8 模块 / 7 反模式本身的定义解释（用户已知）
- 对 Skill 所服务领域的专业评论（超出范围）

模式特定禁止:
- fix 模式：禁止只说"已修复"而不展示验证方法和结果
- create 模式：禁止生成与现有 Skill 路由冲突的触发条件

---

## 执行流程

每个模式的详细步骤（含失败降级路径和 ✅ Checkpoint）在对应 reference 文件中，执行时按需加载。**每步必须输出 Checkpoint 后才能进入下一步。**

### check 模式 → Read `references/check-guide.md`
- 快速检查: 3 步（结构扫描 → 模块存在性 → 快速报告），每步有 ✅ Checkpoint
- 深度检查: 先 quick check 识别问题区域，再**按需加载**对应 reference（不一次性加载全部）
- 评分: 模块(55%) + 反模式(20%) + 完整性(15%) + Decision Gate(10%)，实战检查为附加
- 上下文保护: quick check 不加载完整标准；deep check 才加载 quality-standards.md 与 decision-gates.md

### fix 模式 → Read `references/fix-guide.md`
- 8 步: 结构扫描 → 加载清单+约束 → 深度评估 → 问题清单 → P0修复 → P1修复 → P2修复 → 全局验证+**回归评估**
- 每项修复强制: 修改 → 读回验证 → 变更影响扫描(4种关联：引用方/对称文件/下游消费者/同层文件) → 关联同步
- 审计结果先输出，再改文件。每步有 ✅ Checkpoint

### create 模式 → Read `references/create-guide.md`
- 6 步: 明确需求 → 规模判断 → 生成文件 → 自检清单 → **自动化验证**(validate-metadata + validate-structure) → 创建报告
- 规模适配: 轻量(模块1+2+4+8) / 中等(1-5+8) / 重型(全部8个)。每步有 ✅ Checkpoint

### audit 模式 → Read `references/audit-guide.md`
- 6 步: 系统扫描 → 加载标准 → 路由审计 → 一致性审计 → 验证闭环 → 系统报告
- 多 Skill 专属: 路由边界、角色分工、旧口径残留、外围文档传播。每步有 ✅ Checkpoint

---

## 依赖链

**check**: 检查清单 → 评估步骤(不自创标准) → Decision Gate 检查 → 报告引用评分(不重估) → 行动项总数 == 各步问题数之和
**fix**: 评估结果 → 问题清单(不遗漏) → 逐项修复 → 回归 Decision Gate → 修复数 + 未修复数 == 问题总数
**create**: 需求 → 规模判断(基于需求) → 必需模块(全部填充) → Decision Gate 模板 → 自检(逐项核对) → 已填充数 == 必需模块数
**audit**: 系统扫描 → 覆盖所有 Skill → 路由/一致性/Decision Gate → 发现总数 == 各步问题数之和

---

## 子 Agent 委派

**check 深度**: 8模块/7反模式/3原则 可并行 3 个子 agent，各收到目标内容 + 检查清单原文（复制不转述），边界明确，合并时去重+一致性+计数验证
**fix**: 评估可并行，修复不可并行（修复间有依赖）
**create**: 通常不需要子 agent
**audit**: 路由审计 + 一致性审计 可并行 2 个子 agent

---

## 审计历史（Memory）

每次 check/fix/audit 完成后，将结果追加到审计历史文件（一行一条 JSON）：

**存储路径**（按优先级）：
1. `${CLAUDE_PLUGIN_DATA}/audit-history.jsonl`（plugin 安装时可用）
2. `~/.claude/skill-craft-data/audit-history.jsonl`（fallback）

```jsonl
{"ts":"2026-03-26T10:00:00Z","mode":"check","skill":"skill-name","path":"/abs/path","weights_version":"2.0","score":7.2,"p0":1,"p1":3,"p2":2,"modules":"6/8","antipatterns_high":1,"dg":"Pass"}
```

**读取时机**：
- check/fix 模式：执行前先查历史，同一 Skill 有历史记录时输出对比（`上次 → 本次`）
- audit 模式：系统报告末尾附"评分趋势"表（仅有历史的 Skill）
- 无历史 → 不提及，不编造

**写入时机**：报告输出后，先展示待写入记录；仅在用户确认后写入。fix 模式写入修复后的分数。

---

## Gotchas（使用本 Skill 的常见陷阱）

1. **check 快速模式漏检**：快速检查（3 步）只查模块存在性，不查反模式和完整性原则。Skill 结构看起来完整但质量差的情况只有深度检查能发现。**默认用深度检查**，仅在用户明确说"快速看一下"时才用快速模式。
2. **fix 前必须 check**：直接 fix 缺少基线分数，无法量化改进效果。fix 流程已内置评估步骤，但如果用户说"直接改不用评估"，需要提醒：没有基线分数无法验证修复是否有效。
3. **audit 大量 Skill 时超上下文**：目录下 Skill 数量 > 15 时必须分批 audit。分批规则：按子目录分组，每批 ≤8 个 Skill（每个 SKILL.md ~200行 × 8 = ~1600行 ≈ 6400t，留余量给检查清单）。每批独立出报告，最终合并为系统报告。无子目录时按字母序分组。
4. **fix 的"顺便优化"陷阱**：修复过程中发现审计未提及的问题，强烈想"顺便改掉"。禁止。审计未发现 = 不在本轮修复范围，记录到报告的"后续建议"节即可。
5. **评分不可跨 Skill 横向比较**：8 模块框架对不同规模的 Skill 权重不同（轻量 Skill 模块 7 标 N/A），分数只适合同一 Skill 的纵向趋势对比。
6. **权重改版后分数不可跨版本比较**：旧基线（60/25/15，无 Decision Gate）与新基线（55/20/15/10）的 `score` 语义不同；读取 audit-history.jsonl 时按 `weights_version` 字段区分，不同版本记录不得直接生成 `上次 → 本次` 对比，需标注 "⚠️ 基线变更 (v{旧} → v{新})"。

---

## 事实性约束

所有模式: 结论必须引用来源（文件路径+行号），无来源 = 不输出。

| 场景 | 正确输出 | 禁止输出 |
|------|---------|---------|
| 模块缺失 | "ABSENT: 模块 N 不存在" | "模块 N 较弱" |
| 反模式无风险 | "PASS: 未发现漏洞指标" | 编造风险 |
| 无法判断 | "UNABLE TO ASSESS: [原因]" | 猜测评分 |

标注: 工具确认→无标注 / 降级推测→"⚠️ 降级分析" / 领域建议→"💡 通用建议"

**fix**: 修复仅限审计发现，不可"顺便优化"；每项修复须说明出处+内容+验证结果
**create**: 触发条件基于用户描述，不添加用户未要求的领域知识
**audit**: 路由冲突基于实际 description 对比；旧口径通过 grep 验证
