#!/usr/bin/env python3
"""
汇总所有模块的 ai-friendly-arch-guard-module-single-responsibility 分析结果，
输出符合 aia_metric_fact 格式的 summary.json。
"""
import argparse
import glob
import json
import re
import statistics
import sys
from datetime import datetime, timezone
from pathlib import Path


def classify_score(score: float) -> str:
    if score >= 90:
        return "excellent"
    elif score >= 70:
        return "good"
    elif score >= 50:
        return "medium"
    else:
        return "poor"


def _repair_and_load(fp, _path: str) -> dict | None:
    """尝试直接解析，失败后自动修复常见 JSON 格式问题后重试。

    支持修复的问题：
    - suggestion_summary 等字符串值缺少闭合引号（SubAgent LLM 常见输出错误）
    - 非转义的双引号出现在字符串值内部（如中文引号"替代"）
    - resource_list 等数组末尾元素缺失 trailing comma
    """
    content = fp.read()

    # 第一次尝试：直接解析
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        pass

    # 修复1：字符串值缺少闭合引号（同一行内 suggestion_summary/resource_list 等值的末尾）
    # 特征：stripped 包含 ": " 且其后的内容不以 " 结尾
    lines = content.split('\n')
    fixed_lines = []
    i = 0
    while i < len(lines):
        line = lines[i]
        stripped = line.rstrip()
        if stripped.endswith('"'):
            fixed_lines.append(line)
            i += 1
            continue
        # 如果本行包含 ": " 且以非 " 字符结尾，说明字符串值未闭合
        if '": "' in stripped or '": "' in line:
            fixed_line = line.rstrip('\n\r') + '"\n'
            fixed_lines.append(fixed_line)
            lines[i] = fixed_line
        else:
            fixed_lines.append(line)
        i += 1

    # 重新组装并尝试解析
    content = '\n'.join(fixed_lines)
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        pass

    # 修复2：非转义引号（中文文本中的双引号字符）
    def _escape_inner_quotes(m):
        key = m.group(1)
        val = m.group(2)
        # 在字符串值内部的双引号前加反斜杠转义
        val = re.sub(r'(?<!\\)(")(?![,\] \}])', r'\\"', val)
        return key + val + '"'

    # 重新从文件读取（因为上面可能已修改 lines）
    content = '\n'.join(fixed_lines)
    content = re.sub(r'("(?:[^"\\]|\\.)*")\s*:\s*("(?:[^"\\]|\\.)*)', _escape_inner_quotes, content)
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        pass

    # 修复3：缺失 trailing comma in arrays
    # 在 ] 前一行（数组元素行）末尾缺少 , 的情况
    lines = content.split('\n')
    fixed_lines = []
    for idx, line in enumerate(lines):
        stripped = line.rstrip()
        # 如果本行是数组元素（以 "xxx" 或 "xxx", 结尾）且下一行是 ],
        if idx + 1 < len(lines):
            next_stripped = lines[idx + 1].strip()
            if next_stripped == '],':
                # 如果本行末不是 , 且是元素行（以 " 结尾）
                if stripped.endswith('"') and not stripped.endswith(','):
                    fixed_lines.append(line.rstrip() + ',\n')
                    continue
        fixed_lines.append(line)
    content = '\n'.join(fixed_lines)
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        pass

    return None


def load_module_results(input_dir: str) -> list[dict]:
    pattern = str(Path(input_dir) / "*.json")
    files = sorted(glob.glob(pattern))
    results = []
    for f in files:
        try:
            with open(f, encoding="utf-8") as fp:
                data = _repair_and_load(fp, f)
            if data is None:
                # 最后尝试：原始 json.load
                fp2 = open(f, encoding="utf-8")
                data = json.load(fp2)
                fp2.close()
            results.append({"file": f, "data": data})
        except Exception as e:
            print(f"[warn] skip {f}: {e}", file=sys.stderr)
    return results


