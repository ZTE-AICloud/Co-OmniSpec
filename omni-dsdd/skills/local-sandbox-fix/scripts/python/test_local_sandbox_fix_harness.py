#!/usr/bin/env python3
"""local-sandbox-fix harness / wait 脚本单元测试。"""

import json
import sys
import tempfile
import unittest
from pathlib import Path

_SCRIPT_DIR = Path(__file__).resolve().parent
if str(_SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPT_DIR))

import wait_sandboxcheck as wait_mod  # noqa: E402


class WaitSandboxcheckTest(unittest.TestCase):
    def test_is_done_result_json(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = Path(tmp) / "result.json"
            result.write_text('{"code": 200}', encoding="utf-8")
            done, reason = wait_mod.is_done(result, "")
            self.assertTrue(done)
            self.assertEqual(reason, "result_json")

    def test_is_done_log_marker(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = Path(tmp) / "result.json"
            tail = "==================本地沙盒检查完成================="
            done, reason = wait_mod.is_done(result, tail)
            self.assertTrue(done)
            self.assertEqual(reason, "log_marker")

    def test_log_tail_since_session(self):
        with tempfile.TemporaryDirectory() as tmp:
            run_log = Path(tmp) / "run.log"
            run_log.write_text("old\n=== 执行开始 ===\nnew\n", encoding="utf-8")
            session = {"run_log_offset": len("old\n")}
            tail = wait_mod.log_tail_since_session(run_log, session)
            self.assertIn("=== 执行开始 ===", tail)
            self.assertNotIn("old", tail.splitlines()[0] if tail else "")


class HarnessInitTest(unittest.TestCase):
    def test_init_without_feature_dir_and_no_records(self):
        """未传 --feature-dir 且无记录文件可解析时 init 返回 1。"""
        import local_sandbox_fix_harness as harness

        with tempfile.TemporaryDirectory() as plugin_tmp, tempfile.TemporaryDirectory() as work_tmp:
            plugin = Path(plugin_tmp)
            working = Path(work_tmp)
            skill_dir = plugin / "skills" / "local-sandbox-fix"
            skill_dir.mkdir(parents=True)
            (skill_dir / "SKILL.md").write_text("---\nname: local-sandbox-fix\n---\n", encoding="utf-8")
            sandboxcheck = plugin / "skills" / "local-sandboxcheck" / "scripts"
            sandboxcheck.mkdir(parents=True)
            (sandboxcheck / "run_local_ci.py").write_text("# stub\n", encoding="utf-8")

            class Args:
                plugin_root = str(plugin)
                working_dir = str(working)
                feature_dir = ""
                run_id = "test-run"

            self.assertEqual(harness.cmd_init(Args), 1)

    def test_init_writes_paths_under_feature_dir(self):
        """harness 产物落在 FEATURE_DIR/.runs/local-sandbox-fix 下。"""
        import local_sandbox_fix_harness as harness

        with tempfile.TemporaryDirectory() as plugin_tmp, tempfile.TemporaryDirectory() as work_tmp:
            plugin = Path(plugin_tmp)
            working = Path(work_tmp)
            feature = working / "changes" / "001-f"
            feature.mkdir(parents=True)
            skill_dir = plugin / "skills" / "local-sandbox-fix"
            skill_dir.mkdir(parents=True)
            (skill_dir / "SKILL.md").write_text("---\nname: local-sandbox-fix\n---\n", encoding="utf-8")
            sandboxcheck = plugin / "skills" / "local-sandboxcheck" / "scripts"
            sandboxcheck.mkdir(parents=True)
            (sandboxcheck / "run_local_ci.py").write_text("# stub\n", encoding="utf-8")

            class Args:
                plugin_root = str(plugin)
                working_dir = str(working)
                feature_dir = str(feature)
                run_id = "test-run"

            rc = harness.cmd_init(Args)
            self.assertEqual(rc, 0)
            harness_dir = feature / ".runs" / "local-sandbox-fix"
            paths = json.loads((harness_dir / "paths.json").read_text(encoding="utf-8"))
            self.assertEqual(paths["working_dir"], str(working.resolve()))
            self.assertEqual(paths["feature_dir"], str(feature.resolve()))
            self.assertEqual(paths["harness_dir"], str(harness_dir.resolve()))
            self.assertTrue(Path(paths["devops_src"]).name == "devops_config.yaml")

    def test_init_resolves_feature_dir_from_records(self):
        """未传 --feature-dir 时，harness 从 changes/<f>/.runs 记录自动解析 feature_dir。"""
        import local_sandbox_fix_harness as harness

        # 复用真实 omnispec_state.py（动态加载需要它在 plugin_root/scripts/python/ 下）
        # 测试文件位于 omni-dsdd/skills/local-sandbox-fix/scripts/python/，parents[4] = omni-dsdd
        repo_state = (
            Path(__file__).resolve().parents[4] / "scripts" / "python" / "omnispec_state.py"
        )
        self.assertTrue(repo_state.is_file(), "omnispec_state.py 不存在，无法测试自动解析")

        with tempfile.TemporaryDirectory() as plugin_tmp, tempfile.TemporaryDirectory() as work_tmp:
            plugin = Path(plugin_tmp)
            working = Path(work_tmp)
            feature = working / "changes" / "001-f"
            (feature / ".runs").mkdir(parents=True)

            skill_dir = plugin / "skills" / "local-sandbox-fix"
            skill_dir.mkdir(parents=True)
            (skill_dir / "SKILL.md").write_text("---\nname: local-sandbox-fix\n---\n", encoding="utf-8")
            sandboxcheck = plugin / "skills" / "local-sandboxcheck" / "scripts"
            sandboxcheck.mkdir(parents=True)
            (sandboxcheck / "run_local_ci.py").write_text("# stub\n", encoding="utf-8")

            # 把真实 omnispec_state.py 放到 plugin 下，使 harness 能动态加载
            state_dst = plugin / "scripts" / "python"
            state_dst.mkdir(parents=True)
            (state_dst / "omnispec_state.py").write_text(repo_state.read_text(encoding="utf-8"), encoding="utf-8")

            # 造记录：changes/001-f/.runs/paths.json（含 feature_dir）+ .omnispec-state.json
            import json as _json
            (feature / ".runs" / "paths.json").write_text(
                _json.dumps({"feature_dir": str(feature)}), encoding="utf-8"
            )
            (feature / ".runs" / ".omnispec-state.json").write_text("{}", encoding="utf-8")

            class Args:
                plugin_root = str(plugin)
                working_dir = str(working)
                feature_dir = ""  # 故意不传
                run_id = "resolve-run"

            rc = harness.cmd_init(Args)
            self.assertEqual(rc, 0)
            harness_dir = feature / ".runs" / "local-sandbox-fix"
            paths = _json.loads((harness_dir / "paths.json").read_text(encoding="utf-8"))
            self.assertEqual(paths["feature_dir"], str(feature.resolve()))

    def test_workflow_gate_pre_and_complete(self):
        import local_sandbox_fix_harness as harness

        with tempfile.TemporaryDirectory() as plugin_tmp, tempfile.TemporaryDirectory() as work_tmp:
            plugin = Path(plugin_tmp)
            working = Path(work_tmp)
            feature = working / "changes" / "001-f"
            feature.mkdir(parents=True)
            (working / "devops_config.yaml").write_text("repos: []\n", encoding="utf-8")
            (feature / ".runs").mkdir(parents=True)
            (feature / ".runs" / "env.sh").write_text(
                f'export CLAUDE_WORKING_DIR="{working}"\nexport FEATURE_DIR="{feature}"\n',
                encoding="utf-8",
            )

            class PreArgs:
                feature_dir = str(feature)
                working_dir = str(working)
                check = "pre"

            self.assertEqual(harness.cmd_workflow_gate(PreArgs), 0)

            status = feature / ".runs" / "local-sandbox-fix-status.json"
            status.write_text('{"status": "success"}', encoding="utf-8")
            (feature / ".runs" / "local-sandbox-fix").mkdir(parents=True)
            (feature / ".runs" / "local-sandbox-fix" / "summary.json").write_text(
                '{"status": "success"}', encoding="utf-8"
            )

            class DoneArgs:
                feature_dir = str(feature)
                working_dir = str(working)
                check = "complete"

            self.assertEqual(harness.cmd_workflow_gate(DoneArgs), 0)

    def test_pre_allows_missing_devops(self):
        """devops_config.yaml 缺失时，pre 检查不再拦截（放宽为可选）。"""
        import local_sandbox_fix_harness as harness

        with tempfile.TemporaryDirectory() as work_tmp:
            working = Path(work_tmp)
            feature = working / "changes" / "001-f"
            feature.mkdir(parents=True)
            # 刻意不创建 devops_config.yaml
            (feature / ".runs").mkdir(parents=True)
            (feature / ".runs" / "env.sh").write_text(
                f'export CLAUDE_WORKING_DIR="{working}"\nexport FEATURE_DIR="{feature}"\n',
                encoding="utf-8",
            )

            class PreArgs:
                feature_dir = str(feature)
                working_dir = str(working)
                check = "pre"

            rc = harness.cmd_workflow_gate(PreArgs)
            self.assertEqual(rc, 0)

    def test_gate0_skip_when_devops_missing(self):
        """gate 0-init 在 devops_config.yaml 缺失时返回 skip 并成功收尾，不进主循环。"""
        import argparse
        import local_sandbox_fix_harness as harness

        with tempfile.TemporaryDirectory() as plugin_tmp, tempfile.TemporaryDirectory() as work_tmp:
            plugin = Path(plugin_tmp)
            working = Path(work_tmp)
            feature = working / "changes" / "001-f"
            feature.mkdir(parents=True)

            skill_dir = plugin / "skills" / "local-sandbox-fix"
            skill_dir.mkdir(parents=True)
            (skill_dir / "SKILL.md").write_text("---\nname: local-sandbox-fix\n---\n", encoding="utf-8")
            sandboxcheck = plugin / "skills" / "local-sandboxcheck"
            (sandboxcheck / "scripts").mkdir(parents=True)
            (sandboxcheck / "scripts" / "run_local_ci.py").write_text("# stub\n", encoding="utf-8")

            class InitArgs:
                plugin_root = str(plugin)
                working_dir = str(working)
                feature_dir = str(feature)
                run_id = "skip-run"

            # init 只建地基，不碰业务配置
            self.assertEqual(harness.cmd_init(InitArgs), 0)
            harness_dir = feature / ".runs" / "local-sandbox-fix"
            # 刻意不创建 devops_config.yaml → gate 0-init 触发 skip 收尾
            gate_ns = argparse.Namespace(
                harness_dir=str(harness_dir),
                working_dir="",
                step="0-init",
                record=True,
            )
            rc = harness.cmd_gate(gate_ns)
            self.assertEqual(rc, 0)

            summary = json.loads((harness_dir / "summary.json").read_text(encoding="utf-8"))
            self.assertEqual(summary["status"], "success")
            self.assertTrue(summary["skipped"])

            status = json.loads((feature / ".runs" / "local-sandbox-fix-status.json").read_text(encoding="utf-8"))
            self.assertEqual(status["status"], "success")
            self.assertTrue(status["skipped"])

    def test_gate0_copies_devops_and_enters_loop(self):
        """有 devops_config.yaml 时 gate 0-init 完成 cp 并置 phase=loop（首步 2-start-ci）。"""
        import argparse
        import local_sandbox_fix_harness as harness

        with tempfile.TemporaryDirectory() as plugin_tmp, tempfile.TemporaryDirectory() as work_tmp:
            plugin = Path(plugin_tmp)
            working = Path(work_tmp)
            feature = working / "changes" / "001-f"
            feature.mkdir(parents=True)

            skill_dir = plugin / "skills" / "local-sandbox-fix"
            skill_dir.mkdir(parents=True)
            (skill_dir / "SKILL.md").write_text("---\nname: local-sandbox-fix\n---\n", encoding="utf-8")
            sandboxcheck = plugin / "skills" / "local-sandboxcheck"
            (sandboxcheck / "scripts").mkdir(parents=True)
            (sandboxcheck / "scripts" / "run_local_ci.py").write_text("# stub\n", encoding="utf-8")
            (working / "devops_config.yaml").write_text("repos: []\n", encoding="utf-8")

            class InitArgs:
                plugin_root = str(plugin)
                working_dir = str(working)
                feature_dir = str(feature)
                run_id = "cp-run"

            self.assertEqual(harness.cmd_init(InitArgs), 0)
            harness_dir = feature / ".runs" / "local-sandbox-fix"

            # init 不做 cp；cp 由 gate 0-init 完成
            paths = json.loads((harness_dir / "paths.json").read_text(encoding="utf-8"))
            self.assertFalse(Path(paths["devops_dst"]).exists(), "init 不应 cp")

            gate_ns = argparse.Namespace(
                harness_dir=str(harness_dir),
                working_dir="",
                step="0-init",
                record=True,
            )
            self.assertEqual(harness.cmd_gate(gate_ns), 0)
            self.assertTrue(Path(paths["devops_dst"]).is_file(), "gate 0-init 应完成 cp")

            manifest = json.loads((harness_dir / "run-manifest.json").read_text(encoding="utf-8"))
            self.assertEqual(manifest["phase"], "loop")
            self.assertNotIn("1-prepare-config", manifest["gates"])
            self.assertNotIn("1-prepare-config", harness.GATE_STEPS)
            self.assertEqual(harness.LOOP_STEPS[0], "2-start-ci")


if __name__ == "__main__":
    unittest.main()
