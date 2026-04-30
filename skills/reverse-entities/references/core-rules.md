# 实体反构核心规则

## 分批处理规则

### 触发条件
- 接口聚合文件数量 > 20时，必须执行分批处理
- 实体数量 > 30时，必须执行分批处理

### 批次大小
- 文件处理：每批10个文件
- 实体处理：每批40个实体（融合阶段）
- 价值评估：每批30个实体

### 状态管理
- 使用统一的状态文件：`{REPO_ROOT}/.cache/reverse/entities/.cache-status.json`
- 状态文件格式（优化后）：
```json
{
  "version": "1.0",
  "stage": "entity_extraction",
  "total_items": 150,
  "batch_size": 10,
  "total_batches": 15,
  "processed_batches": 5,
  "current_batch": 5,
  "failed_batches": 0,
  "summary": {
    "total_entities_found": 45,
    "total_empty_batches": 0,
    "average_processing_time": 15
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
- 使用轻量级索引文件定位批次结果，不合并大文件

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
- 实体处理前：清空上一实体上下文信息

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
6. 在未验证接口反构已完成的情况下执行实体反构

### 必须行为
1. 按顺序处理所有批次
2. 及时更新状态文件
3. 执行上下文清理
4. 遵守Token使用限制
5. 在执行每个阶段前验证阶段文件存在
6. 直接访问预定的阶段文件路径，不得通过搜索查找
7. 在执行前验证接口反构已完成阶段4（详细信息提取与文档生成）

## 阶段文件定位规则

### 文件路径约定
- 阶段文件统一存储在：`本 Skill 内 references/stages/`
- 文件命名格式：`NN-stage-name.md`（NN为两位数字序号）

### 阶段映射关系
1. 阶段1：从接口抽取实体 → `stages/01-entity-extraction-from-interfaces.md`
2. 阶段2：实体融合和去重 → `stages/02-entity-consolidation.md`
3. 阶段3：实体文档生成 → `stages/03-entity-document-generation.md`
4. 阶段4：实体关系建立 → `stages/04-entity-relationship-building.md`

## 依赖验证规则

### 前置依赖检查
- 必须检查接口反构的缓存状态文件：`{REPO_ROOT}/.cache/reverse/interfaces/.cache-status.json`
- 必须验证 `document_generation.confirmed` 字段为 `true`
- 如果接口反构未完成，必须给出明确的错误提示，要求用户先完成接口反构
- 必须验证接口聚合文件存在：`{REPO_ROOT}/.cache/reverse/interfaces/interface-aggregation/` 或类似路径

## 并发处理规则

### 实体抽取阶段
- 使用线程池并发处理多个接口文件
- 默认最大并发数：20
- 每个线程处理一个接口聚合文件

### 实体融合阶段
- 批次并发处理
- 每批40个实体，最大并发20
- 基本信息融合和类图整合分别并发处理

### 价值评估阶段
- 批次并发处理
- 每批30个实体，最大并发20

