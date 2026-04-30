#!/usr/bin/env python3
"""
将 step02-analyze-modules 的分析文件适配为 aggregate.py 期望的 aia_metric_fact 格式。

支持两种输入格式：
  1. 新格式（pdm-cli step02）：metrics.srp_compliance_score, srp_violations,
     identified_responsibilities, total_files, single_responsibility_assessment
  2. 旧格式（旧版 step02）：srp_compliance.score, violations, responsibilities_identified,
     file_count

输出（适配后）：
  metric_result.total_score       float 0-100
  metric_result.confidence        float 0-1
  metric_result.score_detail.directory_single_score
  metric_result.score_detail.module_cohesion_score
  metric_result.score_detail.file_single_score
  violation_info.total_count
  violation_info.level_summary
  violation_info.list
"""
import json
import statistics
from pathlib import Path

INPUT_DIR = Path(__file__).parent.parent / "state" / "step02-analyze-modules"
OUTPUT_DIR = INPUT_DIR.parent / "step02-analyze-modules-adapter"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


# ─── 置信度映射 ───────────────────────────────────────────────────────────────

def confidence_level_to_float(level: str | None) -> float:
    """将 confidence_level 字符串映射为 0-1 数值（新格式）。"""
    mapping = {
        "high": 0.95,
        "medium": 0.75,
        "low": 0.50,
        "unknown": 0.40,
    }
    if not level:
        return 0.5
    return mapping.get(str(level).strip().lower(), 0.5)


# ─── 新格式检测 ───────────────────────────────────────────────────────────────

def is_new_format(data: dict) -> bool:
    """新格式以 metrics.srp_compliance_score 或 metrics.cohesion_score 为标志。"""
    return "metrics" in data and isinstance(data["metrics"], dict)


# ─── 新格式适配（pdm-cli step02） ────────────────────────────────────────────

def adapt_new(data: dict, mod_name: str) -> dict:
    """
    将 pdm-cli step02 格式适配为 aggregate.py 期望的格式。

    字段映射：
      metrics.srp_compliance_score  → metric_result.total_score
      single_responsibility_assessment.confidence_level → confidence
      metrics.cohesion_score        → module_cohesion_score
      total_files                    → directory_single_score 计算
      identified_responsibilities[]  → cohesion 计算 & violation_info.list
      srp_violations[]              → violation_info.list（按 level 分类）
    """
    metrics = data.get("metrics", {})
    srp_compliance_score = metrics.get("srp_compliance_score", 0.5)
    cohesion_score = metrics.get("cohesion_score", 0.5)
    coupling_score = metrics.get("coupling_score", 0.0)

    # confidence
    sra = data.get("single_responsibility_assessment", {})
    confidence_level = sra.get("confidence_level", "unknown")
    confidence = confidence_level_to_float(confidence_level)

    # sub-scores
    # directory_single: 基于 total_files（文件越多，目录职责越多）
    total_files = data.get("total_files", 1)
    if total_files <= 5:
        dir_single = 1.0
    elif total_files <= 20:
        dir_single = 0.9
    elif total_files <= 50:
        dir_single = 0.8
    elif total_files <= 100:
        dir_single = 0.7
    else:
        dir_single = round(max(0.4, 1.0 - (total_files - 100) / 500), 4)

    # module_cohesion_score: 直接用 metrics.cohesion_score（已是 0-1），上限 1.0
    module_cohesion = round(min(1.0, float(cohesion_score)), 4)

    # file_single: cohesion 和 directory_single 的综合
    file_single = round((module_cohesion + dir_single) / 2, 4)

    # violations
    srp_violations = data.get("srp_violations", [])
    if not isinstance(srp_violations, list):
        srp_violations = []

    level_summary = {"P0": 0, "P1": 0, "P2": 0}
    violation_list = []
    for v in srp_violations:
        level = str(v.get("level", v.get("violation_level", "P1"))).strip().upper()
        if level not in ("P0", "P1", "P2"):
            level = "P1"
        level_summary[level] = level_summary.get(level, 0) + 1

        violation_list.append({
            "violation_type": v.get("type", v.get("violation_type", "unknown")),
            "violation_level": level,
            "scope_path": v.get("scope_path", data.get("module_path", "")),
            "resource_list": v.get("resources", v.get("resource_list", [])),
            "suggestion_summary": v.get("suggestion", v.get("suggestion_summary", "")),
        })

    total_violations = len(violation_list)

    # identified_responsibilities：用于判断内聚（职责越少=越内聚）
    identified = data.get("identified_responsibilities", [])
    if not isinstance(identified, list):
        identified = []
    resp_count = len(identified)
    # 如果没有 identified_responsibilities，用 cohesion_score 反推
    if resp_count == 0 and cohesion_score > 0:
        # cohesion_score 高 → resp_count 低 → cohesion 仍可信
        pass

    return {
        "module_path": data.get("module_path", ""),
        "module_name": mod_name,
        "metric_result": {
            "total_score": round(min(1.0, max(0.0, float(srp_compliance_score))), 4),
            "confidence": confidence,
            "score_detail": {
                "directory_single_score": dir_single,
                "module_cohesion_score": module_cohesion,
                "file_single_score": file_single,
            },
            "confidence_detail": {
                "structure_confidence": round(min(1.0, coupling_score + 0.3), 4),
                "semantic_confidence": confidence,
                "context_confidence": confidence,
            },
        },
        "violation_info": {
            "total_count": total_violations,
            "level_summary": level_summary,
            "list": violation_list,
            "exempt_list": [],
        },
        # 保留原始数据供追溯
        "original_data": {
            k: v for k, v in data.items()
            if k not in ("metric_result", "violation_info")
        },
    }


