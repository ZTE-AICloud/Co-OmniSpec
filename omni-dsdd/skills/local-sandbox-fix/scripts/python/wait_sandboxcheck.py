#!/usr/bin/env python3
"""轮询 local-sandboxcheck 执行进度，直到 result.json 或 log marker 出现。"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

DONE_MARKERS = [
    "==================本地沙盒检查完成=================",
    "**本地沙盒检查最终结果如下**",
]
SESSION_START_MARKER = "=== 执行开始 ==="


def _read_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _valid_result_json(path: Path) -> bool:
    if not path.is_file():
        return False
    try:
        json.loads(path.read_text(encoding="utf-8"))
        return True
    except (json.JSONDecodeError, OSError):
        return False


def log_tail_since_session(run_log: Path, session: Dict[str, Any]) -> str:
    offset = int(session.get("run_log_offset", 0) or 0)
    if not run_log.is_file():
        return ""
    data = run_log.read_bytes()
    if offset > len(data):
        offset = 0
    return data[offset:].decode("utf-8", errors="replace")


def is_done(result_json: Path, tail_text: str) -> Tuple[bool, str]:
    if _valid_result_json(result_json):
        return True, "result_json"
    if any(marker in tail_text for marker in DONE_MARKERS):
        return True, "log_marker"
    return False, ""


def process_alive(pid: int) -> bool:
    if pid <= 0:
        return False
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


def read_pid(pid_file: Optional[Path]) -> int:
    if pid_file is None or not pid_file.is_file():
        return 0
    try:
        return int(pid_file.read_text(encoding="utf-8").strip())
    except (ValueError, OSError):
        return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Wait for local-sandboxcheck completion")
    parser.add_argument("--run-log", required=True)
    parser.add_argument("--result-json", required=True)
    parser.add_argument("--session-file", required=True)
    parser.add_argument("--pid-file", default="")
    parser.add_argument("--stale-timeout", type=int, default=120)
    parser.add_argument("--global-timeout", type=int, default=5400)
    parser.add_argument("--poll-interval", type=int, default=5)
    args = parser.parse_args()

    run_log = Path(args.run_log).resolve()
    result_json = Path(args.result_json).resolve()
    session_file = Path(args.session_file).resolve()
    pid_file = Path(args.pid_file).resolve() if args.pid_file else None

    if not session_file.is_file():
        print(json.dumps({"error": f"session file missing: {session_file}"}, ensure_ascii=False))
        return 1

    session = _read_json(session_file)
    pid = read_pid(pid_file)
    poll = max(1, args.poll_interval)
    stale_timeout = max(1, args.stale_timeout)
    global_timeout = max(1, args.global_timeout)

    start = time.time()
    last_mtime = run_log.stat().st_mtime if run_log.is_file() else 0.0
    last_change_time = start

    while True:
        now = time.time()
        tail = log_tail_since_session(run_log, session)
        done, reason = is_done(result_json, tail)
        if done:
            out = {
                "status": "ok",
                "reason": reason,
                "wait_sec": int(now - start),
                "result_json": str(result_json),
            }
            print(json.dumps(out, ensure_ascii=False))
            return 0

        if now - start > global_timeout and not result_json.is_file():
            print(json.dumps({"error": "GLOBAL_TIMEOUT: 90min 内未产出 result.json"}, ensure_ascii=False))
            return 11

        if run_log.is_file():
            mtime = run_log.stat().st_mtime
            if mtime != last_mtime:
                last_mtime = mtime
                last_change_time = now
            elif now - last_change_time > stale_timeout:
                print(json.dumps({"error": "STALE_LOG: run.log 超过 120s 未更新"}, ensure_ascii=False))
                return 10
        elif now - last_change_time > stale_timeout:
            print(json.dumps({"error": "STALE_LOG: run.log 不存在且超时"}, ensure_ascii=False))
            return 10

        if pid and not process_alive(pid) and not result_json.is_file():
            print(json.dumps({"error": "CI_PROCESS_DIED"}, ensure_ascii=False))
            return 12

        time.sleep(poll)


if __name__ == "__main__":
    sys.exit(main())
