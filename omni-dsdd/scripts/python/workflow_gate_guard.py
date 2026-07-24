#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""机械门禁守卫（非 LLM）：检查某阶段的 blocking 分数门禁是否真的通过。

供 workflow-update-state.sh 在 --mark-complete <stage> 前调用，是 LLM 绕不过的 choke point。
日志实拍：orchestrator 跑 check-eval-score.sh 得到 exit 1（score 82<95），却仍自行决定继续进入
clarify。本守卫把"门禁结果"变成 state 推进的硬条件——blocking 阶段无 PASS verdict → 拒绝标记完成。

判定来源（全部脚本化，不依赖 LLM）：
  1. workflows/<flow_mode>.yaml 中该 stage 的 blocking 配置（gate.blocking 或 stage.blocking）
  2. .runs/evaluations/.gate-verdict-<stage>.json（check-eval-score.sh 落盘的判决）

退出码: 0 放行 / 1 拒绝（blocking 门禁未过或未跑）/ 2 参数错误
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, Optional


def _load_yaml(path: Path) -> Optional[Any]:
    try:
        import yaml
    except ImportError:
        return None
    try:
        return yaml.safe_load(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def stage_gate_cfg(workflow_yaml: Path, stage_name: str) -> Optional[Dict[str, Any]]:
    """从工作流 YAML 提取 stage 的门禁配置：blocking / min_score / 是否有 eval。"""
    data = _load_yaml(workflow_yaml)
    if not isinstance(data, dict):
        return None
    stages = data.get("stages")
    if not isinstance(stages, list):
        return None
    for s in stages:
        if not isinstance(s, dict) or s.get("name") != stage_name:
            continue
        gate_raw = s.get("gate")
        gate: dict = gate_raw if isinstance(gate_raw, dict) else {}
        blocking = gate.get("blocking", s.get("blocking"))
        min_score = gate.get("min_score", s.get("min_score"))
        eval_file = gate.get("eval_file", s.get("eval_file"))
        has_eval = bool(eval_file or min_score is not None)
        return {
            "blocking": bool(blocking),
            "min_score": min_score,
            "has_eval": has_eval,
        }
    return None


def read_verdict(feature_dir: Path, stage: str) -> Optional[Dict[str, Any]]:
    p = feature_dir / ".runs" / "evaluations" / f".gate-verdict-{stage}.json"
    if not p.is_file():
        return None
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return None


def main() -> int:
    ap = argparse.ArgumentParser(description="机械门禁守卫：blocking 阶段必须有 PASS verdict 才放行")
    ap.add_argument("--feature-dir", required=True)
    ap.add_argument("--flow-mode", required=True)
    ap.add_argument("--stage", required=True)
    ap.add_argument("--plugin-root", default=None, help="插件根（定位 workflows/，缺省从本脚本反推）")
    args = ap.parse_args()

    plugin_root = Path(args.plugin_root) if args.plugin_root else Path(__file__).resolve().parents[2]
    workflow_yaml = plugin_root / "workflows" / f"{args.flow_mode}.yaml"

    cfg = stage_gate_cfg(workflow_yaml, args.stage)
    if cfg is None:
        # flow 下找不到该 stage / yaml 缺失：保守放行（不误伤未知 stage）
        print(f"[gate-guard] stage '{args.stage}' 不在 {args.flow_mode}.yaml 中，放行")
        return 0
    if not cfg["blocking"]:
        print(f"[gate-guard] stage '{args.stage}' 非阻断（blocking=false），放行")
        return 0

    feature_dir = Path(args.feature_dir)
    verdict = read_verdict(feature_dir, args.stage)
    if verdict is None:
        print(
            f"[gate-guard] BLOCKED: stage '{args.stage}' 为 blocking 分数门禁阶段，"
            f"但未检测到 check-eval-score.sh 的 verdict 标记（.gate-verdict-{args.stage}.json）。"
            f"必须先跑分数门禁且通过，才允许标记完成。",
            file=sys.stderr,
        )
        return 1
    # 来源签名校验：只信任 check-eval-score 产出的 verdict，拒绝 LLM 手写/伪造（P1a）
    if verdict.get("source") != "check-eval-score":
        print(
            f"[gate-guard] BLOCKED: stage '{args.stage}' verdict 来源非法 "
            f"(source={verdict.get('source')!r})，必须由 check-eval-score.sh 产出，"
            f"禁止手写/伪造 verdict 标记。",
            file=sys.stderr,
        )
        return 1
    if not verdict.get("passed"):
        print(
            f"[gate-guard] BLOCKED: stage '{args.stage}' 分数门禁未通过 "
            f"(score={verdict.get('score')} min={verdict.get('min_score')} "
            f"status={verdict.get('status')})。禁止标记完成 / 推进下一阶段。",
            file=sys.stderr,
        )
        return 1

    print(f"[gate-guard] stage '{args.stage}' 门禁已通过 (score={verdict.get('score')})，放行")
    return 0


if __name__ == "__main__":
    sys.exit(main())
