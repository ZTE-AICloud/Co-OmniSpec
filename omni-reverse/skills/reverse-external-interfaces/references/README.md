## `reverse.external-interfaces` 外部依赖接口识别说明（配合 `reverse --target external-interfaces` 使用）

本目录定义**外部依赖接口识别**的完整行为：阶段拆分、缓存与重录、运行模式、目录排除。

### 1. 入口与实现位置

- 主入口：命令 `reverse`（`claude/commands/reverse.md`），`--target external-interfaces` 时调用 Skill `omni-reverse:reverse-external-interfaces`
- 编排与阶段说明：本 Skill 的 `SKILL.md` 及 `references/` 下文档
- 实现目录：`本 Skill（reverse-external-interfaces）的 references/`
  - `core-rules.md`：执行与输出规则
  - `data.md`：缓存与数据约定
  - `stages/01-import-patterns-and-scan.md`：阶段1 导入模式与扫描
  - `stages/02-external-calls-and-docs.md`：阶段2 外部调用与文档生成

### 2. 两阶段概览

1. **阶段1：导入模式与扫描**  
   识别主要语言，用大模型归纳导入语法并区分系统/本库/外部；在 `--path` 范围内、并应用 `--exclude` 与默认排除后扫描源文件，输出 `import-list.json`。
2. **阶段2：外部调用与文档生成**  
   对分类为“外部”的符号在代码库中检索调用点；仅保留有至少一处调用的项；生成 `EXTERNAL-API_{001..N}_{描述}.md` 与 `EXTERNAL-API_SUMMARY.json` 到 `omni-doc/specs/external-interfaces/`。

### 3. 默认行为与注意事项（与 reverse.rules 对齐）

- **自动化模式（默认）**：不传 `--interactive` 时，全自动执行；各阶段「是否确认？」按已确认处理，自动跑完阶段1～2。
- **对话模式**：传入 `--interactive` 时，阶段1、阶段2 完成后暂停并询问确认；阶段2 内还有两处确认：（1）**识别出待生成外部接口清单之后、生成实际接口文件之前**：展示清单并支持用户对清单**增删改查**，用户确认后再生成 EXTERNAL-API_xxx.md；（2）单接口文档全部生成后、**汇总文件（EXTERNAL-API_SUMMARY.json）生成前**再次暂停并询问是否生成汇总文件；`--non-interactive` / `--yes` 强制全自动。
- **重录/多次执行**：  
  - 使用 `--clear-cache` 或在对话中明确要求重跑时，已确认阶段也会重新执行。  
  - 阶段2 重录时先删除 `omni-doc/specs/external-interfaces/` 下已有 `EXTERNAL-API_*.md` 与 `EXTERNAL-API_SUMMARY.json`，再重新生成。
- **目录排除**：  
  - 支持 `--exclude <pattern>` 可多次使用；扫描与调用点检索均应用排除。  
  - 默认排除隐藏目录（如 `.git/`、`.idea/`、`.vscode/` 等）。  
  - external-interfaces 额外默认排除 `omni-doc/`，避免把已生成文档当源码扫描。

更多细节见 `core-rules.md`、`data.md` 与各阶段文件。
