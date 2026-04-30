---
description: 外部依赖接口反构的数据交换规范
parent: reverse-external-interfaces
target: external-interfaces
---

### 缓存目录与文件

- **缓存目录**：`{REPO_ROOT}/.cache/reverse/external-interfaces/`
- **import-list.json**：阶段1 输出，包含所有扫描到的导入及分类（system / local / external）
- **.cache-status.json**：阶段确认状态

### import-list.json 建议结构

```json
{
  "languages": ["cpp", "python"],
  "import_patterns": {
    "cpp": { "include_directive": "#include", "angle_brackets": "system_or_external", "quotes": "local_or_external" },
    "python": { "import_stmt": "import x / from x import y" }
  },
  "imports": [
    {
      "symbol": "PropertyHelper::defaultHelper",
      "module_or_header": "Poco/Util/PropertyHelper.h",
      "source_file": "source/OAM_LTM_Fsm.cpp",
      "classification": "external",
      "language": "cpp"
    },
    {
      "symbol": "std::string",
      "module_or_header": "string",
      "source_file": "source/foo.cpp",
      "classification": "system",
      "language": "cpp"
    }
  ],
  "stats": { "total": 120, "system": 40, "local": 30, "external": 50 }
}
```

### 输出目录与命名

- **输出目录**：`{REPO_ROOT}/omni-doc/specs/external-interfaces/`
- **单接口文档**：`EXTERNAL-API_{001..N}_{简短描述}.md`
- **汇总**：`EXTERNAL-API_SUMMARY.json`（含 stats 与 generated_files 列表）

### 运行模式与重录（与 reverse.rules 对齐）

- **自动化模式（默认）**：不传 `--interactive` 时全自动执行，各阶段确认步骤视为已确认。
- **对话模式**：`--interactive` 时阶段1、阶段2 完成后暂停并询问用户确认；`--non-interactive` / `--yes` 强制全自动。
- **重录**：`--clear-cache` 或用户在对话中要求重跑时，已确认阶段也重新执行；阶段2 重录前先删除输出目录下已有 `EXTERNAL-API_*.md` 与 `EXTERNAL-API_SUMMARY.json`。

### 目录排除

- **`--exclude`**：可多次使用，排除模式应用于扫描与调用点检索；与 `--path` 一起从 `$ARGUMENTS` 解析。
- **默认排除**：隐藏目录（如 `.git/`、`.idea/`、`.vscode/`、`.cache/`）；external-interfaces 额外默认排除 `omni-doc/`。
- 阶段1 可将本次 `path`、`exclude_patterns` 写入 `import-list.json`，供阶段2 与重录时保持一致。