def aggregate(module_results: list[dict]) -> tuple[dict, dict, dict, list]:
    scores, confidences = [], []
    dir_scores, cohesion_scores, file_scores = [], [], []
    modules_summary = []
    distribution = {"excellent": 0, "good": 0, "medium": 0, "poor": 0}

    total_violations = 0
    p0_count = 0
    p1_count = 0
    violation_unit_count = 0

    for item in module_results:
        data = item["data"]
        file_path = item["file"]
        module_name = Path(file_path).stem

        if module_name == "processing_summary":
            continue

        metric = data.get("metric_result", {})
        total_score = metric.get("total_score", 0.0)
        confidence = metric.get("confidence", 0.0)
        score_detail = metric.get("score_detail", {})

        violation_info = data.get("violation_info", {})
        violation_count = violation_info.get("total_count", 0)

        # p0/p1 per-module aggregation（支持新旧字段名混写）
        level_dist = violation_info.get("level_summary") or violation_info.get("level_distribution", {})
        p0_count += level_dist.get("P0", 0)
        p1_count += level_dist.get("P1", 0)
        total_violations += violation_count
        if violation_count > 0:
            violation_unit_count += 1

        scores.append(total_score)
        confidences.append(confidence)
        if "directory_single_score" in score_detail:
            dir_scores.append(score_detail["directory_single_score"])
        if "module_cohesion_score" in score_detail:
            cohesion_scores.append(score_detail["module_cohesion_score"])
        if "file_single_score" in score_detail:
            file_scores.append(score_detail["file_single_score"])

        distribution[classify_score(total_score)] += 1

        modules_summary.append({
            "module_name": module_name,
            "module_path": data.get("module_path", ""),
            "total_score": total_score,
            "confidence": confidence,
            "violation_count": violation_count,
            "detail_path": file_path,
        })

    def safe_mean(lst):
        return round(statistics.mean(lst), 4) if lst else 0.0

    total_modules = len(scores)

    core_metrics = {
        "total_score": safe_mean(scores),
        "confidence_score": safe_mean(confidences),
        "total_violation_count": total_violations,
        "p0_violation_count": p0_count,
        "p1_violation_count": p1_count,
    }

    evaluation_details = {
        "score_detail": {
            "directory_single_score": safe_mean(dir_scores),
            "module_cohesion_score": safe_mean(cohesion_scores),
            "file_single_score": safe_mean(file_scores),
        },
        "score_distribution": distribution,
        "confidence_detail": {},
    }

    scan_statistics = {
        "total_units": {"modules": total_modules},
        "violation_units": {"modules": violation_unit_count},
        "valid_units": {"modules": total_modules - violation_unit_count},
    }

    return core_metrics, evaluation_details, scan_statistics, modules_summary


def _normalize_violation(v: dict, fallback_scope_path: str) -> dict:
    """规范化违规记录字段名（支持新旧规范混写）。"""
    return {
        "type": v.get("violation_type") or v.get("type", ""),
        "level": v.get("violation_level") or v.get("level", ""),
        "scope_path": v.get("scope_path") or fallback_scope_path,
        "resources": v.get("resource_list") or v.get("resources", []),
        "suggestion": v.get("suggestion_summary") or v.get("suggestion", ""),
    }


def build_violation_records(module_results: list[dict], filter_p2: bool = True) -> dict:
    """
    构建违规记录

    Args:
        module_results: 各模块分析结果列表
        filter_p2: 是否过滤 P2 级别违规（默认 True，门禁判定忽略 P2）
    """
    level_summary = {"P0": 0, "P1": 0, "P2": 0}  # 始终统计全部，但输出时可过滤
    violation_infos = []

    for item in module_results:
        data = item["data"]
        module_name = Path(item["file"]).stem
        if module_name == "processing_summary":
            continue

        violation_info = data.get("violation_info", {})
        level_dist = violation_info.get("level_summary") or violation_info.get("level_distribution", {})
        # 统计所有级别的原始数量
        p0_count = level_dist.get("P0", 0)
        p1_count = level_dist.get("P1", 0)
        p2_count = level_dist.get("P2", 0) if filter_p2 else 0

        level_summary["P0"] += p0_count
        level_summary["P1"] += p1_count
        level_summary["P2"] += p2_count

        fallback_path = data.get("module_path", "")
        violations = violation_info.get("list") or violation_info.get("violations", [])
        for v in violations:
            # 【优化点】过滤 P2 级别违规，减少输出体积
            v_level = v.get("violation_level") or v.get("level", "")
            if filter_p2 and v_level == "P2":
                continue
            violation_infos.append(_normalize_violation(v, fallback_path))

    # 如果过滤了 P2，从 level_summary 中移除 P2 统计（避免混淆）
    if filter_p2:
        # 保留 P2=0 以保持字段一致性，但不计入输出
        output_summary = {"P0": level_summary["P0"], "P1": level_summary["P1"]}
    else:
        output_summary = level_summary

    return {
        "level_summary": output_summary,
        "violation_infos": violation_infos[:50],
        "exempt_infos": [],
        "_internal": {
            "p2_filtered": filter_p2,
            "p2_total_count": level_summary["P2"],  # 保留内部参考
        } if filter_p2 else {},
    }


