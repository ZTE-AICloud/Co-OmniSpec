#!/usr/bin/env python3
"""tasks 阶段 Harness: 任务生成、上下文收集、需求/场景生成、质量验证"""

import argparse
import importlib.util
import json
import re
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

_SCRIPT_DIR = Path(__file__).resolve().parent
if str(_SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPT_DIR))

_OMNI_STATE = None
MIN_BYTES_DEFAULT = 64

# Tasks 阶段必需的产物
ARTIFACTS_REQUIRED = [
    "tasks.md",
    "spec.md",
    "design.md",
    "context.md",
    ".runs/tasks-run.json",
]

STEP_ARTIFACT = {
    "init": "tasks.md",
    "context": "context.md",
    "requirements": "requirements-content.md",
    "scenarios": "scenarios-content.md",
    "quality": ".runs/tasks-run.json",
}

RESUME_STEPS = ("init", "context", "requirements", "scenarios", "quality")


class FeatureContext:
    """功能目录上下文管理"""

    def __init__(self, feature_dir: Path, branch_name: str = ""):
        self.feature_dir = feature_dir
        self.branch_name = branch_name
        self.spec_file = feature_dir / "spec.md"
        self.design_file = feature_dir / "design.md"
        self.tasks_file = feature_dir / "tasks.md"
        self.context_file = feature_dir / "context.md"
        self.data_model_file = feature_dir / "data-model.md"
        self.contracts_dir = feature_dir / "contracts"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "feature_dir": str(self.feature_dir),
            "branch_name": self.branch_name,
            "spec_file": str(self.spec_file),
            "design_file": str(self.design_file),
            "tasks_file": str(self.tasks_file),
            "context_file": str(self.context_file),
        }


class ContextCollector:
    """上下文收集器 - 扫描和分析相关文档"""

    def __init__(self, context: FeatureContext, doc_dir: Optional[Path] = None):
        self.context = context
        self.doc_dir = doc_dir

    def collect(self) -> Dict[str, Any]:
        """收集上下文信息"""
        result = {
            "feature_dir": str(self.context.feature_dir),
            "branch_name": self.context.branch_name,
            "related_docs": [],
            "context_mode": "default",
        }

        # 扫描 doc_specs 目录
        if self.doc_dir and self.doc_dir.exists():
            specs_dir = self.doc_dir / "specs"
            if specs_dir.exists():
                for spec_file in specs_dir.glob("*.md"):
                    # 分析文档关联度
                    related = self._analyze_relationship(spec_file)
                    if related:
                        result["related_docs"].append(related)

        return result

    def _analyze_relationship(self, doc_path: Path) -> Optional[Dict[str, Any]]:
        """分析文档与当前业务的关联度"""
        try:
            content = doc_path.read_text(encoding="utf-8")
            # 简单关键词匹配
            score = 0
            keywords = self._extract_keywords()
            for kw in keywords:
                if kw.lower() in content.lower():
                    score += 1

            if score > 0:
                return {
                    "path": str(doc_path),
                    "score": score,
                    "relevance": "high" if score >= 3 else "medium",
                }
        except Exception:
            pass
        return None

    def _extract_keywords(self) -> List[str]:
        """从规范文件中提取关键词"""
        keywords = []
        if self.context.spec_file.exists():
            content = self.context.spec_file.read_text(encoding="utf-8")
            # 提取标题中的关键词
            for match in re.finditer(r"##?\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+){0,2})", content):
                keywords.append(match.group(1))
        return keywords[:10]  # 限制数量


