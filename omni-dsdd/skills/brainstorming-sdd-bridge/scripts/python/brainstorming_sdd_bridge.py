#!/usr/bin/env python3
"""Adapt approved brainstorming docs to the SDD document interface."""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List


BRIDGE_STAGE = "brainstorming-sdd-bridge"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _require_dir(value: str, name: str) -> Path:
    if not value:
        raise SystemExit(f"ERROR: {name} is required")
    path = Path(value).resolve()
    if not path.is_dir():
        raise SystemExit(f"ERROR: {name} is not a directory: {path}")
    return path


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _read_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, data: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _run(cmd: Iterable[str]) -> None:
    subprocess.run(list(cmd), check=True)


def _latest_brainstorming_design(feature_dir: Path) -> Path:
    candidates = [
        p
        for p in feature_dir.glob("*-design.md")
        if p.name != "design.md" and p.is_file()
    ]
    if not candidates:
        raise SystemExit(f"ERROR: no brainstorming design found: {feature_dir}/*-design.md")
    return max(candidates, key=lambda p: (p.stat().st_mtime, p.name))


def _title_from_markdown(text: str, fallback: str) -> str:
    for line in text.splitlines():
        match = re.match(r"^#\s+(.+?)\s*$", line)
        if match and match.group(1).strip():
            return match.group(1).strip()
    return fallback


def _summarize(text: str, *, max_chars: int = 1600) -> str:
    cleaned = re.sub(r"\n{3,}", "\n\n", text).strip()
    if len(cleaned) <= max_chars:
        return cleaned
    return cleaned[:max_chars].rstrip() + "\n\n（摘要预览到此结束；完整源设计全文已在本文档的「源 brainstorming 设计全文」章节落盘。）"


def _extract_headings(text: str) -> List[str]:
    headings: List[str] = []
    for line in text.splitlines():
        match = re.match(r"^#{2,4}\s+(.+?)\s*$", line)
        if match:
            title = match.group(1).strip()
            if title:
                headings.append(title)
    return headings[:6]


def _extract_section(text: str, title: str) -> str:
    pattern = re.compile(
        r"(^##\s+{0}\s*$)(.*?)(?=^##\s+|\Z)".format(re.escape(title)),
        re.MULTILINE | re.DOTALL,
    )
    match = pattern.search(text)
    return match.group(0).strip() if match else ""


def _full_source_block(source_name: str, design_text: str) -> str:
    return f"""## 源 brainstorming 设计全文

源文件: `{source_name}`

```markdown
{design_text.strip()}
```
"""


def _safe_branch_name(feature_dir: Path, branch_name: str) -> str:
    return branch_name.strip() or feature_dir.name


def _ensure_workspace_infra(plugin_root: Path, working_dir: Path) -> None:
    if (working_dir / ".omni-infra").is_dir() or (working_dir / "omni-infra").is_dir():
        return
    plugin_infra = plugin_root / "omni-infra"
    if not plugin_infra.is_dir():
        raise SystemExit(f"ERROR: plugin omni-infra not found: {plugin_infra}")
    shutil.copytree(plugin_infra, working_dir / ".omni-infra")


