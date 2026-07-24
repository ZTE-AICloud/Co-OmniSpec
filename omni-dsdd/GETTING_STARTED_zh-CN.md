# Co-OmniSpec 入门指南

本指南介绍如何以两个 Claude Code 插件（`omni-dsdd` 与 `omni-reverse`）方式安装 Co-OmniSpec，并跑通第一次规范驱动开发流程。

> **English** — See [GETTING_STARTED.md](GETTING_STARTED.md) for the English version.

---

## 目录

- [前置条件](#前置条件)
- [安装](#安装)
- [验证安装](#验证安装)
- [首次使用：章程](#首次使用章程)
- [首次使用：规格编写](#首次使用规格编写)
- [下一步](#下一步)

---

## 前置条件

开始前请确认：

| 要求 | 说明 |
|------|------|
| **Claude Code** | [code.claude.com](https://code.claude.com/)，需支持插件市场。 |
| **Git** | 用于特性分支与 `changes/` 目录。 |
| **Bash 或 PowerShell** | 用于运行 `.omni-infra/scripts/` 下的共享脚本。 |

---

## 安装

Co-OmniSpec 现在以**两个**插件形式发布，请始终一起安装，使 DSDD 核心与逆向能力都可即时可用。

### 方式一：通过会话斜杠命令安装（推荐）

```text
/plugin marketplace add ZTE-AICloud/Co-OmniSpec
/plugin install omni-dsdd@CoMind-plugins
/plugin install omni-reverse@CoMind-plugins
```

若习惯简写，第一条命令可替换为 `/market add ZTE-AICloud/Co-OmniSpec`。

### 方式二：Claude 命令行安装

如果偏好脚本化或非交互安装，按以下顺序执行：

```bash
claude plugin marketplace add ZTE-AICloud/Co-OmniSpec
claude plugin install omni-dsdd@CoMind-plugins
claude plugin install omni-reverse@CoMind-plugins
```

三条命令完成后，Claude Code 会同时为两个插件装载所需命令、技能、Hook 以及共享的 `.omni-infra/` 模板。

---

## 验证安装

1. **在 Claude Code 中打开目标项目**。
2. **打开 AI 对话**，确认能看到 `/constitution`、`/specify`、`/reverse`、`/routing` 等斜杠命令。
3. **确认市场与插件状态**：

   - 运行 `/plugin marketplace list`（或 `/market list`）应能列出 `CoMind-plugins`；
   - 运行 `/plugin`（Discover）应能同时看到 `omni-dsdd` 与 `omni-reverse` 已安装。

若缺失其中任一项，重新执行上一节的对应安装命令即可。安装完成后可能需要重新打开项目会话才能生效。

---

## 首次使用：章程

章程定义项目原则与约束，后续的规格、设计、任务与实施都应与之一致。

1. 在 Claude Code 中打开 AI 对话。
2. 执行：

   ```text
   /constitution
   ```

3. 在同一句或下一句中加入你希望的原则描述，例如：

   ```text
   创建关注代码质量、测试标准、用户体验一致性和性能的原则，
   并说明这些原则应如何指导技术决策。
   ```

4. Agent 会创建或更新 `.omni-infra/memory/constitution.md`。之后可随时编辑该文件以细化原则。

---

## 首次使用：规格编写

规格编写把简短的功能描述转化为完整规范（分支、上下文、spec、需求检查清单）。

1. **创建特性分支与规范**，执行：

   ```text
   /specify
   ```

2. **在同一句或下一句提供功能描述**。侧重「做什么」和「为什么」，暂不写技术栈。示例：

   ```text
   做一个简单的相册应用：用户可以创建相册、上传照片、以网格形式浏览。
   相册是扁平的，不嵌套。第一版不需要登录，单用户即可。
   ```

3. Agent 将：

   - 创建特性分支（如 `001-photo-albums`）；
   - 在 `changes/` 下创建目录（如 `changes/001-photo-albums/`）；
   - 生成 `spec.md`、`context.md` 以及 `checklists/` 下的需求检查清单。

4. **检查**生成的 `changes/<分支名>/spec.md` 与 `checklists/requirements.md`。如有不清楚之处，接着运行 `/clarify`。

---

## 下一步

- **澄清** — 运行 `/clarify` 消除规范中的歧义（建议在设计前执行）。
- **设计** — 运行 `/design` 并描述技术栈与架构，生成 `design.md`、数据模型、契约等。
- **任务** — 运行 `/tasks` 根据设计生成 `tasks.md`。
- **分析** — 运行 `/analyze` 检查 spec、design、tasks 之间的一致性。
- **实施** — 运行 `/implement` 按顺序执行任务。
- **归档** — 运行 `/archive` 对已完成特性进行归档/回流。
- **逆向** — 安装 [`omni-reverse`](../omni-reverse/README.md)，在迭代现有代码前用 `/reverse` 先文档化。

完整工作流与所有命令说明见 [用户指南](USER_GUIDE_zh-CN.md)。
