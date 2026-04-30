# Co-OmniSpec 入门指南

本文介绍如何以 Claude Code 插件方式安装 Co-OmniSpec，并完成第一次规范驱动开发流程。

---

## 目录

- [Co-OmniSpec 入门指南](#co-omnispec-入门指南)
  - [目录](#目录)
  - [前置条件](#前置条件)
  - [安装](#安装)
    - [方式一：从克隆的仓库安装](#方式一从克隆的仓库安装)
    - [方式二：从发布包安装](#方式二从发布包安装)
  - [验证安装](#验证安装)
  - [首次使用：章程](#首次使用章程)
  - [首次使用：规格编写](#首次使用规格编写)
  - [下一步](#下一步)
---

## 前置条件

开始前请确认：

| 要求 | 说明 |
|------|------|
| **Claude Code** | [code.claude.com](https://code.claude.com/)（需支持插件市场）。 |
| **Git** | 用于特性分支与 `changes/` 目录。 |

---

## 安装

### 方式一：会话命令安装（推荐）

1. 在 Claude Code 会话中添加市场：

   ```text
   /plugin marketplace add ZTE-AICloud/Co-OmniSpec
   ```

   也可使用简写：

   ```text
   /market add ZTE-AICloud/Co-OmniSpec
   ```

2. 安装插件：

   ```text
   /plugin install omni@CoMind-plugins
   ```

3. **结果：** Claude Code 会安装 OmniSpec 所需命令、技能与 Hook。

### 方式二：Claude 命令行安装

如果你偏好命令行方式，可执行：

```bash
claude plugin marketplace add ZTE-AICloud/Co-OmniSpec
claude plugin install omni@CoMind-plugins
```

---

## 验证安装

1. **在 Claude Code 中打开目标项目**。
2. **打开 AI 对话**，确认可以触发 OmniSpec 命令，例如：
   - `/constitution`
   - `/specify`
3. **确认市场/插件状态：**
   - 运行 `/plugin marketplace list`（或 `/market list`）确认存在 `CoMind-plugins`；
   - 运行 `/plugin`（Discover）或 `/market`，确认可看到并使用 `omni`。

若未生效，请重新执行添加市场与安装插件命令。

---

## 首次使用：章程

章程定义项目的原则与约束，后续的规格、设计、任务与实现都应与之一致。

1. 在 Claude Code 中打开 AI 对话。
2. 执行：

   ```
   /constitution
   ```

3. 在同一句或下一句中加入你希望的原则描述，例如：

   ```
   创建关注代码质量、测试标准、用户体验一致性和性能的原则，
   并说明这些原则应如何指导技术决策。
   ```

4. Agent 会创建或更新 `.specify/memory/constitution.md`。之后可随时编辑该文件以细化原则。

---

## 首次使用：规格编写

规格编写将简短的功能描述转化为完整规范（分支、上下文、spec 与需求检查清单）。

1. **创建特性分支与规范**，执行：

   ```
   /specify
   ```

2. **在同一句或下一句提供功能描述**。侧重“做什么”和“为什么”，暂不写技术栈。示例：

   ```
   做一个简单的相册应用：用户可以创建相册、上传照片、以网格形式浏览。
   相册是扁平的，不嵌套。第一版不需要登录，单用户即可。
   ```

3. Agent 将：

   - 创建特性分支（如 `001-photo-albums`）；
   - 在 `changes/` 下创建目录（如 `changes/001-photo-albums/`）；
   - 生成 `spec.md`、`context.md` 以及 `checklists/` 下的需求检查清单。

4. **检查**生成的 `changes/<分支名>/spec.md` 与 `checklists/requirements.md`。若有不清楚之处，可接着运行 `/clarify`。

---

## 下一步

- **澄清** — 运行 `/clarify` 消除规范中的歧义（建议在设计前执行）。
- **设计** — 运行 `/design` 并描述技术栈与架构，生成 `design.md`、数据模型、契约等。
- **任务** — 运行 `/tasks` 根据设计生成 `tasks.md`。
- **分析** — 运行 `/analyze` 检查 spec、design、tasks 之间的一致性。
- **实施** — 运行 `/implement` 按顺序执行任务。
- **归档** — 运行 `/archive` 对已完成特性进行归档/回流。

完整工作流与所有命令说明见 [用户指南](USER_GUIDE_zh-CN.md)。


