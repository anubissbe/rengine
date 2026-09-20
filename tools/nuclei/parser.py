"""Normalise one nuclei JSONL record into the shape reNgine stores."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any
from urllib.parse import SplitResult, urlsplit

from shared.definitions.ports import SCHEME_PORTS
from shared.definitions.vulnerabilities import (
    MAX_EVIDENCE_BYTES,
    Protocol,
    Scanner,
    coerce_protocol,
    coerce_severity,
    is_kev,
)
from shared.utils.net import split_host_port, url_port
from shared.utils.text import scrub, strip_control

_PROTOCOL_ALIASES = {
    "tcp": Protocol.NETWORK.value,
    "network": Protocol.NETWORK.value,
    "js": Protocol.JAVASCRIPT.value,
}


def _as_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        parts = [strip_control(p).strip() for p in value.replace("\n", ",").split(",")]
        return [p for p in parts if p]
    if isinstance(value, (list, tuple, set)):
        out: list[str] = []
        for item in value:
            out.extend(_as_list(item))
        return out
    return [str(value)]


def _as_text(value: Any, limit: int = 0) -> str | None:
    if value is None:
        return None
    text = strip_control(str(value)).strip()
    if not text:
        return None
    return text[:limit] if limit else text


def _as_float(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _as_int(value: Any) -> int | None:
    try:
        return int(str(value).strip())
    except (TypeError, ValueError):
        return None


def _timestamp(value: Any) -> datetime | None:
    text = _as_text(value)
    if not text:
        return None
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None


@dataclass
class Finding:
    fingerprint: str
    scanner: str
    template_id: str
    template_name: str
    template_path: str | None
    template_url: str | None
    severity: str
    protocol: str
    matcher_name: str | None
    extractor_name: str | None
    extracted_results: list[str]
    description: str | None
    impact: str | None
    remediation: str | None
    references: list[str]
    tags: list[str]
    authors: list[str]
    cve_ids: list[str]
    cwe_ids: list[str]
    cvss_metrics: str | None
    cvss_score: float | None
    epss_score: float | None
    epss_percentile: float | None
    cpe: str | None
    is_kev: bool
    matched_at: str
    host: str | None
    ip: str | None
    port: int | None
    scheme: str | None
    url: str | None
    path: str | None
    request: str | None
    response: str | None
    curl_command: str | None
    interaction: dict = field(default_factory=dict)
    extra: dict = field(default_factory=dict)
    observed_at: datetime | None = None
    replayed_from: str | None = None


def fingerprint(
    scanner: str, template_id: str, matcher: str | None, matched_at: str
) -> str:
    raw = f"{scanner}|{template_id}|{matcher or ''}|{matched_at}"
    return hashlib.sha256(raw.encode("utf-8", "ignore")).hexdigest()


def _split(value: str | None) -> SplitResult | None:
    """The split URL, or None when it does not parse."""
    if not value or "://" not in value:
        return None
    try:
        return urlsplit(value)
    except ValueError:
        return None


def _declared_port(parts: SplitResult) -> int | None:
    """The URL's port or its scheme's default. None when the port does not read."""
    return url_port(parts) or SCHEME_PORTS.get((parts.scheme or "").lower())


def _hostname(candidate: str | None) -> str | None:
    if not candidate:
        return None
    value = candidate.strip()
    if "://" in value:
        parts = _split(value)
        return (parts.hostname or None) if parts else None
    head = value.split("/", 1)[0]
    host, _port = split_host_port(head)
    return host or None


def _port_of(record: dict, url: str | None) -> int | None:
    direct = _as_int(record.get("port"))
    if direct:
        return direct
    parts = _split(url)
    if parts is not None and (port := _declared_port(parts)) is not None:
        return port
    host = record.get("host") or ""
    if isinstance(host, str) and host:
        _host, declared = split_host_port(host.split("/", 1)[0])
        return _as_int(declared)
    return None


def _without_query(value: str) -> str:
    parts = _split(value)
    if parts is None:
        return value
    return parts._replace(query="", fragment="").geturl()


def _locator(record: dict, url: str | None, matched_at: str, interaction) -> str:
    """The finding's location without the payload."""
    base = url or matched_at
    if record.get("is_fuzzing_result"):
        position = _as_text(record.get("fuzzing_position"), 40) or ""
        parameter = _as_text(record.get("fuzzing_parameter"), 200) or ""
        return f"{_without_query(base)}#{position}:{parameter}"
    if interaction:
        return _without_query(base)
    return matched_at


