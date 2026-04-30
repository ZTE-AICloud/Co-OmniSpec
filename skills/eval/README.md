# OmniEval 综合代码评测技能

## 概述

OmniEval 是一个综合性的代码评测技能，它整合了两个核心功能：
1. **代码变更采集** (`eval-collector`)
2. **代码质量评测** (`eval-evaluator`)

该技能专为 SDD（Spec-Driven Development）流程设计，能够自动化地采集代码变更并进行质量评估。

## 使用方法

### 基础用法
```bash
/eval
```
自动检测项目中的主要代码目录（优先级：networking_zte > src > lib）进行评测。

### 指定目录
```bash
/eval tests
```
对指定的目录（如 `tests`）进行评测，覆盖自动检测。

## 执行流程

1. **自动检测当前分支**：通过 `git branch --show-current` 获取当前 SDD 分支
2. **采集代码变更**：自动检测代码目录并调用 `/eval-collector` 生成评测数据文件
3. **执行评测**：调用 `/eval-evaluator` 对采集的数据进行评测
4. **输出结果**：将评测结果显示在控制台并保存到文件

## 输出文件

- **评测数据**：`changes/{FEATURE_DIR}/evalset/config.result.json` 或 `eval.result.json`
- **评测结果**：`changes/{FEATURE_DIR}/evalset/result.txt`

## 评测指标

- **ICE Score**：包含功能正确性和实用性评分
- **Code Judge**：代码一致性和质量问题分析
- **综合评分**：所有指标的平均值

## 依赖要求

- Python 3.x
- 已安装并配置好以下技能：
  - `eval-collector`
  - `eval-evaluator`
- Git 仓库环境
- 有效的 LLM API 配置

## 注意事项

- 确保在 git 仓库的根目录执行
- 当前分支应为有效的 SDD 分支
- 需要有有效的网络连接以调用 LLM API
- 评测过程可能需要几分钟时间

## 故障排除

### 常见问题

1. **找不到分支**
   - 确保在 git 仓库中
   - 使用 `git branch --show-current` 检查

2. **找不到评测数据文件**
   - 检查 `changes/{FEATURE_DIR}/evalset/` 目录
   - 确保 `eval-collector` 执行成功

3. **评测失败**
   - 检查 API 配置
   - 确保网络连接正常
   - 查看错误日志获取详细信息