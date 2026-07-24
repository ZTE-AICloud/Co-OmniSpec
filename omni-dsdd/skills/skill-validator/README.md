# Skill Validator

Claude Skill 验证器 - 检查、修复和优化 Claude Skill 的规范性、完整性和最佳实践。

## 快速开始

### 基本语法
```bash
/skill-validator [技能路径] [模式] [检查项编号...]
```

**参数说明：**
- **技能路径**：必选，要验证的技能目录路径
- **模式**：可选，默认为检查模式
  - `check`：检查模式（默认）
  - `fix`：修复模式
  - `auto-fix`：自动化修复模式
- **检查项编号**：可选，默认执行全部检查项

### 三种工作模式

#### 1. 检查模式 (check)
只检查问题，不执行修复。

```bash
# 检查所有问题（默认模式）
/skill-validator ~/.claude/skills/my-skill

# 显式指定检查模式
/skill-validator ~/.claude/skills/my-skill check

# 检查特定检查项
/skill-validator ~/.claude/skills/my-skill 01 03 07
```

#### 2. 修复模式 (fix)
检查后交互式修复，每项修复前需要确认。

```bash
# 修复所有可修复问题
/skill-validator ~/.claude/skills/my-skill fix

# 修复特定检查项的问题
/skill-validator ~/.claude/skills/my-skill fix 基础 元数据 权限
```

#### 3. 自动化修复模式 (auto-fix)
检查后自动执行修复，无需确认。

```bash
# 自动修复所有安全的问题
/skill-validator ~/.claude/skills/my-skill auto-fix

# 自动修复特定检查项
/skill-validator ~/.claude/skills/my-skill auto-fix 01 02 03
```

## 检查项编号

| 编号 | 中文名称 | 英文别名 | 说明 |
|------|----------|----------|------|
| 01 | 基础 | basic, structure | 基础结构与层级检查 |
| 02 | 类型 | type, category | 技能类型识别 |
| 03 | 元数据 | metadata, yaml | 前置元数据验证 |
| 04 | 内容 | content, format | 内容结构与格式 |
| 05 | 附属 | auxiliary | 附属文件检查 |
| 06 | 一致性 | consistency | 内容类型一致性 |
| 07 | 权限 | permission, auth | 权限配置检查 |
| 08 | 子代理 | agent, subagent | 子代理配置检查 |
| 09 | 高级 | advanced | 高级用法检查 |
| 10 | 兼容 | compatibility, deploy | 兼容性与部署检查 |
| 11 | 质量 | quality, doc | 文档质量与最佳实践 |
| 12 | 性能 | performance, troubleshoot | 性能与故障排除 |
| 13 | 交叉引用 | cross-reference | 交叉引用验证（新增） |
| 14 | 章节 | section, completeness | 章节完整性检查（新增） |
| 15 | 质量增强 | quality-enhanced | 内容质量增强检查（新增） |

**快捷方式：**
- `all` - 所有检查项
- `基础识别` - 检查项01-03
- `内容验证` - 检查项04-06
- `配置验证` - 检查项07-09
- `质量评估` - 检查项10-12
- `完整性验证` - 检查项13-15（新增）

## 使用场景

### 新技能开发
```bash
# 1. 检查新技能（默认检查全部）
/skill-validator ~/.claude/skills/new-skill

# 2. 交互式修复基础和元数据
/skill-validator ~/.claude/skills/new-skill fix 基础 元数据

# 3. 自动修复格式问题
/skill-validator ~/.claude/skills/new-skill auto-fix 内容 附属
```

### 现有技能优化
```bash
# 1. 检查当前状态
/skill-validator .claude/skills/existing-skill

# 2. 分阶段修复，每次修复后验证
/skill-validator .claude/skills/existing-skill fix 基础识别
/skill-validator .claude/skills/existing-skill fix 内容验证
/skill-validator .claude/skills/existing-skill fix 配置验证
/skill-validator .claude/skills/existing-skill fix 质量评估
/skill-validator .claude/skills/existing-skill fix 完整性验证
```

### 快速修复
```bash
# 1. 自动修复基础结构问题（安全）
/skill-validator ~/.claude/skills/my-skill auto-fix 01

# 2. 批量修复多个技能
for skill in ~/.claude/skills/*/; do
  /skill-validator "$skill" auto-fix 01 02
done
```

### 新增完整性验证（阶段5）
```bash
# 1. 仅验证交叉引用
/skill-validator ~/.claude/skills/my-skill check 13

# 2. 仅验证章节完整性
/skill-validator ~/.claude/skills/my-skill check 14

# 3. 仅验证内容质量
/skill-validator ~/.claude/skills/my-skill check 15

# 4. 验证整个阶段5（完整性验证）
/skill-validator ~/.claude/skills/my-skill check 完整性验证
```

