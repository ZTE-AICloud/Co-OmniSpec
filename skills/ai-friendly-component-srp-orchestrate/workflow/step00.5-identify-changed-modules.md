# Step 0.5: 识别变更模块（增量模式）

## 执行者
脚本 `scripts/identify-changed-modules.sh`

## 输入
- `project_path`: 项目根目录绝对路径
- `state/modules.json`: step01 输出的全量模块清单
- `base_commit`: 对比基线（如 `origin/master`）
- `target_commit`: 目标提交（默认 `HEAD`）

## 输出
- `state/changed-modules.json`: 变更模块清单

## 执行说明

### 1. 收集变更文件（三种来源）

| 类型 | 命令 | 说明 |
|------|------|------|
| 已跟踪文件变更 | `git diff --name-only` | 修改/删除的文件 |
| Untracked 新增文件 | `git ls-files --others --exclude-standard` | 新增且未跟踪的文件（**默认启用**） |
| Staged 变更 | `git diff --cached --name-only` | 已 git add 但未 commit 的变更（需 `--detect-staged`） |

> **注意**：所有变更必须先 `git add` 再运行脚本。未跟踪文件默认会被检测，
> 如需跳过（如只想分析已 commit 的 diff），传入 `--no-detect-untracked`。

### 2. 精确模块匹配

将变更文件路径与 `state/modules.json` 中的模块路径做**层级精确匹配**：
- 从变更文件的顶层往下逐层查找最近的模块路径
- 例如：`src/utils/helper.py` 匹配模块 `src/utils`（而非 `src`）
- 避免 `src/utils-extra` 错误归属到 `src/utils`（通过路径层级而非字符串前缀判断）

### 3. Orphan 文件追踪

未匹配到任何模块的变更文件（如新增模块、旧模块被删除后的残留引用），
会记录在 `orphan_files` 字段中，下游可感知并处理。

### 4. 输出格式

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
  "orphan_files": [],
  "statistics": {
    "total_changed_modules": 3,
    "total_changed_files": 8,
    "orphan_files_count": 0
  }
}
```

字段说明：
- `orphan_files`: 未匹配到任何模块的变更文件（可能是新增模块或删除文件）
- `orphan_files_count`: orphan 文件数量

## 执行命令

```bash
./scripts/identify-changed-modules.sh \
  --project-path "$PROJECT_PATH" \
  --modules-json state/modules.json \
  --output state/changed-modules.json \
  --base-commit origin/master \
  --target-commit HEAD
```

可选 flags：
- `--detect-staged`: 同时检测已 staged 但未 commit 的变更
- `--no-detect-untracked`: 跳过 untracked 新增文件（仅分析已跟踪文件的 diff）

## 验证检查点
- [ ] `state/changed-modules.json` 文件存在
- [ ] `mode` 字段为 `"incremental"`
- [ ] `modules` 对象包含至少一个架构层（如有变更）
- [ ] `orphan_files` 字段存在（可为空数组）
- [ ] `statistics.orphan_files_count` 字段存在
- [ ] `statistics.total_changed_modules` >= 0
- [ ] 每个模块包含 `changed_files` 字段
