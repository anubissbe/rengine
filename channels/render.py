"""Tool results as lines of styled spans, packed into messages that fit a channel."""

from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from mcp.result import ToolResult
from shared.definitions.toolbox import Block, BlockKind, RunStatus, ToolRunRead
from toolbox.base import ToolOutcome

BOLD = "bold"
ITALIC = "italic"
CODE = "code"
PRE = "pre"
LINK = "text_link"

MAX_ROWS = 20
MAX_LIST_ITEMS = 12
MAX_PAIRS = 6
MAX_INLINE_ITEMS = 4
MAX_VALUE = 96
MAX_PRE = 1500
INDENT = "  "
BULLET = "• "
OPEN_LABEL = "Open in reNgine"
MAX_ENTITIES = 90

_UUID = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$", re.I
)
_ISO = re.compile(r"^(\d{4}-\d{2}-\d{2})[T ](\d{2}:\d{2})")
_HASH = re.compile(r"^[0-9a-f]{32,}$", re.I)


@dataclass(frozen=True)
class Span:
    text: str
    style: str | None = None
    url: str | None = None


Line = list[Span]


@dataclass
class Message:
    text: str
    entities: list[dict] = field(default_factory=list)


def plain(text: str) -> Span:
    return Span(text)


def bold(text: str) -> Span:
    return Span(text, BOLD)


def italic(text: str) -> Span:
    return Span(text, ITALIC)


def code(text: str) -> Span:
    return Span(text, CODE)


def link(text: str, url: str) -> Span:
    return Span(text, LINK, url)


def line(*spans: Span | str) -> Line:
    return [s if isinstance(s, Span) else plain(s) for s in spans]


def text_lines(text: str) -> list[Line]:
    return [line(part) for part in text.splitlines()] or [line("")]


def error_lines(message: str) -> list[Line]:
    return text_lines(message)


# ---------- packing ----------


def utf16_len(text: str) -> int:
    return len(text.encode("utf-16-le")) // 2


def _line_len(spans: Line) -> int:
    return sum(len(s.text) for s in spans)


def _clip_line(spans: Line, limit: int) -> list[Line]:
    """Split one over-long line into pieces that fit."""
    pieces: list[Line] = []
    current: Line = []
    used = 0
    for span in spans:
        text = span.text
        while text:
            room = limit - used
            if room <= 0:
                pieces.append(current)
                current, used = [], 0
                room = limit
            head, text = text[:room], text[room:]
            current.append(Span(head, span.style, span.url))
            used += len(head)
    if current:
        pieces.append(current)
    return pieces or [[]]


def chunk(lines: list[Line], limit: int) -> list[Message]:
    """Pack lines into messages of at most `limit` characters."""
    messages: list[Message] = []
    text_parts: list[str] = []
    entities: list[dict] = []
    offset = 0
    used = 0

    def flush() -> None:
        nonlocal text_parts, entities, offset, used
        if text_parts:
            messages.append(Message("\n".join(text_parts), entities))
        text_parts, entities, offset, used = [], [], 0, 0

    for original in lines:
        for spans in _clip_line(original, limit):
            length = _line_len(spans)
            styled = sum(1 for s in spans if s.style and s.text)
            separator = 1 if text_parts else 0
            if used + separator + length > limit or (
                text_parts and len(entities) + styled > MAX_ENTITIES
            ):
                flush()
                separator = 0
            if separator:
                offset += 1
                used += 1
            parts: list[str] = []
            for span in spans:
                if span.style and span.text:
                    entity: dict[str, Any] = {
                        "type": span.style,
                        "offset": offset,
                        "length": utf16_len(span.text),
                    }
                    if span.style == LINK and span.url:
                        entity["url"] = span.url
                    entities.append(entity)
                parts.append(span.text)
                offset += utf16_len(span.text)
            text_parts.append("".join(parts))
            used += length
    flush()
    return messages


# ---------- values ----------


def _humanise(key: str) -> str:
    return key.replace("_", " ")


def _is_id_key(key: str) -> bool:
    return key == "id" or key.endswith("_id")


def _short_id(value: str) -> str:
    return value[:8]


