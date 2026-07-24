---
name: mini-implement-review
description: 评审极简SDD生成的代码
version: 1.0.0
---

仓库根目录下执行脚本(不要从技能目录下找) `scripts/bash/mini-delete-review.sh --implement`。

## 准备阶段
- 判断当前操作系统，windows还是linux系统;

1. 清理上次评审结果：
- linux:仓库根目录下执行脚本(不要从技能目录下找) `scripts/bash/mini-delete-review.sh --implement`。
- windows: 仓库根目录下执行脚本(不要从技能目录下找) `scripts/powershell/mini-delete-review.ps1 --implement`。
2. 获取详设文档
* linux：仓库根目录下执行脚本(不要从技能目录下找):`scripts/bash/mini-check.sh --json`
* windows：仓库根目录下执行脚本(不要从技能目录下找):`scripts/powershell/mini-check.ps1 --json`
   - 解析 JSON 获取 DESIGN ，DESIGN 为详设文档。 对于参数中的单引号如 "I'm Groot", 使用转义语法: 例如 'I'\''m Groot'(或尽可能使用双引号: "I'm Groot").
   - 解析 JSON 获取 FEATURE_DIR ， FEATURE_DIR 需求相关文档产物所在目录。
3. 判断详设文档 DESIGN  是否存在，且内容不为空。如果详设文档 DESIGN 不存在或者内容为空，则结束该SKILL。


## 评审次数上限保护
1. 读取文件 FEATURE_DIR/implement-review-times.md ，该文件内容为一个数字，表示当前为第几次评审。
2. *** 当前评审次数大于等于3 *** ，向FEATURE_DIR/review-result.md中写入`评审通过`，然后直接结束本技能，不执行后续步骤。

## 检查校验
通过git diff 获取本次代码修改，检查代码是否修改是否满足下述各类检查项，检查结果写到文档 FEATURE_DIR/review-result.md， 写清楚哪个位置违反了什么校验条件
*** 只评审下述提到的要求评审，不自己增加评审项 ***
### 功能实现完整检查
1. 读取详设文档 DESIGN，判断每个用户故事、每个修改点是否修改完成。
2. 如果全部修改完成，则 FEATURE_DIR/review-result.md 中写入，`功能实现完整检查：通过`


### 宪章检查
1. 读取`.omni-infra/memory/constitution.md`：了解章程约束，判断代码修改中是否有违反规章约束。
2. 如果没有违反该项检查，则 FEATURE_DIR/review-result.md 中写入，`宪章检查：通过`

### 新增函数检查
1. 新实现的任何函数，需要确认无相同功能的函数。
2. 如果没有违反该项检查，则 FEATURE_DIR/review-result.md 中写入，`新增函数检查：通过`

### 调用现有函数检查
1. 调用的已有函数，需要实际读取函数完整代码确认实现逻辑是否符合本次需求要求。
2. 如果没有违反该项检查，则 FEATURE_DIR/review-result.md 中写入，`调用现有函数检查：通过`


### 清理未使用代码
1. 检查：本次修改代码后，不再使用的函数、全局变量等，判断是否还有其他位置使用，如果未使用，需要删除。
2. 如果没有违反该项检查，则 FEATURE_DIR/review-result.md 中写入，`清理未使用代码检查：通过`

### 新增常量检查
1. 检查新增的常量，在现有代码中是否已有全局变量定义，如果有，则复用原有变量。
2. 如果没有违反该项检查，则 FEATURE_DIR/review-result.md 中写入，`新增常量检查检查：通过`

### 新增全局变量位置检查
1. 检查新增的全局变量定义位置是否和现有风格保持一致，查看是否有类似功能的全局变量统一定义在了某个文件。
2. 如果没有违反该项检查，则 FEATURE_DIR/review-result.md 中写入，`新增全局变量位置检查：通过`

