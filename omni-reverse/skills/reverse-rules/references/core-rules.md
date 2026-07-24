# 规则反构核心规则

## 分批处理规则

### 触发条件

- 规则数量 > 10 时，建议按优先级分阶段执行
- 单阶段内规则可并行生成时，每批建议不超过 5 个

### 阶段划分

- **阶段1（基础规则 P0）**：00-architecture、08-style-patterns，串行
- **阶段2（核心功能 P1）**：03-data-access、05-logging、07-config，可并行
- **阶段3（扩展 P2）**：01-routing-dispatch、02-state-management、04-communication，可并行
- **阶段4（运维 P3）**：09-testing、06-monitoring、10-deployment，可并行
- **阶段5（特化 P4）**：11～15 系列，按需、可并行

### 状态管理

- 使用统一状态文件：`{REPO_ROOT}/.cache/reverse/rules/.cache-status.json`
- 每阶段完成后更新对应 `confirmed` 与 `timestamp`
- 支持从未确认阶段恢复

### 执行要求

- 必须按工作流阶段顺序执行（阶段1 → 2 → 3 → 4）；同工作流阶段内，规则按优先级 P0→P1→P2→P3→P4 串行生成
- 每批处理完成后更新状态
- 支持断点续跑

## Token 管理规则

### 监控级别

- 正常：Token 使用率 < 80%
- 警告：Token 使用率 >= 80%

### 防护机制

1. 按阶段/批次处理，避免单次加载全部规则提示
2. 单次读取特征报告或单规则提示，避免整目录读入
3. 阶段开始前清理上一阶段上下文

### 上下文清理

- 阶段开始：清空上一阶段上下文
- 批次开始前：清空上一批次上下文

## 执行约束

### 禁止行为

1. 跳过未处理的规则批次
2. 在未生成 01-features 时执行规则映射
3. 在未确认规则映射时执行规则生成
4. 忽略状态文件更新

### 必须行为

1. 按阶段顺序执行
2. 及时更新 .cache-status.json
3. 执行上下文清理
4. 在执行每阶段前验证阶段文件存在并直接访问预定路径

## 阶段文件定位规则

### 文件路径约定

- 阶段文件统一位于：`本 Skill 内 references/stages/`
- 命名格式：`NN-stage-name.md`（NN 为两位数字）

### 阶段映射

1. 阶段1：特征检测 → `stages/01-features-scan.md`
2. 阶段2：规则映射与分批 → `stages/02-rule-mapping-and-batching.md`
3. 阶段3：规则文档生成 → `stages/03-rule-document-generation.md`
4. 阶段4：用户规则注入 → `stages/04-user-rules-injection.md`
