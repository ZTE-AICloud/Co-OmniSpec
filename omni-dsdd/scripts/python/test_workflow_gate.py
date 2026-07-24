#!/usr/bin/env python3
"""workflow-gate.sh 集成回归测试。"""

import json
import subprocess
import tempfile
import unittest
from pathlib import Path


PLUGIN_ROOT = Path(__file__).resolve().parents[2]
WORKFLOW_GATE = PLUGIN_ROOT / "scripts" / "bash" / "workflow-gate.sh"


class WorkflowGateTest(unittest.TestCase):
    def setUp(self):
        self._tmpdir = tempfile.TemporaryDirectory()
        self.working = Path(self._tmpdir.name) / "workspace"
        self.feature = self.working / "changes" / "001-f"
        (self.feature / ".runs").mkdir(parents=True)
        (self.feature / ".runs" / "paths.json").write_text(
            json.dumps(
                {
                    "feature_dir": str(self.feature),
                    "working_dir": str(self.working),
                    "flow_mode": "expert",
                }
            ),
            encoding="utf-8",
        )
        (self.feature / ".runs" / "env.sh").write_text(
            "\n".join(
                [
                    f'export CLAUDE_PLUGIN_ROOT="{PLUGIN_ROOT}"',
                    f'export CLAUDE_WORKING_DIR="{self.working}"',
                    f'export FEATURE_DIR="{self.feature}"',
                    'export FLOW_MODE="expert"',
                    "",
                ]
            ),
            encoding="utf-8",
        )

    def tearDown(self):
        self._tmpdir.cleanup()

    def _write_state(self, completed):
        (self.feature / ".runs" / ".omnispec-state.json").write_text(
            json.dumps(
                {
                    "flow_mode": "expert",
                    "current_stage": "workflow-complete",
                    "completed_stages": completed,
                }
            ),
            encoding="utf-8",
        )

    def _run_gate(self):
        return subprocess.run(
            [
                "bash",
                str(WORKFLOW_GATE),
                "--feature-dir",
                str(self.feature),
                "--check",
                "workflow-complete",
            ],
            text=True,
            capture_output=True,
            check=False,
        )

    def test_expert_workflow_complete_requires_local_sandbox_status(self):
        """不能只靠 completed_stages 中的 local-sandbox-fix 宣告 expert 完成。"""
        self._write_state(["implement", "review", "local-sandbox-fix"])

        result = self._run_gate()

        self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("local-sandbox-fix", result.stdout + result.stderr)
        self.assertIn("workflow status", result.stdout + result.stderr)

    def test_expert_workflow_complete_accepts_successful_local_sandbox_status(self):
        self._write_state(["implement", "review", "local-sandbox-fix"])
        (self.feature / ".runs" / "local-sandbox-fix-status.json").write_text(
            json.dumps({"status": "success", "skipped": True}),
            encoding="utf-8",
        )
        summary_dir = self.feature / ".runs" / "local-sandbox-fix"
        summary_dir.mkdir(parents=True)
        (summary_dir / "summary.json").write_text(
            json.dumps({"status": "success", "skipped": True}),
            encoding="utf-8",
        )

        result = self._run_gate()

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
