# Co-OmniSpec 入门指南

本文介绍如何安装 Co-OmniSpec，并在 Cursor 中完成第一次规范驱动开发流程。

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
| **Cursor** | [cursor.sh](https://cursor.sh/) 或支持斜杠命令的兼容 IDE。 |
| **Git** | 用于特性分支与 `changes/` 目录。 |
| **Bash**（Linux/macOS）或 **PowerShell**（Windows） | 用于运行安装与项目脚本。 |

---

## 安装

### 方式一：从克隆的仓库安装

1. **克隆 Co-OmniSpec**（或下载并解压仓库）：

   ```bash
   git clone <你的-omnispec2-仓库地址> omnispec2
   cd omnispec2
   ```

2. **在 `build/` 目录下执行安装脚本**。

   **Linux / macOS：**

   ```bash
   ./build/install.sh cursor /path/to/your/target/project
   ```

   **Windows（PowerShell）：**

   ```powershell
   .\build\install.ps1 cursor C:\path\to\your\target\project
   ```

   将 `/path/to/your/target/project` 替换为**你要用 Cursor 开发的目标项目的绝对路径**。

3. **结果：** 安装脚本会复制：

   - Co-OmniSpec 的 `src/agent/`（命令与技能）到目标项目的 `.cursor/`；
   - Co-OmniSpec 的 `src/specify/` 到目标项目的 `.specify/`。

   之后在 Cursor 中打开目标项目即可使用 OmniSpec 命令。

### 方式二：从发布包安装

若你有预构建的 zip（例如来自 CI 或发布页）：

1. 将 zip 解压到某一目录（如 `omnispec2-build`）。
2. 在该目录下执行与上面相同的安装命令，并指向目标项目：

   ```bash
   ./install.sh cursor /path/to/your/project
   ```

   （Windows 下使用 `install.ps1`，参数相同。）

---

## 验证安装

1. **在 Cursor 中打开目标项目**（即传入 `install.sh` / `install.ps1` 的那个路径）。
2. **打开 AI 对话**，确认可以触发 OmniSpec 命令，例如：
   - `/omni.constitution`
   - `/omni.specify`
3. **确认项目中存在以下路径：**
   - `.cursor/commands/` — 包含 `omni.*.md` 命令文件；
   - `.specify/` — 包含 `memory/`、`metamodel/`、`scripts/`、`templates/`。

若缺失，请重新执行安装脚本并确认目标路径正确。

---

## 首次使用：章程

章程定义项目的原则与约束，后续的规格、设计、任务与实现都应与之一致。

1. 在 Cursor 中打开 AI 对话。
2. 执行：

   ```
   /omni.constitution
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
   /omni.specify
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

4. **检查**生成的 `changes/<分支名>/spec.md` 与 `checklists/requirements.md`。若有不清楚之处，可接着运行 `/omni.clarify`。

---

## 下一步

- **澄清** — 运行 `/omni.clarify` 消除规范中的歧义（建议在设计前执行）。
- **设计** — 运行 `/omni.design` 并描述技术栈与架构，生成 `design.md`、数据模型、契约等。
- **任务** — 运行 `/omni.tasks` 根据设计生成 `tasks.md`。
- **分析** — 运行 `/omni.analyze` 检查 spec、design、tasks 之间的一致性。
- **实施** — 运行 `/omni.implement` 按顺序执行任务。

完整工作流与所有命令说明见 [用户指南](USER_GUIDE_zh-CN.md)。

构建与发布脚本（打 zip 包、版本号等）见 [构建说明](../build/readme.md)。
