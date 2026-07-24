# Skill Craft — Skill 质量工程工具

> 评估 / 修复 / 创建 / 系统审计，覆盖 Skill 全生命周期。

## 功能概览

| 模式 | 触发词 | 作用 |
|------|--------|------|
| **check** | "评估 skill"、"skill 质量"、"review skill" | 对单个 Skill 做 8 模块质量评分 |
| **fix** | "修复 skill"、"fix skill" | 评估 + 分优先级修复 + 回归验证 |
| **create** | "创建 skill"、"新建 skill" | 从零生成符合质量标准的 Skill |
| **audit** | "系统审计"、"路由冲突检查" | 多 Skill 系统级一致性审计 |

## 评估体系

**四维评分**（加权）：
- **8 模块检查**（55%）：触发条件、行为准则、工具优先级、输出约束、流程 Checkpoint、依赖链、子 Agent 委派、幻觉防护
- **7 反模式评估**（20%）：约束衰减、工具漂移、输出膨胀、依赖链断裂、并行孤岛、触发模糊、幻觉填充
- **3 完整性原则**（15%）：可计数验收、Checkpoint 切断、失败路径定义
- **Decision Gate**（10%）：检查 signal 是否绕过 evidence / counter-evidence 被误升级为强结论

> **封顶规则**：命中触发冲突 / DG Fail ≥2 / 核心文件断链 / validate 脚本 FAIL / quick check 冒充 deep 任一项，加权总分 clamp 至 `≤ 6.0/10`，报告顶部标注 "⚠️ 封顶触发"。

## 目录结构

```
skill-craft/
├── SKILL.md
├── references/
│   ├── check-guide.md
│   ├── fix-guide.md
│   ├── create-guide.md
│   ├── audit-guide.md
│   ├── quality-standards.md
│   ├── decision-gates.md
│   ├── practical-best-practices.md
│   ├── report-template.md
│   └── skill-scaffold.md
└── scripts/
    ├── validate-metadata.py
    └── validate-structure.py
```

## 快速使用

### 评估一个 Skill
```
评估 /path/to/my-skill
```
输出：8 模块评分 + 7 反模式风险 + 3 完整性评级 + 行动项清单

### 修复一个 Skill
```
修复 /path/to/my-skill
```
输出：问题清单（P0/P1/P2）→ 逐项修复 → 回归评估（修复前 vs 修复后分数）

### 创建一个 Skill
```
创建一个代码审计 skill
```
输出：需求确认 → 规模判断 → 生成文件 → 自检 → 自动化验证

### 审计多 Skill 系统
```
审计 /path/to/skills-directory
```
输出：路由冲突 + 一致性 + 引用完整性 + P0/P1/P2 系统级问题

## 自动化验证

```bash
# 验证元数据（name + description）
python3 scripts/validate-metadata.py --path /path/to/skill

# 验证结构（目录 + 8模块 + 引用完整性 + 空文件检测）
python3 scripts/validate-structure.py --path /path/to/skill
```

## 设计原则

- **上下文保护**：SKILL.md 保持轻量入口，references 按需加载
- **Checkpoint 驱动**：每步必须输出 Checkpoint 后才能进入下一步
- **回归验证**：fix 模式修复后强制重跑 check 对比分数
- **评分校准**：5 个模块有 0/1/2 分具体示例，降低 LLM 判断偏差
- **Decision Gate**：防止把弱信号、关键词、结构命中直接升级为强结论
- **防失效**：基于 7 类 LLM 系统性失效模式设计防御机制

## 版本

- `skill-craft`：单目录版本，按用户语言输出
