#!/usr/bin/env python3
"""reverse-on-demand harness 单元测试。"""

import json
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import reverse_on_demand_harness as harness  # noqa: E402


class ReverseOnDemandHarnessTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.feature = Path(self.tmp.name) / "changes" / "feat-a"
        self.repo = Path(self.tmp.name)
        self.on_demand = self.feature / "on-demand"
        self.on_demand.mkdir(parents=True)
        (self.repo / "src").mkdir()
        (self.repo / "config").mkdir()

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def _write(self, name: str, data: dict) -> None:
        path = self.on_demand / name
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    @staticmethod
    def _valid_languages() -> list:
        return [
            {
                "name": "Go",
                "role": "primary",
                "coverage_status": "covered",
                "analysis_method": "lsp",
            },
            {
                "name": "Shell",
                "role": "auxiliary",
                "coverage_status": "degraded",
                "analysis_method": "read",
                "degraded_rationale": "运维脚本，无 LSP，按文件读取分析",
                "impact_status": "no_hit",
                "no_impact_rationale": "本需求不涉及部署/运维脚本改动",
            },
        ]

    def _valid_coverage(self) -> dict:
        tops = sorted(harness._repo_top_level_dirs(self.repo))
        return {
            "schema_version": "1",
            "scan_mode": "full_repo",
            "focused_dirs_only": False,
            "full_repo_scan": {
                "tool": "rg",
                "search_root": str(self.repo.resolve()),
                "keywords_used": ["auth"],
                "top_level_entries_scanned": tops,
                "subset_only_dirs": [],
            },
            "narrow_scan_detected": False,
            "languages": self._valid_languages(),
        }

    def _valid_scoped_coverage(self) -> dict:
        scope_path = str((self.repo / "src").resolve())
        return {
            "schema_version": "1",
            "scan_mode": "scoped",
            "focused_dirs_only": True,
            "scope": {
                "include_paths": [scope_path],
                "exclude_globs": ["**/test/**"],
            },
            "scoped_scan": {
                "tool": "rg",
                "search_root": str(self.repo.resolve()),
                "include_paths": [scope_path],
                "exclude_globs": ["**/test/**"],
                "keywords_used": ["auth"],
                "covered_paths": [scope_path],
            },
            "languages": self._valid_languages(),
        }

    def _valid_trace(self) -> dict:
        return {
            "schema_version": "1",
            "min_required_depth": 8,
            "max_depth_cap": 32,
            "premature_stop_count": 0,
            "traces": [
                {
                    "root_symbol": "HandleAuth",
                    "max_depth_achieved": 10,
                    "stopped_reason": "leaf_no_callees",
                    "leaf_evidence": "src/auth.go:42",
                    "hops": [{"file": "src/auth.go", "symbol": "HandleAuth", "depth": 0}],
                }
            ],
        }

    def _valid_static(self) -> dict:
        return {
            "schema_version": "1",
            "config_files": [
                {
                    "file_path": str(self.repo / "config" / "app.yaml"),
                    "parse_status": "parsed",
                    "parse_method": "yaml",
                    "extracted_keys": ["server.port", "auth.enabled"],
                    "structure_summary": "server and auth blocks",
                    "consumer_refs": ["src/main.go:LoadConfig"],
                }
            ],
        }

    def test_gate_passes_with_valid_artifacts(self) -> None:
        self._write("stage2-search-coverage.json", self._valid_coverage())
        self._write("stage2-call-trace.json", self._valid_trace())
        self._write("stage2-static-asset-scan.json", self._valid_static())
        (self.on_demand / "stage2-impact-candidates.json").write_text(
            '{"functions":[]}', encoding="utf-8"
        )
        errors = harness._gate_step_stage2(self.feature, self.repo)
        self.assertEqual(errors, [])

    def test_gate_fails_focused_dirs_only(self) -> None:
        cov = self._valid_coverage()
        cov["focused_dirs_only"] = True
        self._write("stage2-search-coverage.json", cov)
        self._write("stage2-call-trace.json", self._valid_trace())
        self._write("stage2-static-asset-scan.json", self._valid_static())
        (self.on_demand / "stage2-impact-candidates.json").write_text("{}", encoding="utf-8")
        errors = harness._gate_step_stage2(self.feature, self.repo)
        self.assertTrue(any("focused_dirs_only" in e for e in errors))

    def test_gate_passes_scoped_mode(self) -> None:
        self._write("stage2-search-coverage.json", self._valid_scoped_coverage())
        self._write("stage2-call-trace.json", self._valid_trace())
        self._write("stage2-static-asset-scan.json", self._valid_static())
        (self.on_demand / "stage2-impact-candidates.json").write_text("{}", encoding="utf-8")
        scope_paths = [str((self.repo / "src").resolve())]
        errors = harness._gate_step_stage2(
            self.feature, self.repo, scope_paths=scope_paths, exclude_globs=["**/test/**"]
        )
        self.assertEqual(errors, [])

    def test_gate_fails_shallow_call_stop(self) -> None:
        trace = self._valid_trace()
        trace["traces"][0]["max_depth_achieved"] = 2
        trace["traces"][0]["stopped_reason"] = "depth_limit"
        trace["traces"][0]["leaf_evidence"] = ""
        self._write("stage2-search-coverage.json", self._valid_coverage())
        self._write("stage2-call-trace.json", trace)
        self._write("stage2-static-asset-scan.json", self._valid_static())
        (self.on_demand / "stage2-impact-candidates.json").write_text("{}", encoding="utf-8")
        errors = harness._gate_step_stage2(self.feature, self.repo)
        self.assertTrue(any("min_required_depth" in e for e in errors))

    def test_gate_fails_config_listed_only(self) -> None:
        static = self._valid_static()
        static["config_files"][0]["parse_status"] = "listed_only"
        self._write("stage2-search-coverage.json", self._valid_coverage())
        self._write("stage2-call-trace.json", self._valid_trace())
        self._write("stage2-static-asset-scan.json", static)
        (self.on_demand / "stage2-impact-candidates.json").write_text("{}", encoding="utf-8")
        errors = harness._gate_step_stage2(self.feature, self.repo)
        self.assertTrue(any("parse_status" in e for e in errors))

    def test_gate_fails_missing_languages(self) -> None:
        cov = self._valid_coverage()
        cov["languages"] = []
        self._write("stage2-search-coverage.json", cov)
        self._write("stage2-call-trace.json", self._valid_trace())
        self._write("stage2-static-asset-scan.json", self._valid_static())
        (self.on_demand / "stage2-impact-candidates.json").write_text("{}", encoding="utf-8")
        errors = harness._gate_step_stage2(self.feature, self.repo)
        self.assertTrue(any("languages" in e for e in errors))

    def test_gate_fails_auxiliary_bare_uncovered(self) -> None:
        cov = self._valid_coverage()
        # 附属语言裸 uncovered（无 rationale）→ 必须报错
        cov["languages"] = [
            {
                "name": "Go",
                "role": "primary",
                "coverage_status": "covered",
                "analysis_method": "lsp",
            },
            {
                "name": "Lua",
                "role": "auxiliary",
                "coverage_status": "uncovered",
                "analysis_method": "",
            },
        ]
        self._write("stage2-search-coverage.json", cov)
        self._write("stage2-call-trace.json", self._valid_trace())
        self._write("stage2-static-asset-scan.json", self._valid_static())
        (self.on_demand / "stage2-impact-candidates.json").write_text("{}", encoding="utf-8")
        errors = harness._gate_step_stage2(self.feature, self.repo)
        self.assertTrue(any("Lua" in e and "coverage_status" in e for e in errors))

    def test_gate_fails_undeclared_language(self) -> None:
        # 仓库实际含 .lua 文件，但 coverage.languages 未声明 Lua → 必须报错
        (self.repo / "src" / "rule.lua").write_text("-- rule", encoding="utf-8")
        cov = self._valid_coverage()
        cov["languages"] = [
            {
                "name": "Go",
                "role": "primary",
                "coverage_status": "covered",
                "analysis_method": "lsp",
            }
        ]
        self._write("stage2-search-coverage.json", cov)
        self._write("stage2-call-trace.json", self._valid_trace())
        self._write("stage2-static-asset-scan.json", self._valid_static())
        (self.on_demand / "stage2-impact-candidates.json").write_text("{}", encoding="utf-8")
        errors = harness._gate_step_stage2(self.feature, self.repo)
        self.assertTrue(any("Lua" in e and "未在 languages 中声明" in e for e in errors))

    def test_gate_fails_auxiliary_missing_impact_status(self) -> None:
        # 附属语言未声明 impact_status（沉默遗漏）→ 报错
        cov = self._valid_coverage()
        cov["languages"] = [
            {
                "name": "Go",
                "role": "primary",
                "coverage_status": "covered",
                "analysis_method": "lsp",
            },
            {
                "name": "Lua",
                "role": "auxiliary",
                "coverage_status": "covered",
                "analysis_method": "grep",
            },
        ]
        self._write("stage2-search-coverage.json", cov)
        self._write("stage2-call-trace.json", self._valid_trace())
        self._write("stage2-static-asset-scan.json", self._valid_static())
        (self.on_demand / "stage2-impact-candidates.json").write_text("{}", encoding="utf-8")
        errors = harness._gate_step_stage2(self.feature, self.repo)
        self.assertTrue(any("Lua" in e and "impact_status" in e for e in errors))

    def test_gate_fails_impact_hit_but_not_in_list(self) -> None:
        # 声明 impact_status=hit 但波及清单无该语言 → 报错
        cov = self._valid_coverage()
        cov["languages"] = [
            {
                "name": "Go",
                "role": "primary",
                "coverage_status": "covered",
                "analysis_method": "lsp",
            },
            {
                "name": "Lua",
                "role": "auxiliary",
                "coverage_status": "covered",
                "analysis_method": "grep",
                "impact_status": "hit",
            },
        ]
        self._write("stage2-search-coverage.json", cov)
        self._write("stage2-call-trace.json", self._valid_trace())
        self._write("stage2-static-asset-scan.json", self._valid_static())
        # 波及清单只命中 Go，无 Lua
        (self.on_demand / "stage2-impact-candidates.json").write_text(
            json.dumps(
                {
                    "functions": [
                        {"function_key": "f1", "code_file_path": "src/app.go"}
                    ]
                }
            ),
            encoding="utf-8",
        )
        errors = harness._gate_step_stage2(self.feature, self.repo)
        self.assertTrue(any("Lua" in e and "hit" in e for e in errors))

    def test_gate_passes_impact_hit_with_match(self) -> None:
        # 声明 Lua impact_status=hit，波及清单确有 .lua 命中 → 通过
        cov = self._valid_coverage()
        cov["languages"] = [
            {
                "name": "Go",
                "role": "primary",
                "coverage_status": "covered",
                "analysis_method": "lsp",
            },
            {
                "name": "Lua",
                "role": "auxiliary",
                "coverage_status": "covered",
                "analysis_method": "grep",
                "impact_status": "hit",
            },
        ]
        self._write("stage2-search-coverage.json", cov)
        self._write("stage2-call-trace.json", self._valid_trace())
        self._write("stage2-static-asset-scan.json", self._valid_static())
        (self.on_demand / "stage2-impact-candidates.json").write_text(
            json.dumps(
                {
                    "functions": [
                        {"function_key": "f1", "code_file_path": "rules/biz.lua"}
                    ]
                }
            ),
            encoding="utf-8",
        )
        errors = harness._gate_step_stage2(self.feature, self.repo)
        # 排除 Go 主语言相关的顶层目录覆盖错误（src/config 已建），仅校验无 Lua 相关波及错误
        self.assertFalse(any("Lua" in e for e in errors))


if __name__ == "__main__":
    unittest.main()