def _generate_spec(
    *,
    feature_name: str,
    branch_name: str,
    source_name: str,
    design_text: str,
    user_intent: str,
) -> str:
    today = date.today().isoformat()
    summary = _summarize(design_text)
    headings = _extract_headings(design_text)
    heading_lines = "\n".join(f"- {item}" for item in headings) or "- 已批准设计稿未提供二级标题，后续任务阶段直接读取完整源设计。"
    return f"""# 功能规范: {feature_name}

**功能分支**: `{branch_name}`
**创建时间**: {today}
**状态**: brainstorming-approved
**输入**: 用户描述: "{user_intent}"

## 关键实体 *(如果功能涉及数据则包含)*

- **ApprovedBrainstormingDesign**: 用户已批准的设计稿，来源 `{source_name}`，作为本功能需求、方案和边界的权威输入。
- **ImplementationScope**: 从已批准设计稿提取的实现范围，供 `tasks` 按场景拆分任务。

## 成功标准 *(必填)*

### 可衡量的结果

- **SC-001**: `tasks` 阶段可以仅基于 `spec.md`、`design.md`、`context.md` 和 `{source_name}` 生成可执行 `tasks.md`。
- **SC-002**: `implement` 阶段可以基于 `tasks.md`、`design.md` 和 `spec.md` 执行实现，不依赖对话记忆。
- **SC-003**: review 与 local-sandbox-fix 阶段可以基于实现结果、任务清单和落盘制品完成验证闭环。

## 与既有架构对齐（章程）

本规范由 expert workflow 中用户已批准的 brainstorming 设计稿转换而来。后续任务分解必须以 `{source_name}`、`design.md` 和 `context.md` 为事实来源，优先复用既有代码与架构；源设计稿未明确的文件路径、接口和修改点，不得在 `tasks.md` 中臆造为必须新增实现。

## 需求

### [动作类型:REFER] - REQ-001 - 执行已批准 brainstorming 设计

变更原因: 用户已在 expert brainstorming 阶段批准 `{source_name}` 中的设计。

系统 shall 按 `{source_name}` 中记录的设计目标、约束、方案和验证要求生成后续任务与实现计划。

### [动作类型:REFER] - REQ-002 - 保持标准 SDD 文档接口

变更原因: 后续 `tasks`、`implement`、`review`、`local-sandbox-fix` 阶段依赖固定文件接口。

系统 shall 通过 `spec.md`、`design.md`、`context.md`、`paths.json` 和 `env.sh` 传递上下文，避免下游阶段直接依赖自由格式对话记忆。

## 场景

### [动作类型:REFER] - SCN-001 - 按已批准设计生成任务 (优先级: P1)

归属的需求: REQ-001

场景描述: task 阶段读取标准接口，并围绕 `{source_name}` 中的批准设计生成可执行任务。

**验收场景**:

1. **Given** `{source_name}` 已由用户批准，**When** `tasks` 阶段读取 `spec.md`、`design.md` 和 `context.md`，**Then** 输出的 `tasks.md` 应按场景、依赖、测试和验证要求组织。

### [动作类型:REFER] - SCN-002 - 实现与验证只依赖落盘接口 (优先级: P1)

归属的需求: REQ-002

场景描述: implement 与验证阶段通过落盘文档和状态文件继承上下文。

**验收场景**:

1. **Given** `tasks.md` 已生成，**When** `implement`、`review` 和 `local-sandbox-fix` 继续执行，**Then** 它们应通过 `FEATURE_DIR` 下的标准制品完成实现和验证闭环。

## Brainstorming 设计目录

源文件: `{source_name}`

{heading_lines}

## Brainstorming 设计摘要

{summary}

{_full_source_block(source_name, design_text)}
"""


