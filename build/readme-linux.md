# OmniSpec 构建脚本使用指南 (Linux / macOS)

本指南适用于 Linux 和 macOS 平台，介绍如何使用 OmniSpec 的构建和安装脚本。

## ⚡ 快速概览

### 最常用命令

#### 🚀 发布新版本（推荐）

```bash
./build/build-release.sh --version v1.0.0
```

#### 🔨 构建单个 agent

```bash
./build/build.sh claude --version v1.0.0
```

#### 📦 直接安装到项目

```bash
./build/install.sh claude /path/to/project
```

### 使用场景速查表

| 场景 | 命令 |
|------|------|
| 发布新版本（所有 agent） | `./build/build-release.sh --version v1.0.0` |
| 测试单个 agent | `./build/build.sh claude --version v1.0.0` |
| 开发环境安装 | `./build/install.sh claude /path/to/project` |

### 脚本层级关系

```text
build-release.sh  (批量构建) 
    ↓ 调用
build.sh          (单个构建)
    ↓ 调用
install.sh        (基础安装)
```

---

## 📋 目录结构

```
build/
├── install.sh          # Linux 安装脚本（Level 1）
├── build.sh            # Linux 构建脚本（Level 2）
├── build-release.sh    # Linux 发布构建脚本（Level 3）
└── readme-linux.md     # 本文档
```

## 🏗️ 脚本架构

### 三级调用层级

```text
Level 3: build-release.sh  (批量发布构建)
    ↓ 调用
Level 2: build.sh           (单个 agent 构建)
    ↓ 调用
Level 1: install.sh          (基础安装)
```

### 脚本职责说明

#### Level 1: 安装脚本（install.sh）

**职责：** 将 agent 和 src/specify 目录复制到目标代码工程路径

**功能：**
- 检查源目录（agent 和 src/specify）是否存在
- 将 agent 目录复制到目标工程的指定目录（增量覆盖）
- 将 src/specify 目录复制到目标工程的 `.specify` 目录（完整拷贝）
- 自动设置脚本可执行权限
- 更新 agent 配置文件

**使用场景：** 直接安装到现有项目

**示例：**
```bash
./build/install.sh claude /path/to/project
```

---

#### Level 2: 构建脚本（build.sh）

**职责：** 创建带时间戳的打包目录，运行安装脚本，并压缩为 zip 文件

**功能：**
- 创建带时间戳的构建目录（格式：`omnispec-version-agent-timestamp`）
- 调用安装脚本（install.sh）
- 复制版本发布说明文件到 .specify 目录
- 压缩为 zip 文件
- 可选：构建完成后删除构建目录

**使用场景：** 构建单个 agent 的发布包

**示例：**
```bash
# 构建 claude agent
./build/build.sh claude --version v1.0.0 --output /tmp/builds

# 构建并删除构建目录
./build/build.sh cursor --version v2.0.0 --clean
```

---

#### Level 3: 发布构建脚本（build-release.sh）

**职责：** 为所有 agent（flow, claude, cursor）批量执行构建

**功能：**
- 自动为所有 agent 执行构建
- 按版本号组织输出目录结构
- 可选：使用 --clean-output 清理输出目录（默认不清理）
- 可选：构建完成后删除构建目录
- 输出构建统计信息

**使用场景：** 发布新版本，需要构建所有 agent

**示例：**
```bash
# 构建所有 agent，版本 v1.0.0（默认不清理输出目录）
./build/build-release.sh --version v1.0.0

# 指定输出路径，清理输出目录
./build/build-release.sh --version v2.0.0 --output /tmp/release --clean-output

# 构建并删除构建目录
./build/build-release.sh --version v1.5.0 --clean
```

## 🎯 使用场景指南

### 场景 1: 直接安装到项目

**适用：** 开发环境，需要快速安装到现有项目

```bash
./build/install.sh claude /path/to/my-project
```

### 场景 2: 构建单个 agent 发布包

**适用：** 需要为特定 agent 创建发布包

```bash
./build/build.sh flow --version v1.0.0 --output ./release
```

### 场景 3: 批量构建所有 agent

**适用：** 发布新版本，需要构建所有 agent 的发布包

```bash
./build/build-release.sh --version v1.0.0
```

**输出目录结构：**
```
release/
└── OmniSpecV1.0.0/
    ├── flow/
    │   └── omnispec-v1.0.0-flow-20251206123456.zip
    ├── claude/
    │   └── omnispec-v1.0.0-claude-20251206123457.zip
    └── cursor/
        └── omnispec-v1.0.0-cursor-20251206123458.zip
```

## 📝 参数说明

### install.sh

| 参数 | 说明 | 必需 | 示例 |
|------|------|------|------|
| `<agent名称>` | Agent 目录名 | ✅ | `claude`, `cursor`, `flow` |
| `<目标路径>` | 目标代码工程路径 | ✅ | `/path/to/project` |

