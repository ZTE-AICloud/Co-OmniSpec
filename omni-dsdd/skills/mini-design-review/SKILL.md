---
name: mini-design-review
description: 评审极简SDD生成的详设文档
version: 1.0.0
---

## 准备阶段
- 判断当前操作系统，windows还是linux系统;
1. 清理上次评审文档
* windows: 仓库根目录下执行脚本(不要从技能目录下找): `scripts/powershell/mini-delete-review.ps1 --design`。
* linux: 仓库根目录下执行脚本(不要从技能目录下找): `scripts/bash/mini-delete-review.sh --design`。
2. 获取详设文档
* windows： 仓库根目录下执行脚本(不要从技能目录下找):`scripts/powershell/mini-check.ps1 --json`
* linux:仓库根目录下执行脚本(不要从技能目录下找):`scripts/bash/mini-check.sh --json`
   - 解析 JSON 获取 DESIGN ，DESIGN 为详设文档。 对于参数中的单引号如 "I'm Groot", 使用转义语法: 例如 'I'\''m Groot'(或尽可能使用双引号: "I'm Groot").
   - 解析 JSON 获取 FEATURE_DIR ， FEATURE_DIR 需求相关文档产物所在目录。
3. 判断详设文档 DESIGN  是否存在，且内容不为空。如果详设文档 DESIGN 不存在或者内容为空，则结束该SKILL。


## 评审次数上限保护
1. 读取文件 FEATURE_DIR/design-review-times.md ，该文件内容为一个数字，表示当前为第几次评审。
2. *** 当前评审次数大于等于3 *** 向FEATURE_DIR/review-result.md中写入`评审通过`，然后直接退出本次评审，不执行后续步骤。

## 检查校验
按以下要求检查详设文档 DESIGN，将不满足校验的内容，写到文档 FEATURE_DIR/review-result.md， 写清楚哪个位置违反了什么校验条件。
*** 只评审下述提到的要求评审，不自己增加评审项 ***
### 宪章检查
1. 读取`.omni-infra/memory/constitution.md`：了解章程约束，判断 DESIGN 中是否有违反规章约束。
2. 如果没有违反该项检查，则 FEATURE_DIR/review-result.md 中写入，`宪章检查：通过`

### 新增函数检查
1. 新实现的任何函数，需要确认无相同功能的函数。
2. 如果没有违反该项检查，则 FEATURE_DIR/review-result.md 中写入，`新增函数检查：通过`

### 调用现有函数检查
1. 调用的已有函数，需要实际读取函数完整代码确认实现逻辑是否符合本次需求要求。
2. 如果没有违反该项检查，则 FEATURE_DIR/review-result.md 中写入，`调用现有函数检查：通过`

