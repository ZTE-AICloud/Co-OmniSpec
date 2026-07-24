#!/usr/bin/env python3
"""resolve_feature_dir 工作区边界校验测试。"""

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import omnispec_state as mod  # noqa: E402


class ResolveFeatureDirWorkspaceBoundTest(unittest.TestCase):
    def setUp(self):
        self._tmpdir = tempfile.TemporaryDirectory()
        self.working = Path(self._tmpdir.name) / "workspace"
        self.other = Path(self._tmpdir.name) / "other"
        self.working.mkdir()
        self.other.mkdir()

    def tearDown(self):
        self._tmpdir.cleanup()

    def _feature(self, root, name):
        # type: (Path, str) -> Path
        d = root / "changes" / name
        (d / ".runs").mkdir(parents=True)
        return d

    def _write_state(self, feature_dir, completed=None):
        # type: (Path, list) -> None
        state = {
            "flow_mode": "express",
            "current_stage": "review",
            "completed_stages": completed or ["implement", "review"],
        }
        (feature_dir / ".runs" / ".omnispec-state.json").write_text(
            json.dumps(state), encoding="utf-8"
        )

    def test_rejects_feature_dir_env_outside_working_dir(self):
        local = self._feature(self.working, "001-local")
        external = self._feature(self.other, "002-external")
        self._write_state(external)
        old = os.environ.get("FEATURE_DIR")
        os.environ["FEATURE_DIR"] = str(external)
        try:
            resolved = mod.resolve_feature_dir(
                working_dir=self.working, use_prerequisites=False
            )
            self.assertEqual(resolved, None)
        finally:
            if old is None:
                os.environ.pop("FEATURE_DIR", None)
            else:
                os.environ["FEATURE_DIR"] = old

    def test_rejects_active_feature_pointer_outside_working_dir(self):
        external = self._feature(self.other, "003-external")
        self._write_state(external)
        pointer = self.working / "changes" / ".active-feature"
        pointer.parent.mkdir(parents=True, exist_ok=True)
        pointer.write_text(str(external) + "\n", encoding="utf-8")
        resolved = mod.resolve_feature_dir(
            working_dir=self.working, use_prerequisites=False
        )
        self.assertEqual(resolved, None)

    def test_ignores_paths_json_feature_dir_outside_working_dir(self):
        local = self._feature(self.working, "004-local")
        external = self._feature(self.other, "005-external")
        self._write_state(local)
        paths = {
            "feature_dir": str(external),
            "working_dir": str(self.working),
        }
        (local / ".runs" / "paths.json").write_text(
            json.dumps(paths), encoding="utf-8"
        )
        resolved = mod.resolve_feature_dir(
            working_dir=self.working, use_prerequisites=False
        )
        self.assertEqual(resolved.resolve(), local.resolve())

    def test_accepts_feature_dir_under_working_changes(self):
        local = self._feature(self.working, "006-local")
        self._write_state(local, completed=[])
        old = os.environ.get("FEATURE_DIR")
        os.environ["FEATURE_DIR"] = str(local)
        try:
            resolved = mod.resolve_feature_dir(
                working_dir=self.working, use_prerequisites=False
            )
            self.assertEqual(resolved.resolve(), local.resolve())
        finally:
            if old is None:
                os.environ.pop("FEATURE_DIR", None)
            else:
                os.environ["FEATURE_DIR"] = old


    def test_validate_feature_dir_under_changes(self):
        local = self._feature(self.working, "007-local")
        err = mod.validate_feature_dir_under_changes(self.working, local)
        self.assertIsNone(err)
        external = self._feature(self.other, "008-external")
        err2 = mod.validate_feature_dir_under_changes(self.working, external)
        self.assertIsNotNone(err2)

    def test_validate_nested_feature_dir_under_changes(self):
        nested = self.working / "changes" / "DSDD" / "001-example"
        (nested / ".runs").mkdir(parents=True)
        err = mod.validate_feature_dir_under_changes(self.working, nested)
        self.assertIsNone(err)

    def test_resolve_flow_mode_from_pending(self):
        feature = self._feature(self.working, "009-pending")
        mod.write_pending_workflow(self.working, "express", arguments="add login")
        fm = mod.resolve_flow_mode(feature, working_dir=self.working)
        self.assertEqual(fm, "express")

    def test_resolve_flow_mode_cli_overrides_pending(self):
        feature = self._feature(self.working, "010-cli")
        mod.write_pending_workflow(self.working, "express")
        fm = mod.resolve_flow_mode(
            feature, cli_override="standard", working_dir=self.working
        )
        self.assertEqual(fm, "standard")

    def test_resolve_flow_mode_accepts_explicit_expert_without_valid_flow_mode(self):
        feature = self._feature(self.working, "010-expert")
        self.assertNotIn("expert", mod.VALID_FLOW_MODES)
        fm = mod.resolve_flow_mode(
            feature, cli_override="expert", working_dir=self.working
        )
        self.assertEqual(fm, "expert")

    def test_pending_workflow_does_not_auto_add_expert(self):
        mod.write_pending_workflow(self.working, "expert")
        pending = mod.read_pending_workflow(self.working)
        self.assertEqual(pending["flow_mode"], "express")

    def test_forced_pending_workflow_accepts_expert(self):
        feature = self._feature(self.working, "010-forced-expert")
        mod.write_pending_workflow(self.working, "expert", forced=True)
        pending = mod.read_pending_workflow(self.working)
        self.assertEqual(pending["flow_mode"], "expert")
        fm = mod.resolve_flow_mode(feature, working_dir=self.working)
        self.assertEqual(fm, "expert")

    def test_resolve_flow_mode_state_over_pending(self):
        feature = self._feature(self.working, "011-state")
        mod.write_pending_workflow(self.working, "express")
        (feature / ".runs" / ".omnispec-state.json").write_text(
            json.dumps({"flow_mode": "deep"}), encoding="utf-8"
        )
        fm = mod.resolve_flow_mode(feature, working_dir=self.working)
        self.assertEqual(fm, "deep")

    def test_resolve_flow_mode_preserves_state_expert(self):
        feature = self._feature(self.working, "011-state-expert")
        mod.write_pending_workflow(self.working, "express")
        (feature / ".runs" / ".omnispec-state.json").write_text(
            json.dumps({"flow_mode": "expert"}), encoding="utf-8"
        )
        fm = mod.resolve_flow_mode(feature, working_dir=self.working)
        self.assertEqual(fm, "expert")

    def test_sync_flow_mode_to_paths_and_env(self):
        feature = self._feature(self.working, "012-sync")
        paths = {"feature_dir": str(feature), "branch_name": "012-sync"}
        (feature / ".runs" / "paths.json").write_text(
            json.dumps(paths), encoding="utf-8"
        )
        (feature / ".runs" / "env.sh").write_text(
            'export FEATURE_DIR="{0}"\n'.format(feature), encoding="utf-8"
        )
        mod.sync_flow_mode_to_paths(feature, "express")
        paths_data = json.loads((feature / ".runs" / "paths.json").read_text())
        self.assertEqual(paths_data["flow_mode"], "express")
        env = (feature / ".runs" / "env.sh").read_text()
        self.assertIn('export FLOW_MODE="express"', env)

    def test_update_state_syncs_expert_flow_mode_to_paths_and_env(self):
        feature = self._feature(self.working, "013-update-expert")
        paths = {"feature_dir": str(feature), "flow_mode": "express"}
        (feature / ".runs" / "paths.json").write_text(
            json.dumps(paths), encoding="utf-8"
        )
        (feature / ".runs" / "env.sh").write_text(
            'export FLOW_MODE="express"\n', encoding="utf-8"
        )

        state = mod.update_state(feature, "tasks", flow_mode="expert")

        self.assertEqual(state["flow_mode"], "expert")
        paths_data = json.loads((feature / ".runs" / "paths.json").read_text())
        self.assertEqual(paths_data["flow_mode"], "expert")
        env = (feature / ".runs" / "env.sh").read_text()
        self.assertIn('export FLOW_MODE="expert"', env)

    def test_consume_pending_workflow(self):
        mod.write_pending_workflow(self.working, "express")
        mod.consume_pending_workflow(self.working)
        self.assertEqual(mod.read_pending_workflow(self.working), {})


if __name__ == "__main__":
    unittest.main()