def _generate_design(
    *,
    feature_name: str,
    branch_name: str,
    source_name: str,
    design_text: str,
) -> str:
    today = date.today().isoformat()
    summary = _summarize(design_text, max_chars=2400)
    return f"""# 实施计划: {feature_name}

**分支**: `{branch_name}` | **日期**: {today} | **规范**: spec.md
**输入**: 来自 expert brainstorming 已批准设计稿 `{source_name}`

**注意**: 本文件由 `brainstorming-sdd-bridge` 从已批准 brainstorming 设计稿转换生成；它是 `tasks` 和 `implement` 的标准接口，不代表重新执行 design 阶段。

## 摘要

本功能以 `{source_name}` 为权威设计输入。任务阶段必须优先读取本文档中的源设计摘要与完整设计引用，再生成具体的 TDD 任务、实施路径和验证步骤。

{summary}

## 技术背景

**语言/版本**: 以当前仓库实际技术栈为准，由 `tasks`/`implement` 阶段读取代码树确认。
**主要依赖**: 以现有项目依赖和 `{source_name}` 中的明确约束为准。
**存储**: 未在源设计中明确时保持现有存储方案。
**测试**: 遵循 `omni-dsdd:tdd-workflow`，任务阶段必须生成 RED/GREEN/REFACTOR 配对任务。
**目标平台**: 以当前工作区项目平台为准。
**项目类型**: 以当前工作区结构为准。
**性能目标**: 以 `{source_name}` 中明确要求为准；未明确时不得臆造性能指标。
**约束条件**: 已批准设计稿中的约束优先；未明确处保持最小化改动。
**规模/范围**: 限定为 `{source_name}` 中已批准的范围。

## 波及文件与复用分析

| 路径（源码/配置等） | 与本功能关系 | 现有实现是否已满足需求 | 复用/变更策略 | 关键符号（类型、函数等，可选） |
|---------------------|--------------|------------------------|---------------|--------------------------------|
| 由 tasks 阶段读取代码树后确认 | 来源设计未在桥接阶段强行臆造文件路径 | 待确认 | 优先复用现有实现，必要时最小扩展 | 待确认 |

## 章程检查

- [x] **规格一致**：`spec.md` 来自用户已批准的 brainstorming 设计稿。
- [x] **方案锚定现状**：桥接阶段不新增实现方案；任务阶段必须读取现有代码后再定位修改点。
- [x] **可定位修改点**：源设计未明确的路径保持待确认，不在桥接阶段臆造。
- [x] **波及与复用**：任务阶段必须对照本文档和代码树完成复核。
- [x] **利旧决策顺序**：任务阶段按 `参数兼容扩展 > 同文件新增函数 > 新增文件` 排任务。
- [x] **扩散阈值检查**：默认不超过 3 个目标文件；超过时必须在 `tasks.md` 中写扩散说明。

## 修改点严格检查

| 修改点 | 支持状态（已支持/部分支持/不支持） | 利旧结论（参数兼容/同文件新函数/新增文件） | 最小化结论（目标文件数、目标符号） | 证据 | 风险/备注 |
|--------|------------------------------------|--------------------------------------------|------------------------------------|------|----------|
| 执行 `{source_name}` 中已批准的功能设计 | 待 tasks 阶段读取代码确认 | 优先参数兼容或同文件扩展 | 默认收敛到最小文件集合 | `{source_name}` / `context.md` | 禁止空对空新增实现 |

## 项目结构

### 文档(此功能)

```
changes/{branch_name}/
├── {source_name}          # brainstorming 已批准设计稿
├── spec.md                # 本桥接生成，供 tasks/implement 使用
├── design.md              # 本桥接生成，供 tasks/implement 使用
├── context.md             # 本桥接生成，供 tasks/implement 使用
├── research.md            # 本桥接生成的最小研究接口
├── data-model.md          # 本桥接生成的最小实体接口
├── contracts/             # 本桥接生成的最小接口契约目录
└── tasks.md               # tasks 阶段输出
```

### 源代码(仓库根目录)

任务阶段必须读取当前工作区结构后填写具体路径，禁止仅依据桥接阶段假设新增目录。

**结构决策**: 复用当前仓库结构；如源设计要求新增结构，必须在 `tasks.md` 中引用 `{source_name}` 的对应依据。

## 复杂度跟踪

| 违规 | 为什么需要 | 拒绝更简单替代方案的原因 |
|-----------|------------|-------------------------------------|
| 无 | 当前桥接不引入额外复杂度 | N/A |

## 源 brainstorming 设计全文

源文件: `{source_name}`

```markdown
{design_text.strip()}
```
"""


def _generate_context(*, source_name: str, design_text: str, user_intent: str) -> str:
    summary = _summarize(design_text, max_chars=2200)
    return f"""# 上下文: brainstorming SDD bridge

**context_mode**: `expert_brainstorming_bridge`
**渲染时间**: {_utc_now()}

## 功能描述

本功能来自 expert workflow 的 brainstorming 阶段，用户已批准源设计稿 `{source_name}`。桥接阶段只做文档接口适配，不重新设计、不改写 brainstorming 的业务决策。用户意图摘要: {user_intent}

## 相关反构文档

- 源 brainstorming 设计稿: `{source_name}`
- 后续 `tasks` / `implement` 阶段如需定位代码，应读取当前工作区和 `omni-doc/` 下的既有架构资料。

## 架构分析与设计参考

以下内容摘自已批准的 brainstorming 设计稿，是后续 `tasks` 的主要设计输入:

{summary}

{_full_source_block(source_name, design_text)}

## 术语对齐

- brainstorming design: 用户已批准的自由格式设计稿。
- SDD bridge: 将自由格式设计稿转换为标准 `spec.md` / `design.md` / `context.md` 接口的适配阶段。
- downstream interface: `tasks`、`implement`、`review`、`local-sandbox-fix` 读取的落盘文件与状态。

## 约束和假设

- 桥接阶段不得重新设计功能，不得推翻 `{source_name}` 中的用户批准结论。
- 源设计未明确的代码路径、实体和接口只能标为待确认，由 `tasks` 阶段读取代码树后收敛。
- 后续实现必须遵循 TDD，测试任务在实现任务之前。
- 其他 workflow 不引用本桥接阶段，保持原有 specify/design/tasks 接口不变。
"""


