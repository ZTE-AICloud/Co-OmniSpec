# Step 02: 顺序执行已解析的 Skill

## 职责

按照 `state/resolved-skills.json` 中的顺序，逐一调用各度量 skill，收集执行结果。

## 输入

- `state/resolved-skills.json`：Step 1 产物，包含待执行 skill 列表
- `project_path`：待分析项目的根目录（绝对路径）

## 输出

- 各 skill 的输出文件（路径由 `output_path_hint` 指定，如 `output/srp/summary.json`）

## 执行流程

1. 读取 `state/resolved-skills.json`，获取 `resolved` 列表
2. 若列表为空，跳过本步骤，进入 Step 3
3. **顺序**执行每个 skill（带缓存探针，不并发，原因见下文）：

   **对 `resolved` 列表中的每个 skill，执行以下流程：**

   #### a. 缓存探针（断点续跑检查）

   **在调用 skill 之前**，先检查 `output_path_hint` 文件是否已存在且有效。

   **缓存命中条件**（全部满足）：
   1. `output_path_hint` 对应文件存在
   2. 文件可解析为合法 JSON
   3. `execution_ctx` 字段存在
   4. `execution_ctx.execute_status == "success"`
   5. `core_metrics.total_score` 存在且数值在 0-100 范围内

   **判断逻辑**：

   ```
   output_file = skill.output_path_hint

   IF output_file 不存在:
     → [CACHE MISS] skill {skill_id}: 输出文件不存在，正常执行
     → 执行步骤 b

   ELSE 尝试解析 JSON:
     IF 解析失败:
       → [CACHE INVALID] skill {skill_id}: 输出文件 JSON 格式损坏，重新执行
       → 执行步骤 b
     ELSE IF execution_ctx 字段缺失:
       → [CACHE INVALID] skill {skill_id}: execution_ctx 字段缺失，重新执行
       → 执行步骤 b
     ELSE IF execution_ctx.execute_status != "success":
       → [CACHE INVALID] skill {skill_id}: 上次执行状态为 {status}（非 success），重新执行
       → 执行步骤 b
     ELSE IF core_metrics.total_score 缺失 OR 不在 0-100 范围:
       → [CACHE INVALID] skill {skill_id}: core_metrics.total_score 无效，重新执行
       → 执行步骤 b
     ELSE:
       → [CACHE HIT] skill {skill_id}: {output_path_hint} 已存在且有效（score={N:.4f}），跳过执行
       → 跳过步骤 b，继续下一个 skill（不记入失败列表）
   ```

   > **注意**：全部 skill 均缓存命中时，步骤 3 循环走完但不调用任何 Agent tool，自然进入 Step 3（正确行为）。
   > 若需强制重新执行某 skill，删除对应 `output_path_hint` 文件后重新运行即可。

   #### b. 执行 skill（仅在 Cache Miss / Cache Invalid 时）

   - 调用对应 skill，传入 `project_path` 和 `output_path`
   - 等待 skill 完成
   - 验证 `output_path_hint` 对应文件已生成
   - 若执行失败：记录到失败列表，**继续执行**下一个 skill（容错策略）

4. 全部 skill 处理完毕后，进入 Step 3

## 调用规范

### 调用 `ai-friendly-component-srp-orchestrate`

```
调用技能 `ai-friendly-component-srp-orchestrate`
参数：
  project_path: <project_path>
  output_path: output/srp/summary.json
```

### 通用调用模式

对 `resolved` 列表中的每个 skill，传入：
- `project_path`：待分析项目路径
- `output_path`：skill 的 `output_path_hint` 字段值

## 容错策略

- **��个 skill 失败**：记录 skill_id 到失败列表，继续执行下一个 skill
- **所有 skill 均失败**：标记整体失败，仍进入 Step 3（聚合脚本将生成失败报告）
- **失败判定**：skill 执行返回错误，或 `output_path_hint` 对应文件在执行后不存在

## 顺序执行的原因

各度量 skill 内部可能已使用 subagent 并发，叠加并发会导致资源不可控；顺序执行便于错误定位。

## 验证检查点

- [ ] `resolved` 列表中每个 skill 执行完毕后，`output_path_hint` 对应文件存在
- [ ] 某 skill 失败时，其余 skill 正常继续执行（不中断）
- [ ] 每个 skill 输出文件符合 `aia_metric_fact` 格式（有 `identity_info`、`execution_ctx`、`core_metrics` 字段）