### build.sh

| 参数 | 说明 | 必需 | 默认值 | 示例 |
|------|------|------|--------|------|
| `[agent名称]` | Agent 名称（位置参数） | ❌ | `claude` | `claude`, `cursor`, `flow` |
| `-h, --help` | 显示帮助信息 | ❌ | - | - |
| `-v, --version` | 版本号（vX.Y.Z） | ❌ | `v1.0.0` | `v1.0.0`, `v2.1.3` |
| `-o, --output` | 输出路径 | ❌ | 脚本目录 | `/tmp/builds` |
| `--clean` | 构建后删除构建目录 | ❌ | 否 | - |

### build-release.sh

| 参数 | 说明 | 必需 | 默认值 | 示例 |
|------|------|------|--------|------|
| `-h, --help` | 显示帮助信息 | ❌ | - | - |
| `-v, --version` | 版本号（vX.Y.Z） | ❌ | `v1.0.0` | `v1.0.0`, `v2.1.3` |
| `-o, --output` | 基础输出路径 | ❌ | `release` | `/tmp/release` |
| `--clean` | 构建后删除构建目录 | ❌ | 否 | - |
| `--clean-output` | 清理输出目录 | ❌ | 不清理 | - |

## 🔧 技术细节

### Linux 脚本特性

- **安装脚本：** `install.sh` → 使用 `rsync` 或 `cp` 复制
- **构建脚本：** `build.sh` → 调用 `install.sh`
- **发布脚本：** `build-release.sh` → 调用 `build.sh`

### 依赖要求

- Bash shell
- `rsync` 或 `cp` 命令（用于文件复制）
- `zip` 命令（用于压缩）

## 📦 输出文件说明

### 构建产物

- **构建目录：** `omnispec-version-agent-timestamp/`
  - 包含 `.agent` 目录（如 `.claude`）
  - 包含 `.specify` 目录
  - 包含 `版本发布说明.md` 文件

- **ZIP 文件：** `omnispec-version-agent-timestamp.zip`
  - 可直接解压到目标项目
  - 解压后得到 `.agent` 和 `.specify` 目录

### 版本信息文件

构建目录中的 `.specify/版本发布说明.md` 包含：
- 完整的版本发布说明
- 版本号、发布日期、构建时间
- Agent 支持信息
- 主要变化和新功能
- 技术实现说明

## 🚀 快速开始

### 1. 构建单个 agent（推荐用于测试）

```bash
# 基本用法
./build/build.sh claude --version v1.0.0

# 指定输出路径
./build/build.sh claude --version v1.0.0 --output /tmp/builds

# 构建后删除构建目录
./build/build.sh claude --version v1.0.0 --clean
```

### 2. 批量构建所有 agent（推荐用于发布）

```bash
# 基本用法（默认不清理输出目录）
./build/build-release.sh --version v1.0.0

# 清理输出目录
./build/build-release.sh --version v1.0.0 --clean-output

# 指定输出路径并清理输出目录
./build/build-release.sh --version v1.0.0 --output /tmp/release --clean-output

# 构建后删除构建目录
./build/build-release.sh --version v1.0.0 --clean
```

### 3. 直接安装到项目（推荐用于开发）

```bash
# 指定 agent 和目标路径
./build/install.sh claude /path/to/project
./build/install.sh cursor /path/to/project
./build/install.sh flow /path/to/project
```

## ❓ 常见问题

### Q: 如何查看脚本的详细帮助信息？

A: 运行脚本时添加 `-h` 或 `--help` 参数：
```bash
./build/build.sh --help
```

### Q: 版本号格式要求是什么？

A: 必须为三段式格式：`vX.Y.Z`，例如：`v1.0.0`, `v2.1.3`

### Q: 构建目录和 ZIP 文件的命名规则是什么？

A: 格式为：`omnispec-version-agent-timestamp`
- `version`: 版本号（如 `v1.0.0`）
- `agent`: agent 名称（如 `claude`）
- `timestamp`: 时间戳（如 `20251206123456`）

### Q: 如何清理构建目录？

A: 使用 `--clean` 参数：
```bash
./build/build.sh claude --version v1.0.0 --clean
./build/build-release.sh --version v1.0.0 --clean
```

### Q: 脚本没有执行权限怎么办？

A: 使用 `chmod +x` 添加执行权限：
```bash
chmod +x build/*.sh
```

## 📚 更多信息

- 各脚本的详细使用说明可通过 `-h` 或 `--help` 参数查看
- 脚本支持交互式确认，确保操作安全
- 所有脚本都会输出详细的执行日志，便于排查问题
- 返回 [主文档](readme.md) 查看跨平台信息

