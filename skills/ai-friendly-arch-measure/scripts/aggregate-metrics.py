#!/usr/bin/env python3
"""
聚合所有度量 skill 的结果，生成符合 aia_component_summary 格式的总报告。
输入：state/resolved-skills.json + aia_output/**/aia_metric_fact.json
输出：aia_output/aia_component_summary.json

输出结构（两个表名作为顶层 key）：
{
  "aia_metric_fact": [ ... ],    // 各 skill 完整详情（aia_metric_fact 格式 list）
  "aia_component_summary": { ... } // 组件汇总（aia_component_summary 格式）
}
"""
import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path


GRADE_MAP = [
    (90, "S"),
    (75, "A"),
    (60, "B"),
    (40, "C"),
]


def grade(score: float) -> str:
    for threshold, g in GRADE_MAP:
        if score >= threshold:
            return g
    return "D"


def get_build_config() -> dict:
    """
    从环境变量读取构建配置
    """
    return {
        "uuid": os.getenv("UUID", "").strip(),
        "project_id": os.getenv("PMS_PROJECT_NO", "").strip(),
        "project_name": os.getenv("PMS_PROJECT_NAME", "").strip(),
        "component_name": os.getenv("COMPONENT_NAME", "").strip(),
        "repo_name": os.getenv("REPO_NAME", "").strip(),
        "branch_name": os.getenv("BRANCH_NAME", "").strip(),
    }


def load_json(path: str) -> dict:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


STATUS_SUCCESS = "success"
STATUS_FAILED = "failed"
STATUS_SKIPPED = "skipped"


def build_minimal_fact(skill_id: str, dimension: str, status: str) -> dict:
    """为失败/跳过的 skill 构造最小可用的 aia_metric_fact（满足必填字段）。"""
    return {
        "identity_info": {
            "skill_id": skill_id,
            "arch_dimension": dimension,
        },
        "execution_ctx": {
            "skill_version": "",
            "scan_mode": "full",
            "execute_status": status,
            "start_time": "",
            "end_time": "",
            "duration_ms": 0,
        },
        "core_metrics": {
            "total_score": None,
            "confidence_score": None,
            "total_violation_count": 0,
            "p0_violation_count": 0,
            "p1_violation_count": 0,
        },
        "evaluation_details": {},
        "violation_records": {},
        "scan_statistics": {},
    }


