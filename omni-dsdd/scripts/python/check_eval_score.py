#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""分数门禁（确定性）：读取阶段 eval 文件，比对 min_score，不达标即 exit 1。

替代原先「orchestrator LLM 自己读 eval 判断 score>=95」的软约束（日志实拍：
specify 91/100、design 80.4/100 均低于阈值却因 `gate exit 0` 被放行）。

支持格式（自动探测，可用 --format 覆盖）：
  - JSON : 取 summary.total_score / summary.overall_score / 顶层 score
  - YAML : 取 overall_score / total_score / score（兼容嵌套 stage 块）
  - MD   : 正则提取 `overall_score**:` 等模式

退出码：
  0  通过（score >= min_score 且 status 非 fail）
  1  未通过（score < min_score 或 status == fail）
  2  参数错误 / eval 文件缺失或无法解析
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

FAIL_STATUSES = {"fail", "failed", "error", "blocked", "block"}
# warning 不算 fail（与 eval 三档 pass/warning/fail 语义一致），但仍受 min_score 约束。

Verdict = Dict[str, Any]


def _try_json(text: str) -> Optional[dict]:
    try:
        return json.loads(text)
    except (json.JSONDecodeError, ValueError):
        return None


def _extract_from_json(data: object) -> Tuple[Optional[float], Optional[str]]:
    """从 JSON 提取 (score, status)。

    支持两代 design/specify eval 格式：
      - 新（当前 eval-design）: {"meta":{}, "scores":{<dim>:{"score":..}, "total":85, "max_total":100}, "badcases":[...]}
      - 老（v3.1.0）: {"summary":{"total_score":80.4, "pass":true, ...}} 或顶层 overall_score
    总分优先取 scores.total；不取裸 "score"（design eval 里 scores.<dim>.score 是维度分，非总分）。
    """
    if not isinstance(data, dict):
        return None, None
    summary_raw = data.get("summary")
    summary: dict = summary_raw if isinstance(summary_raw, dict) else {}
    scores_raw = data.get("scores")  # 新格式：各维度分 + total
    scores: dict = scores_raw if isinstance(scores_raw, dict) else {}

    # 优先级：scores.total(新 design 总分) > overall_score > total_score
    # 注意：不取裸 "score"（避免误取 scores.<dim>.score 维度分）
    candidates = [
        scores.get("total"),
        data.get("overall_score"),
        summary.get("overall_score"),
        data.get("total_score"),
        summary.get("total_score"),
    ]
    score = None
    for c in candidates:
        if isinstance(c, (int, float)) and not isinstance(c, bool):
            score = float(c)
            break

    # status：新格式用 validation_status / 老 summary.pass
    status = (
        summary.get("status")
        or summary.get("verdict")
        or data.get("validation_status")
        or data.get("status")
        or data.get("verdict")
    )
    pass_val = summary.get("pass")
    if isinstance(pass_val, bool):
        status = "pass" if pass_val else "fail"
    return score, (str(status) if status is not None else None)


def _extract_from_text(text: str) -> Tuple[Optional[float], Optional[str]]:
    """YAML / Markdown 通用正则提取（兜底，JSON 通常不走这里）。

    只认总分键（overall_score / total_score / "total"），跳过维度分 scores.<dim>.score，
    避免把维度分当成总分。取所有命中的最大值（保守）。
    """
    score_pat = re.compile(
        r'(?:overall_score|total_score|"total"|^\s*total\s*:)\s*[:=]?\s*\**\s*([0-9]+(?:\.[0-9]+)?)',
        re.IGNORECASE | re.MULTILINE,
    )
    status_pat = re.compile(r"status\s*[:=]\s*\*?\*?\"?(\w+)\"?", re.IGNORECASE)

    nums = [float(m.group(1)) for m in score_pat.finditer(text)]
    # 区分百分制（>1，如 91、80.4）与小数制（<=1，如 0.91）
    score = max(nums) if nums else None

    statuses = [m.group(1).lower() for m in status_pat.finditer(text)]
    status = statuses[-1] if statuses else None  # 取最后一个 status（通常为总评）
    return score, status


def _normalize_score(score: Optional[float]) -> Optional[float]:
    """小数制（<=1，如 0.95）归一到百分制。"""
    if score is None:
        return None
    return score * 100.0 if score <= 1.0 else score


