---
description: 逻辑架构要素反构的数据与路径约定
parent: reverse
target: logic_architecture
---

## 路径契约（固定）

| 用途 | 路径 |
|------|------|
| 架构识别 JSON（**供各要素读取**） | `{REPO_ROOT}/omni-doc/specs/logic_architecture/architecture.json` |
| 本要素阶段状态 | `{REPO_ROOT}/.cache/reverse/logic_architecture/.cache-status.json` |

## 状态文件示例

```json
{
  "architecture_identification": {
    "confirmed": true,
    "progress": "completed",
    "timestamp": "2024-01-01T00:00:00Z"
  }
}
```

## 与下游的关系

- **接口反构**（`reverse-interfaces`）在阶段1仅**校验/读取** `omni-doc/specs/logic_architecture/architecture.json`，不生成该文件。
- **`--target all`**：编排层须**先**完成本要素，再进入 `interfaces` 等阶段，以保证下游可读。