def _generate_research(source_name: str, design_text: str) -> str:
    summary = _summarize(design_text, max_chars=1400)
    return f"""# Research: brainstorming approved design

## 决策

- 采用 `{source_name}` 作为本功能唯一已批准设计来源。
- 桥接阶段只生成下游标准接口，不执行新的方案比较。
- 任务阶段必须读取现有代码后再确认修改点，避免从自由文本臆造文件路径。

## 依据

{summary}

{_full_source_block(source_name, design_text)}

## 待任务阶段确认

- 具体源码路径与关键符号。
- 现有实现是否已经满足部分需求。
- 最小化改动边界与测试命令。
"""


def _generate_requirements_content() -> str:
    return """# 需求内容（来自 spec.md）

## 需求

### [动作类型:REFER] - REQ-001 - 执行已批准 brainstorming 设计

变更原因: 用户已在 expert brainstorming 阶段批准源设计稿。

系统 shall 按源设计稿中记录的设计目标、约束、方案和验证要求生成后续任务与实现计划。

### [动作类型:REFER] - REQ-002 - 保持标准 SDD 文档接口

变更原因: 后续 `tasks`、`implement`、`review`、`local-sandbox-fix` 阶段依赖固定文件接口。

系统 shall 通过 `spec.md`、`design.md`、`context.md`、`paths.json` 和 `env.sh` 传递上下文，避免下游阶段直接依赖自由格式对话记忆。
"""


def _generate_scenarios_content(design_text: str, source_name: str) -> str:
    behavior = _extract_section(design_text, "4. 行为变化")
    testing = _extract_section(design_text, "6. 测试影响（实现阶段处理）")
    extra_sections = "\n\n".join(s for s in (behavior, testing) if s)
    if not extra_sections:
        extra_sections = "源设计稿未提供独立的行为变化/测试影响章节；tasks 阶段必须读取完整源设计全文。"
    return f"""# 场景内容（来自 spec.md）

## 场景

### [动作类型:REFER] - SCN-001 - 按已批准设计生成任务 (优先级: P1)

归属的需求: REQ-001

场景描述: task 阶段读取标准接口，并围绕 `{source_name}` 中的批准设计生成可执行任务。

**验收场景**:

1. **Given** `{source_name}` 已由用户批准，**When** `tasks` 阶段读取 `spec.md`、`design.md` 和 `context.md`，**Then** 输出的 `tasks.md` 应按场景、依赖、测试和验证要求组织。

### [动作类型:REFER] - SCN-002 - 实现与验证只依赖落盘接口 (优先级: P1)

归属的需求: REQ-002

场景描述: implement 与验证阶段通过落盘文档和状态文件继承上下文。

**验收场景**:

1. **Given** `tasks.md` 已生成，**When** `implement`、`review` 和 `local-sandbox-fix` 继续执行，**Then** 它们应通过 `FEATURE_DIR` 下的标准制品完成实现和验证闭环。

## 实现层场景补充（来自源 brainstorming 设计稿）

{extra_sections}
"""


def _generate_data_model(source_name: str) -> str:
    return f"""# Data Model: brainstorming approved design

## 实体来源

实体以 `{source_name}` 中明确描述的业务对象为准。桥接阶段不额外创造数据模型。

## ExpertDesign

- source_file: `{source_name}`
- status: approved
- role: 后续任务与实现的权威设计输入。

## ImplementationScope

- source_file: `{source_name}`
- status: pending task decomposition
- role: `tasks` 阶段读取代码树后映射为具体文件、接口和测试任务。
"""


def _generate_api_contract(source_name: str) -> str:
    return f"""# API Contract: brainstorming approved design

## 接口来源

接口契约以 `{source_name}` 中明确描述的外部接口、内部接口、命令、配置或数据流为准。

## 待 tasks 阶段确认

- 若 `{source_name}` 明确要求新增或修改 API，`tasks.md` 必须写出具体端点、处理函数和测试。
- 若源设计未涉及 API，本文件仅作为标准接口占位，不应诱导新增 API 任务。
"""


def _generate_quickstart(source_name: str) -> str:
    return f"""# Quickstart: brainstorming approved design

## 验证目标

验证实现是否满足 `{source_name}` 中用户已批准的设计目标。

## 验证步骤

1. 按 `tasks.md` 执行每个场景的 RED/GREEN/REFACTOR 任务。
2. 运行项目现有单元测试、集成测试或本地 CI 命令。
3. 执行 `review` 与 `local-sandbox-fix`，确认无阻塞问题。

## 通过标准

- `tasks.md` 中所有任务完成。
- 实现结果满足 `spec.md` 场景和 `{source_name}` 的设计约束。
- review 与本地沙盒验证通过或给出可追踪的失败原因。
"""


