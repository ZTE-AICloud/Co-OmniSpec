---
description: 外部依赖接口反构核心规则
parent: reverse-external-interfaces
---

## 执行原则

- **按语言识别**：必须根据代码库主要语言，通过大模型归纳该语言的导入/引用语法后再扫描。
- **三分类**：系统（标准库/系统 API）、本代码库（本地模块）、外部（第三方/代码库外）。
- **仅文档化有调用的外部**：只对在代码库中至少有一处调用点的外部符号生成 `EXTERNAL-API_xxx.md`。
- **输出命名**：`EXTERNAL-API_{三位数字}_{简短描述}.md`，输出到 `omni-doc/specs/external-interfaces/`。
- **运行模式**：默认自动化；`--interactive` 为对话模式（阶段完成后询问确认）；`--clear-cache` 或用户要求重跑时强制重录。
- **目录排除**：应用 `--exclude`（可多个）及默认排除（隐藏目录、`omni-doc/`）；扫描与调用点检索均在同一排除规则下进行。

## 分批与规模

- 若导入数量或文件数量很大，可分批扫描、分批生成文档，控制单次上下文与 Token。
- 阶段文件位于：`本 Skill 内 references/stages/`。
