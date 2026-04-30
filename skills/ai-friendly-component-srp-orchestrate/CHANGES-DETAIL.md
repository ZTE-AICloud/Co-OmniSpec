# 变更内容详细说明

## 版本信息
- **版本**: v1.1
- **发布日期**: 2026-03-27
- **Commit**: f654499

## 功能概述

本次更新为 `ai-friendly-component-srp-orchestrate` skill 新增**增量模式**支持，允许仅分析 git diff 涉及的变更模块，并提供门禁判定能力，适用于 CI/CD 场景。

---

## 核心功能

### 1. 增量模式
**功能描述**: 通过 git diff 识别变更模块，仅对变更部分进行 SRP 分析

**使用场景**:
- CI/CD 流水线中的质量门禁
- Pull Request 代码审查
- 增量代码质量检查

**工作流程**:
```
Step 01: 识别全量模块 → state/modules.json
Step 0.5: 识别变更模块 → state/changed-modules.json
Step 02: 分析变更模块 → state/step02-analyze-modules/*.json
Step 03: 聚合结果 → output/summary.json (标注 analysis_mode)
Step 04: 门禁判定 → output/gate-result.json (可选)
```

### 2. 门禁判定
**功能描述**: 根据配置的阈值判定代码质量是否达标

**判定指标**:
- `min_avg_score`: 最低平均分数 (默认 0.7)
- `max_avg_violation_count`: 最大平均违规数 (默认 5)
- `min_confidence`: 最低置信度 (默认 0.6)

**输出**:
- `gate_passed`: true/false
- `violations`: 未通过的检查项列表
- `actual_values`: 实际度量值

---

## 新增脚本详解

### scripts/identify-changed-modules.sh
**功能**: 识别 git diff 涉及的变更模块

**输入参数**:
- `--project-path`: 项目根目录
- `--modules-json`: 全量模块清单路径
- `--output`: 输出文件路径
- `--base-commit`: 对比基线
- `--target-commit`: 目标提交 (默认 HEAD)

**输出格式**:
```json
{
  "mode": "incremental",
  "base_commit": "abc123",
  "target_commit": "HEAD",
  "modules": {
    "核心业务域": [
      {
        "name": "commands",
        "path": "pdmcli/commands",
        "changed_files": ["pdmcli/commands/cli.py"],
        "files": ["cli.py", "utils.py"]
      }
    ]
  },
  "statistics": {
    "total_changed_modules": 1,
    "total_changed_files": 1
  }
}
```

### scripts/gate-check.py
**功能**: 门禁判定脚本

**输入参数**:
- `--input`: summary.json 路径
- `--config`: 门禁配置文件路径 (默认 .gate-config.json)
- `--output`: 输出文件路径

**退出码**:
- 0: 门禁通过
- 1: 门禁失败

**输出格式**:
```json
{
  "gate_passed": true,
  "thresholds": {
    "min_avg_score": 0.7,
    "max_avg_violation_count": 5,
    "min_confidence": 0.6
  },
  "actual_values": {
    "avg_total_score": 0.85,
    "avg_violation_count": 2,
    "avg_confidence": 0.9
  },
  "violations": []
}
```

---

## 修改内容详解

### scripts/aggregate.py
**新增参数**:
- `--changed-modules-json`: 变更模块清单路径（用于检测增量模式）

**新增输出字段**:
- `analysis_mode`: "full" 或 "incremental"
- `base_commit`: 对比基线（增量模式）
- `target_commit`: 目标提交（增量模式）

**逻辑变更**:
```python
# 自动检测增量模式
if args.changed_modules_json and Path(args.changed_modules_json).exists():
    analysis_mode = "incremental"
    # 读取 base_commit 和 target_commit
```

### SKILL.md
**新增章节**:
1. 增量模式输入参数说明
2. 增量模式工作流表格
3. 使用示例（全量/增量/门禁）
4. 门禁配置说明

**更新内容**:
- description 字段增加增量模式和门禁说明
- 目录结构增加 changed-modules.json 和 gate-result.json
- 最终输出增加增量模式相关字段说明

### DESIGN.md
**新增章节**: "增量模式设计（v1.1 新增）"

**内容包括**:
- 背景和动机
- 增量流程说明
- 关键设计原则
- 目录结构扩展

---

## 配置文件

### .gate-config.json
门禁阈值配置模板：
```json
{
  "min_avg_score": 0.7,
  "max_avg_violation_count": 5,
  "min_confidence": 0.6
}
```

**自定义方法**: 直接编辑此文件修改阈值

---

## 测试脚本

### scripts/test-incremental.sh
**功能**: 完整的增量模式流程测试

**测试内容**:
1. 创建模拟数据（modules.json, changed-modules.json）
2. 测试聚合脚本（验证 analysis_mode 字段）
3. 测试门禁判定（验证通过场景）

### scripts/test-gate-fail.sh
**功能**: 门禁失败场景测试

**测试内容**:
1. 创建低分模块数据
2. 验证门禁正确识别失败场景

---

## 使用示例

### 全量模式
```bash
/ai-friendly-component-srp-orchestrate --project-path /path/to/repo
```

### 增量模式
```bash
/ai-friendly-component-srp-orchestrate \
  --project-path /path/to/repo \
  --incremental \
  --base-commit origin/master
```

### CI 集成
```yaml
# GitHub Actions
- name: SRP Check
  run: |
    BASE_COMMIT=$(git merge-base HEAD origin/master)
    /ai-friendly-component-srp-orchestrate \
      --project-path . \
      --incremental \
      --base-commit $BASE_COMMIT \
      --enable-gate
```

---

## 兼容性

- **向后兼容**: 全量模式保持不变，现有用法无需修改
- **模式切换**: 通过 `changed-modules.json` 存在性自动识别
- **可选功能**: 门禁判定为可选步骤，不影响基础分析流程

---

## 验证结果

✅ 增量模式流程测试通过
✅ 门禁通过场景验证成功
✅ 门禁失败场景验证成功
✅ 所有脚本可执行权限已设置
✅ 文档完整性验证通过
