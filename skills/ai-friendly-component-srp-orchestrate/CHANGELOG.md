# 变更清单

## 提交信息
- **Commit**: f654499
- **分支**: develop
- **日期**: 2026-03-27
- **标题**: AI友好架构skill：增量代码度量支持

## 变更统计
- 10 个文件变更
- 新增 628 行
- 删除 8 行

## 新增文件

### 1. `.gate-config.json`
门禁阈值配置模板
- 路径: `agent/skills/ai-friendly-component-srp-orchestrate/.gate-config.json`
- 行数: 5 行
- 用途: 定义门禁判定的阈值标准

### 2. `README-INCREMENTAL.md`
增量模式使用指南
- 路径: `agent/skills/ai-friendly-component-srp-orchestrate/README-INCREMENTAL.md`
- 行数: 79 行
- 用途: 提供增量模式的使用说明和 CI 集成示例

### 3. `scripts/gate-check.py`
门禁判定脚本
- 路径: `agent/skills/ai-friendly-component-srp-orchestrate/scripts/gate-check.py`
- 行数: 81 行
- 用途: 根据阈值判定 SRP 分析结果是否通过门禁

### 4. `scripts/identify-changed-modules.sh`
变更模块识别脚本
- 路径: `agent/skills/ai-friendly-component-srp-orchestrate/scripts/identify-changed-modules.sh`
- 行数: 96 行
- 用途: 识别 git diff 涉及的变更模块

### 5. `scripts/test-incremental.sh`
增量模式测试脚本
- 路径: `agent/skills/ai-friendly-component-srp-orchestrate/scripts/test-incremental.sh`
- 行数: 131 行
- 用途: 验证增量模式完整流程

### 6. `scripts/test-gate-fail.sh`
门禁失败场景测试脚本
- 路径: `agent/skills/ai-friendly-component-srp-orchestrate/scripts/test-gate-fail.sh`
- 行数: 54 行
- 用途: 验证门禁失败场景

### 7. `workflow/step00.5-identify-changed-modules.md`
Step 0.5 工作流文档
- 路径: `agent/skills/ai-friendly-component-srp-orchestrate/workflow/step00.5-identify-changed-modules.md`
- 行数: 63 行
- 用途: 描述变更模块识别步骤

## 修改文件

### 8. `DESIGN.md`
设计文档更新
- 路径: `agent/skills/ai-friendly-component-srp-orchestrate/DESIGN.md`
- 变更: +34 行
- 主要内容: 新增"增量模式设计"章节

### 9. `SKILL.md`
技能说明更新
- 路径: `agent/skills/ai-friendly-component-srp-orchestrate/SKILL.md`
- 变更: +73 行, -8 行
- 主要内容:
  - 更新 description 支持增量模式
  - 新增增量模式工作流表格
  - 新增使用示例和门禁配置说明

### 10. `scripts/aggregate.py`
聚合脚本更新
- 路径: `agent/skills/ai-friendly-component-srp-orchestrate/scripts/aggregate.py`
- 变更: +20 行
- 主要内容:
  - 新增 `--changed-modules-json` 参数
  - 自动检测增量模式
  - 输出中添加 `analysis_mode`、`base_commit`、`target_commit` 字段