## 完整验证工作流

### 新技能完整验证流程
```bash
# 第1步：基础结构检查
/skill-validator ~/.claude/skills/new-skill check 01 02 03

# 第2步：内容和附属文件检查
/skill-validator ~/.claude/skills/new-skill check 04 05 06

# 第3步：配置验证
/skill-validator ~/.claude/skills/new-skill check 07 08 09

# 第4步：质量评估
/skill-validator ~/.claude/skills/new-skill check 10 11 12

# 第5步：完整性验证（新增）
/skill-validator ~/.claude/skills/new-skill check 13 14 15
```

### 按阶段批量检查
```bash
# 阶段1：基础识别
/skill-validator ~/.claude/skills/my-skill check 基础识别

# 阶段2：内容验证
/skill-validator ~/.claude/skills/my-skill check 内容验证

# 阶段3：配置验证
/skill-validator ~/.claude/skills/my-skill check 配置验证

# 阶段4：质量评估
/skill-validator ~/.claude/skills/my-skill check 质量评估

# 阶段5：完整性验证（新增）
/skill-validator ~/.claude/skills/my-skill check 完整性验证
```

### 交互式修复工作流
```bash
# 1. 先检查所有问题
/skill-validator ~/.claude/skills/my-skill check

# 2. 修复基础和元数据问题
/skill-validator ~/.claude/skills/my-skill fix 01 02 03

# 3. 修复内容和附属文件问题
/skill-validator ~/.claude/skills/my-skill fix 04 05 06

# 4. 验证完整性（新增检查项）
/skill-validator ~/.claude/skills/my-skill check 13 14 15
```

### 自动修复安全工作流
```bash
# 1. 自动修复基础结构问题（通常安全）
/skill-validator ~/.claude/skills/my-skill auto-fix 01

# 2. 自动修复元数据格式问题
/skill-validator ~/.claude/skills/my-skill auto-fix 03

# 3. 自动修复内容格式问题
/skill-validator ~/.claude/skills/my-skill auto-fix 04

# 4. 验证交叉引用和完整性（新增检查项）
/skill-validator ~/.claude/skills/my-skill check 13 14 15
```

## 实际应用场景

### 多技能批量验证
```bash
# 验证项目中的所有技能
for skill in .claude/skills/*/; do
  echo "验证技能：$skill"
  /skill-validator "$skill" check
  echo "---"
done
```

### 重点验证内容质量
```bash
# 仅验证与内容质量相关的检查项
/skill-validator ~/.claude/skills/my-skill check 03 04 11 15
# 03-元数据（description质量）
# 04-内容结构与格式
# 11-文档质量与最佳实践
# 15-内容质量增强（新增）
```

### 重点验证引用和依赖
```bash
# 仅验证引用相关检查项
/skill-validator ~/.claude/skills/my-skill check 05 13
# 05-附属文件检查
# 13-交叉引用验证（新增）
```

### 插件技能特殊验证
```bash
# 验证插件技能的引用和路径
/skill-validator path/to/plugin/skills/my-plugin-skill check 13 15
# 13-交叉引用验证（特别重要）
# 15-内容质量增强（包含 ${CLAUDE_SKILL_DIR} 检查）
```

## 输出说明

### 检查模式输出
- 📋 技能基本信息
- ❌ 发现的问题（按严重程度分类）
- 📊 验证统计

### 修复模式输出
- 包含检查模式的所有输出
- 🔧 修复待办清单
- 📋 修复执行报告（成功/失败/跳过统计）

### 自动修复模式输出
- 包含检查模式的所有输出
- 📋 自动修复执行报告
- 📝 修改记录和备份信息

### 优先级修复建议
按优先级列出修复建议：
- 🔴 立即修复（严重问题）
- 🟡 尽快修复（警告）
- 🔵 后续优化（建议）

## 新增检查项详细说明

### 13-交叉引用验证（18项检查点）

**主要检查内容：**
- 所有相对链接能解析到现有文件
- 阶段文档引用验证
- references/ 目录存在性检查
- 核心规则文件引用验证
- 数据文件引用验证
- Token 管理文件验证
- 文件命名规范（NN-description.md）
- 循环引用检测（文件、依赖、技能间）
- 引用完整性和组织性

**适用场景：**
- 复杂多阶段技能的深度验证
- 插件技能的引用和路径验证
- 技能发布前的完整质量检查

### 14-章节完整性检查（13项检查点）

**主要检查内容：**
- 必须包含概述章节（职责与输入输出）
- 概述章节应包含职责说明、输入输出说明
- 多阶段 skill 必须包含阶段总览章节
- 阶段总览应列出所有阶段及简要描述
- 复杂 skill 应包含 Cache/Todo/Token 管理指导
- 复杂 skill（3+ 阶段）应包含错误处理章节
- 应包含参考文档（References）章节
- 章节顺序和层级应合理

