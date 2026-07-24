#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
接口详情文档文件名/frontmatter 校验与修复脚本（质量门禁版）

目标：
1. 校验接口详情文档文件名是否符合规范：{接口ID}_{中文业务简要总结}.md
2. 按 interface-list.json 的 business_name/name 进行“按标准修改”（重命名 + frontmatter 回写 id/name）
3. 二次校验：重命名/回写后仍不合规则直接报错（退出码非 0），用于质量门禁

退出码：
- 0：全量合规（可能发生重命名/回写，但最终校验通过）
- 1：脚本执行错误
- 2：合规校验不通过（已尝试修复，但仍存在不合规项）
"""

import argparse
import json
import os
import re
import sys
from datetime import datetime, timezone
from typing import Any, Dict, List, Tuple, Optional, Set


INTERFACE_LIST_REL = ".cache/reverse/interfaces/interface-list.json"
DOCS_DIR_REL = "omni-doc/specs/interfaces"
REPORT_REL = ".cache/reverse/interfaces/interface-filename-validation-report.json"

# Linux 文件名常见危险字符；同时去掉控制字符
INVALID_FILENAME_CHARS = r'[\\/:*?"<>|\x00-\x1f]'


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def load_json(path: str) -> Any:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_json(path: str, data: Dict[str, Any]) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def sanitize_suffix(text: str) -> str:
    s = re.sub(INVALID_FILENAME_CHARS, "_", text or "")
    s = re.sub(r"\s+", "_", s)
    s = re.sub(r"_+", "_", s).strip("._ ")
    return s or "未命名接口"


def parse_filename(filename: str) -> Tuple[str, str]:
    """
    从文件名解析 interface_id 和 suffix（不含 .md）
    """
    name = filename[:-3] if filename.endswith(".md") else filename
    # 新标准：API_001_事务创建调度回调接口.md
    m = re.match(r"^(API_\d{3})_(.+)$", name)
    if m:
        return m.group(1).strip(), m.group(2).strip()
    # 兼容旧标准：API-001-xxx.md 或 API-001_xxx.md
    m = re.match(r"^(API-\d{3})[_-](.+)$", name)
    if m:
        return m.group(1).replace("-", "_").strip(), m.group(2).strip()
    return "", ""


def ensure_unique_target(path: str) -> str:
    if not os.path.exists(path):
        return path
    base, ext = os.path.splitext(path)
    idx = 1
    while True:
        candidate = f"{base}-{idx}{ext}"
        if not os.path.exists(candidate):
            return candidate
        idx += 1


def parse_frontmatter(text: str) -> Optional[Tuple[str, str, str]]:
    """
    返回(frontmatter_text, frontmatter_prefix, frontmatter_suffix)
    - frontmatter_prefix: "---\n"
    - frontmatter_suffix: "\n---\n"（保持简化一致格式）
    """
    # 简单解析：要求 frontmatter 必须位于文件开头
    if not text.startswith("---"):
        return None
    lines = text.splitlines(keepends=True)
    if not lines or lines[0].strip() != "---":
        return None

    end_idx = None
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            end_idx = i
            break
    if end_idx is None:
        return None

    # lines[1:end_idx] 是内容
    fm_text = "".join(lines[1:end_idx])
    prefix = lines[0]  # usually '---\n'
    suffix = "".join(lines[end_idx:end_idx + 1])  # usually '---\n'
    return fm_text, prefix, suffix


def update_frontmatter_id_name(md_path: str, interface_id: str, desired_name: str) -> Tuple[bool, str]:
    """
    返回 (changed, error_message)
    - changed: 是否发生写入
    - error_message: 若失败则返回原因；成功则返回 ''
    """
    try:
        with open(md_path, "r", encoding="utf-8") as f:
            original = f.read()
    except Exception as exc:  # noqa: BLE001
        return False, f"读取失败: {exc}"

    parsed = parse_frontmatter(original)
    if not parsed:
        return False, "缺少或无法解析 YAML frontmatter（frontmatter 必须位于文件开头）"

    fm_text, prefix, suffix = parsed

    new_fm = fm_text
    # 更新 id/name，如果不存在则追加到末尾
    id_re = re.compile(r"^id:\s*.*$", re.MULTILINE)
    name_re = re.compile(r"^name:\s*.*$", re.MULTILINE)

    if id_re.search(new_fm):
        new_fm = id_re.sub(f"id: {interface_id}", new_fm)
    else:
        new_fm = new_fm.rstrip() + f"\nid: {interface_id}\n"

    if name_re.search(new_fm):
        new_fm = name_re.sub(f"name: {desired_name}", new_fm)
    else:
        new_fm = new_fm.rstrip() + f"\nname: {desired_name}\n"

    new_text = f"{prefix}{new_fm}{suffix}"
    # frontmatter 结束符之后需要追加原始剩余内容
    # 重新切分：prefix+fm+suffix 在原始中的范围
    # 为避免复杂解析，这里通过再次找到 end_idx 来拼回正文
    lines = original.splitlines(keepends=True)
    # 找到 second '---'
    end_idx = None
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            end_idx = i
            break
    if end_idx is None:
        return False, "无法定位 frontmatter 结束符"

    body = "".join(lines[end_idx + 1:])
    new_text = f"{prefix}{new_fm}{suffix}{body}"

    if new_text == original:
        return False, ""

    try:
        with open(md_path, "w", encoding="utf-8") as f:
            f.write(new_text)
    except Exception as exc:  # noqa: BLE001
        return False, f"写入失败: {exc}"

    return True, ""


def read_frontmatter_id_name(md_path: str) -> Tuple[str, str, str]:
    """
    返回 (interface_id, name, error_message)
    """
    try:
        with open(md_path, "r", encoding="utf-8") as f:
            text = f.read()
    except Exception as exc:  # noqa: BLE001
        return "", "", f"读取失败: {exc}"

    parsed = parse_frontmatter(text)
    if not parsed:
        return "", "", "缺少或无法解析 YAML frontmatter"

    fm_text, _, _ = parsed
    id_re = re.compile(r"^id:\s*(.+)\s*$", re.MULTILINE)
    name_re = re.compile(r"^name:\s*(.+)\s*$", re.MULTILINE)
    iid_m = id_re.search(fm_text)
    name_m = name_re.search(fm_text)
    iid = iid_m.group(1).strip() if iid_m else ""
    nm = name_m.group(1).strip() if name_m else ""
    return iid, nm, ""


def main() -> int:
    parser = argparse.ArgumentParser(description="接口详情文档文件名强制校验与修复")
    parser.add_argument("repo_root", help="仓库根目录")
    args = parser.parse_args()

    repo_root = os.path.abspath(args.repo_root)
    if not os.path.isdir(repo_root):
        print(f"错误: 仓库根目录不存在: {repo_root}", file=sys.stderr)
        return 1

    interface_list_file = os.path.join(repo_root, INTERFACE_LIST_REL)
    docs_dir = os.path.join(repo_root, DOCS_DIR_REL)
    report_file = os.path.join(repo_root, REPORT_REL)

    if not os.path.exists(interface_list_file):
        print(f"错误: 接口清单不存在: {interface_list_file}", file=sys.stderr)
        return 1
    if not os.path.isdir(docs_dir):
        print(f"错误: 接口文档目录不存在: {docs_dir}", file=sys.stderr)
        return 1

    interface_data = load_json(interface_list_file)
    interfaces = interface_data.get("interfaces", [])
    if not isinstance(interfaces, list):
        print("错误: interface-list.json 格式错误（interfaces 不是数组）", file=sys.stderr)
        return 1

    # interface_id -> 期望（用于文件名后缀）
    expected_suffix: Dict[str, str] = {}
    # interface_id -> 期望（用于 frontmatter name）
    expected_name_raw: Dict[str, str] = {}
    for item in interfaces:
        if not isinstance(item, dict):
            continue
        iid = str(item.get("interface_id", "")).strip()
        if not iid:
            continue
        raw_name = str(item.get("business_name", "")).strip() or str(item.get("name", "")).strip() or "未命名接口"
        expected_name_raw[iid] = raw_name
        expected_suffix[iid] = sanitize_suffix(raw_name)

    expected_ids: Set[str] = set(expected_suffix.keys())
    api_md_files: List[str] = []
    for name in os.listdir(docs_dir):
        if not name.endswith(".md"):
            continue
        if name == "接口清单.md":
            continue
        api_md_files.append(name)

    invalid_name_files: List[str] = []
    # iid -> files
    docs_by_iid: Dict[str, List[str]] = {}
    api_name_like_re = re.compile(r"^API[_-]\d{3}[_-].+\.md$|^API-\d{3}_.+\.md$|^API_\d{3}_.+\.md$")

    for name in sorted(api_md_files):
        iid, suffix = parse_filename(name)
        if iid:
            if iid in expected_ids:
                docs_by_iid.setdefault(iid, []).append(name)
            else:
                invalid_name_files.append(name)
            continue
        # 解析不到 interface_id，但文件名看起来像 API 文档 -> 视为非法
        if api_name_like_re.match(name):
            invalid_name_files.append(name)

    renamed: List[Dict[str, str]] = []
    frontmatter_updated: List[Dict[str, str]] = []
    errors: List[str] = []
    missing_ids: List[str] = []

    # 修复：保证每个 interface_id 只存在 1 个合规命名的文档
    for iid in sorted(expected_ids):
        correct_suffix = expected_suffix[iid]
        expected_filename = f"{iid}_{correct_suffix}.md"

        candidates = docs_by_iid.get(iid, [])
        if not candidates:
            missing_ids.append(iid)
            continue

        correct_files = [f for f in candidates if f == expected_filename]

        if correct_files:
            # 已存在正确文件名，但如果还有其它文件 -> 认为重复，直接失败
            if len(candidates) != 1:
                errors.append(f"接口 {iid} 存在重复详情文档（期望 {expected_filename}，实际 {candidates}）")
                continue
            file_name = expected_filename
        else:
            # 不存在正确文件名，只允许恰好 1 个候选（否则重复，直接失败）
            if len(candidates) != 1:
                errors.append(f"接口 {iid} 文档命名不合规且存在多个候选（{candidates}），需要人工清理后重跑")
                continue
            old_name = candidates[0]
            old_path = os.path.join(docs_dir, old_name)
            new_path = os.path.join(docs_dir, expected_filename)
            if os.path.exists(new_path):
                errors.append(f"接口 {iid} 期望目标文件已存在，无法重命名（old={old_name} to={expected_filename}）")
                continue
            os.rename(old_path, new_path)
            renamed.append({"from": old_name, "to": expected_filename})
            file_name = expected_filename

        md_path = os.path.join(docs_dir, file_name)
        # 回写 frontmatter id/name，保证接口清单构建时字段一致
        changed, err = update_frontmatter_id_name(md_path, iid, expected_name_raw[iid])
        if err:
            errors.append(f"接口 {iid} frontmatter 写入失败: {err}")
        elif changed:
            frontmatter_updated.append({"file": file_name, "id": iid, "name": expected_name_raw[iid]})

    # 若存在明显非法/API 文档，直接失败（避免下游混入残留产物）
    if invalid_name_files:
        errors.append(f"发现非法接口文档文件名（不在 interface-list.json 中或无法解析）：{invalid_name_files[:50]}{'...' if len(invalid_name_files) > 50 else ''}")

    # 二次校验：确保所有 expected iid 都有且只有一个合规文件
    final_missing: List[str] = []
    duplicates: List[str] = []

    for iid in sorted(expected_ids):
        expected_filename = f"{iid}_{expected_suffix[iid]}.md"
        expected_path = os.path.join(docs_dir, expected_filename)
        if not os.path.exists(expected_path):
            final_missing.append(iid)
            continue
        # 再检查同 iid 是否存在其它文件
        iid_files = []
        for name in os.listdir(docs_dir):
            if not name.endswith(".md") or name == "接口清单.md":
                continue
            parsed_iid, _ = parse_filename(name)
            if parsed_iid == iid:
                iid_files.append(name)
        if len(iid_files) != 1:
            duplicates.append(f"{iid}: {iid_files}")

        # frontmatter 字段校验
        fr_id, fr_name, fr_err = read_frontmatter_id_name(expected_path)
        if fr_err:
            errors.append(f"接口 {iid} frontmatter 读取失败: {fr_err}")
        if fr_id != iid:
            errors.append(f"接口 {iid} frontmatter id 不一致: expected={iid} actual={fr_id}")
        # name 允许轻微空白差异
        if expected_name_raw[iid].strip() != (fr_name or "").strip():
            errors.append(f"接口 {iid} frontmatter name 不一致: expected={expected_name_raw[iid]} actual={fr_name}")

    if final_missing:
        errors.append(f"缺失合规详情文档（final_missing）: {final_missing[:50]}{'...' if len(final_missing) > 50 else ''}")
    if duplicates:
        errors.append(f"接口存在重复详情文档（duplicates）: {duplicates[:20]}{'...' if len(duplicates) > 20 else ''}")

    ok = len(errors) == 0

    report = {
        "version": "2.0",
        "generated_at": utc_now(),
        "docs_dir": docs_dir,
        "total_interfaces": len(expected_ids),
        "renamed_count": len(renamed),
        "frontmatter_updated_count": len(frontmatter_updated),
        "invalid_name_files_count": len(invalid_name_files),
        "invalid_name_files_sample": invalid_name_files[:50],
        "missing_ids": missing_ids[:50],
        "errors_count": len(errors),
        "errors_sample": errors[:50],
        "renamed": renamed,
        "frontmatter_updated": frontmatter_updated,
        "filename_rule": "{接口ID}_{中文业务简要总结}.md",
        "frontmatter_rule": {"id": "API_XXX", "name": "应与 interface-list.json 的 business_name/name 一致"},
        "quality_gate": "用于生成接口清单.md 前的门禁"
    }
    save_json(report_file, report)

    print(json.dumps({
        "ok": ok,
        "report": report_file,
        "renamed_count": len(renamed),
        "frontmatter_updated_count": len(frontmatter_updated),
        "invalid_name_files_count": len(invalid_name_files),
        "errors_count": len(errors),
        "missing_count": len(missing_ids),
    }, ensure_ascii=False))

    if ok:
        return 0
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
