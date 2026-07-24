# 实战最佳实践检测标准

> 用途：check/fix/create 模式均可加载。来源于 1214 条 Prompt 的实战数据和多个 Skill 迭代经验。
>
> 这些检查项来自真实踩坑，优先级基于出现频率。

---

## 一、变更影响扫描（fix 模式必用）

**核心原则**：修改了系统中的一个节点，必须遍历该节点的所有关联边。

**四种关联查找方式**（覆盖所有场景）：

| 查找方式 | 操作 | 覆盖的场景 |
|---------|------|-----------|
| **调用方** | grep 函数名/接口名/变量名/文件名 | 路径引用、步骤引用、规则引用 |
| **对称方** | 搜索成对出现的另一侧 | SKILL.md↔references/、文档↔脚本、触发↔不触发、create↔destroy |
| **消费方** | 搜索数据的下游使用者 | 模板中引用的变量、报告中引用的分数、检查清单中的项数 |
| **同层方** | 搜索相同模式的平行代码 | 一处修复后检查同类模块是否有同样问题 |

**执行流程**（每次修改后强制）：
1. 列出本次所有变更点（改了什么文件、什么字段、什么结构）
2. 对每个变更点，用 grep 找到所有关联代码
3. 逐一验证一致性
4. 输出扫描结果表

**输出格式**：
```
| 变更点 | 关联代码 | 是否一致 |
|--------|---------|---------|
| SKILL.md 删除了 Step 3 | references/flow-3.md | ❌ 文件仍存在 |
| 规则数从 5 改为 7 | README.md 第 12 行 | ❌ 仍写 5 条 |
```

**反模式**：
- Case-by-case 列规则（"改了 SKILL.md 要查 references/"）— 规则越列越多仍覆盖不了新场景
- 只检查自己改的文件 — 问题往往出在"没改但应该改"的地方
- 改完就交付，跳过扫描

---

## 二、description 质量检查（check/create 模式用）

**核心事实**：description 不是给人看的注释，是 Claude 判断是否触发 Skill 的唯一依据。

**必需要素**：
- [ ] 功能描述（做什么）
- [ ] 触发短语（中英文关键词，≥5 个）
- [ ] 负面边界（DO NOT TRIGGER 场景）

**检查方法**：读取 SKILL.md frontmatter 的 description 字段，逐项核对。

**差的 description**：
```yaml
description: Find prompts for your situation.  # 只有功能，无触发词无负面边界
```

**好的 description**：
```yaml
description: >
  Diagnose your problem and find the right prompt.
  Trigger on "/prompt-handbook", "一直不对", "Claude 在猜", "多轮还是错".
  DO NOT trigger on general conversations about prompts.
```

---

## 三、信号路由优先级（check 模式用）

**核心原则**：用户描述的是问题现象（"一直错""改了又坏"），不是任务类型（"调试""审计"）。

**正确的路由优先级**：
1. **问题信号**（现象描述）→ 最准。如："多轮结果在变" → 数据驱动
2. **关键词**（任务类型）→ 兜底。如："调试" → during.md
3. **不确定** → 问用户

**检查项**：
- [ ] Skill 的触发条件是否包含问题现象信号（而非仅关键词）？
- [ ] 路由逻辑是否优先匹配信号再匹配关键词？

---

## 四、Token 预算检查（check/create 模式用）

**核心事实**：SKILL.md 的正文部分始终加载到上下文，references/ 按需加载。

**预算标准**：
- SKILL.md 正文目标约 ≤ 300 tokens（常见为 ~100 行，路由逻辑为主）
- SKILL.md > 200 行时必须审查是否有大段内容应移到 `references/`
- SKILL.md > 300 行视为明确超预算，应拆分
- 单次 reference 读取 ≤ 1000 tokens
- 每次调用总消耗 ≤ 1500 tokens

**检查方法**：
- [ ] SKILL.md 行数是否合理（>200 行需要检查是否有大段内容应移到 references/）
- [ ] references/ 文件是否按场景拆分（而非一个大文件）

---

## 五、反模式对照表（check 模式用，10 条）

| # | 反模式 | 问题 | 正确做法 | 检查方法 |
|---|--------|------|----------|---------|
| 1 | 不指定目录结构 | Claude 用扁平结构 | 明确 SKILL.md + references/ + scripts/ | 检查是否有标准目录 |
| 2 | 不指定 token 预算 | 设计成读全文 | 明确"SKILL.md 目标 ~100 行，>200 行审查，>300 行拆分；单次 <1000" | 检查 SKILL.md 行数 |
| 3 | 不指定触发条件 | description 太弱不触发 | 列出 5-7 触发词 + 负面边界 | 检查 description |
| 4 | 重复段 | 同一规则在两个段中出现 | 每段职责唯一 | grep 关键词查重复 |
| 5 | Action 嵌在输出格式里 | 格式和执行逻辑混在一起 | Action 独立成段 | 检查输出模板中是否有执行指令 |
| 6 | 写入操作无前置检查 | 直接追加导致膨胀 | 先读→重复不写→不完善补充 | 检查写入步骤是否有读取前置 |
| 7 | case-by-case 加规则 | 规则越多越覆盖不了 | 找统一原则替代多条规则 | 检查规则数是否 >10 且同类 |
| 8 | 只按关键词路由 | 用户描述的是现象不是类型 | 信号优先于关键词 | 检查路由逻辑 |
| 9 | 追加不检查重复 | "完整规则"重复"行为准则" | 追加前检查已有段 | 查相似标题 |
| 10 | 新增内容不同步关联 | 加了文件但路由没更新 | 原子操作同步 4 处 | 查引用完整性 |

