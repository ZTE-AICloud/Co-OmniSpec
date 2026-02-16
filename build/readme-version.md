# 版本号管理

## 概述

为了消除多脚本版本号读取逻辑不一致的风险，版本号相关函数统一提取到 `version-utils.sh` 工具脚本中。

## 优先级规则

所有构建脚本遵循统一的版本号获取优先级：

```
1️⃣ 用户输入（命令行 --version 参数）
   ↓ 如果未指定
2️⃣ build/version 文件
   ↓ 如果文件不存在或读取失败
3️⃣ 默认值（v2.0.0）
```

## 核心函数

### `validate_version(version)`
验证版本号格式是否符合三段式规范（vX.Y.Z）

```bash
validate_version "v2.0.0"  # 返回 0 (成功)
validate_version "v1.2"    # 返回 1 (失败)
```

### `read_version_from_file([version_file])`
从 version 文件读取版本号，失败时返回默认值

```bash
version=$(read_version_from_file)
version=$(read_version_from_file "$custom_path/version")
```

### `get_version([specified_version], [version_file])`
获取版本号，自动处理优先级

```bash
version=$(get_version)                           # 从文件读取
version=$(get_version "$user_specified_version") # 优先使用参数
version=$(get_version "" "$custom_version_file") # 使用自定义文件
```

## 使用方式

### 在脚本中使用

```bash
#!/bin/bash

# 获取脚本所在目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# 加载版本号工具函数
source "$SCRIPT_DIR/version-utils.sh"

# 获取版本号（自动处理优先级）
version=$(get_version "$user_input_version")

# 验证版本号
if ! validate_version "$version"; then
    echo "版本号格式错误"
    exit 1
fi
```

### 应用的脚本

| 脚本 | 版本号读取方式 |
|------|--------------|
| `build.sh` | `get_version()` |
| `build-release.sh` | `get_version()` |
| `build-art.sh` | `get_version()` |

## 使用示例

```bash
# 1. 使用文件中的版本号（v2.0.0）
./build/build.sh

# 2. 用户指定版本号（优先级最高）
./build/build.sh --version v3.0.0

# 3. 修改默认版本号（修改一处，影响所有脚本）
echo "version=v3.0.0" > build/version
```

## 版本号格式

**格式：** `vX.Y.Z`

- `X` - 主版本号：不兼容的 API 修改
- `Y` - 次版本号：向后兼容的功能新增
- `Z` - 修订号：向后兼容的问题修正

**有效示例：**
- ✅ `v1.0.0`
- ✅ `v2.3.5`
- ✅ `v10.20.30`

**无效示例：**
- ❌ `v1.0` (缺少修订号)
- ❌ `1.0.0` (缺少 v 前缀)
- ❌ `v1.2.3.4` (超过三段)

## 测试验证

```bash
# 快速测试
cd /media/vdc/sdd/omnispec2/OmniSpec2
source build/version-utils.sh

# 场景1：用户输入优先
version=$(get_version "v3.0.0")
echo "用户指定: $version"  # 输出: v3.0.0

# 场景2：从文件读取
version=$(get_version "")
echo "从文件读取: $version"  # 输出: v2.0.0

# 场景3：文件不存在使用默认值
version=$(get_version "" "/nonexistent/version")
echo "默认值: $version"  # 输出: v2.0.0
```

## 维护指南

### 添加新的构建脚本

1. 在脚本开头加载工具函数：
```bash
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/version-utils.sh"
```

2. 使用 `get_version()` 获取版本号
3. 使用 `validate_version()` 验证版本号格式

### 修改版本号逻辑

⚠️ **重要：** 所有版本号相关逻辑都应该在 `version-utils.sh` 中统一修改，而不是在各个脚本中单独修改。

## 重构历史

**日期：** 2026-02-09

**问题：**
- 版本号读取逻辑在 3 个脚本中重复实现
- 各脚本实现逻辑略有不同，存在维护风险
- 默认版本号不一致（v1.0.0 vs v2.0.0）

**解决方案：**
- 创建统一的 `version-utils.sh` 工具脚本
- 提取并统一版本号读取和验证函数
- 所有脚本通过 `source` 加载统一工具
- 统一默认版本号为 `v2.0.0`

**影响的文件：**
- ✅ `build/version-utils.sh` (新建)
- ✅ `build/build.sh` (修改)
- ✅ `build/build-release.sh` (修改)
- ✅ `build/build-art.sh` (修改)

## 相关文件

- `build/version-utils.sh` - 版本号工具函数
- `build/version` - 版本配置文件
- `build/readme-linux.md` - Linux 构建说明
- `build/readme-windows.md` - Windows 构建说明
