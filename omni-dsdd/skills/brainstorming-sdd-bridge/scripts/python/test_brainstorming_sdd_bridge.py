#!/usr/bin/env python3
"""Tests for brainstorming_sdd_bridge."""

import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).resolve().parent / "brainstorming_sdd_bridge.py"
PLUGIN_ROOT = Path(__file__).resolve().parents[4]


class BrainstormingSddBridgeTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.working = Path(self.tmp.name) / "workspace"
        self.plugin = self.working / "omni-dsdd"
        ignore = shutil.ignore_patterns(
            ".git",
            "node_modules",
            "__pycache__",
            ".pytest_cache",
            "graphify-out",
        )
        shutil.copytree(PLUGIN_ROOT, self.plugin, ignore=ignore)
        self.feature = self.working / "changes" / "999-bridge"
        self.feature.mkdir(parents=True)
        (self.feature / "2026-07-03-bridge-design.md").write_text(
            "# Bridge Feature\n\n"
            "## Architecture\n\n"
            "Use the approved expert brainstorming design as the source of truth.\n\n"
            "## User Scenario\n\n"
            "A workflow can continue from brainstorming to tasks without rerunning design.\n\n"
            "## Testing\n\n"
            "Downstream stages must use TDD tasks and standard verification gates.\n\n"
            "## Very Detailed Tail\n\n"
            "Tail content must not be lost when bridge documents are generated.\n",
            encoding="utf-8",
        )

    def tearDown(self):
        self.tmp.cleanup()

    def test_generates_downstream_sdd_interface_without_design_stage(self):
        subprocess.run(
            [
                sys.executable,
                str(SCRIPT),
                "--plugin-root",
                str(self.plugin),
                "--working-dir",
                str(self.working),
                "--feature-dir",
                str(self.feature),
                "--branch-name",
                "999-bridge",
            ],
            check=True,
        )

        spec = (self.feature / "spec.md").read_text(encoding="utf-8")
        design = (self.feature / "design.md").read_text(encoding="utf-8")
        context = (self.feature / "context.md").read_text(encoding="utf-8")
        self.assertIn("REQ-001", spec)
        self.assertIn("SCN-001", spec)
        self.assertIn("系统 shall", spec)
        self.assertIn("2026-07-03-bridge-design.md", spec)
        self.assertIn("源 brainstorming 设计全文", spec)
        self.assertIn("Tail content must not be lost", spec)
        self.assertIn("不代表重新执行 design 阶段", design)
        self.assertIn("源 brainstorming 设计全文", design)
        self.assertIn("Tail content must not be lost", design)
        self.assertIn("expert_brainstorming_bridge", context)
        self.assertIn("Tail content must not be lost", context)

        for rel in (
            "research.md",
            "data-model.md",
            "contracts/api-contract.md",
            "quickstart.md",
            "requirements-content.md",
            "scenarios-content.md",
            "checklists/requirements.md",
            ".runs/evaluations/eval-specify-report.yaml",
            ".runs/metrics/omni-metrics-log.json",
        ):
            self.assertTrue((self.feature / rel).is_file(), rel)

        paths = json.loads((self.feature / ".runs" / "paths.json").read_text(encoding="utf-8"))
        self.assertEqual(paths["design_file"], str(self.feature / "design.md"))
        self.assertEqual(paths["tasks_file"], str(self.feature / "tasks.md"))
        self.assertEqual(paths["bridge_stage"], "brainstorming-sdd-bridge")

        env = (self.feature / ".runs" / "env.sh").read_text(encoding="utf-8")
        self.assertIn('export FEATURE_SPEC="', env)
        self.assertIn('export IMPL_DESIGN="', env)
        self.assertIn('export TASKS="', env)

        state = json.loads(
            (self.feature / ".runs" / ".omnispec-state.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual(state["flow_mode"], "expert")
        self.assertIn("brainstorming-sdd-bridge", state["completed_stages"])
        self.assertEqual(state["current_stage"], "tasks")
        self.assertNotIn("specify", state["completed_stages"])
        self.assertNotIn("design", state["completed_stages"])

        subprocess.run(
            [
                sys.executable,
                str(self.plugin / "skills/tasks/scripts/python/tasks_harness.py"),
                "gate",
                "--feature-dir",
                str(self.feature),
                "--step",
                "context",
            ],
            check=True,
        )


if __name__ == "__main__":
    unittest.main()
