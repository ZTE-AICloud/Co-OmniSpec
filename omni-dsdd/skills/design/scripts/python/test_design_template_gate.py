#!/usr/bin/env python3
"""design template-contract 与 harness gate 集成测试（unittest）。"""

import json
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from design_template_gate import load_contract, validate_artifact, validate_gate_step  # noqa: E402


VALID_RESEARCH = """# Research

## 主题: 选用 Web 框架

- **Details**: graphify 查询确认团队历史项目以 FastAPI 为主
- **Rationale**: 团队熟悉且 async 友好，类型提示完善
- **Reference**: graphify://teams/web-stack

补充说明使文档超过最小长度要求，避免被 min_chars 门禁拒绝。
"""

VALID_DESIGN_STEP3 = """# 实施计划: Demo

**分支**: `001-demo` | **日期**: 2026-05-23 | **规范**: spec.md

## 摘要

实现 demo 能力。

## 技术背景

**语言/版本**: Python 3.11
**主要依赖**: FastAPI
**存储**: N/A
**测试**: pytest
**目标平台**: Linux
**项目类型**: 单一
**性能目标**: 100 rps
**约束条件**: p95 < 200ms
**规模/范围**: 内部试用

## 波及文件与复用分析

| 路径 | 关系 | 满足 | 策略 | 符号 |
|------|------|------|------|------|
| `src/app.py` | 入口 | 部分 | 小改 | `main` |
| `src/service.py` | 逻辑 | 否 | 修改 | `run` |

## 章程检查

- [x] **规格一致**：与 spec 一致
- [x] **方案锚定现状**：复用 app
- [x] **可定位修改点**：已列出
- [x] **波及与复用**：已填表

## 修改点严格检查

| 修改点 | 支持状态 | 利旧结论 | 最小化结论 | 证据 | 风险/备注 |
|--------|----------|----------|------------|------|-----------|
| 扩展 handler | 部分支持 | 同文件新函数 | 1 文件 | context.md | 低 |

## 项目结构

**结构决策**: 沿用 src/ 布局
"""

VALID_FUNC_SECTION = """

## 功能

### INSERT - FUNC-001 - 示例功能

**来源场景**: SCN-001 - 主流程

变更原因: 新增

**功能描述**: 提供示例能力

详细说明超过一行。
"""

VALID_ENTITY_SECTION = """

## 逻辑实体

### INSERT - [ENTITY-001](示例实体)

**变更原因**: 新增

**支撑的功能**: FUNC-001 - 示例功能

**映射目录**: src/models

实体职责说明。
"""

VALID_DATA_MODEL = """# 数据模型设计

## 核心数据结构图

### 1. DemoRecord(src/models/demo.py)

**定义**:
```python
class DemoRecord:
    id: str
```

**关键字段**:
- `id`(str)：主键

**验证规则**:
必填

## 数据结构关系

DemoRecord 独立使用。
"""

VALID_API_CONTRACT = """# 接口契约

## 对外接口

### INSERT - API-001 - 查询示例

**变更原因**: 新增

**所属逻辑实体**: ENTITY-001 - 示例实体

**调用方**: 前端

GET /api/v1/demo 返回 200。
"""

VALID_QUICKSTART = """# Quickstart: Demo

## 前置条件

- Python 3.11 已安装

## 验证步骤

1. 启动服务 `uvicorn app:app`
2. 调用 `curl localhost:8000/api/v1/demo`

## 期望结果

- 返回 200 与 JSON body
"""