def _fmt_scalar(key: str, value: Any) -> Span:  # noqa: PLR0911
    if isinstance(value, bool):
        return plain("yes" if value else "no")
    if isinstance(value, int | float) and not isinstance(value, bool):
        if isinstance(value, float):
            return plain(f"{value:.2f}".rstrip("0").rstrip("."))
        return plain(str(value))
    text = str(value)
    if _UUID.match(text) or _HASH.match(text):
        return code(_short_id(text))
    if _is_id_key(key):
        return code(text[:MAX_VALUE])
    stamp = _ISO.match(text)
    if stamp:
        return plain(f"{stamp.group(1)} {stamp.group(2)}")
    if len(text) > MAX_VALUE:
        text = text[: MAX_VALUE - 1] + "…"
    return plain(text)


def _is_scalar(value: Any) -> bool:
    return not isinstance(value, list | tuple | set | dict)


def _empty(value: Any) -> bool:
    return value is None or value in ("", [], {})


def _pairs(row: dict) -> Line:
    """One row of a list as `key: value · key: value`."""
    spans: Line = []
    shown = 0
    for key, value in row.items():
        if _empty(value) or shown >= MAX_PAIRS:
            continue
        if spans:
            spans.append(plain(" · "))
        if _is_scalar(value):
            spans.extend([plain(f"{_humanise(key)}: "), _fmt_scalar(key, value)])
        elif isinstance(value, list) and all(_is_scalar(v) for v in value):
            head = ", ".join(str(v) for v in value[:MAX_INLINE_ITEMS])
            more = (
                f" +{len(value) - MAX_INLINE_ITEMS}"
                if len(value) > MAX_INLINE_ITEMS
                else ""
            )
            spans.append(plain(f"{_humanise(key)}: {head}{more}"))
        elif isinstance(value, list):
            spans.append(plain(f"{_humanise(key)}: {len(value)}"))
        elif isinstance(value, dict):
            spans.append(plain(f"{_humanise(key)}: {len(value)} fields"))
        shown += 1
    return spans


def data_lines(data: Any, depth: int = 0) -> list[Line]:
    pad = INDENT * depth
    out: list[Line] = []
    if isinstance(data, dict):
        for key, value in data.items():
            if _empty(value):
                continue
            label = _humanise(key)
            if _is_scalar(value):
                out.append(line(f"{pad}{label}: ", _fmt_scalar(key, value)))
            elif isinstance(value, list) and all(_is_scalar(v) for v in value):
                head = ", ".join(str(v) for v in value[:MAX_LIST_ITEMS])
                more = (
                    f" (+{len(value) - MAX_LIST_ITEMS} more)"
                    if len(value) > MAX_LIST_ITEMS
                    else ""
                )
                out.append(line(f"{pad}{label}: {head}{more}"))
            elif isinstance(value, list):
                out.append(line(bold(f"{pad}{label} ({len(value)})")))
                out.extend(_rows(value, depth + 1))
            elif isinstance(value, dict):
                out.append(line(bold(f"{pad}{label}")))
                out.extend(data_lines(value, depth + 1))
    elif isinstance(data, list):
        out.extend(_rows(data, depth))
    elif not _empty(data):
        out.append(line(f"{pad}{data}"))
    return out


def _rows(items: list, depth: int) -> list[Line]:
    pad = INDENT * depth
    out: list[Line] = []
    for item in items[:MAX_ROWS]:
        if isinstance(item, dict):
            out.append([plain(f"{pad}{BULLET}"), *_pairs(item)])
        elif isinstance(item, list):
            out.append(line(f"{pad}{BULLET}{', '.join(str(v) for v in item[:6])}"))
        else:
            out.append(line(f"{pad}{BULLET}", _fmt_scalar("", item)))
    if len(items) > MAX_ROWS:
        out.append(line(italic(f"{pad}… {len(items) - MAX_ROWS} more")))
    return out


# ---------- blocks ----------


def block_lines(blocks: list[Block]) -> list[Line]:
    out: list[Line] = []
    for block in blocks:
        rendered = _block(block)
        if rendered:
            if out:
                out.append(line(""))
            out.extend(rendered)
    return out


def _hero(block: Block) -> list[Line]:
    out: list[Line] = []
    if block.headline:
        out.append(line(bold(block.headline)))
    if block.sub:
        out.append(line(block.sub))
    if block.metric:
        label = f" {block.metric.label}" if block.metric.label else ""
        out.append(line(f"{block.metric.value}{label}"))
    if block.marks:
        out.append(line(" · ".join(m.label for m in block.marks)))
    return out


