#!/usr/bin/env python3
"""统一解析 omni-dsdd 共享层根目录。

前提：omni-reverse 与 omni-dsdd 安装在同一 marketplace 下且目录并列。
用法：
    from pathlib import Path
    import sys
    sys.path.insert(0, str(Path(__file__).parent))  # 若非作为包导入
    from resolve_dsdd_root import dsdd_root
    DSDD = dsdd_root()
"""
import os
import sys
from pathlib import Path


def dsdd_root() -> Path:
    pr = os.environ.get("CLAUDE_PLUGIN_ROOT")
    if pr:
        cand = Path(pr).parent / "omni-dsdd"
    else:
        # 本脚本位于 omni-reverse/lib -> parents[2] = marketplace 根
        cand = Path(__file__).resolve().parents[2] / "omni-dsdd"
    if not (cand / "scripts").is_dir() or not (cand / "omni-infra").is_dir():
        sys.exit(
            f"ERROR: 未找到共享插件 omni-dsdd（{cand}）。"
            f"omni-reverse 需与 omni-dsdd 同 marketplace 安装。"
        )
    return cand.resolve()


if __name__ == "__main__":
    print(dsdd_root())
