#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""机械重试控制器（非 LLM）：按 max_retries 确定性判定"通过/重试/耗尽"。

消除 LLM 对"何时停止重试"的自由裁量（日志实拍：LLM 在第 2 次就放弃，未到 max_retries）。
本脚本读 verdict 标记 + 重试计数，机械输出指令；编排器只能执行，不得自行决定停止。

退出码（编排器据此时机械行事）:
  0  CONVERGED  verdict PASS → 可 mark-complete 推进下一阶段
  1  RETRY      FAIL 且 attempts < max → 必须再次增量派发该阶段，禁止停止
  2  EXHAUSTED  FAIL 且 attempts >= max → 已达上限，停止报告（不推进）
  3  NO_VERDICT 未跑 check-eval-score → 先跑门禁再调本脚本
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


def stage_max_retries(plugin_root: Path, flow_mode: str, stage_name: str, default: int = 5) -> int:
    """从 YAML 读 stage.auto_converge.max_retries，缺失回退 default。"""
    yml = plugin_root / "workflows" / f"{flow_mode}.yaml"
    data = _load_yaml(yml)
    if not isinstance(data, dict):
        return default
    stages = data.get("stages")
    if not isinstance(stages, list):
        return default
    for s in stages:
        if isinstance(s, dict) and s.get("name") == stage_name:
            ac = s.get("auto_converge")
            if isinstance(ac, dict):
                mr = ac.get("max_retries")
                if isinstance(mr, int) and mr > 0:
                    return mr
            break
    return default


def read_verdict(feature_dir: Path, stage: str) -> Optional[Dict[str, Any]]:
    p = feature_dir / ".runs" / "evaluations" / f".gate-verdict-{stage}.json"
    if not p.is_file():
        return None
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return None


def read_counter(feature_dir: Path, stage: str) -> Dict[str, Any]:
    p = feature_dir / ".runs" / f".converge-{stage}.json"
    if not p.is_file():
        return {"attempts": 0, "last_verdict_seq": None}
    try:
        d = json.loads(p.read_text(encoding="utf-8"))
        if isinstance(d, dict):
            return d
    except Exception:
        pass
    return {"attempts": 0, "last_verdict_seq": None}


def write_counter(feature_dir: Path, stage: str, data: Dict[str, Any]) -> None:
    p = feature_dir / ".runs" / f".converge-{stage}.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser(description="机械重试控制器：按 max_retries 判定 通过/重试/耗尽")
    ap.add_argument("--feature-dir", required=True)
    ap.add_argument("--flow-mode", required=True)
    ap.add_argument("--stage", required=True)
    ap.add_argument("--plugin-root", default=None)
    ap.add_argument("--reset", action="store_true", help="重置该阶段重试计数（阶段全新开始时用）")
    args = ap.parse_args()

    plugin_root = Path(args.plugin_root) if args.plugin_root else Path(__file__).resolve().parents[2]
    feature_dir = Path(args.feature_dir)

    if args.reset:
        write_counter(feature_dir, args.stage, {"attempts": 0, "last_verdict_seq": None})
        print(f"[converge] {args.stage}: 重试计数已重置")
        return 0

    max_retries = stage_max_retries(plugin_root, args.flow_mode, args.stage)
    verdict = read_verdict(feature_dir, args.stage)
    counter = read_counter(feature_dir, args.stage)

    if verdict is None:
        print(f"[converge] {args.stage}: NO_VERDICT —— 先跑 check-eval-score.sh 再调本脚本")
        return 3

    score = verdict.get("score")
    v_seq = verdict.get("seq")

    if verdict.get("passed"):
        # 收敛：复位计数，允许推进
        write_counter(feature_dir, args.stage, {"attempts": 0, "last_verdict_seq": v_seq, "converged": True})
        print(f"[converge] {args.stage}: CONVERGED (score={score} ≥ 阈值) → 可 mark-complete 推进")
        return 0

    # FAIL：仅当来了新 verdict（新一次派发+门禁，seq 不同）才计数，避免重复调用虚增
    if v_seq is not None and v_seq == counter.get("last_verdict_seq"):
        attempts = int(counter.get("attempts", 0))
    else:
        attempts = int(counter.get("attempts", 0)) + 1
        write_counter(feature_dir, args.stage, {"attempts": attempts, "last_verdict_seq": v_seq})

    if attempts < max_retries:
        print(
            f"[converge] {args.stage}: RETRY {attempts}/{max_retries} "
            f"(score={score} 未达标) → 必须再次增量派发该阶段（注入 eval 修复点，Edit 现有制品），"
            f"重跑 check-eval-score.sh 后再调本脚本。禁止停止、禁止 mark-complete。"
        )
        return 1

    print(
        f"[converge] {args.stage}: EXHAUSTED {attempts}/{max_retries} "
        f"(score={score} 仍未达标) → 已达重试上限，停止报告，不推进下一阶段。"
    )
    return 2


if __name__ == "__main__":
    sys.exit(main())
