# 增量模式使用指南

## 概述

增量模式仅分析 git diff 涉及的变更模块，适用于 CI 门禁场景。

## 快速开始

### 全量模式
```bash
# 分析所有模块
/ai-friendly-component-srp-orchestrate --project-path /path/to/repo
```

### 增量模式
```bash
# 仅分析变更模块
/ai-friendly-component-srp-orchestrate \
  --project-path /path/to/repo \
  --incremental \
  --base-commit origin/master
```

### 增量模式 + 门禁
```bash
# 分析变更模块并启用门禁判定
/ai-friendly-component-srp-orchestrate \
  --project-path /path/to/repo \
  --incremental \
  --base-commit origin/master \
  --enable-gate
```

## CI 集成示例

### GitHub Actions
```yaml
- name: SRP Check
  run: |
    BASE_COMMIT=$(git merge-base HEAD origin/master)
    /ai-friendly-component-srp-orchestrate \
      --project-path . \
      --incremental \
      --base-commit $BASE_COMMIT \
      --enable-gate
```

### GitLab CI
```yaml
srp_check:
  script:
    - BASE_COMMIT=$(git merge-base HEAD origin/master)
    - /ai-friendly-component-srp-orchestrate --project-path . --incremental --base-commit $BASE_COMMIT --enable-gate
```

## 门禁配置

编辑 `.gate-config.json` 自定义阈值：
```json
{
  "min_avg_score": 0.7,
  "max_avg_violation_count": 5,
  "min_confidence": 0.6
}
```

## 输出说明

### summary.json
- `analysis_mode`: "incremental" 或 "full"
- `base_commit`: 对比基线
- `target_commit`: 目标提交
- `aggregate`: 统计数据
- `modules`: 模块详情

### gate-result.json
- `gate_passed`: true/false
- `violations`: 未通过的检查项
- `actual_values`: 实际度量值
