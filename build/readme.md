# OmniSpec 构建脚本使用指南

本目录包含 OmniSpec 的构建和安装脚本，采用分级调用架构，支持不同场景的使用需求。

## 📖 平台文档

根据您的操作系统，选择对应的详细文档：

- **[Linux / macOS 使用指南](readme-linux.md)** 🐧 - 包含完整的使用说明、参数说明、示例和常见问题
- **[Windows 使用指南](readme-windows.md)** 🪟 - 包含完整的使用说明、参数说明、示例和常见问题

---

## 🏗️ 脚本架构概览

### 三级调用层级

```text
Level 3: build-release.sh/ps1  (批量发布构建)
    ↓ 调用
Level 2: build.sh/ps1           (单个 agent 构建)
    ↓ 调用
Level 1: install.sh/ps1         (基础安装)
```

### 跨平台脚本对应关系

| 层级 | Linux / macOS | Windows | 功能说明 |
|------|--------------|---------|---------|
| Level 1 | `install.sh` | `install.ps1` | 将 agent 和 specify 目录复制到目标项目 |
| Level 2 | `build.sh` | `build.ps1` | 创建打包目录，运行安装脚本，压缩为 zip |
| Level 3 | `build-release.sh` | `build-release.ps1` | 为所有 agent 批量执行构建 |

---

## 📋 目录结构

```
build/
├── install.sh          # Linux 安装脚本（Level 1）
├── install.ps1         # Windows 安装脚本（Level 1）
├── build.sh            # Linux 构建脚本（Level 2）
├── build.ps1           # Windows 构建脚本（Level 2）
├── build-release.sh    # Linux 发布构建脚本（Level 3）
├── build-release.ps1  # Windows 发布构建脚本（Level 3）
├── readme.md           # 本文档（导航索引）
├── readme-linux.md     # Linux 详细文档
└── readme-windows.md   # Windows 详细文档
```

---

## 📚 更多信息

- 各脚本的详细使用说明可通过 `-h` 或 `--help` 参数查看
- 脚本支持交互式确认，确保操作安全
- 所有脚本都会输出详细的执行日志，便于排查问题
