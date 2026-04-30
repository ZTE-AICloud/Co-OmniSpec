---
name: eval
description: 综合评测技能：先采集SDD流程的代码变更信息，再使用第三方评测模型对代码质量进行评估。当用户需要"综合评测"、"完整评测流程"、"SDD评测"时触发本技能。
compatibility: Requires Python environment with requests, jinja2, loguru packages and access to LLM API endpoint
---
# OmniEval 综合代码评测技能

本技能整合了代码变更采集和第三方模型评测功能，提供完整的 SDD 流程代码质量评估。

## 功能说明

1. **代码变更采集**：从当前 SDD 分支采集代码变更信息，生成评测所需的 JSON 文件
2. **自动评测**：使用第三方评测模型对生成的代码进行质量评估
3. **结果输出**：将评测结果同时输出到控制台和文件

## 执行流程

### 阶段 1：代码变更采集

调用 `/eval-collector` 技能：

- 自动检测当前 SDD 分支
- 扫描目标目录下的代码变更
- 提取 feature_infos 和 code_blocks
- 生成 `changes/{FEATURE_DIR}/evalset/config.result.json`

### 阶段 2：代码质量评测

调用 `/eval-evaluator` 技能：

- 读取 `changes/{FEATURE_DIR}/evalset/config.result.json` 文件
- 使用 ICE Score 和 Code Judge 指标进行评测
- 生成详细的评测报告

## 输入参数

自动检测当前项目的主要代码目录：

- 优先级顺序： 当前目录
- 用户可以通过参数指定特定目录来覆盖自动检测
- **评测模型**：使用配置文件中指定的模型（默认 glm4.6）

## 输出

1. **控制台输出**：显示评测进度和最终结果
2. **文件输出**：`changes/{FEATURE_DIR}/evalset/result.txt` - 包含详细的评测报告

## 评测指标

### ICE Score 组件

- **功能正确性 (0-1)**：代码是否正确实现了需求
- **实用性 (0-1)**：代码是否实用且结构良好

### Code Judge 组件

- **评分 (0-1)**：代码一致性和整体质量
- **不一致问题**：发现的问题列表
  - 严重级别：Small, Major, Fatal
- **问题数量**：发现的问题总数

### 综合指标

- **平均 LLM 评测指标**：所有指标的综合得分

## 使用示例

### 基础用法

```
/eval
```

执行步骤：

1. 自动检测并采集当前项目的主要代码目录变更
2. 自动进行代码质量评测
3. 输出评测结果到控制台和文件

### 指定目录

```
/eval tests
```

执行步骤：

1. 采集 `tests` 目录的变更
2. 进行评测
3. 输出结果

## 输出模板

```
评测开始...

第一步：采集代码变更信息
- 当前分支: 001-TCF-5064840-vpn-service
- 目标目录: networking_zte (自动检测)
- 采集完成，生成 evalset/config.result.json

第二步：执行代码质量评测
- 使用模型: glm4.6
- 评测中...

评测结果

代码已使用 glm4.6 模型完成评测，以下是详细结果：

📊 综合评分

平均LLM评测指标: 0.83
- 功能正确性: 0.75
- 实用性: 1.0
- 代码一致性: 0.75

🔍 详细分析

功能正确性 (0.75/1.0)
优点:
- xxx

主要问题:
- xxx

实用性 (1.0/1.0)
优点:
- xxx

代码一致性 (0.75/1.0)
发现的不一致问题:
- xxx

💡 改进建议
1. xxx
2. xxx

总结：xxxx

结果已保存到: changes/001-TCF-5064840-vpn-service/evalset/result.txt
```

## 错误处理

- 分支检测失败：确保在 git 仓库中且在有效的 SDD 分支上
- 文件不存在：检查 `tasks.md` 和目标目录是否存在
- API 调用失败：检查网络连接和 API 配置
- 评测失败：检查输入格式和模板文件

## 注意事项

- 确保当前目录是 git 仓库根目录
- 需要配置有效的 LLM API 访问权限
- 评测过程可能需要几分钟，请耐心等待
- 结果文件会保存在当前分支的 evalset 目录下