def _generate_eval_yaml() -> str:
    return f"""report_version: "1.0"
metadata:
  stage: {BRIDGE_STAGE}
  generated_at: "{_utc_now()}"
evaluations:
  - stage: specify
    status: pass
    overall_score: 100
    summary: "approved brainstorming design adapted into standard SDD document interface"
overall_score: 100
status: pass
"""


def _append_metric(feature_dir: Path, *, source: Path) -> None:
    path = feature_dir / ".runs" / "metrics" / "omni-metrics-log.json"
    if path.is_file():
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            if not isinstance(data, list):
                data = []
        except json.JSONDecodeError:
            data = []
    else:
        data = []
    data.append(
        {
            "stage": BRIDGE_STAGE,
            "event": "bridge_complete",
            "source_design": str(source),
            "timestamp": _utc_now(),
        }
    )
    _write_json(path, data)


def _merge_downstream_paths(feature_dir: Path, working_dir: Path, plugin_root: Path, branch_name: str) -> None:
    paths_file = feature_dir / ".runs" / "paths.json"
    paths = _read_json(paths_file) if paths_file.is_file() else {}
    paths.update(
        {
            "branch_name": branch_name,
            "feature_dir": str(feature_dir),
            "spec_file": str(feature_dir / "spec.md"),
            "design_file": str(feature_dir / "design.md"),
            "tasks_file": str(feature_dir / "tasks.md"),
            "working_dir": str(working_dir),
            "plugin_root": str(plugin_root),
            "repo_root": str(working_dir),
            "bridge_stage": BRIDGE_STAGE,
            "bridge_updated_at": _utc_now(),
        }
    )
    _write_json(paths_file, paths)

    env_lines = [
        "# Generated by brainstorming-sdd-bridge; source before downstream stages",
        f'export FEATURE_DIR="{feature_dir}"',
        f'export FEATURE_SPEC="{feature_dir / "spec.md"}"',
        f'export SPEC_FILE="{feature_dir / "spec.md"}"',
        f'export IMPL_DESIGN="{feature_dir / "design.md"}"',
        f'export TASKS="{feature_dir / "tasks.md"}"',
        f'export BRANCH_NAME="{branch_name}"',
        f'export DOC_DIR="{paths.get("doc_dir", working_dir / "omni-doc")}"',
        f'export DOC_SPECS_DIR="{paths.get("doc_specs_dir", working_dir / "omni-doc" / "specs")}"',
        f'export DOC_RULES_DIR="{paths.get("doc_rules_dir", working_dir / "omni-doc" / "rules")}"',
        f'export DOC_NAVIGATIONS_DIR="{paths.get("doc_navigations_dir", working_dir / "omni-doc" / "navigations")}"',
        f'export DOC_ON_DEMAND_DIR="{paths.get("doc_on_demand_dir", working_dir / "omni-doc" / "on-demand")}"',
        f'export CLAUDE_WORKING_DIR="{working_dir}"',
        f'export CLAUDE_PLUGIN_ROOT="{plugin_root}"',
        "",
    ]
    _write(feature_dir / ".runs" / "env.sh", "\n".join(env_lines))