class DesignTemplateGateTests(unittest.TestCase):
    def test_research_valid(self) -> None:
        errors = validate_artifact("research.md", VALID_RESEARCH, load_contract())
        self.assertEqual(errors, [], errors)

    def test_research_accepts_bold_and_fullwidth(self) -> None:
        # 标签加粗 + 全角冒号 应与裸 token 等价，门禁须放行。
        bold = (
            "# Research\n\n"
            "**Details：** 用 FastAPI 作为本轮 Web 框架候选。\n"
            "__Rationale__：团队历史项目以 FastAPI 为主，async 友好且类型提示完善。\n"
            "`Reference:` graphify://teams/web-stack\n"
            "补充内容以满足最小长度要求，避免被 min_chars 门禁拒绝。\n"
        )
        errors = validate_artifact("research.md", bold, load_contract())
        self.assertEqual(errors, [], errors)

    def test_research_rejects_placeholder(self) -> None:
        bad = "# Research\n\nHarness 占位\n## Details: TBD\n"
        errors = validate_artifact("research.md", bad, load_contract())
        self.assertTrue(errors)

    def test_design_step3_valid(self) -> None:
        errors = validate_artifact(
            "design.md", VALID_DESIGN_STEP3, load_contract(), gate_step="3"
        )
        self.assertEqual(errors, [], errors)

    def test_design_step3_rejects_template_placeholders(self) -> None:
        bad = (
            VALID_DESIGN_STEP3.replace("Python 3.11", "[例如: Python 3.11")
            .replace("001-demo", "[###-feature-name]")
            .replace("实现 demo", "[从功能规范中提取")
        )
        errors = validate_artifact("design.md", bad, load_contract(), gate_step="3")
        self.assertTrue(errors, errors)

    def test_design_step1a_requires_func_block(self) -> None:
        design = VALID_DESIGN_STEP3 + VALID_FUNC_SECTION
        errors = validate_artifact("design.md", design, load_contract(), gate_step="1a")
        self.assertEqual(errors, [], errors)

    def test_api_contract_valid(self) -> None:
        errors = validate_artifact("contracts/api-contract.md", VALID_API_CONTRACT, load_contract())
        self.assertEqual(errors, [], errors)

    def test_quickstart_valid(self) -> None:
        errors = validate_artifact("quickstart.md", VALID_QUICKSTART, load_contract())
        self.assertEqual(errors, [], errors)


class HarnessGateIntegration(unittest.TestCase):
    def test_gate_step_3_rejects_freeform_design(self) -> None:
        import design_harness

        with tempfile.TemporaryDirectory() as tmp:
            feature = Path(tmp)
            design = feature / "design.md"
            design.write_text(
                "# 随意设计\n\n只有自由文本 " * 20 + "\n## 技术背景\n短\n## 章程检查\n短\n",
                encoding="utf-8",
            )
            errors = design_harness._gate_step_3(feature, 64)
            self.assertTrue(errors)
            self.assertTrue(
                any("摘要" in e or "template" in e or "波及" in e for e in errors)
            )

    def test_gate_step_1a_rejects_missing_func_template(self) -> None:
        import design_harness

        with tempfile.TemporaryDirectory() as tmp:
            feature = Path(tmp)
            (feature / "design.md").write_text(
                VALID_DESIGN_STEP3 + "\n## 功能\n\n一段无 FUNC 的自由描述。\n",
                encoding="utf-8",
            )
            errors = design_harness._gate_step_1a(feature, 64)
            self.assertTrue(any("FUNC" in e for e in errors))

    def test_init_seeds_design_from_template(self) -> None:
        import design_harness

        plugin_root = Path(__file__).resolve().parents[4]
        with tempfile.TemporaryDirectory() as tmp:
            feature = Path(tmp)
            args = type(
                "Args",
                (),
                {
                    "plugin_root": str(plugin_root),
                    "working_dir": str(plugin_root),
                    "feature_dir": str(feature),
                    "branch_name": "001-demo",
                    "spec_file": str(feature / "spec.md"),
                    "design_file": str(feature / "design.md"),
                    "doc_dir": "omni-doc",
                    "repo_root": "",
                    "start_time": "",
                    "run_id": "",
                    "enable_e2e": False,
                },
            )()
            design_harness.cmd_init(args)
            text = (feature / "design.md").read_text(encoding="utf-8")
            self.assertIn("## 技术背景", text)
            self.assertIn("001-demo", text)
            self.assertNotIn("[###-feature-name]", text)


if __name__ == "__main__":
    unittest.main()
