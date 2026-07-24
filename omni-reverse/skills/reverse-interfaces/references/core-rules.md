# 接口反构核心规则

## 分批处理规则

### 触发条件
- 文件数量 > 30时，必须执行分批处理
- 接口数量 > 15时，必须执行分批处理

### 批次大小
- 文件处理：每批10个文件
- 接口处理：每批5个接口

### 状态管理
- 使用统一的状态文件：`{REPO_ROOT}/.cache/reverse/interfaces/.cache-status.json`
- 状态文件格式（优化后）：
```json
{
  "version": "1.0",
  "stage": "interface_scanning",
  "total_items": 384,
  "batch_size": 10,
  "total_batches": 39,
  "processed_batches": 7,
  "current_batch": 7,
  "failed_batches": 0,
  "summary": {
    "total_interfaces_found": 45,
    "total_empty_batches": 1,
    "average_processing_time": 12
  },
  "recent_batches": [
    // 只保留最近5个批次详情
  ],
  "failed_batch_details": [
    // 只保留最近5个失败批次详情
  ]
}
```

### 执行要求
- 必须按顺序处理所有批次
- 每批处理完成后必须更新状态文件
- 支持从失败点恢复继续处理
- 每批处理完成后必须检查是否还有未处理的批次
- 如果还有未处理的批次，必须继续处理，绝对不能跳过
- 状态文件大小必须控制在合理范围内，防止Token超限

## Token管理规则

### 监控级别
- 正常状态：Token使用率 < 80%
- 警告状态：Token使用率 >= 80%

### 防护机制
1. 分批处理作为主要防护机制
2. 限制单次读取文件大小为500行
3. 自动上下文清理
4. 使用缓存避免重复处理

### 上下文清理
- 阶段开始时：清空上一阶段所有上下文信息
- 批次开始前：清空上一批次上下文信息
- 接口处理前：清空上一接口上下文信息

### 响应机制
- 正常状态（< 80%）：保持正常处理流程
- 警告状态（>= 80%）：减少非必要信息输出，压缩中间结果

## 执行约束

### 禁止行为
1. 跳过未处理的批次
2. 读取不必要的文件
3. 生成超过限制的输出内容
4. 忽略状态文件更新
5. 在未验证阶段文件存在的情况下执行阶段

### 必须行为
1. 按顺序处理所有批次
2. 及时更新状态文件
3. 执行上下文清理
4. 遵守Token使用限制
5. 在执行每个阶段前验证阶段文件存在
6. 直接访问预定的阶段文件路径，不得通过搜索查找

## 阶段文件定位规则

### 文件路径约定
- 阶段文件统一存储在：`本 Skill 内 references/stages/`
- 文件命名格式：`NN-stage-name.md`（NN为两位数字序号）

### 阶段映射关系
1. 阶段1：逻辑架构产物校验 → `stages/01-logic-architecture-prerequisite.md`
2. 阶段2：接口模式识别与示例生成 → `stages/02-interface-scanning-and-few-shot.md`
3. 阶段3：接口清单扫描 → `stages/03-interface-list-scanning.md`
4. 阶段4：详细信息提取与文档生成 → `stages/04-detail-extraction-and-document-generation.md`

## 子 Agent 启动方式

- **阶段 3（方式 A）**：每轮最多启动 2 个 `interface-recognizer` 子 Agent，处理 1–2 个批次；轮次间执行 `/compact`（与 [SKILL.md](../SKILL.md)、阶段 3 文档一致）
- **阶段 4**：每轮最多启动 2 个 `interface-analyzer` 子 Agent；轮次间执行 `/compact`
- **禁止**：超过每轮上限并行；禁止手工合并批次 JSON（须用 `merge_interface_results.py` / `ensure_all_interface_docs_generated.py`）
- **方式 B**：不得启动任何子 Agent，仅执行 `reverse_by_call_chain` 脚本链