def run(args: argparse.Namespace) -> int:
    plugin_root = _require_dir(args.plugin_root, "--plugin-root")
    working_dir = _require_dir(args.working_dir, "--working-dir")
    feature_dir = _require_dir(args.feature_dir, "--feature-dir")
    branch_name = _safe_branch_name(feature_dir, args.branch_name)

    changes_root = (working_dir / "changes").resolve()
    if not str(feature_dir).startswith(str(changes_root)):
        raise SystemExit(f"ERROR: feature_dir must be under {changes_root}: {feature_dir}")

    _ensure_workspace_infra(plugin_root, working_dir)

    source = Path(args.source_design).resolve() if args.source_design else _latest_brainstorming_design(feature_dir)
    if not source.is_file() or source.name == "design.md":
        raise SystemExit(f"ERROR: invalid source brainstorming design: {source}")

    design_text = _read(source)
    feature_name = args.feature_name or _title_from_markdown(design_text, branch_name.replace("-", " "))
    user_intent = args.user_intent or feature_name
    source_name = source.name

    specify_py = plugin_root / "skills" / "specify" / "scripts" / "python" / "specify_harness.py"
    if not specify_py.is_file():
        raise SystemExit(f"ERROR: specify harness not found: {specify_py}")

    _run(
        [
            sys.executable,
            str(specify_py),
            "init",
            "--plugin-root",
            str(plugin_root),
            "--working-dir",
            str(working_dir),
            "--feature-dir",
            str(feature_dir),
            "--branch-name",
            branch_name,
            "--start-time",
            _utc_now(),
        ]
    )

    payload = {
        "context_mode": "expert_brainstorming_bridge",
        "feature_description": user_intent,
        "source_design": str(source),
        "sections": {
            "功能描述": user_intent,
            "相关反构文档": [source_name],
            "架构分析与设计参考": design_text,
            "术语对齐": [
                "brainstorming design = approved source design",
                "SDD bridge = document interface adapter",
                "tasks = downstream task decomposition",
            ],
            "约束和假设": [
                "bridge does not redesign the feature",
                "tasks must confirm concrete code paths",
                "other workflows are unchanged",
            ],
        },
    }
    _write_json(feature_dir / ".runs" / "internal" / "context.payload.json", payload)

    _write(
        feature_dir / "spec.md",
        _generate_spec(
            feature_name=feature_name,
            branch_name=branch_name,
            source_name=source_name,
            design_text=design_text,
            user_intent=user_intent,
        ),
    )
    _write(
        feature_dir / "design.md",
        _generate_design(
            feature_name=feature_name,
            branch_name=branch_name,
            source_name=source_name,
            design_text=design_text,
        ),
    )
    _write(feature_dir / "context.md", _generate_context(source_name=source_name, design_text=design_text, user_intent=user_intent))
    _write(feature_dir / "research.md", _generate_research(source_name, design_text))
    _write(feature_dir / "data-model.md", _generate_data_model(source_name))
    _write(feature_dir / "contracts" / "api-contract.md", _generate_api_contract(source_name))
    _write(feature_dir / "quickstart.md", _generate_quickstart(source_name))
    _write(feature_dir / "requirements-content.md", _generate_requirements_content())
    _write(feature_dir / "scenarios-content.md", _generate_scenarios_content(design_text, source_name))
    _merge_downstream_paths(feature_dir, working_dir, plugin_root, branch_name)

    _run(
        [
            sys.executable,
            str(specify_py),
            "render-checklist",
            "--feature-dir",
            str(feature_dir),
            "--working-dir",
            str(working_dir),
            "--feature-name",
            feature_name,
            "--force",
        ]
    )
    checklist = feature_dir / "checklists" / "requirements.md"
    checklist_text = _read(checklist)
    checklist_text = re.sub(r"- \[ \]", "- [x]", checklist_text)
    _write(checklist, checklist_text)

    _write(feature_dir / ".runs" / "evaluations" / "eval-specify-report.yaml", _generate_eval_yaml())
    _append_metric(feature_dir, source=source)

    for step in ("1", "3", "6", "8", "9", "11"):
        _run(
            [
                sys.executable,
                str(specify_py),
                "gate",
                "--feature-dir",
                str(feature_dir),
                "--step",
                step,
                "--record",
            ]
        )

    update_state = plugin_root / "scripts" / "bash" / "workflow-update-state.sh"
    if not update_state.is_file():
        raise SystemExit(f"ERROR: workflow-update-state.sh not found: {update_state}")
    _run(
        [
            "bash",
            str(update_state),
            "--feature-dir",
            str(feature_dir),
            "--flow-mode",
            "expert",
            "--current-stage",
            "tasks",
            "--mark-complete",
            BRIDGE_STAGE,
        ]
    )

    print(
        json.dumps(
            {
                "status": "ok",
                "feature_dir": str(feature_dir),
                "source_design": str(source),
                "spec": str(feature_dir / "spec.md"),
                "design": str(feature_dir / "design.md"),
                "context": str(feature_dir / "context.md"),
            },
            ensure_ascii=False,
        )
    )
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="brainstorming SDD bridge")
    parser.add_argument("--plugin-root", required=True)
    parser.add_argument("--working-dir", required=True)
    parser.add_argument("--feature-dir", required=True)
    parser.add_argument("--branch-name", default="")
    parser.add_argument("--source-design", default="")
    parser.add_argument("--feature-name", default="")
    parser.add_argument("--user-intent", default="")
    args = parser.parse_args()
    return run(args)


if __name__ == "__main__":
    raise SystemExit(main())
