# [PROJECT_NAME] 项目章程
<!-- 示例: Spec 章程, TaskFlow 章程等 -->

<!-- 填写方式：
1. 内容来源
   - 按优先级处理：存在冲突时，高优先级覆盖低优先级；不冲突时，合并语义相同的描述

   - 优先级1：命令的用户输入，作为最高优先级，其他来源不得违背已填写内容
   - 优先级2：本模板中已填写的内容，作为默认配置
   - 优先级3：从`参考文档`提取，读取前需确认文档存在
   - 优先级4：从项目中的文档(.md, .txt等)及相关代码文件推断

2. 内容要求：
   - 可实践性：每个标题下的内容必须具体可执行，避免空泛的原则描述
     * 提供具体代码示例：包含实际的类名、函数名、模块路径等（如：使用 `BaseRepository` 基类、在 `services/` 目录下实现业务逻辑）
     * 说明实践方法：不只是"做什么"，还要说明"怎么做"（如：不只说"保持模块解耦"，而要说明"通过依赖注入和接口抽象实现模块解耦"）
     * 关联项目实际：引用项目中真实存在的文件、目录、代码结构作为参考（如：参考 `src/core/base.py` 中的基类实现）

3. 格式规范：
   - 每个章节下的原则使用列表格式
     * 一级列表使用 `-`（短横线），表示主要原则
     * 二级列表使用 `*`（星号），表示原则的细则或子项
   - 在列表中使用代码块（格式为`代码`）、行内代码、粗体等格式增强可读性，但需保持整体格式统一
-->

## 核心原则

### [PRINCIPLE_1_NAME]
<!-- 示例: 架构原则 -->
[PRINCIPLE_1_DESCRIPTION]
<!--
    参考文档：`[DOC_DIR]/rules/00-architecture.mdc`（DOC_DIR 可通过环境变量 SPECIFY_DOC_DIR 或 .specify/config 配置，默认为 "omni-doc"）
    内容说明：包含分层架构、领域驱动设计（DDD）、模块划分、依赖原则等
-->

### [PRINCIPLE_2_NAME]
<!-- 示例: 接口与通信原则 -->
[PRINCIPLE_2_DESCRIPTION]
<!--
    参考文档：`[DOC_DIR]/rules/01-routing-dispatch.mdc`、`[DOC_DIR]/rules/04-communication.mdc`（DOC_DIR 可通过环境变量 SPECIFY_DOC_DIR 或 .specify/config 配置，默认为 "omni-doc"）
    内容说明：包含对外处理入口描述，路由与分发机制，入参处理，对外交互机制等
-->

### [PRINCIPLE_3_NAME]
<!-- 示例: 状态与数据管理原则 -->
[PRINCIPLE_3_DESCRIPTION]
<!--
    参考文档：`[DOC_DIR]/rules/02-state-management.mdc`、`[DOC_DIR]/rules/03-data-access.mdc`（DOC_DIR 可通过环境变量 SPECIFY_DOC_DIR 或 .specify/config 配置，默认为 "omni-doc"）
    内容说明：包含状态机制及生命周期，数据库接口等
-->

### [PRINCIPLE_4_NAME]
<!-- 示例: 测试与质量保证原则 -->
[PRINCIPLE_4_DESCRIPTION]
<!--
    参考文档：`[DOC_DIR]/rules/09-testing.mdc`（DOC_DIR 可通过环境变量 SPECIFY_DOC_DIR 或 .specify/config 配置，默认为 "omni-doc"）
    内容说明：包含测试框架，测试用例命名与格式规范，mock方法，测试文件组织方式，FT/UT分层，TDD方法等
-->

### [PRINCIPLE_5_NAME]
<!-- 示例: 可观测性与运维原则 -->
[PRINCIPLE_5_DESCRIPTION]
<!--
    参考文档：`[DOC_DIR]/rules/05-logging.mdc`、`[DOC_DIR]/rules/06-monitoring.mdc`、`[DOC_DIR]/rules/10-deployment.mdc`（DOC_DIR 可通过环境变量 SPECIFY_DOC_DIR 或 .specify/config 配置，默认为 "omni-doc"）
    内容说明：包含指标采集，流程统计，告警，内容监控等