def main():
    parser = argparse.ArgumentParser(description="Aggregate module SRP analysis results")
    parser.add_argument("--input-dir", required=True, help="Directory containing per-module JSON files")
    parser.add_argument("--output", required=True, help="Output summary JSON file path")
    parser.add_argument("--project-path", default="", help="Project root path (informational)")
    parser.add_argument("--changed-modules-json", default="", help="Path to changed-modules.json for incremental mode")
    parser.add_argument("--arch-dimension", default="结构可导航性",
                        help="架构维度名称（对应 metric-registry.json 中的 dimension 字段）")
    parser.add_argument("--skill-start-time", default="",
                        help="Skill 实际开始时间（ISO8601），由编排层传入")
    parser.add_argument("--skill-end-time", default="",
                        help="Skill 实际结束时间（ISO8601），由编排层传入")
    parser.add_argument("--filter-p2", action="store_true", default=True,
                        help="过滤 P2 级别违规（默认启用，减少输出体积）。使用 --no-filter-p2 禁用")
    parser.add_argument("--no-filter-p2", dest="filter_p2", action="store_false",
                        help="不禁用 P2 过滤（保留所有 P2 违规）")
    parser.add_argument("--uuid", default="", help="Build UUID from pipeline")
    args = parser.parse_args()

    # skill 实际起止时间由编排层传入；若未传入则回退到自身计时
    if args.skill_start_time and args.skill_end_time:
        try:
            s_dt = datetime.fromisoformat(args.skill_start_time.replace("Z", "+00:00"))
            e_dt = datetime.fromisoformat(args.skill_end_time.replace("Z", "+00:00"))
            skill_start = args.skill_start_time
            skill_end = args.skill_end_time
            duration_ms = int((e_dt - s_dt).total_seconds() * 1000)
        except Exception:
            skill_start = datetime.now(timezone.utc).isoformat()
            skill_end = skill_start
            duration_ms = 0
    else:
        skill_start = datetime.now(timezone.utc).isoformat()
        skill_end = skill_start
        duration_ms = 0

    module_results = load_module_results(args.input_dir)
    if not module_results:
        print(f"[error] No JSON files found in {args.input_dir}", file=sys.stderr)
        sys.exit(1)

    core_metrics, evaluation_details, scan_statistics, modules_summary = aggregate(module_results)
    violation_records = build_violation_records(module_results, filter_p2=args.filter_p2)

    # Detect incremental mode
    scan_mode = "full"
    base_commit = ""
    target_commit = ""
    orphan_files_count = 0
    orphan_files = []
    if args.changed_modules_json and Path(args.changed_modules_json).exists():
        try:
            with open(args.changed_modules_json, "r", encoding="utf-8") as f:
                changed_data = json.load(f)
            raw_mode = changed_data.get("mode", "incremental")
            scan_mode = "increment" if raw_mode != "full" else "full"
            base_commit = changed_data.get("base_commit", "")
            target_commit = changed_data.get("target_commit", "")
            orphan_files_count = changed_data.get("statistics", {}).get("orphan_files_count", 0)
            orphan_files = changed_data.get("orphan_files", [])
        except Exception:
            pass

    execution_ctx = {
        "skill_version": "v1.0",
        "scan_mode": scan_mode,
        "execute_status": "success",
        "start_time": skill_start,
        "end_time": skill_end,
        "duration_ms": duration_ms,
    }
    if scan_mode == "increment":
        execution_ctx["base_commit"] = base_commit
        execution_ctx["target_commit"] = target_commit
        execution_ctx["orphan_files_count"] = orphan_files_count
        execution_ctx["orphan_files"] = orphan_files

    summary = {
        "uuid": args.uuid,
        "identity_info": {
            "skill_id": "ai-friendly-component-srp-orchestrate",
            "arch_dimension": args.arch_dimension,
        },
        "execution_ctx": execution_ctx,
        "core_metrics": core_metrics,
        "evaluation_details": evaluation_details,
        "violation_records": violation_records,
        "scan_statistics": scan_statistics,
        "project_path": args.project_path,
        "modules": modules_summary,
    }

    # 强制以 project_path 为基准将 --output 转为绝对路径
    # 避免因 CWD 不同导致输出写到错误位置（如技能内部目录而非项目根）
    if args.project_path:
        output_path = Path(args.project_path) / args.output
    else:
        output_path = Path(args.output)
    output_path = output_path.resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as fp:
        json.dump(summary, fp, ensure_ascii=False, indent=2)

    print(f"[ok] summary written to {output_path} ({len(modules_summary)} modules)")


if __name__ == "__main__":
    main()