def parse_finding(record: dict, scanner: str = Scanner.NUCLEI.value) -> Finding | None:
    template_id = _as_text(record.get("template-id"), 200)
    if not template_id:
        return None
    info = record.get("info") if isinstance(record.get("info"), dict) else {}
    classification = info.get("classification")
    classification = classification if isinstance(classification, dict) else {}
    metadata = info.get("metadata")
    metadata = metadata if isinstance(metadata, dict) else {}

    matched_at = (
        _as_text(record.get("matched-at"), 2000)
        or _as_text(record.get("url"), 2000)
        or _as_text(record.get("host"), 2000)
        or template_id
    )
    url = _as_text(record.get("url"), 2000) or (
        matched_at if "://" in matched_at else None
    )
    raw_type = (_as_text(record.get("type")) or "").lower()
    tags = _as_list(info.get("tags"))[:60]
    matcher = _as_text(record.get("matcher-name"), 200)
    interaction = record.get("interaction") or {}

    return Finding(
        fingerprint=fingerprint(
            scanner,
            template_id,
            matcher,
            _locator(record, url, matched_at, interaction),
        ),
        scanner=scanner,
        template_id=template_id,
        template_name=_as_text(info.get("name"), 500) or template_id,
        template_path=_as_text(record.get("template"), 500)
        or _as_text(record.get("template-path"), 500),
        template_url=_as_text(record.get("template-url"), 1000),
        severity=coerce_severity(_as_text(info.get("severity"))),
        protocol=coerce_protocol(_PROTOCOL_ALIASES.get(raw_type, raw_type)),
        matcher_name=matcher,
        extractor_name=_as_text(record.get("extractor-name"), 200),
        extracted_results=_as_list(record.get("extracted-results"))[:50],
        description=_as_text(info.get("description")),
        impact=_as_text(info.get("impact")),
        remediation=_as_text(info.get("remediation")),
        references=_as_list(info.get("reference"))[:40],
        tags=tags,
        authors=_as_list(info.get("author"))[:20],
        cve_ids=[c.upper() for c in _as_list(classification.get("cve-id"))][:20],
        cwe_ids=[c.upper() for c in _as_list(classification.get("cwe-id"))][:20],
        cvss_metrics=_as_text(classification.get("cvss-metrics"), 200),
        cvss_score=_as_float(classification.get("cvss-score")),
        epss_score=_as_float(classification.get("epss-score")),
        epss_percentile=_as_float(classification.get("epss-percentile")),
        cpe=_as_text(classification.get("cpe"), 300),
        is_kev=is_kev(tags),
        matched_at=matched_at,
        host=(_hostname(record.get("host")) or _hostname(matched_at) or "")[:500]
        or None,
        ip=_as_text(record.get("ip"), 45),
        port=_port_of(record, url),
        scheme=_as_text(record.get("scheme"), 16),
        url=url,
        path=_as_text(record.get("path"), 2000),
        request=_as_text(record.get("request"), MAX_EVIDENCE_BYTES),
        response=_as_text(record.get("response"), MAX_EVIDENCE_BYTES),
        curl_command=_as_text(record.get("curl-command"), MAX_EVIDENCE_BYTES),
        interaction=scrub(interaction) if isinstance(interaction, dict) else {},
        extra=scrub(
            {
                k: v
                for k, v in metadata.items()
                if isinstance(v, (str, int, float, bool))
            }
        ),
        observed_at=_timestamp(record.get("timestamp")),
    )
