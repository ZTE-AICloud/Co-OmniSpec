"""
SDDEval 代码变更采集脚本
用于采集 SDD 流程执行后的代码变更信息，生成评测所需的 JSON 文件。

用法:
    python collect.py [--repo-root <path>] [--target-dir <dir>] [--branch <branch_name>] [--output <path>]
"""

import argparse
import json
import subprocess
import os
from pathlib import Path
from typing import Dict, List, Set, Optional


# API 配置
API_URL = "https://maas-apigateway.dt.zte.com.cn/model/ai-ide/model-separation/v1/chat/completions"
API_KEY = "a5ec9c73-4d21-44e0-ba49-180eed598e27"
MODEL_NAME = "glm4.6"
API_TIMEOUT = 600
LLM_MAX_TOKENS = 16000


def run_git(repo_root: Path, args: List[str], check: bool = True) -> str:
    """执行 git 命令并返回输出"""
    cmd = ["git", "-C", str(repo_root)] + args
    result = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if check and result.returncode != 0:
        raise RuntimeError(f"git command failed: {' '.join(cmd)}\n{result.stderr}")
    return result.stdout


def get_current_branch(repo_root: Path) -> Optional[str]:
    """获取当前分支名称"""
    try:
        branch = run_git(repo_root, ["branch", "--show-current"]).strip()
        if branch:
            return branch
        # 如果 --show-current 返回空，尝试其他方式
        branch = run_git(repo_root, ["rev-parse", "--abbrev-ref", "HEAD"]).strip()
        return branch if branch else None
    except Exception:
        return None


def parse_feature_infos(tasks_md: Path) -> List[str]:
    """
    从 tasks.md 中提取所有 '**目的**: xxx' 行，作为 feature_infos。
    """
    feature_infos: List[str] = []
    if not tasks_md.exists():
        return feature_infos

    lines = tasks_md.read_text(encoding="utf-8", errors="replace").splitlines()
    for line in lines:
        text = line.strip()
        if text.startswith("**目的**:"):
            purpose = text.split(":", 1)[1].strip()
            if purpose:
                feature_infos.append(purpose)
    return feature_infos


def get_changed_files(repo_root: Path, target_dir: str) -> Set[str]:
    """
    获取目标目录下所有变更文件（暂存、未暂存、未跟踪）。
    """
    changed: Set[str] = set()

    # Unstaged + staged tracked files
    for args in (
        ["diff", "--name-only", "--", target_dir],
        ["diff", "--cached", "--name-only", "--", target_dir],
    ):
        out = run_git(repo_root, args, check=False)
        for line in out.splitlines():
            fp = line.strip()
            if fp:
                changed.add(fp)

    # Untracked files inside target dir
    out_untracked = run_git(
        repo_root,
        ["ls-files", "--others", "--exclude-standard", "--", target_dir],
        check=False,
    )
    for line in out_untracked.splitlines():
        fp = line.strip()
        if fp:
            changed.add(fp)

    return changed


def split_diff_by_file(diff_text: str) -> Dict[str, str]:
    """
    将 git unified diff 按文件拆分：
    返回 { "path/to/file": "diff --git ... (该文件完整patch)" }
    """
    blocks: Dict[str, str] = {}
    current_lines: List[str] = []
    current_path: str = ""

    for line in diff_text.splitlines():
        if line.startswith("diff --git "):
            if current_path and current_lines:
                blocks[current_path] = "\n".join(current_lines).strip()
            current_lines = [line]
            current_path = ""
            continue

        if current_lines and line.startswith("+++ b/"):
            current_path = line[len("+++ b/"):].strip()

        if current_lines:
            current_lines.append(line)

    if current_path and current_lines:
        blocks[current_path] = "\n".join(current_lines).strip()

    return blocks


def extract_code_snippets_from_patch(patch_text: str) -> List[str]:
    """
    从单文件 patch 中提取"实际代码变更内容"：
    - 去掉 diff/index/---/+++/@@ 等元信息
    - 保留变更行（+/-，但不包含文件头 +++/---）
    - 连续变更行合并为一个片段
    """
    snippets: List[str] = []
    current: List[str] = []

    for line in patch_text.splitlines():
        # 跳过 patch 元信息
        if (
            line.startswith("diff --git ")
            or line.startswith("index ")
            or line.startswith("--- ")
            or line.startswith("+++ ")
            or line.startswith("@@ ")
        ):
            if current:
                snippets.append("\n".join(current).strip())
                current = []
            continue

        # 保留真正变更代码行
        if line.startswith("+") or line.startswith("-"):
            current.append(line)
        else:
            # 碰到上下文行，结束当前变更片段
            if current:
                snippets.append("\n".join(current).strip())
                current = []

    if current:
        snippets.append("\n".join(current).strip())

    # 清理空片段
    return [s for s in snippets if s]


