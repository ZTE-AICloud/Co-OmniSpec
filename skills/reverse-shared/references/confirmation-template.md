# 用户确认机制（统一模板）

## 🔴 使用说明

**AI Agent 在执行确认步骤时，必须严格按照本模板执行，无需在每个阶段文档中重复说明判断逻辑。**

## 阶段结束确认模板

### 执行步骤

1. **展示结果摘要**（阶段特定内容）
2. **调用统一确认机制**（按以下流程执行）：
   - 调用脚本获取交互模式状态：
     - Linux: `bash {REPO_ROOT}/scripts/bash/check-interactive-mode.sh "$ARGUMENTS"`
     - Windows: `pwsh {REPO_ROOT}/scripts/powershell/check-interactive-mode.ps1 "$ARGUMENTS"`
   - 解析 JSON 输出，获取 `interactive` 字段
   - **如果 `interactive: true`**：
     - 询问用户："[阶段名称]已完成，是否确认结果？[Y/n]"
     - 等待用户响应
     - 如果用户确认（Y/yes/回车），执行步骤3
     - 如果用户拒绝（n/no），允许查看详情或重新生成，不执行步骤3
   - **如果 `interactive: false`**：
     - 自动确认，直接执行步骤3
3. **更新缓存状态**：
   - 读取状态文件 `{REPO_ROOT}/.cache/reverse/{target}/.cache-status.json`
   - 更新对应的阶段状态字段，设置 `confirmed: true` 和当前时间戳
   - 使用 `write` 工具保存更新后的状态文件
   - 明确说明阶段已完成，清空上下文
   - 自动继续执行下一阶段（或结束流程）

### 在阶段文档中的使用方式

```markdown
### 5. [ ] 展示结果并向用户确认
- 🔴 强制验证缓存状态：AI Agent直接读取状态文件，验证 `{stage_name}.confirmed == false`
- 读取结果文件 `{REPO_ROOT}/.cache/reverse/{target}/{result_file}`
- 总结并展示结果摘要：
  - [阶段特定的展示内容]
- **🔴 执行统一确认机制**：按照 `本 Skill（reverse-shared）内 references/confirmation-template.md` 中的"阶段结束确认模板"执行
- 🔴 状态双重检查：用户响应后（或自动确认后）AI Agent再次读取状态文件，验证更新成功

### 6. [ ] 处理用户确认，更新缓存状态
- **🔴 执行统一确认机制**：按照 `本 Skill（reverse-shared）内 references/confirmation-template.md` 中的"阶段结束确认模板"的步骤3执行
```

## 过程中确认模板

### 类型1：配置选择确认

#### 执行步骤

1. **准备配置选项**（阶段特定内容）
2. **调用统一确认机制**（按以下流程执行）：
   - 调用脚本获取交互模式状态：
     - Linux: `bash {REPO_ROOT}/scripts/bash/check-interactive-mode.sh "$ARGUMENTS"`
     - Windows: `pwsh {REPO_ROOT}/scripts/powershell/check-interactive-mode.ps1 "$ARGUMENTS"`
   - 解析 JSON 输出，获取 `interactive` 字段
   - **如果 `interactive: true`**：
     - 展示配置选项
     - 等待用户选择
     - 根据用户选择执行相应操作
   - **如果 `interactive: false`**：
     - 使用默认配置
     - 自动执行相应操作

#### 在阶段文档中的使用方式

```markdown
### 5. [ ] 用户确认扫描配置 - 接口类型选择
- 读取接口类型选择模板
- **🔴 执行统一确认机制**：按照 `本 Skill（reverse-shared）内 references/confirmation-template.md` 中的"过程中确认模板 - 类型1：配置选择确认"执行
  - 默认配置：全选所有接口类型
  - 根据选择生成 `{REPO_ROOT}/.cache/reverse/interfaces/interface-types.json` 文件
```

### 类型2：是否继续处理确认

#### 执行步骤

1. **检查处理状态**（阶段特定内容）
2. **判断是否需要确认**（根据条件，如剩余批次数 > 3）
3. **如果需要确认，调用统一确认机制**（按以下流程执行）：
   - 调用脚本获取交互模式状态：
     - Linux: `bash {REPO_ROOT}/scripts/bash/check-interactive-mode.sh "$ARGUMENTS"`
     - Windows: `pwsh {REPO_ROOT}/scripts/powershell/check-interactive-mode.ps1 "$ARGUMENTS"`
   - 解析 JSON 输出，获取 `interactive` 字段
   - **如果 `interactive: true`**：
     - 询问用户："检测到还有 {remaining_count} 个{单位}未处理，是否继续处理？[Y/n]"
     - 等待用户响应
     - 如果用户确认（Y/yes/回车），继续处理
     - 如果用户拒绝（n/no），暂停处理，等待进一步指令
   - **如果 `interactive: false`**：
     - 自动继续处理所有剩余项

#### 在阶段文档中的使用方式

```markdown
### 4.7. [ ] 检查是否还有未处理的批次
- 调用脚本检查是否还有待处理批次
- 如果还有待处理批次且满足确认条件（如剩余批次数 > 3）：
  - **🔴 执行统一确认机制**：按照 `本 Skill（reverse-shared）内 references/confirmation-template.md` 中的"过程中确认模板 - 类型2：是否继续处理确认"执行
- 如果所有批次已完成：跳出循环
```

## 技术细节

### 脚本调用

- **Linux/macOS**：`bash {REPO_ROOT}/scripts/bash/check-interactive-mode.sh "$ARGUMENTS"`
- **Windows**：`pwsh {REPO_ROOT}/scripts/powershell/check-interactive-mode.ps1 "$ARGUMENTS"`

### JSON 输出格式

```json
{
  "interactive": true/false,
  "auto_confirm": true/false,
  "mode": "interactive" | "auto"
}
```

### 参数支持

1. **`--interactive yes`**：明确启用交互模式
2. **`--interactive no`**：明确禁用交互模式
3. **`--interactive`**：启用交互模式（向后兼容）
4. **`--non-interactive`**：禁用交互模式
5. **`--yes`**：禁用交互模式

### 参数优先级

1. `--non-interactive` 或 `--yes`：最高优先级
2. `--interactive no`：明确禁用
3. `--interactive yes` 或 `--interactive`：启用
4. 默认：非交互模式（全自动）

## 注意事项

1. **脚本调用失败**：如果脚本调用失败，默认使用非交互模式
2. **跨平台支持**：确保 bash 和 PowerShell 版本行为一致
3. **状态更新**：阶段结束确认必须更新缓存状态，过程中确认根据具体情况决定
4. **条件确认**：某些过程中确认有条件触发，在非交互模式下应自动满足条件继续执行
