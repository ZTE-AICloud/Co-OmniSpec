#!/usr/bin/env python3
"""
根据执行模式从 metric-registry.json 解析待执行 skill 列表。
输出 state/resolved-skills.json。

支持四种模式：
  default   - 无参数，执行 tags 包含 "default" 且 enabled: true 的 skill
  all       - --all，执行所有 enabled: true 的 skill
  dimension - --dimension <名称>，执行指定维度下所有 enabled: true 的 skill
  skills    - --skills <id,...>，执行指定 skill（忽略 enabled 状态，强制执行）
"""
import argparse
import json
import sys
from pathlib import Path


def load_registry(registry_path: str) -> dict:
    path = Path(registry_path)
    if not path.exists():
        print(f"[error] registry not found: {registry_path}", file=sys.stderr)
        sys.exit(1)
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def resolve_default(metrics: list):
    resolved, skipped = [], []
    for m in metrics:
        if m.get("enabled", False) and "default" in m.get("tags", []):
            resolved.append(m)
        else:
            reason = "enabled: false" if not m.get("enabled", False) else "not in default tags"
            skipped.append({"skill_id": m["skill_id"], "reason": reason})
    return resolved, skipped


def resolve_all(metrics: list):
    resolved, skipped = [], []
    for m in metrics:
        if m.get("enabled", False):
            resolved.append(m)
        else:
            skipped.append({"skill_id": m["skill_id"], "reason": "enabled: false"})
    return resolved, skipped


def resolve_dimension(metrics: list, dimension: str, valid_dimensions: list):
    if dimension not in valid_dimensions:
        print(
            f"[error] unknown dimension: '{dimension}'. "
            f"Valid values: {valid_dimensions}",
            file=sys.stderr,
        )
        sys.exit(1)
    resolved, skipped = [], []
    for m in metrics:
        if m.get("dimension") != dimension:
            skipped.append({"skill_id": m["skill_id"], "reason": f"dimension != {dimension}"})
        elif not m.get("enabled", False):
            skipped.append({"skill_id": m["skill_id"], "reason": "enabled: false"})
        else:
            resolved.append(m)
    return resolved, skipped


def resolve_skills_by_id(metrics: list, skill_ids: list):
    index = {m["skill_id"]: m for m in metrics}
    resolved, skipped = [], []
    for sid in skill_ids:
        if sid in index:
            resolved.append(index[sid])
        else:
            skipped.append({"skill_id": sid, "reason": "not found in registry"})
    # remaining metrics not requested
    requested = set(skill_ids)
    for m in metrics:
        if m["skill_id"] not in requested:
            skipped.append({"skill_id": m["skill_id"], "reason": "not in --skills list"})
    return resolved, skipped


def build_resolved_entry(m: dict) -> dict:
    return {
        "skill_id": m["skill_id"],
        "display_name": m.get("display_name", ""),
        "dimension": m.get("dimension", ""),
        "output_path_hint": m.get("output_path_hint", ""),
    }


def main():
    parser = argparse.ArgumentParser(description="Resolve skills from metric registry")
    parser.add_argument("--registry", default="config/metric-registry.json", help="Path to metric-registry.json")
    parser.add_argument("--output", default="state/resolved-skills.json", help="Output path for resolved-skills.json")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--all", dest="all_mode", action="store_true", help="Execute all enabled skills")
    group.add_argument("--dimension", dest="dimension", help="Execute skills in the specified dimension")
    group.add_argument("--skills", dest="skills", help="Comma-separated skill IDs to execute (ignores enabled)")
    args = parser.parse_args()

    registry = load_registry(args.registry)
    metrics = registry.get("metrics", [])
    valid_dimensions = registry.get("dimensions", [])

    if args.all_mode:
        execute_mode = "all"
        resolved_raw, skipped = resolve_all(metrics)
    elif args.dimension:
        execute_mode = "dimension"
        resolved_raw, skipped = resolve_dimension(metrics, args.dimension, valid_dimensions)
    elif args.skills:
        execute_mode = "skills"
        skill_ids = [s.strip() for s in args.skills.split(",") if s.strip()]
        resolved_raw, skipped = resolve_skills_by_id(metrics, skill_ids)
    else:
        execute_mode = "default"
        resolved_raw, skipped = resolve_default(metrics)

    resolved = [build_resolved_entry(m) for m in resolved_raw]

    result = {
        "execute_mode": execute_mode,
        "resolved": resolved,
        "skipped": skipped,
    }

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(f"[ok] resolved {len(resolved)} skill(s), skipped {len(skipped)}, written to {args.output}")


if __name__ == "__main__":
    main()
