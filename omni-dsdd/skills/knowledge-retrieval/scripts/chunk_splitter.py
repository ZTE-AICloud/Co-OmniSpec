"""baseline 模式：Markdown 标题层级感知切分（按真实 token 计长）。"""
from __future__ import annotations
import re
from dataclasses import dataclass
from typing import Optional, Any

_HEADING_RE = re.compile(r'^(#{1,6})\s+(.*?)\s*#*\s*$')
_FM_RE = re.compile(r'^---\s*\n.*?\n---\s*\n', re.DOTALL)


@dataclass
class Chunk:
    source_file: str
    breadcrumb: str        # "支付 > 退款 > 异常处理"
    location: str          # "支付/退款/异常处理[0]"
    text: str              # 含 breadcrumb 前缀，用于 embedding 与展示


class TokenCounter:
    """token 适配器。传入 HF tokenizer → 按真实 token；否则按字符退化。

    encode 返回不透明 token 单元列表（HF 下是 int id，退化下是单字符），
    decode 还原为文本，count 返回 token 数。
    """

    def __init__(self, hf_tokenizer: Any = None):
        self._tok = hf_tokenizer

    def encode(self, text: str) -> list:
        if self._tok is None:
            return list(text)  # 字符退化：1 char = 1 token
        return self._tok.encode(text, add_special_tokens=False)

    def decode(self, units: list) -> str:
        if self._tok is None:
            return "".join(units)
        return self._tok.decode(units, skip_special_tokens=True)

    def count(self, text: str) -> int:
        return len(self.encode(text))


def _strip_frontmatter(text: str) -> str:
    return _FM_RE.sub('', text, count=1)


def split_markdown(
    md_text: str,
    source_file: str,
    chunk_size: int = 512,
    chunk_overlap: int = 64,
    min_chunk_len: int = 40,
    tokenizer: Optional[TokenCounter] = None,
) -> list[Chunk]:
    tok = tokenizer or TokenCounter(None)
    body = _strip_frontmatter(md_text)
    lines = body.splitlines()

    # 1) 按任意标题切 segment，用祖先标题栈维护 breadcrumb
    segments: list[tuple[list[str], list[str]]] = []
    stack: list[tuple[int, str]] = []
    cur_lines: list[str] = []
    cur_crumb: list[str] = []

    def flush():
        if cur_lines or cur_crumb:
            segments.append((list(cur_crumb), list(cur_lines)))

    for ln in lines:
        m = _HEADING_RE.match(ln)
        if m:
            flush()
            level = len(m.group(1))
            title = m.group(2).strip()
            while stack and stack[-1][0] >= level:   # 退栈到父层级
                stack.pop()
            stack.append((level, title))
            cur_crumb = [t for _, t in stack]
            cur_lines = []
        else:
            cur_lines.append(ln)
    flush()

    # 2) 整篇无标题 → 固定窗口降级
    if not any(crumb for crumb, _ in segments):
        return _window_chunks(body, source_file, "", chunk_size,
                              chunk_overlap, min_chunk_len, tok)

    # 3) 逐段产 chunk，含极短并入 / 超长二次切分（均按 token 计长）
    chunks: list[Chunk] = []
    pending_text = ""
    pending_crumb = ""
    for crumb, body_lines in segments:
        seg_body = "\n".join(body_lines).strip()
        breadcrumb = " > ".join(crumb)
        if seg_body and tok.count(seg_body) < min_chunk_len:
            # 极短正文并入缓冲，挂到当前 breadcrumb
            pending_text = (pending_text + "\n" + seg_body).strip()
            pending_crumb = breadcrumb
            continue
        if not seg_body:
            continue  # 纯标题空段跳过
        full = (pending_text + "\n" + seg_body).strip() if pending_text else seg_body
        pending_text = ""
        use_crumb = breadcrumb or pending_crumb
        if tok.count(full) > chunk_size:
            chunks.extend(_window_chunks(full, source_file, use_crumb,
                                         chunk_size, chunk_overlap, min_chunk_len, tok))
        else:
            chunks.append(_make_chunk(source_file, use_crumb, full, len(chunks)))
    # 收尾：残留 pending（全文都是极短段的情况）
    if pending_text:
        chunks.append(_make_chunk(source_file, pending_crumb, pending_text, len(chunks)))
    return chunks


def _make_chunk(source_file: str, breadcrumb: str, body: str, idx: int) -> Chunk:
    loc = (breadcrumb.replace(" > ", "/") if breadcrumb else "root") + f"[{idx}]"
    text = f"{breadcrumb}\n{body}" if breadcrumb else body
    return Chunk(source_file=source_file, breadcrumb=breadcrumb, location=loc, text=text)


def _window_chunks(
    body: str,
    source_file: str,
    breadcrumb: str,
    chunk_size: int,
    overlap: int,
    min_len: int,
    tok: TokenCounter,
) -> list[Chunk]:
    body = body.strip()
    if not body:
        return []
    ids = tok.encode(body)
    if len(ids) <= chunk_size:
        return [_make_chunk(source_file, breadcrumb, body, 0)] if len(ids) >= min_len else []

    step = max(1, chunk_size - overlap)
    out: list[Chunk] = []
    i = 0
    start = 0
    while start < len(ids):
        window = ids[start:start + chunk_size]
        if len(window) >= min_len:
            piece = tok.decode(window).strip()
            if piece:
                out.append(_make_chunk(source_file, breadcrumb, piece, i))
                i += 1
        if start + chunk_size >= len(ids):
            break
        start += step
    return out