class SpecGenerator:
    """规范生成器 - 生成 EARS 格式需求和 Given/When/Then 场景"""

    def __init__(self, context: FeatureContext):
        self.context = context
        self.generated_ids: Set[str] = set()

    def generate_requirements(self, context_data: Dict[str, Any]) -> List[str]:
        """生成 EARS 格式需求"""
        requirements = []

        # 解析场景
        scenarios = self._parse_scenarios()

        for i, scenario in enumerate(scenarios, start=1):
            req_id = f"REQ-{i:03d}"
            if req_id in self.generated_ids:
                continue
            self.generated_ids.add(req_id)

            # 生成 EARS 格式需求
            requirement = f"""### [动作类型:INSERT] - {req_id} - {scenario.get('title', '需求')}

变更原因: {scenario.get('description', '用户需要此功能')}

{scenario.get('ears_format', '''
When 用户执行操作时，系统 shall 执行预期行为。
''')}"""
            requirements.append(requirement)

        return requirements

    def generate_scenarios(self, requirements: List[str]) -> List[str]:
        """生成 Given/When/Then 格式场景"""
        scenarios = []

        # 从规范中解析需求 ID
        for req in requirements:
            req_match = re.search(r'REQ-\d{3}', req)
            if req_match:
                req_id = req_match.group(0)
                scenario_id = f"SCN-{req_id.split('-')[1]}"

                scenario = f"""### [动作类型:INSERT] - {scenario_id} - 场景描述 (优先级: P2)

归属的需求: {req_id}

场景描述: TBD（基于 {req_id} 的验收场景）

**验收场景**:

1. **Given** 初始条件，**When** 触发动作，**Then** 预期结果
"""
                scenarios.append(scenario)

        return scenarios

    def _parse_scenarios(self) -> List[Dict[str, str]]:
        """从 spec.md 中解析场景列表"""
        scenarios = []
        if not self.context.spec_file.exists():
            return scenarios

        content = self.context.spec_file.read_text(encoding="utf-8")

        # 解析 SCN-xxx 场景
        pattern = r'### \[动作类型:INSERT\] - (SCN-\d{3}).*?\n.*?\n场景描述: (.+?)(?=\n###|\Z)'
        for match in re.finditer(pattern, content, re.DOTALL):
            scenarios.append({
                "id": match.group(1),
                "title": match.group(2).strip()[:50],
                "description": match.group(2).strip(),
            })

        return scenarios


class QualityValidator:
    """质量验证器 - 验证规范质量"""

    REQUIRED_SECTIONS = [
        "## 功能描述",
        "## 关键实体",
        "## 成功标准",
        "## 需求",
        "## 场景",
    ]

    def __init__(self, context: FeatureContext):
        self.context = context

    def validate_spec_quality(self) -> Dict[str, Any]:
        """验证规范质量"""
        result = {
            "validation_status": "pass",
            "blocking_issues": [],
            "eval_score": 1.0,
        }

        if not self.context.spec_file.exists():
            result["validation_status"] = "fail"
            result["blocking_issues"].append("spec.md 文件不存在")
            result["eval_score"] = 0.0
            return result

        content = self.context.spec_file.read_text(encoding="utf-8")

        # 检查必需章节
        for section in self.REQUIRED_SECTIONS:
            if section not in content:
                result["blocking_issues"].append(f"缺少必需章节: {section}")
                result["validation_status"] = "warning"

        # 验证需求格式
        ears_issues = self.check_ears_format(content)
        if ears_issues:
            result["blocking_issues"].extend(ears_issues)

        # 计算评分
        if result["blocking_issues"]:
            result["eval_score"] = max(0.0, 1.0 - len(result["blocking_issues"]) * 0.1)
            if result["validation_status"] == "fail":
                result["eval_score"] = 0.0

        return result

    def check_ears_format(self, content: str) -> List[str]:
        """验证 EARS 格式需求"""
        issues = []

        # 查找需求条目
        req_pattern = r'### \[动作类型:INSERT\] - (REQ-\d{3}|SCN-\d{3})'
        if not re.search(req_pattern, content):
            issues.append("未发现需求或场景 ID 格式")

        # 检查 EARS 关键词
        ears_keywords = ["shall", "should", "When", "Where", "If"]
        found = sum(1 for kw in ears_keywords if kw in content)
        if found < 2:
            issues.append("EARS 格式关键词不足")

        return issues