def main():
    parser = argparse.ArgumentParser(
        description="Aggregate all metric skill results into aia_component_summary.json"
    )
    parser.add_argument(
        "--resolved-skills", default="state/resolved-skills.json",
        help="Path to resolved-skills.json"
    )
    parser.add_argument(
        "--output-dir", default="aia_output",
        help="Directory where skill output subdirs reside"
    )
    parser.add_argument(
        "--output", default="aia_output/aia_component_summary.json",
        help="Final report output path"
    )
    parser.add_argument("--project-path", default="", help="Project root path")
    parser.add_argument("--project-id", default="", help="Project ID (from PMS)")
    parser.add_argument("--component-id", default="", help="Component ID")
    parser.add_argument("--component-name", default="", help="Component name")
    parser.add_argument("--uuid", default="", help="Build UUID from pipeline")
    args = parser.parse_args()

    # ── Timing: record start time ──────────────────────────────────────────────
    start_time = datetime.now(timezone.utc).isoformat()

    # Load resolved skills
    resolved_path = Path(args.resolved_skills)
    if not resolved_path.exists():
        print(
            f"[error] resolved-skills.json not found: {args.resolved_skills}",
            file=sys.stderr
        )
        sys.exit(1)
    resolved_data = load_json(args.resolved_skills)
    execute_mode = resolved_data.get("execute_mode", "default")
    resolved_skills = resolved_data.get("resolved", [])
    skipped_data = resolved_data.get("skipped", [])

    # ── 收集阶段：构建 aia_metric_fact 列表 + 聚合统计 ──────────────────────
    aia_metric_fact: list = []
    failed_skills: list = []
    total_p0, total_p1, total_violations = 0, 0, 0
    scores: list = []
    stat_info: dict = {}
    scan_time = datetime.now(timezone.utc).isoformat()

    # 预加载 registry（只读一次，用于 skipped skill 的 dimension 回查）
    registry_index: dict[str, str] = {}
    registry_path = Path(__file__).parent.parent / "config" / "metric-registry.json"
    if registry_path.exists():
        try:
            for m in load_json(str(registry_path)).get("metrics", []):
                registry_index[m["skill_id"]] = m.get("dimension", "")
        except Exception:
            pass

    # 1. resolved skill：读取 summary.json（失败时写最小占位 fact）
    # output_hint 现在是完整相对路径（如 aia_output/srp/aia_metric_fact.json），
    # 基于 project_path 直接 resolve，与最终输出路径保持一致。
    for skill in resolved_skills:
        skill_id = skill["skill_id"]
        dimension = skill.get("dimension", "")
        output_hint = skill.get("output_path_hint", "")
        if output_hint:
            if args.project_path:
                summary_path = (Path(args.project_path) / output_hint).resolve()
            else:
                summary_path = Path(output_hint).resolve()
        else:
            summary_path = None
        if summary_path is None or not summary_path.exists():
            failed_skills.append(skill_id)
            aia_metric_fact.append(build_minimal_fact(skill_id, dimension, STATUS_FAILED))
            continue
        try:
            data = load_json(str(summary_path))
        except Exception as e:
            print(f"[warn] cannot parse {summary_path}: {e}", file=sys.stderr)
            failed_skills.append(skill_id)
            aia_metric_fact.append(build_minimal_fact(skill_id, dimension, STATUS_FAILED))
            continue

        aia_metric_fact.append(data)
        exec_status = data.get("execution_ctx", {}).get("execute_status", STATUS_FAILED)
        core = data.get("core_metrics", {})
        total_score = core.get("total_score")
        if exec_status == STATUS_SUCCESS and total_score is not None:
            scores.append(total_score)
        else:
            failed_skills.append(skill_id)
        total_violations += core.get("total_violation_count", 0)
        total_p0 += core.get("p0_violation_count", 0)
        total_p1 += core.get("p1_violation_count", 0)
        for k, v in data.get("scan_statistics", {}).get("total_units", {}).items():
            stat_info[k] = stat_info.get(k, 0) + v

    # 2. skipped skill：最小占位 fact，dimension 从 registry 预加载索引查找
    skipped_skills: list = []
    for s in skipped_data:
        skill_id = s["skill_id"]
        dimension = registry_index.get(skill_id, "")
        skipped_skills.append(skill_id)
        aia_metric_fact.append(build_minimal_fact(skill_id, dimension, STATUS_SKIPPED))

    # ── 聚合阶段 ────────────────────────────────────────────────────────────
    total_score_avg = round(sum(scores) / len(scores), 4) if scores else 0.0

    fact_statuses = [f.get("execution_ctx", {}).get("execute_status", STATUS_FAILED) for f in aia_metric_fact]
    has_success = STATUS_SUCCESS in fact_statuses
    has_failed = STATUS_FAILED in fact_statuses
    if has_success and not has_failed:
        execute_status = STATUS_SUCCESS
    elif has_failed and has_success:
        execute_status = "partial"
    elif has_failed:
        execute_status = STATUS_FAILED
    else:
        execute_status = STATUS_SUCCESS

    # 推导 skill_id 列表和 dimension 映射（一次遍历）
    skill_id_set: list = []
    dimension_metric_mapping: dict[str, list] = {}
    for fact in aia_metric_fact:
        skill_id = fact.get("identity_info", {}).get("skill_id", "")
        dimension = fact.get("identity_info", {}).get("arch_dimension", "")
        if skill_id and skill_id not in skill_id_set:
            skill_id_set.append(skill_id)
        if dimension:
            dimension_metric_mapping.setdefault(dimension, []).append(skill_id)

    arch_dimension_list = list(dimension_metric_mapping.keys())

    # dimension_summary：单次遍历，合并 success_scores 和 skipped_in_dim 判断
    dimension_summary = {}
    for dim in dimension_metric_mapping:
        success_scores: list = []
        any_success = False
        skipped_in_dim = False
        for fact in aia_metric_fact:
            if fact.get("identity_info", {}).get("arch_dimension") != dim:
                continue
            exec_status = fact.get("execution_ctx", {}).get("execute_status", STATUS_FAILED)
            if exec_status == STATUS_SUCCESS:
                score = fact.get("core_metrics", {}).get("total_score")
                if score is not None:
                    success_scores.append(score)
                any_success = True
            elif exec_status == STATUS_SKIPPED:
                skipped_in_dim = True
        dim_score = round(sum(success_scores) / len(success_scores), 4) if success_scores else None
        if any_success:
            dim_status = STATUS_SUCCESS
        elif skipped_in_dim:
            dim_status = STATUS_SKIPPED
        else:
            dim_status = STATUS_FAILED
        dimension_summary[dim] = {
            "score": dim_score,
            "status": dim_status,
            "skill_count": len(dimension_metric_mapping[dim]),
        }

    # ── Timing: derive from skill facts, not script wall-clock ──────────────────
    # 累计各 skill fact 的 duration_ms，取最早 start_time 和最晚 end_time
    earliest_start: str | None = None
    latest_end: str | None = None
    total_skill_duration_ms = 0
    for fact in aia_metric_fact:
        ctx = fact.get("execution_ctx", {})
        st = ctx.get("start_time", "")
        et = ctx.get("end_time", "")
        dm = ctx.get("duration_ms", 0) or 0
        if st and (not earliest_start or st < earliest_start):
            earliest_start = st
        if et and (not latest_end or et > latest_end):
            latest_end = et
        if dm > 0:
            total_skill_duration_ms += dm

    # 若能从 start/end 推导则用推导值（更准确），否则用累计值
    computed_duration_ms: int
    if earliest_start and latest_end:
        try:
            from datetime import datetime as dt
            s_dt = dt.fromisoformat(earliest_start.replace("Z", "+00:00"))
            e_dt = dt.fromisoformat(latest_end.replace("Z", "+00:00"))
            computed_duration_ms = int((e_dt - s_dt).total_seconds() * 1000)
        except Exception:
            computed_duration_ms = total_skill_duration_ms
    else:
        computed_duration_ms = total_skill_duration_ms

    execution_ctx = {
        "skill_version": "v1.0",
        "scan_mode": execute_mode,
        "execute_status": execute_status,
        "start_time": earliest_start or start_time,
        "end_time": latest_end or datetime.now(timezone.utc).isoformat(),
        "duration_ms": computed_duration_ms,
    }

    # 读取环境变量配置（用于填充 identity_info）
    env_config = get_build_config()

    # 构建 identity_info：命令行参数优先，回退到环境变量
    identity_info = {
        "project_id": args.project_id or env_config["project_id"],
        "project_name": env_config["project_name"],
        "component_id": args.component_id,
        "component_name": args.component_name or env_config["component_name"],
        "component_repo": args.project_path or env_config.get("repo_name", ""),
        "tool_version": "v1.0",
    }

    # 构建顶层 uuid 字段（与 identity_info 并列）
    build_uuid = args.uuid or env_config["uuid"]

    aia_component_summary = {
        "uuid": build_uuid,
        "identity_info": identity_info,
        "execution_ctx": execution_ctx,
        "scan_result": {
            "total_skill_count": len(aia_metric_fact),
            "total_score_avg": total_score_avg,
            "total_violations": total_violations,
            "p0_total": total_p0,
            "p1_total": total_p1,
            "p2_total": 0,
            "scan_time": scan_time,
            "statistic_info": stat_info,
        },
        "dimension_data": {
            "arch_dimension_list": arch_dimension_list,
            "dimension_summary": dimension_summary,
        },
        "relation_mapping": {
            "skill_id_list": skill_id_set,
            "dimension_metric_mapping": dimension_metric_mapping,
        },
        "_meta": {
            "execute_status": execute_status,
            "execute_mode": execute_mode,
            "overall_grade": grade(total_score_avg),
            "skipped_skills": skipped_skills,
            "failed_skills": failed_skills,
        },
    }

    # ── 写出最终报告 ─────────────────────────────────────────────────────────
    report = {
        "aia_metric_fact": aia_metric_fact,
        "aia_component_summary": aia_component_summary,
    }

    # 基于 project_path 确保输出写到正确位置（避免 CWD 依赖）
    if args.project_path:
        output_path = (Path(args.project_path) / args.output).resolve()
    else:
        output_path = Path(args.output).resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    print(
        f"[ok] aia_component_summary.json written to {output_path} "
        f"(grade={grade(total_score_avg)}, status={execute_status})"
    )


if __name__ == "__main__":
    main()