def _facts(block: Block) -> list[Line]:
    out: list[Line] = []
    if block.title:
        out.append(line(bold(block.title)))
    for fact in block.facts:
        value = code(fact.value) if fact.mono else plain(fact.value)
        note = f" ({fact.note})" if fact.note else ""
        out.append(line(f"{fact.label}: ", value, note))
    return out


def _table(block: Block) -> list[Line]:
    out: list[Line] = []
    count = f" ({block.total})" if block.total is not None else ""
    if block.title:
        out.append(line(bold(f"{block.title}{count}")))
    if not block.rows and block.empty:
        out.append(line(italic(block.empty)))
    for row in block.rows[:MAX_ROWS]:
        cells = [c.value for c in row if c.value]
        out.append(line(BULLET + " · ".join(cells)))
    if len(block.rows) > MAX_ROWS:
        out.append(line(italic(f"… {len(block.rows) - MAX_ROWS} more")))
    return out


def _tags(block: Block) -> list[Line]:
    if block.tags:
        head = f"{block.title}: " if block.title else ""
        return [line(head + ", ".join(t.value for t in block.tags))]
    if block.empty:
        return [line(italic(block.empty))]
    return []


def _code(block: Block) -> list[Line]:
    out: list[Line] = []
    if block.title:
        out.append(line(bold(block.title)))
    if block.text:
        out.append(line(Span(block.text[:MAX_PRE], PRE)))
    return out


def _note(block: Block) -> list[Line]:
    return text_lines(block.text) if block.text else []


_BLOCK_RENDERERS = {
    BlockKind.HERO.value: _hero,
    BlockKind.FACTS.value: _facts,
    BlockKind.TABLE.value: _table,
    BlockKind.TAGS.value: _tags,
    BlockKind.CODE.value: _code,
    BlockKind.NOTE.value: _note,
}


def _block(block: Block) -> list[Line]:
    renderer = _BLOCK_RENDERERS.get(block.kind)
    return renderer(block) if renderer else []


# ---------- results ----------


def result_lines(
    result: ToolResult, rewrite: Callable[[str], str] | None = None
) -> list[Line]:
    """`rewrite` respells agent-facing text for the chat: tool names, ids, stamps."""
    fix = rewrite or (lambda text: text)
    lead = result.blocks[0] if result.blocks else None
    out: list[Line] = []
    if lead is None or lead.kind != BlockKind.HERO.value:
        out.append(line(bold(result.summary)))
    body = block_lines(result.blocks) if result.blocks else data_lines(result.data)
    if body:
        if out:
            out.append(line(""))
        out.extend(body)
    if result.caveats:
        out.append(line(""))
        out.extend(line(italic(fix(c))) for c in result.caveats)
    if result.pivot:
        out.append(line(""))
        out.append(line(link(OPEN_LABEL, result.pivot)))
    return out


def outcome_lines(outcome: ToolOutcome, ui_base: str) -> list[Line]:
    out: list[Line] = [line(bold(outcome.summary))]
    body = block_lines(outcome.blocks)
    if body:
        out.append(line(""))
        out.extend(body)
    if outcome.caveats:
        out.append(line(""))
        out.extend(line(italic(c)) for c in outcome.caveats)
    if outcome.pivot and outcome.pivot.href:
        href = outcome.pivot.href
        if href.startswith("/"):
            href = f"{ui_base.rstrip('/')}{href}"
        out.append(line(""))
        out.append(line(link(outcome.pivot.label or OPEN_LABEL, href)))
    return out


def run_lines(run: ToolRunRead, ui_base: str) -> list[Line]:
    """A finished toolbox run, read back from its record."""
    if run.status != RunStatus.COMPLETED.value:
        return error_lines(run.error or "The run failed.")
    out: list[Line] = [line(bold(run.summary or run.title))]
    body = block_lines(run.blocks)
    if body:
        out.append(line(""))
        out.extend(body)
    if run.caveats:
        out.append(line(""))
        out.extend(line(italic(c)) for c in run.caveats)
    if run.pivot and run.pivot.href:
        href = run.pivot.href
        if href.startswith("/"):
            href = f"{ui_base.rstrip('/')}{href}"
        out.append(line(""))
        out.append(line(link(run.pivot.label or OPEN_LABEL, href)))
    return out