class GateManager:
    """门禁管理器 - 执行分步门禁"""

    def __init__(self, context: FeatureContext):
        self.context = context

    def check_gate(self, step: str, min_bytes: int = MIN_BYTES_DEFAULT) -> List[str]:
        """执行门禁检查"""
        errors = []

        if step == "init" or step == "all":
            errors.extend(self._gate_init(min_bytes))
        if step == "context" or step == "all":
            errors.extend(self._gate_context(min_bytes))
        if step == "requirements" or step == "all":
            errors.extend(self._gate_requirements(min_bytes))
        if step == "scenarios" or step == "all":
            errors.extend(self._gate_scenarios(min_bytes))
        if step == "quality" or step == "all":
            errors.extend(self._gate_quality(min_bytes))

        return errors

    def _gate_init(self, min_bytes: int) -> List[str]:
        """初始化门禁"""
        errors = []

        # 检查 tasks.md
        if not self.context.tasks_file.exists():
            errors.append("tasks.md: missing")
        elif self.context.tasks_file.stat().st_size < min_bytes:
            errors.append(f"tasks.md: too_small ({self.context.tasks_file.stat().st_size} < {min_bytes})")

        # 检查 paths.json
        paths_file = self.context.feature_dir / ".runs/paths.json"
        if not paths_file.exists():
            errors.append(".runs/paths.json: missing")

        return errors

    def _gate_context(self, min_bytes: int) -> List[str]:
        """上下文收集门禁"""
        errors = []

        if not self.context.context_file.exists():
            errors.append("context.md: missing")
        elif self.context.context_file.stat().st_size < min_bytes:
            errors.append(f"context.md: too_small")

        return errors

    def _gate_requirements(self, min_bytes: int) -> List[str]:
        """需求生成门禁"""
        errors = []

        req_file = self.context.feature_dir / "requirements-content.md"
        if not req_file.exists():
            errors.append("requirements-content.md: missing")

        return errors

    def _gate_scenarios(self, min_bytes: int) -> List[str]:
        """场景生成门禁"""
        errors = []

        scn_file = self.context.feature_dir / "scenarios-content.md"
        if not scn_file.exists():
            errors.append("scenarios-content.md: missing")

        return errors

    def _gate_quality(self, min_bytes: int) -> List[str]:
        """质量验证门禁"""
        errors = []

        # 检查规范质量
        validator = QualityValidator(self.context)
        result = validator.validate_spec_quality()

        if result["validation_status"] == "fail":
            errors.extend(result["blocking_issues"])

        return errors


class TaskOrchestrator:
    """流程编排器 - 协调全流程"""

    def __init__(self, context: FeatureContext, plugin_root: Path, working_dir: Path, doc_dir: Optional[Path] = None):
        self.context = context
        self.plugin_root = plugin_root
        self.working_dir = working_dir
        self.doc_dir = doc_dir

    def run(self) -> Dict[str, Any]:
        """执行任务生成流程"""
        result = {
            "status": "ok",
            "completed_stages": [],
            "feature_dir": str(self.context.feature_dir),
        }

        # 1. 收集上下文
        collector = ContextCollector(self.context, self.doc_dir)
        context_data = collector.collect()
        result["completed_stages"].append("context_collection")

        # 2. 生成需求
        generator = SpecGenerator(self.context)
        requirements = generator.generate_requirements(context_data)
        result["completed_stages"].append("requirements_generation")

        # 3. 生成场景
        scenarios = generator.generate_scenarios(requirements)
        result["completed_stages"].append("scenarios_generation")

        return result


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, data: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _file_ok(path: Path, min_bytes: int) -> tuple:
    if not path.is_file():
        return False, "missing"
    size = path.stat().st_size
    if size < min_bytes:
        return False, f"too_small ({size} < {min_bytes})"
    return True, f"{size} bytes"


def _load_run(feature_dir: Path) -> Dict[str, Any]:
    run_path = feature_dir / ".runs/tasks-run.json"
    if run_path.is_file():
        return _read_json(run_path)
    return {
        "run_id": str(uuid.uuid4()),
        "stage": "tasks",
        "started_at": _utc_now(),
        "last_updated": _utc_now(),
        "steps": {},
        "artifacts_required": ARTIFACTS_REQUIRED,
    }


def _save_run(feature_dir: Path, run: Dict[str, Any]) -> None:
    run["last_updated"] = _utc_now()
    _write_json(feature_dir / ".runs/tasks-run.json", run)


def cmd_gate(args: argparse.Namespace) -> int:
    """门禁命令"""
    feature_dir = Path(args.feature_dir).resolve()
    context = FeatureContext(feature_dir)
    gate_manager = GateManager(context)

    errors = gate_manager.check_gate(args.step, args.min_bytes)

    result = {
        "feature_dir": str(feature_dir),
        "step": args.step,
        "gate_exit": 0 if not errors else 1,
        "errors": errors,
        "artifact": STEP_ARTIFACT.get(args.step, "multiple") if args.step != "all" else "all",
    }

    print(json.dumps(result, ensure_ascii=False, indent=2))

    if args.record and args.step != "all":
        run = _load_run(feature_dir)
        run["steps"][args.step] = {
            "status": "passed" if not errors else "failed",
            "gate_exit": result["gate_exit"],
            "artifact": STEP_ARTIFACT.get(args.step, ""),
            "retries": args.retries,
            "notes": "; ".join(errors) if errors else "ok",
            "updated_at": _utc_now(),
        }
        _save_run(feature_dir, run)

    return result["gate_exit"]


