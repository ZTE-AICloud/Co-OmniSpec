#!/usr/bin/env python3
"""template-contract 与 gate 集成测试（unittest）。"""

import json
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from specify_template_gate import load_contract, validate_artifact  # noqa: E402


VALID_SPEC = """# 功能规范: 测试

**功能分支**: `001-test`
**创建时间**: 2026-05-23
**状态**: 草稿
**输入**: 用户描述: "demo"

## 成功标准

- **SC-001**: 用户可在 3 分钟内完成操作

## 与既有架构对齐（章程）

符合章程复用原则。

## 需求

### 动作类型:INSERT - REQ-001 - 示例需求

变更原因: 新增

系统 shall 提供示例能力

- When 用户提交, 系统 shall 接受请求

## 场景

### 动作类型:INSERT - SCN-001 - 主流程 (优先级: P1)

归属的需求: REQ-001 - 示例需求

**验收场景**:

1. **Given** 初始状态, **When** 操作, **Then** 成功
"""


class TemplateGateTests(unittest.TestCase):
    def test_valid_spec_passes(self) -> None:
        errors = validate_artifact("spec.md", VALID_SPEC, load_contract())
        self.assertEqual(errors, [], errors)

    def test_spec_missing_requirements_fails(self) -> None:
        bad = VALID_SPEC.split("## 需求")[0]
        errors = validate_artifact("spec.md", bad, load_contract())
        self.assertTrue(any("## 需求" in e for e in errors))

    def test_checklist_template_sections(self) -> None:
        plugin_root = Path(__file__).resolve().parents[4]
        working_dir = plugin_root
        from specify_template_gate import render_requirements_checklist_skeleton, working_infra_root

        infra = working_infra_root(working_dir)
        tpl = infra / "templates" / "requirements-template.md"
        if not tpl.is_file():
            self.skipTest(f"template missing: {tpl}")
        text = render_requirements_checklist_skeleton(
            feature_name="测试",
            working_dir=working_dir,
        )
        errors = validate_artifact("checklists/requirements.md", text, load_contract())
        self.assertEqual(errors, [], errors)


class HarnessGateIntegration(unittest.TestCase):
    def test_gate_step_6_rejects_minimal_spec(self) -> None:
        import specify_harness

        with tempfile.TemporaryDirectory() as tmp:
            feature = Path(tmp)
            spec = feature / "spec.md"
            spec.write_text(
                "# 只有标题\n\n"
                + "一些自由文本 " * 10
                + "\n不含模板要求的章节。\n",
                encoding="utf-8",
            )
            errors = specify_harness._gate_step_6(feature, 64)
            self.assertTrue(errors)
            self.assertTrue(any("成功标准" in e or "missing section" in e for e in errors))


if __name__ == "__main__":
    unittest.main()
