# Token 管理

## 概述

本技能编排 8+ 个阶段，各阶段 Token 预算分配如下：

## 各阶段 Token 预算

| 阶段 | 预算 | 说明 |
|------|------|------|
| logic_architecture | 30K | 架构识别与 JSON 生成 |
| interfaces | 100K | 接口清单扫描与详情生成 |
| functions | 80K | 功能规范提取 |
| entities | 40K | 实体识别与融合 |
| scenarios | 50K | 场景描述生成 |
| requirements | 40K | 需求分析与拆分 |
| external-interfaces | 30K | 外部依赖接口识别 |
| rules | 20K | 规则/约束反构 |

## 总预算

- 单 target 模式：建议总预算不超过 150K tokens
- all 全流程模式：建议总预算不超过 400K tokens

## 上下文压缩策略

1. 每阶段完成后执行 `/compact` 压缩上下文
2. 保留当前阶段的必要上下文（产物文件路径、关键状态）
3. 移除上一阶段的详细内容
4. 使用 Todo 状态传递阶段进度信息

## 阶段间数据传递

- 通过文件系统传递：`architecture.json`、`interface-list.json`、`entity-list.json` 等
- 通过 Todo 状态传递：当前阶段、完成状态、关键决策
- 通过缓存文件传递：`reverse-cache/` 目录

## 预算超限处理

1. 优先压缩上下文（执行 `/compact`）
2. 精简阶段输出（减少详细描述）
3. 跳过低优先级阶段（根据 target 决定）
4. 如仍超限，中断执行并提示用户