"""Fuzzers, discovered by module."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from shared.plugins import classes_in_modules
from stages.vulnerability_scan.scanners.base import VulnScanner


@lru_cache(maxsize=1)
def scanners() -> dict[str, type[VulnScanner]]:
    found: dict[str, type[VulnScanner]] = {}
    for cls in classes_in_modules(
        "stages.dast_scan.scanners", Path(__file__).parent, VulnScanner
    ):
        if cls.name:
            found.setdefault(cls.name, cls)
    return found


__all__ = ["scanners"]