def build_code_blocks(repo_root: Path, target_dir: str) -> Dict[str, List[str]]:
    """
    生成 code_blocks:
      key: 文件路径
      value: 变更内容列表（每个元素一段文本）
    """
    code_blocks: Dict[str, List[str]] = {}

    # 1) 先拿 target_dir 下 staged/unstaged 的真实 patch，再按文件拆分
    staged_all = run_git(repo_root, ["diff", "--cached", "-U3", "--", target_dir], check=False)
    unstaged_all = run_git(repo_root, ["diff", "-U3", "--", target_dir], check=False)
    staged_map = split_diff_by_file(staged_all)
    unstaged_map = split_diff_by_file(unstaged_all)

    # 2) 合并文件列表（确保 key 正确）
    changed_files = sorted(get_changed_files(repo_root, target_dir))
    all_files = sorted(set(changed_files) | set(staged_map.keys()) | set(unstaged_map.keys()))

    for rel_path in all_files:
        file_blocks: List[str] = []
        if rel_path in staged_map and staged_map[rel_path]:
            file_blocks.extend(extract_code_snippets_from_patch(staged_map[rel_path]))
        if rel_path in unstaged_map and unstaged_map[rel_path]:
            file_blocks.extend(extract_code_snippets_from_patch(unstaged_map[rel_path]))

        # 只保留真实变更内容；没有真实 patch 的文件不输出到 code_blocks
        if file_blocks:
            code_blocks[rel_path] = file_blocks

    return code_blocks


def build_payload(repo_root: Path, target_dir: str, tasks_md: Path) -> Dict:
    return {
        "api": {
            "url": API_URL,
            "key": API_KEY,
            "model_name": MODEL_NAME,
            "timeout": API_TIMEOUT,
            "max_tokens": LLM_MAX_TOKENS,
            "temperature": 0.1,
        },
        "input": {
            "feature_infos": parse_feature_infos(tasks_md),
            "code_blocks": build_code_blocks(repo_root, target_dir),
            "code_answers": [],
            "output": None,
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="SDDEval 代码变更采集 - 生成评测 JSON")
    parser.add_argument(
        "--repo-root",
        default=".",
        help="Git repository root path (default: .)",
    )
    parser.add_argument(
        "--target-dir",
        default="networking_zte",
        help="目标目录，默认: networking_zte",
    )
    parser.add_argument(
        "--branch",
        default=None,
        help="SDD 分支名称，默认自动检测",
    )
    parser.add_argument(
        "--output",
        default=None,
        help="输出文件路径，默认: changes/<branch>/evalset/config.result.json",
    )
    args = parser.parse_args()

    repo_root = Path(args.repo_root).resolve()

    # 获取分支名
    branch = args.branch
    if not branch:
        branch = get_current_branch(repo_root)
        if not branch:
            raise ValueError("无法获取当前分支名，请通过 --branch 参数指定")

    # 确定 tasks.md 路径
    tasks_md = repo_root / "changes" / branch / "tasks.md"
    if not tasks_md.exists():
        raise FileNotFoundError(f"tasks.md 不存在: {tasks_md}")

    # 确定输出目录和文件
    output_dir = repo_root / "changes" / branch / "evalset"
    if args.output:
        output = Path(args.output)
    else:
        output_dir.mkdir(parents=True, exist_ok=True)
        output = output_dir / "config.result.json"

    # 生成 payload
    payload = build_payload(repo_root=repo_root, target_dir=args.target_dir, tasks_md=tasks_md)

    # 写入文件
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=4), encoding="utf-8")

    print(f"Generated: {output}")
    print(f"feature_infos: {len(payload['input']['feature_infos'])}")
    print(f"code_blocks files: {len(payload['input']['code_blocks'])}")


if __name__ == "__main__":
    main()