-->

### [PRINCIPLE_6_NAME]
<!-- 示例: 编码风格与设计模式 -->
[PRINCIPLE_6_DESCRIPTION]
<!--
    参考文档：`[DOC_DIR]/rules/08-style-patterns.mdc`（DOC_DIR 可通过环境变量 SPECIFY_DOC_DIR 或 .specify/config 配置，默认为 "omni-doc"）
    内容说明：包含变量命名规范、函数命名规范、代码文件组织原则，设计模式等
-->

### 目录结构
[DIRECTORY_STRUCTURE]
<!--
    参考文档：`[DOC_DIR]/rules/00-architecture.mdc`（DOC_DIR 可通过环境变量 SPECIFY_DOC_DIR 或 .specify/config 配置，默认为 "omni-doc"）
    内容说明：包含项目代码主要目录结构及其简要说明，展示项目的组织方式和模块划分
    格式示例：使用树形格式（├──），按以下示例展示所有层级的文件夹
    ├── common/             # 公共模块：跨项目共享的通用组件和工具
    ├── src/                # 核心业务逻辑
    │   ├── network/        # 网络相关处理
    │   └── book/           # 预定服务
    ├── [DOC_DIR]/          # 项目文档（DOC_DIR 可通过环境变量 SPECIFY_DOC_DIR 或 .specify/config 配置，默认为 "omni-doc"）
    └── test/               # 测试模块：单元测试、集成测试和功能测试
-->

- 目录使用原则：
    * 新增代码时必须优先使用已有的目录结构，禁止随意创建新目录
    * 只有在确实需要新的功能模块或架构层次时，才允许创建新目录，且需要经过评审确认
    * 根据代码的功能定位和架构层次，选择对应的已有目录进行代码组织
    * 新增文件时，应在已有目录下创建，保持目录结构的稳定性和一致性

## [SECTION_2_NAME]
<!-- 示例: 附加约束、安全要求、性能标准等 -->

### [OTHER_PRINCIPLE_1_NAME]
<!-- 示例: 配置管理原则 -->
[OTHER_PRINCIPLE_1_DESCRIPTION]
<!--
    参考文档：`[DOC_DIR]/rules/07-config.mdc`（DOC_DIR 可通过环境变量 SPECIFY_DOC_DIR 或 .specify/config 配置，默认为 "omni-doc"）
    内容说明：包含配置框架，配置生命周期管理，配置加载与验证等
-->

### [OTHER_PRINCIPLE_2_NAME]
<!-- 示例: 其他规范原则 -->
[OTHER_PRINCIPLE_2_DESCRIPTION]
<!--
    参考文档：其他rules文档
    内容说明：包含其他未涵盖的规范原则，如安全规范、性能要求、兼容性要求等
-->

## [SECTION_3_NAME]
<!-- 示例: 质量门禁等 -->

[SECTION_3_CONTENT]
<!--
    参考文档：其他rules文档
    内容说明：包含git提交规范，测试覆盖率要求，其他测试门禁等
-->

## [SECTION_4_NAME]
<!-- 示例: 开发工作流程，审查流程等 -->

[SECTION_4_CONTENT]
<!-- 示例: 工作流程，代码审查要求、部署审批流程等 -->

## 治理
<!-- 示例: 章程优先于所有其他实践; 修正需要文档化、批准、迁移计划; 版本政策 -->

[GOVERNANCE_RULES]
<!-- 示例: 所有 PR/审查必须验证合规性; 复杂性必须得到证明; 使用 [GUIDANCE_FILE] 进行运行时开发指导 -->

**版本**: [CONSTITUTION_VERSION] | **批准日期**: [RATIFICATION_DATE] | **最后修正**: [LAST_AMENDED_DATE]
<!-- 示例: 版本: 2.1.1 | 批准日期: 2025-06-13 | 最后修正: 2025-07-16 -->