---

## 六、Decision Gate 检查（check/fix/create/audit 模式用）

**核心原则**：用户信号、关键词、结构命中、统计异常都只是 signal candidate，不能直接升级为强结论。

**检查项**：
- [ ] Skill 是否声明了哪些信号只能作为 candidate？
- [ ] 强结论是否按 claim type 定义 required evidence？
- [ ] 是否要求检查 counter-evidence（例外、版本限制、已有实现、用户约束）？
- [ ] 证据不足时是否降级为 tentative / unresolved？
- [ ] 最终产物是否能追溯 signal → evidence → counter-evidence → decision？
- [ ] 是否定义 evidence completeness ceiling，限制 incomplete evidence 的结论等级？

**反模式**：
- 看到关键词就给结论
- 看到结构存在就断言能力完整
- 看到单个样本就推广为普遍规律
- 看到用户表述就直接写成需求，不做约束和反例检查

---

## 七、交付前 6 条检查清单（check/fix 模式收尾时自动输出）

来源：1214 条 Prompt 中 149 次纠正的统计，这 6 条覆盖 60%+ 的纠正。

```
□ 验证了吗？— 跑过测试/展示过输出/给过证据？
□ 关联检查了吗？— 改了 A，B/C/D 是否也需要改？
□ 是统一方案还是 case-by-case？— 规则数合理吗？有没有更统一的方法？
□ 写入文件了吗？— 需要持久化的经验/规则是否已写入 CLAUDE.md 或 lessons.md？
□ 结构合理吗？— 追加超过 3 次的内容是否需要重组？
□ 执行边界清晰吗？— 是该执行还是只分析？
```

---

## 八、原子操作同步检查（fix/create 模式用）

**核心原则**：新增/修改内容 = 一个原子操作，必须同步所有关联点。

**Skill 修改时的同步清单**：
1. SKILL.md — 主入口修改
2. references/*.md — 对应参考文档同步
3. references/*.md — 模板是否需要更新
4. description — 触发条件是否需要更新

**新增实战经验时的同步清单**：
1. 经验文件本身
2. SKILL.md 信号路由
3. reference 中对应的匹配规则
4. 索引/速查表追加行

**漏任何一步 = 信息断裂。**

---

## 九、可移植性审计（check/audit 模式用，方法论层，不计分）

> 用途：发现 Skill 在非当前宿主环境下的执行风险。**当前为方法论层定义**；是否扩展 `validate-structure.py` 或新建 `validate-portability.py` 取决于后续 2-3 次真实审计的样本数据。

**核心原则**：通用 Skill 契约不应绑死在作者的宿主环境（用户机器、用户名、平台、MCP 可用性）。

**4 类可移植性风险**：

| # | 风险 | 定义 | grep 线索 | 例外白名单 |
|---|------|------|-----------|-----------|
| 1 | **绝对路径硬编码** | SKILL.md / references 正文出现作者具体用户路径 | `/Users/\|/home/\|~/[a-zA-Z]` 后接特定用户名 | 仅在 example / 注释 / 审计历史示例中允许；主流程不允许 |
| 2 | **宿主 MCP/CLI 无 fallback** | 依赖特定 MCP（如 `jadx-mcp-server`）或 CLI（`frida`/`aapt`/`ida-pro`）但未定义"工具不存在时如何降级" | 工具名出现但附近无"fallback"/"降级"/"不可用时" | 工具是 Skill 的**定义属性**时（如 `mobile-security` 离开 jadx 就不成立）可标 N/A |
| 3 | **环境假设写入主契约** | SKILL.md 正文含"我本地已装 X"、"用户机器应该有 Y"等假设 | grep 主 SKILL.md 中的"我"/"本地"/"应该已" | 应隔离到 `references/setup.md` 而非主 SKILL.md |
| 4 | **平台 binary 路径假设** | 硬编码 macOS/Linux binary 路径 | `/usr/local/\|/opt/\|brew\|apt install` | 应改为 `command -v` / `which` 探测 |

**检查项（4 项，对应上面 4 类风险）**：

- [ ] 主 SKILL.md 是否出现绝对路径硬编码？
- [ ] 宿主专属工具依赖是否有 fallback 或"不可用时"路径？
- [ ] 环境假设是否隔离到 `references/` 而非主 SKILL.md？
- [ ] 平台 binary 路径假设是否抽象为 `command -v` / `which` 探测？

**报告格式**：附加在 `report-template.md` 的 "可移植性审计" 节；每项标注 `PASS / WARN / FAIL` + 证据引用（file:line）。**不入加权总分**。

**N/A 触发条件（避免误伤本地逆向类 Skill）**：
- Skill 的核心能力定义依赖特定宿主工具时（如 `mobile-security` 必须有 jadx / frida / ida）→ 风险 #2 可标 N/A，但必须在 SKILL.md 的"前置要求"节明确列出
- Skill 的目标就是操作作者机器的本地文件时 → 风险 #1 仅对非路径部分检查

**脚本化决策（暂缓到样本后）**：
收集 2-3 次真实审计数据后再决定：
- (A) 扩展现有 `scripts/validate-structure.py` 增加 portability grep 检查；或
- (B) 新建独立的 `scripts/validate-portability.py`，支持白名单配置（JSON 文件定义每个 Skill 的 N/A 豁免项）

**判定目的**：不是为了把所有 Skill 改成纯通用的，而是让**环境绑定必须是显式的**，而不是"隐藏在主契约里"。