def evaluate(eval_path: Path, min_score: float, fmt: Optional[str]) -> "Verdict":
    """返回结构化判决 dict（含 passed/score/status/verdict 文本）。"""
    if not eval_path.is_file():
        return {
            "passed": False,
            "score": None,
            "min_score": min_score,
            "status": None,
            "verdict": f"EVAL_FILE_NOT_FOUND: {eval_path}",
            "error": "EVAL_FILE_NOT_FOUND",
        }

    text = eval_path.read_text(encoding="utf-8", errors="replace")
    score: Optional[float] = None
    status: Optional[str] = None

    use_json = (fmt == "json") or (fmt is None and text.lstrip().startswith(("{", "[")))
    if use_json:
        data = _try_json(text)
        if isinstance(data, dict):
            score, status = _extract_from_json(data)

    if score is None:  # YAML / MD / JSON 兜底
        score, status = _extract_from_text(text)

    score = _normalize_score(score)
    if score is None:
        return {
            "passed": False,
            "score": None,
            "min_score": min_score,
            "status": status,
            "verdict": f"SCORE_NOT_PARSEABLE: {eval_path}",
            "error": "SCORE_NOT_PARSEABLE",
        }

    passed = score >= min_score and (status not in FAIL_STATUSES if status else True)
    verdict = (
        f"score={score:g} min={min_score:g} status={status or 'n/a'} -> "
        f"{'PASS' if passed else 'FAIL'}"
    )
    return {
        "passed": passed,
        "score": score,
        "min_score": min_score,
        "status": status,
        "verdict": verdict,
        "error": None,
    }


def write_verdict_marker(feature_dir: Path, stage: str, result: "Verdict") -> Path:
    """落盘门禁判决标记，供 workflow-update-state 守卫 / workflow-converge 读取（机械强制依据）。"""
    verdict_dir = feature_dir / ".runs" / "evaluations"
    verdict_dir.mkdir(parents=True, exist_ok=True)
    # 单调递增 seq：每次写 verdict 自增，供 converge 区分"是否新一次门禁"（避免秒级时间戳同秒误判）
    seq_file = verdict_dir / f".seq-{stage}"
    seq = 0
    try:
        seq = int(seq_file.read_text(encoding="utf-8").strip()) + 1
    except (FileNotFoundError, ValueError):
        seq = 1
    seq_file.write_text(str(seq), encoding="utf-8")
    marker = verdict_dir / f".gate-verdict-{stage}.json"
    payload = {
        "stage": stage,
        "seq": seq,
        "passed": bool(result["passed"]),
        "score": result["score"],
        "min_score": result["min_score"],
        "status": result["status"],
        "verdict": result["verdict"],
        "error": result["error"],
        # 来源签名：守卫只信任由 check-eval-score 产出的 verdict，拒绝 LLM 手写/伪造
        "source": "check-eval-score",
        "written_by": "check_eval_score.py",
        "checked_at": _utc_now(),
    }
    marker.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return marker


def _utc_now() -> str:
    from datetime import datetime, timezone

    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _derive_from_eval_file(eval_file: Path) -> Tuple[Optional[Path], Optional[str]]:
    """从 eval 文件路径反推 (feature_dir, stage)。

    eval 文件位于 <feature_dir>/.runs/evaluations/eval-<stage>-*.{yaml,json/md}，
    故 feature_dir = dirname(eval_file)/../.. ；stage 由文件名前缀解析。
    用于 --eval-file 模式下也能落 verdict 标记（修 wsm-8 verdict 不生成问题）。
    """
    eval_file = eval_file.resolve()
    evaluations_dir = eval_file.parent
    runs_dir = evaluations_dir.parent
    feature_dir = runs_dir.parent if runs_dir.name == ".runs" else None
    name = eval_file.name.lower()
    stage = None
    if name.startswith("eval-specify"):
        stage = "specify"
    elif name.startswith("eval-clarify"):
        stage = "clarify"
    elif name.startswith("eval-design"):
        stage = "design"
    return feature_dir, stage


def main() -> int:
    ap = argparse.ArgumentParser(description="阶段 eval 分数门禁（确定性）")
    ap.add_argument("--eval-file", required=True, help="eval 文件路径")
    ap.add_argument("--min-score", type=float, default=95.0, help="阈值（默认 95）")
    ap.add_argument("--format", choices=["json", "yaml", "md"], default=None, help="强制格式")
    ap.add_argument("--feature-dir", default=None, help="特性目录（提供则落 verdict 标记）")
    ap.add_argument("--stage", default=None, help="阶段名（提供则落 verdict 标记）")
    args = ap.parse_args()

    eval_path = Path(args.eval_file)
    result = evaluate(eval_path, args.min_score, args.format)
    print(f"[check-eval-score] {result['verdict']}")

    # feature_dir / stage 缺省时从 eval 文件路径反推，保证 verdict 必然落盘（P2）
    feature_dir = args.feature_dir
    stage = args.stage
    if (not feature_dir or not stage) and eval_path.is_file():
        d_feat, d_stage = _derive_from_eval_file(eval_path)
        if not feature_dir:
            feature_dir = str(d_feat) if d_feat else None
        if not stage:
            stage = d_stage

    if feature_dir and stage:
        marker = write_verdict_marker(Path(feature_dir), stage, result)
        print(f"[check-eval-score] verdict 标记: {marker} (passed={result['passed']})")

    return 0 if result["passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
