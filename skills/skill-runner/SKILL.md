---
name: skill-runner
description: 执行指定skill并自动记录执行维测数据到json文件
argument-hint: "[skill名称] [skill参数]"
---
# Skill执行器（带维测数据记录）

用于统一记录命令执行过程，并将结构化日志追加写入 `FEATURE_DIR/omni-execution-log.json`。

## 输入

- $ARGUMENTS[0]: `传入的skill`(必填)

## 输出格式
```json
{
  "branch": "",
  "sdd_step": "",
  "start_time": "",
  "end_time": "",
  "execute_duration": "",
  "execute_result": "",
  "input": "",
  "output": ""
}
```

## 执行步骤

### Step 1: `传入的skill` 执行前信息记录

1. 记录 `start_time`
    - 判断当前操作系统，windows还是linux系统;
    - 针对不同操作系统运行脚本获取配置
        windows: `Get-Date -Format "yyyy-MM-dd HH:mm:ss"`
        linux: `date +"%Y-%m-%d %H:%M:%S"`
    - 将获取的时间记录到 `start_time`
2. 将当前命令名称记录到 `sdd_step`

### Step 2: 执行 `传入的skill`

根据 `$ARGUMENTS` 调用对应 Skill

### Step 3: `传入的skill` 执行结果记录

1. 记录 `end_time`
    - 判断当前操作系统，windows还是linux系统;
    - 针对不同操作系统运行脚本获取配置
        windows: `Get-Date -Format "yyyy-MM-dd HH:mm:ss"`
        linux: `date +"%Y-%m-%d %H:%M:%S"`
    - 将获取的时间记录到 `end_time`
2. 计算执行时长，采用 `10 min 20 sec` 格式，并写入 `execute_duration`
3. 捕获上面执行skill的输入，记录到 `input`
4. 捕获上面skill执行的关键结果信息，记录到 `output`
5. 捕获执行结果，记录到 `execute_result`
6. 根据 `FEATURE_DIR` 解析当前任务分支名称，并写入 `branch`


### Step 4: 保存信息到指定文件

按“输出格式”将记录追加到 `FEATURE_DIR/omni-execution-log.json`
  - 若文件不存在，则先初始化为 JSON 数组，再追加日志条目
  - 仅允许追加，不得覆盖历史记录