# ─── 旧格式适配（兼容旧版 step02） ──────────────────────────────────────────

def normalize_old_score(score_val) -> float:
    """将旧格式的 score（0-10）映射到 total_score（0-100）。"""
    try:
        return round(float(score_val) * 10.0, 4)
    except (TypeError, ValueError):
        return 50.0


STATUS_CONFIDENCE = {
    "compliant": 0.95,
    "mostly_compliant": 0.80,
    "partial": 0.60,
    "violation": 0.50,
    "unknown": 0.40,
}


def status_to_confidence(status_val) -> float:
    if not status_val:
        return 0.5
    return STATUS_CONFIDENCE.get(str(status_val).strip().lower(), 0.5)


def adapt_old(data: dict, mod_name: str) -> dict:
    """
    将旧版 step02 格式适配为 aggregate.py 期望的格式。

    字段映射：
      single_responsibility_score     → total_score（映射到 0-100）
      srp_compliance.score           → total_score（/10，旧版字段）
      violations[].file              → scope_path
      violations[].issue             → violation_type
      violations[].severity          → violation_level（critical→P0, high→P1, medium→P2）
      violations[].responsibilities  → resource_list
      violations[].recommendations   → suggestion_summary
      file_count                     → directory_single_score 计算
    """
    # score 提取：优先 single_responsibility_score（0-10），其次 srp_compliance.score
    raw_score = data.get("single_responsibility_score", 5)
    srp = data.get("srp_compliance", {})
    if srp.get("score") is not None:
        raw_score = srp.get("score")
    score = normalize_old_score(raw_score)
    score = round(min(1.0, max(0.0, score)), 4)

    # confidence
    confidence = status_to_confidence(srp.get("status", "unknown"))
    # 旧格式也可能有 confidence_level
    if data.get("confidence_level"):
        confidence = confidence_level_to_float(data.get("confidence_level"))

    # violations
    violations_raw = data.get("violations", [])
    if isinstance(violations_raw, str):
        try:
            violations_raw = json.loads(violations_raw)
        except Exception:
            violations_raw = []
    if not isinstance(violations_raw, list):
        violations_raw = []
    total_violations = len(violations_raw)

    SEVERITY_TO_LEVEL = {
        "critical": "P0",
        "high": "P1",
        "medium": "P2",
    }

    level_summary = {"P0": 0, "P1": 0, "P2": 0}
    violation_list = []
    for v in violations_raw:
        sev = str(v.get("severity", v.get("level", "medium"))).strip().lower()
        level = SEVERITY_TO_LEVEL.get(sev, "P1")
        level_summary[level] = level_summary.get(level, 0) + 1

        violation_list.append({
            "violation_type": v.get("issue", v.get("violation_type", "unknown")),
            "violation_level": level,
            "scope_path": v.get("file", v.get("scope_path", data.get("module_path", ""))),
            "resource_list": v.get("responsibilities", v.get("resource_list", [])),
            "suggestion_summary": v.get("recommendation", v.get("suggestion_summary", "")),
        })

    # file_count / total_files
    file_count = data.get("file_count", data.get("total_files", 1))
    if isinstance(file_count, str):
        try:
            file_count = int(file_count)
        except (ValueError, TypeError):
            file_count = 1
    dir_single = round(min(1.0, 1.0 / max(1, file_count) + 0.5), 4)

    # cohesion：基于违规文件数（违规越多内聚越低）
    cohesion = round(max(0.3, 1.0 - total_violations * 0.1), 4)
    file_single = round((cohesion + dir_single) / 2, 4)

    return {
        "module_path": data.get("module_path", data.get("module_name", "")),
        "module_name": mod_name,
        "metric_result": {
            "total_score": score,
            "confidence": confidence,
            "score_detail": {
                "directory_single_score": dir_single,
                "module_cohesion_score": cohesion,
                "file_single_score": file_single,
            },
            "confidence_detail": {},
        },
        "violation_info": {
            "total_count": total_violations,
            "level_summary": level_summary,
            "list": violation_list,
            "exempt_list": [],
        },
        "original_data": {
            k: v for k, v in data.items()
            if k not in ("metric_result", "violation_info")
        },
    }


# ─── 主逻辑 ──────────────────────────────────────────────────────────────────

def process_file(src_path: Path) -> dict:
    data = json.load(open(src_path, encoding="utf-8"))
    mod_name = src_path.stem
    if is_new_format(data):
        return adapt_new(data, mod_name)
    else:
        return adapt_old(data, mod_name)


def main():
    json_files = sorted(INPUT_DIR.glob("*.json"))
    if not json_files:
        print(f"[warn] no JSON files found in {INPUT_DIR}", file=__import__("sys").stderr)
        return

    print(f"[adapter] {len(json_files)} files found in {INPUT_DIR}")

    scores = []
    for src in json_files:
        adapted = process_file(src)
        dst = OUTPUT_DIR / src.name
        with open(dst, "w", encoding="utf-8") as f:
            json.dump(adapted, f, ensure_ascii=False, indent=2)
        scores.append(adapted["metric_result"]["total_score"])

    print(f"[ok] {len(json_files)} files adapted → {OUTPUT_DIR}")
    if scores:
        print(f"[stats] score mean={statistics.mean(scores):.4f}  "
              f"min={min(scores):.4f}  max={max(scores):.4f}")


if __name__ == "__main__":
    main()
