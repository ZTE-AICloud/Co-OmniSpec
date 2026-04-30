---
name: runlog-record
description: 记录omni的skill的执行的维测数据到json文件
argument-hint: "[skill执行的开始时间start_time]"
---

# Skill执行的维测数据记录

用于统一记录skill的执行结果，并将结构化日志追加写入 `FEATURE_DIR/.runs/metrics/omni-metrics-log.json`。
请在skill执行结束后调用本技能；

## 输入

- start_time: skill执行的开始时间

## 输出格式
```json
{
  "start_time": "",
  "sdd_step": "",
  "feature_desc": "",
  "end_time": "",
  "execute_duration": "",
  "execute_result": "",
  "input": "",
  "output": ""
}
```

## 执行步骤

### Step 1: `skill` 执行结果记录

1. 记录 `end_time`
    - 判断当前操作系统，windows还是linux系统;
    - 针对不同操作系统运行脚本获取配置
        windows: `Get-Date -Format "yyyy-MM-dd HH:mm:ss"`
        linux: `date +"%Y-%m-%d %H:%M:%S"`
    - 将获取的时间记录到 `end_time`
2. 根据传入的start_time计算执行时长，采用 `10 min 20 sec` 格式，并写入 `execute_duration`
3. 捕获被监控的skill的输入，记录到 `input`
4. 捕获被监控的skill执行的输出信息，记录到 `output`
5. 捕获被监控的skill的执行结果，记录到 `execute_result`
6. 根据 `FEATURE_DIR` 解析当前任务分支名称，并写入 `feature_desc`
7. 记录被监控的skill的名字，记录到`sdd_step`字段


### Step 2: 保存信息到指定文件

按“输出格式”将记录追加到 `FEATURE_DIR/.runs/metrics/omni-metrics-log.json`
  - 若文件夹`FEATURE_DIR/.runs/metrics`不存在，则创建文件夹
  - 若文件`FEATURE_DIR/.runs/metrics/omni-metrics-log.json`不存在，则创建文件，并先初始化为 JSON 数组，再追加条目
  - 仅允许追加，不得覆盖历史记录