**适用场景：**
- 确保技能文档的完整性和规范性
- 复杂多阶段技能的结构检查
- 技能发布前的章节完整性验证

### 15-内容质量增强检查（21项检查点）

**主要检查内容：**
- skill 正文应包含可操作的指导（步骤、命令、检查清单）
- 操作指导应使用祈使动词
- 指导应具体而非模糊
- 应使用官方替换变量语法（$ARGUMENTS、${CLAUDE_SESSION_ID} 等）
- 变量语法必须正确
- description + when_to_use 的总长度不应超过 250 个字符
- 描述应前置关键用例
- description 应包含高频场景关键词
- 有副作用的任务型 skill 应设置 'disable-model-invocation: true'
- 无副作用的参考类 skill 不应设置 disable-model-invocation: true
- 引用脚本或自身目录中文件的 skill 应使用 ${CLAUDE_SKILL_DIR}
- ${CLAUDE_SKILL_DIR} 路径构建应正确
- 带有 'context: fork' 的 skill 应包含明确的任务指导
- context: fork 应仅在需要子代理时使用
- 如果 skill 目录包含支持文件，应在 SKILL.md 中引用它们
- 所有的重要支持文件都应被引用
- 技能内容应使用清晰易懂的语言
- 技能内容应逻辑连贯
- 技能内容应完整覆盖主要场景

**适用场景：**
- 提升技能的可操作性和用户体验
- 确保技能描述的准确性和有效性
- 验证技能的副作用配置和上下文使用
- 检查技能的质量和专业性

## 输出示例

### 新增检查项的输出示例
```
正在验证技能：my-awesome-skill
路径：~/.claude/skills/my-awesome-skill
执行检查项：13, 14, 15 (共3项)
验证时间：2026-05-11 10:30:00

📊 验证统计
─────────────────────────────
执行模式：check
执行检查项：13, 14, 15
总检查项：52项
✅ 通过：48项
🟡 警告：4项
🔴 严重问题：0项
🔵 优化建议：0项
通过率：92.3%
─────────────────────────────

📄 详细报告已生成：~/.claude/skills/my-awesome-skill/skill-validation-report.md
```

## 常见问题

**Q: 如何只检查不修复？**
A: 使用默认模式：`/skill-validator [路径]` 或显式指定：`/skill-validator [路径] check`

**Q: 修复模式安全吗？**
A: 安全。修复模式每项修复前都会向您确认，您可以选择跳过或修改修复方案。

**Q: 自动修复模式会修改什么？**
A: 只修复明确的、低风险的问题，如格式错误、文本替换等。不会执行破坏性操作。

**Q: 如何选择检查项？**
A: 可以使用数字编号（01-15）或中文名称（基础、类型、元数据等）。

**Q: 可以同时指定模式和检查项吗？**
A: 可以。例如：`/skill-validator [路径] fix 01 03` 或 `/skill-validator [路径] auto-fix all`

**Q: 如何使用新增的完整性验证？**
A: 使用编号（13、14、15）或中文名称（交叉引用、章节、质量增强），或使用快捷方式"完整性验证"。

**Q: 修复失败了怎么办？**
A: 工具会记录失败原因，您可以手动修复或尝试重新运行。

**Q: 生成的报告在哪里？**
A: 报告自动生成到被验证的技能目录，文件名为 `skill-validation-report.md`

**Q: 如何只验证新增的检查项？**
A: 使用命令：`/skill-validator [路径] check 13 14 15` 或 `/skill-validator [路径] 检查 完整性验证`

**Q: 新增检查项与原有检查项有什么区别？**
A: 新增的检查项（13、14、15）专注于：
- 13：交叉引用的有效性和完整性
- 14：文档章节的完整性和结构性
- 15：内容的质量、可操作性和最佳实践

**Q: 新增检查项适合什么场景？**
A: 特别适合：
- 复杂多阶段技能的深度验证
- 技能发布前的完整质量检查
- 插件技能的引用和路径验证
- 技能维护和改进阶段的质量评估

## 最佳实践

1. **新技能开发**：先用检查模式，再用修复模式分阶段修复
2. **重要技能**：使用修复模式，确保每个修改都经过确认
3. **批量处理**：使用自动修复模式处理格式类问题
4. **定期维护**：定期运行检查模式监控技能质量
5. **完整性验证**：发布前使用完整性验证确保技能质量

## 技术支持

如有问题，请查看详细的检查项文件：
- `references/13-cross-reference-validation.md` - 交叉引用验证详细说明
- `references/14-section-completeness.md` - 章节完整性检查详细说明
- `references/15-content-quality-enhanced.md` - 内容质量增强检查详细说明

---

*skill-validator v1.0.0 - 包含15个检查项，共428个检查点*