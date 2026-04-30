#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
reverse_syntax_parser 工具模块
提供 logger、简单配置、LLM 调用（使用 requests，无 reverse 依赖）
"""

import json
import logging
import os
import re
import time
from pathlib import Path
from typing import Any, Dict, Optional

# 可选：用于从本仓库 llm-config.yaml 读取 LLM 配置
try:
    import yaml as _yaml
except ImportError:
    _yaml = None

try:
    import requests
except ImportError:
    requests = None


def get_logger(name: str = "reverse_syntax_parser") -> logging.Logger:
    """获取 logger"""
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(
            logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
        )
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
    return logger


def _substitute_env(s: str) -> str:
    """将 ${VAR:default} 或 ${VAR} 替换为环境变量值（与 llm-config.yaml 占位符一致）"""
    if not isinstance(s, str):
        return s
    pattern = re.compile(r"\$\{([^}]+)\}")

    def repl(m):
        inner = m.group(1)
        if ":" in inner:
            var, default = inner.split(":", 1)
            return os.environ.get(var, default)
        return os.environ.get(inner, m.group(0))

    return pattern.sub(repl, s)


def _load_llm_from_yaml(config_path: Path) -> Optional[Dict[str, Any]]:
    """
    从本仓库 llm-config.yaml 读取 llm 段（若存在且可解析）。
    返回与 load_config_from_env 同结构的 dict，或 None。
    """
    if _yaml is None:
        return None
    path = Path(config_path)
    if not path.exists():
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = _yaml.safe_load(f)
    except Exception:
        return None
    llm = (data or {}).get("llm")
    if not llm or not isinstance(llm, dict):
        return None
    api_url = _substitute_env(str(llm.get("api_url", "")))
    api_key = _substitute_env(str(llm.get("api_key", "")))
    return {
        "api_url": api_url or os.environ.get("OPENAI_API_URL", os.environ.get("OPENAI_URL", "")),
        "api_key": api_key or os.environ.get("OPENAI_API_KEY", ""),
        "model": _substitute_env(str(llm.get("model", ""))) or os.environ.get("OPENAI_MODEL", "gpt-4"),
        "temperature": float(llm.get("temperature", 0.2)),
        "max_tokens": int(llm.get("max_tokens", 4096)),
        "timeout": int(llm.get("timeout", 120)),
        "max_concurrent": int(llm.get("max_concurrent", 20)),
        "max_retries": int(llm.get("max_retries", 3)),
    }


def load_config_from_env(base_dir: Optional[str] = None) -> Dict[str, Any]:
    """
    加载 LLM 配置：先读环境变量；再尝试本仓库同目录下的 llm-config.yaml（不依赖 reverse）。
    """
    defaults = {
        "api_url": os.environ.get(
            "OPENAI_API_URL",
            os.environ.get("OPENAI_URL", "https://api.openai.com/v1/chat/completions"),
        ),
        "api_key": os.environ.get("OPENAI_API_KEY", ""),
        "model": os.environ.get("OPENAI_MODEL", "gpt-4"),
        "temperature": float(os.environ.get("OPENAI_TEMPERATURE", "0.2")),
        "max_tokens": int(os.environ.get("OPENAI_MAX_TOKENS", "4096")),
        "timeout": int(os.environ.get("OPENAI_TIMEOUT", "120")),
        "max_concurrent": int(os.environ.get("OPENAI_MAX_CONCURRENT", "20")),
        "max_retries": int(os.environ.get("OPENAI_MAX_RETRIES", "3")),
    }

    # 本仓库配置：与 utils.py 同目录的 llm-config.yaml（安装后为 scripts/python/reverse_syntax_parser/llm-config.yaml）
    local_config = Path(__file__).resolve().parent / "llm-config.yaml"
    file_cfg = _load_llm_from_yaml(local_config)
    if file_cfg:
        for k, v in file_cfg.items():
            if v is not None and v != "":
                defaults[k] = v

    return defaults


def call_llm_with_prompts(
    system_prompt: str,
    user_prompt: str,
    config: Optional[Dict[str, Any]] = None,
    logger: Optional[logging.Logger] = None,
) -> str:
    """
    使用 requests 调用 OpenAI 兼容 API
    仅依赖 stdlib + requests
    """
    if requests is None:
        raise ImportError("requests 未安装，请执行: pip install requests")

    cfg = config or load_config_from_env()
    log = logger or get_logger()

    api_url = cfg.get("api_url", "").rstrip("/")
    if not api_url.endswith("/chat/completions"):
        api_url = f"{api_url.rstrip('/')}/chat/completions"

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {cfg.get('api_key', '')}",
    }

    payload = {
        "model": cfg.get("model", "gpt-4"),
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": cfg.get("temperature", 0.2),
        "max_tokens": cfg.get("max_tokens", 4096),
    }

    timeout = cfg.get("timeout", 120)
    max_retries = cfg.get("max_retries", 3)
    last_error = None

    for attempt in range(max_retries + 1):
        try:
            resp = requests.post(
                api_url,
                headers=headers,
                json=payload,
                timeout=timeout,
            )
            resp.raise_for_status()
            data = resp.json()
            choices = data.get("choices", [])
            if choices:
                return choices[0].get("message", {}).get("content", "")
            return ""
        except requests.RequestException as e:
            last_error = e
            err_str = str(e).lower()
            should_retry = (
                "rate limit" in err_str
                or "429" in err_str
                or "timeout" in err_str
                or "503" in err_str
                or "502" in err_str
                or "504" in err_str
            ) and attempt < max_retries
            if not should_retry:
                log.error("LLM 调用失败: %s", e)
                raise
            delay = (attempt + 1) * 2
            log.warning("LLM 调用失败，%s 秒后重试: %s", delay, e)
            time.sleep(delay)

    raise last_error


def extract_json_from_response(response: str) -> str:
    """从 LLM 响应中提取 JSON 字符串"""
    response = response.strip()
    # 尝试提取 ```json ... ``` 块
    m = re.search(r"```(?:json)?\s*(\{.*?\}|\[.*?\])\s*```", response, re.DOTALL)
    if m:
        return m.group(1).strip()
    # 尝试直接找 JSON 对象
    m = re.search(r"\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}", response, re.DOTALL)
    if m:
        return m.group(0).strip()
    return response.strip()