def cmd_record(args: argparse.Namespace) -> int:
    """记录命令"""
    feature_dir = Path(args.feature_dir).resolve()
    run = _load_run(feature_dir)
    step = str(args.step)

    run["steps"][step] = {
        "status": args.status,
        "gate_exit": args.gate_exit,
        "artifact": STEP_ARTIFACT.get(step, ""),
        "retries": args.retries,
        "notes": args.notes or "",
        "updated_at": _utc_now(),
    }
    _save_run(feature_dir, run)
    return 0


def cmd_resume(args: argparse.Namespace) -> int:
    """断点续跑命令"""
    feature_dir = Path(args.feature_dir).resolve()
    run = _load_run(feature_dir)

    pending = []
    for step in RESUME_STEPS:
        info = run.get("steps", {}).get(step, {})
        if info.get("status") != "passed" or info.get("gate_exit", 1) != 0:
            pending.append(step)

    print(json.dumps({"pending_steps": pending, "run_id": run.get("run_id")}, ensure_ascii=False))
    return 0


def cmd_init(args: argparse.Namespace) -> int:
    """初始化命令"""
    feature_dir = Path(args.feature_dir).resolve()
    working_dir = Path(args.working_dir)
    plugin_root = Path(args.plugin_root)

    # 确保目录存在
    feature_dir.mkdir(parents=True, exist_ok=True)
    for sub in ("contracts", ".runs/evaluations", ".runs/metrics", ".runs/internal", "checklists"):
        (feature_dir / sub).mkdir(parents=True, exist_ok=True)

    # 写入路径配置
    paths = {
        "branch_name": args.branch_name or "",
        "feature_dir": str(feature_dir),
        "spec_file": str(feature_dir / "spec.md"),
        "design_file": str(feature_dir / "design.md"),
        "tasks_file": str(feature_dir / "tasks.md"),
        "working_dir": str(working_dir),
        "plugin_root": str(plugin_root),
        "repo_root": str(working_dir),
        "start_time": args.start_time or "",
        "enable_e2e": bool(args.enable_e2e),
        "initialized_at": _utc_now(),
    }
    _write_json(feature_dir / ".runs/paths.json", paths)

    # 初始化运行状态
    run = _load_run(feature_dir)
    run["run_id"] = args.run_id or run.get("run_id") or str(uuid.uuid4())
    run["started_at"] = _utc_now()
    _save_run(feature_dir, run)

    print(json.dumps({"status": "ok", "paths": str(feature_dir / ".runs/paths.json")}, ensure_ascii=False))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="tasks harness")
    sub = parser.add_subparsers(dest="command")

    p_gate = sub.add_parser("gate", help="分步或全量结构门禁")
    p_gate.add_argument("--feature-dir", required=True)
    p_gate.add_argument("--step", required=True, choices=["init", "context", "requirements", "scenarios", "quality", "all"])
    p_gate.add_argument("--min-bytes", type=int, default=MIN_BYTES_DEFAULT)
    p_gate.add_argument("--record", action="store_true")
    p_gate.add_argument("--retries", type=int, default=0)
    p_gate.add_argument("--enable-e2e", action="store_true")
    p_gate.add_argument("--json", action="store_true")

    p_rec = sub.add_parser("record", help="手动记录步骤状态")
    p_rec.add_argument("--feature-dir", required=True)
    p_rec.add_argument("--step", required=True)
    p_rec.add_argument("--status", required=True, choices=["passed", "failed", "skipped"])
    p_rec.add_argument("--gate-exit", type=int, required=True)
    p_rec.add_argument("--retries", type=int, default=0)
    p_rec.add_argument("--notes", default="")

    p_res = sub.add_parser("resume", help="查询待重跑步骤")
    p_res.add_argument("--feature-dir", required=True)

    p_init = sub.add_parser("init", help="初始化 harness 目录")
    p_init.add_argument("--plugin-root", required=True)
    p_init.add_argument("--working-dir", required=True)
    p_init.add_argument("--feature-dir", required=True)
    p_init.add_argument("--branch-name", default="")
    p_init.add_argument("--start-time", default="")
    p_init.add_argument("--run-id", default="")
    p_init.add_argument("--enable-e2e", action="store_true")

    args = parser.parse_args()
    if not getattr(args, "command", None):
        parser.error("command is required")

    handlers = {
        "gate": cmd_gate,
        "record": cmd_record,
        "resume": cmd_resume,
        "init": cmd_init,
    }

    return handlers[args.command](args)


if __name__ == "__main__":
    sys.exit(main())