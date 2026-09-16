"""Tools are discovered by module."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from shared.plugins import classes_in_modules
from toolbox.base import Tool


@lru_cache(maxsize=1)
def discover() -> dict[str, type[Tool]]:
    found: dict[str, type[Tool]] = {}
    for cls in classes_in_modules("toolbox.tools", Path(__file__).parent, Tool):
        if cls.name:
            found.setdefault(cls.name, cls)
    return found


__all__ = ["discover"]
