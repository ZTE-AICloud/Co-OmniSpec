# Decision Gate Framework

> 用途：check/fix/create/audit 模式加载，用领域无关的方式检查 Skill 是否会把弱信号直接升级为强结论。

## 核心模型

```
Signal  ->  Evidence  ->  Counter-Evidence  ->  Decision
trigger     proof set       exception check       claim/action
```

**硬性语义**:
- Signal 是触发信号、关键词、结构命中、用户表述、统计异常或模式匹配；signal 只能启动调查。
- Evidence 是能支撑结论的来源、行为、关系、语义、观测或权威依据。
- Counter-Evidence 是可能推翻、降级或限制结论的例外、缓解条件、版本限制、反例、已有实现或用户约束。
- Decision 是最终判断、行动建议、漏洞结论、文档问题、代码改动或需求判断。
- 无 evidence 的 signal 只能输出 `tentative` / `unresolved` / `needs_more_evidence`，不能输出强结论。
- 未检查 counter-evidence 的强结论最高只能 `tentative`。
- Evidence collection 与 decision making 必须分离：先收集事实，再判断；禁止边找证据边预设结论。

## Gate 类型

| Claim Type | Required Evidence | 常见误用 |
|------------|-------------------|----------|
| `structural` | 文件/字段/格式/schema 证据 + 目标范围 | 看到文件存在就断言功能完整 |
| `behavioral` | 可运行结果、测试、日志、复现步骤或实际输出 | 看到代码路径就断言运行行为 |
| `relational` | 引用链、调用链、依赖链、文档-实现映射 | 看到同名概念就断言有关联 |
| `semantic` | 冲突双方原文、术语定义、source of truth | 看到相似词就断言语义冲突 |
| `empirical` | 样本量、测量方法、基线、统计或观测数据 | 看到个例就断言普遍结论 |
| `authority` | 官方规范、合同、API schema、ADR、用户明确要求 | 看到经验规则就断言必须遵循 |

## 通用字段

每条强结论建议包含以下字段；无法全部结构化时，也必须在正文中可追溯：

```yaml
signal: <triggering signal>
claim_type: structural | behavioral | relational | semantic | empirical | authority
evidence: <supporting proof>
counter_evidence:
  checked: yes | no
  result: <none | mitigated | contradicted | scope_limited | unknown>
completeness: complete | partial | unresolved
scope: <where the decision applies>
confidence: high | medium | low
decision: accepted | tentative | unresolved | rejected | n/a
```

## Evidence Completeness Ceiling

证据完整性决定结论上限：

| Completeness | 条件 | 结论上限 |
|--------------|------|----------|
| `complete` | required evidence 已覆盖，scope 明确，counter-evidence 已检查 | `accepted` |
| `partial` | 主证据存在，但缺少部分范围、验证或关联链 | `tentative` |
| `unresolved` | 证据链中断、工具不可用、关键文件未读或无法确认 | `unresolved` |

**强制规则**:
- 只读 `SKILL.md`，未读相关 `references/` / `scripts/` 时，不能给生产就绪强结论。
- 只跑结构脚本，未检查语义和产物门控时，不能输出 deep quality score。
- 只发现不一致候选，未定位 source of truth 时，不能判定谁错。
- 没有 counter-evidence 检查记录时，不能输出 `accepted`。

## Counter-Evidence Gate

每个 candidate issue 在进入行动项前必须检查反证：

| Candidate Issue | 必查 Counter-Evidence |
|-----------------|-----------------------|
| 缺少 `scripts/` | 该 Skill 是否确实需要确定性脚本？纯阅读/写作流程可 N/A |
| 缺少子 agent 委派 | 任务是否可并行？轻量/顺序依赖任务可 N/A |
| 缺少 README | 当前 Skill 规范是否建议避免人类文档？可能不是缺陷 |
| SKILL.md 行数偏高 | 是否仍低于预算，且内容必须常驻？ |
| 引用文件未读 | 是否该模式确实不需要该 reference？ |

Counter-evidence 结果：
- `none`: 未发现反证，可继续判断
- `mitigated`: 有缓解条件，降级
- `contradicted`: 证据被推翻，reject
- `scope_limited`: 只在部分范围成立，限制 scope
- `unknown`: 未能检查，最高 tentative

## 降级规则

| 情况 | Decision |
|------|----------|
| 仅 signal，无 evidence | `unresolved` |
| evidence 存在但 scope 不清 | `tentative` |
| counter-evidence 未检查 | 最高 `tentative` |
| evidence 被 counter-evidence 抵消 | `rejected` 或 `n/a` |
| evidence 满足 claim type gate | `accepted` |
| 工具/资源不可用导致无法取证 | `unresolved` + 原因 |

## Report Gate

最终报告前必须满足：

1. 每个 P0/P1/P2 行动项都有 `signal + evidence + counter_evidence + decision`。
2. 每个评分维度都有证据来源；无来源不得给分。
3. 所有 `accepted` 结论的 `completeness` 必须为 `complete`。
4. 所有 `tentative/unresolved` 必须单独列出，不得混入已确认问题。
5. quick check 不得冒充 deep check；结构 smoke check 不能产生 deep quality score。
6. **封顶规则生效时**（触发条件见 `check-guide.md` Step 9 封顶规则表），报告顶部必须标注 "⚠️ 封顶触发: [第 N 条] - [原因一句话]"；加权总分 clamp 至 `≤ 6.0/10`；所有 `accepted` 结论自动降为 `tentative`，不得作为强结论发布。封顶是评分层规则，不影响 P0/P1/P2 行动项生成。

## 评估方法

1. 抽样检查目标 Skill 可能输出的 3-5 类强结论。
2. 为每类结论识别 `claim_type`。
3. 检查 Skill 是否定义了 required evidence，而不是只定义 signal。
4. 检查 Skill 是否要求 counter-evidence 与 completeness ceiling。
5. 检查最终报告/产物是否有 report gate。
6. 若强结论只引用 signal，将该问题标为 P1；若会导致错误执行或错误安全/合规/业务判断，标为 P0。

## Create 模式模板

新建 Skill 时，如果它会输出判断、建议、评分、改动或风险结论，必须加入一段领域化 Decision Gate：

```markdown
## Decision Gate

Signal candidates:
- [哪些信号只能作为调查起点]

Required evidence by claim type:
- structural: [...]
- behavioral: [...]
- relational: [...]
- semantic: [...]

Decision rules:
- Signal without evidence -> unresolved
- Strong decisions require complete evidence and checked counter-evidence
- Partial evidence -> tentative
- Unresolved evidence -> unresolved
```
