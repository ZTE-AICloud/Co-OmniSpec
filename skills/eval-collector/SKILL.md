---
name: eval-collector
description: SDD流程代码变更采集Skill。在SDD流程执行完毕后，采集目标目录的代码变更信息，提取feature_infos和code_blocks，生成评测所需的JSON文件并保存到当前SDD分支的evalset目录下。当用户提到"采集SDD变更"、"生成评测数据"、"收集代码变更信息"、"build_configi_eval"、"evalset"时触发本技能。
---
# SDDEval 代码变更采集

本技能用于在 SDD（Spec-Driven Development）流程执行完毕后，采集代码变更信息并生成评测所需的 JSON 文件。

## 功能说明

1. 根据 `FEATURE_DIR` 解析当前任务分支名称, 识别 `changes/` 目录下面的当前分支
2. 扫描当前项目目录下的所有代码变更，但不包含.claude/、.infra/、changes/等目录
3. 从 `tasks.md` 中提取 feature_infos（"**目的**:" 行）
4. 生成符合评测格式的 JSON 文件，保存到 `changes/<branch>/evalset/` 目录

## 输入参数

本技能可通过以下方式触发：

- 直接提供目标目录路径（如 `networking_zte`、`tests`）
- 通过当前分支自动检测tasks.md位置

**默认参数**：

- 目标目录：当前目录
- tasks.md: 自动从 `changes/<branch>/tasks.md` 获取

## 执行流程

### 步骤 1: 确定当前分支和路径

```bash
git branch --show-current
```

从输出识别当前 SDD 分支名称（如 `001-TCF-5064840-vpn-service`）。

### 步骤 2: 验证必要文件存在

检查以下文件/目录是否存在：

- `changes/<branch>/tasks.md` - 必须存在
- `changes/<branch>/evalset/` - 不存在时自动创建

### 步骤 3: 采集代码变更

执行 git diff 命令获取变更文件列表：

```bash
git diff --name-only -- <target_dir>
git diff --cached --name-only -- <target_dir>
git ls-files --others --exclude-standard -- <target_dir>
```

### 步骤 4: 提取 feature_infos

从 `tasks.md` 中解析所有 `**目的**: xxx` 行作为 feature_infos。

### 步骤 5: 生成 code_blocks

对每个变更文件，提取其 unified diff 中的实际代码变更内容（+/- 行）。

### 步骤 6: 生成 JSON 文件

输出文件路径: `changes/<branch>/evalset/config.result.json`

**JSON 格式**:

```json
{
    "api": {
        "url": "https://maas-apigateway.dt.zte.com.cn/model/ai-ide/model-separation/v1/chat/completions",
        "key": "a5ec9c73-4d21-44e0-ba49-180eed598e27",
        "model_name": "glm4.6",
        "timeout": 600,
        "max_tokens": 16000,
        "temperature": 0.1
    },
    "input": {
        "feature_infos": ["目的1", "目的2", ...],
        "code_blocks": {
            "path/to/file.py": ["变更片段1", "变更片段2"],
            ...
        },
        "code_answers": [],
        "output": null
    }
}
```

## 输出

- **成功**: 生成 `changes/<branch>/evalset/config.result.json` 并显示统计信息
- **失败**: 显示错误原因

## 使用示例

### 示例 1: 使用默认参数采集 networking_zte 变更

用户输入: `采集SDD变更`

技能执行:

1. 检测当前分支: `001-TCF-5064840-vpn-service`
2. 目标目录: `networking_zte`
3. tasks.md: `changes/001-TCF-5064840-vpn-service/tasks.md`
4. 输出: `changes/001-TCF-5064840-vpn-service/evalset/config.result.json`

### 示例 2: 指定目标目录

用户输入: `采集 tests 目录的代码变更`

技能执行:

1. 检测当前分支
2. 目标目录: `tests`
3. tasks.md: `changes/<branch>/tasks.md`
4. 输出: `changes/<branch>/evalset/config.result.json`

## 注意事项

- 确保当前目录是 git 仓库根目录
- 目标目录默认是 `networking_zte`，可根据需要指定
- 如果 evalset 目录不存在会自动创建
- code_blocks 只包含实际的代码变更行（+/-），不含元信息
