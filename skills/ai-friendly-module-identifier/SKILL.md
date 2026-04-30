---
name: ai-friendly-module-identifier
version: v1.0
description: 识别代码库中的所有模块（目录级+文件级双层粒度），支持业务模块和非业务模块（数据持久层、接口适配层、基础设施层、公共工具层）。使用时：当需要分析代码库结构、识别模块边界、进行架构分析时。
---

# Module Identifier

识别代码库中的所有模块，采用目录级（架构边界）+ 文件级（代码实现）双层粒度模型。

## 执行方式

**必须使用subagent执行此技能**，通过Agent tool调用，subagent_type为"general-purpose"。

## 输入参数

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `project_path` | string | ✅ | 待分析的项目根目录路径（绝对路径或相对路径） |
| `scan_depth` | enum | ❌ | 扫描深度：`shallow`（浅层，1-2层）或 `deep`（深层，全量），默认 `shallow` |
| `output_path` | string | ❌ | 分析结果的保存路径。编排层调用时传入具体路径（如 `state/modules.json`）；单独调用时默认保存到 `.claude/skills/ai-friendly-module-identifier/output/modules.json` |

## 模块分类标准

基于目录职责分析，分类到5个类型之一：

1. **核心业务域** - 直接承载企业核心商业逻辑（用户、订单、支付、库存等）
2. **数据持久层** - 数据存储、ORM映射（dao、repository、mapper、entity、model）
3. **接口适配层** - 系统交互、协议转换（controller、api、rest、handler、gateway）
4. **基础设施层** - 技术支撑、中间件（cache、mq、log、config、auth）
5. **公共工具层** - 通用工具、常量（util、common、helper、constant）

**分类方法**：
- 综合考虑目录路径、目录名、文件名、文件内容
- 不依赖固定规则，根据实际职责判断
- 每个目录归属唯一类型

## 输出格式

输出严格遵循 `schema/output-schema.json` 定义的 JSON Schema（完整字段定义见该文件）。

关键字段摘要：

| 字段路径 | 类型 | 说明 |
|---------|------|------|
| `skill_id` | string | 固定值 |
| `rule_version` | string | 当前 `v1.0` |
| `scan_depth` | enum | `shallow` \| `deep` |
| `execute_status` | enum | `success` \| `failed` |
| `project_path` | string | 项目根目录路径 |
| `modules` | object | 按架构层分类（核心业务域/数据持久层/接口适配层/基础设施层/公共工具层） |
| `modules.<层>.path` | string | 模块相对路径 |
| `modules.<层>.files` | array | 文件列表（name + lines） |
| `statistics.total_modules` | integer | 总模块数 |
| `statistics.by_category` | object | 各层模块数统计 |

## 分析流程

1. **运行扫描脚本（必须）**: 执行以下命令获取原始模块结构，脚本已自动过滤空文件和行数不足的文件：
   ```bash
   python3 .claude/skills/ai-friendly-module-identifier/scripts/scan_modules.py <project_path>
   ```
   脚本输出为 JSON 数组，每项包含 `path`、`name`、`depth`、`files`（已过滤 lines=0 的文件）。
   > **说明**：默认使用 `shallow` 扫描深度（1-2层），适合大多数场景。如需全量深层扫描，传入 `scan_depth=deep`。

2. **职责识别与分类**: 基于脚本输出结果，对每个目录进行职责分析，归类到5个标准类型之一。

3. **统计汇总**: 计算各类别的模块数、文件数、代码行数（直接使用脚本输出的 lines 值，不重复计算）。

4. **生成报告**: 将分类结果按输出格式写入文件。

## 输出路径

分析结果写入 `output_path` 参数指定的路径。若未传入 `output_path`，默认写入：

`.claude/skills/ai-friendly-module-identifier/output/modules.json`