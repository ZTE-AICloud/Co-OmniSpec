# Skill 质量报告: {skill-name}

**检查模式**: quick / deep
**日期**: {date}
**总分**: {score}/10
**等级**: {8-10 生产就绪 / 5-7 需优化 / <5 需重写}

---

## 结构摘要

| 项目 | 状态 | 详情 |
|------|------|------|
| SKILL.md | ✅/❌ | {行数, 有无 frontmatter} |
| references/ | ✅/❌ | {文件数} |
| references/ | ✅/❌ | {文件数} |
| scripts/ | ✅/❌/N/A | {文件数} |

---

## 8 模块评估（权重 55%）

| 模块 | 分数 | 状态 | 关键发现 |
|------|------|------|---------|
| 1. 触发条件 | 0/1/2 | ✅/⚠️/❌ | {一句话发现} |
| 2. 行为准则 | 0/1/2 | ✅/⚠️/❌ | {一句话发现} |
| 3. 工具优先级 | 0/1/2 | ✅/⚠️/❌ | {一句话发现} |
| 4. 输出约束 | 0/1/2 | ✅/⚠️/❌ | {一句话发现} |
| 5. 流程 Checkpoint | 0/1/2 | ✅/⚠️/❌ | {一句话发现} |
| 6. 依赖链 | 0/1/2 | ✅/⚠️/❌ | {一句话发现} |
| 7. 子 Agent | 0/1/2/N/A | ✅/⚠️/❌/— | {一句话发现} |
| 8. 幻觉防护 | 0/1/2 | ✅/⚠️/❌ | {一句话发现} |

**模块小计**: {X}/{16 或 14(若模块7 N/A)} → 归一化至 5.5 分

---

## 7 反模式脆弱性（权重 20%）

| 模式 | 风险 | 证据 |
|------|------|------|
| 1. 约束衰减 | Low/Med/High | {file:section} |
| 2. 工具漂移 | Low/Med/High | {file:section} |
| 3. 输出膨胀 | Low/Med/High | {file:section} |
| 4. 依赖链断裂 | Low/Med/High | {file:section} |
| 5. 并行孤岛 | Low/Med/High/N/A | {file:section} |
| 6. 触发模糊 | Low/Med/High | {file:section} |
| 7. 幻觉填充 | Low/Med/High | {file:section} |

**反模式小计**: {Y}/7 项有防御 → 归一化至 2.0 分

---

## 3 完整性原则（权重 15%）

| 原则 | 状态 | 证据 |
|------|------|------|
| 1. 可计数验收 | Pass/Partial/Fail | {详情} |
| 2. Checkpoint 阻断 | Pass/Partial/Fail | {详情} |
| 3. 失败路径定义 | Pass/Partial/Fail | {详情} |

**完整性小计**: {Z}/3 → 归一化至 1.5 分

---

## Decision Gate（权重 10%）

| Claim Type | 状态 | Evidence | Counter-Evidence | Completeness | 风险 |
|------------|------|----------|------------------|--------------|------|
| structural / behavioral / relational / semantic / empirical / authority | Pass/Partial/Fail/N/A | {file:section} | checked / missing / N/A | complete / partial / unresolved | {signal-only 或反证缺失风险} |

**Decision Gate 小计**: {D}/10%  
> 计算公式: Pass=10, Partial=5, Fail=0；DG 归一化分 = (Σ 各类得分) / (已评估类数 × 10)；N/A 时权重回冲至模块分（55%→65%）。counter-evidence 未检查 → 该类自动降为 Partial。
**结论**: {是否存在信号直接升级为强结论、证据完整性不足、或反证未检查的风险}

---

## 封顶规则检查（Hard Cap）

- 封顶触发: {是 / 否}
- 触发条款: {第 N 条 - 原因一句话 / — }
- 影响: {加权总分 clamp 至 ≤ 6.0；所有 accepted 结论降为 tentative / — }

> 触发条件见 `check-guide.md` Step 9 封顶规则表；与 `decision-gates.md` Report Gate #6 对齐。

---

## 产物契约附加观察（不计分，样本收集阶段）

> 暂不入加权总分；2-3 次真实审计样本后再决定是否升格为正式模块。

| # | 检查项 | 状态 | 证据 (file:line) |
|---|-------|------|-----------------|
| 1 | 目标 Skill 是否定义稳定输出（文件名/目录/schema/格式）| OBSERVED / MISSING / N/A | {...} |
| 2 | 是否有唯一真值源（同一产物不在多处被原始定义）| OBSERVED / MISSING / N/A | {...} |
| 3 | 是否区分 human-readable / machine-readable / work artifacts | OBSERVED / MISSING / N/A | {...} |

---

## 可移植性审计（方法论层，不计分）

> 当前为方法论落地，检查规则定义在 `practical-best-practices.md` 第九节；脚本化（扩展 `validate-structure.py` 或新建 `validate-portability.py`）推迟到样本后决定。

| # | 风险 | 状态 | 证据 (file:line) |
|---|------|------|-----------------|
| 1 | 绝对路径硬编码（`/Users/\|/home/\|~/`）| PASS / WARN / FAIL | {...} |
| 2 | 宿主 MCP/CLI 无 fallback | PASS / WARN / FAIL | {...} |
| 3 | 环境假设写入主 SKILL.md（未隔离到 references/）| PASS / WARN / FAIL | {...} |
| 4 | 平台 binary 路径假设（`/usr/local/\|/opt/\|brew\|apt`）| PASS / WARN / FAIL | {...} |

---

## 行动项

### P0（阻塞可靠执行）
- {行动项 + file:location 引用}

### P1（导致行为退化）
- {行动项}

### P2（影响可维护性）
- {行动项}

**行动项验证**: 总数 {N} == 模块问题 {a} + 反模式问题 {b} + 完整性问题 {c} + Decision Gate 问题 {d}

---

## 总结

- **优势**: {1-2 条}
- **主要缺口**: {1-2 条}
- **推荐下一步**: {具体行动}

> 注：评分仅适合同一 Skill 的纵向趋势对比，不可跨 Skill 横向比较（不同规模的 Skill 模块权重不同）。
