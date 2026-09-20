"""New checks: a follow-up run that tests a target's web assets with the checks the library gained."""

from __future__ import annotations

RUN_LABEL = "New checks"
NEW_CHECKS_KEY = "_new_checks"
TEMPLATES_MARK_KEY = "templates"

FOLLOW_UP_STAGES: tuple[str, ...] = ("http_probe", "vulnerability_scan")
MAX_SEEDS_PER_RUN = 5000
MAX_TEMPLATE_IDS = 2000

TARGET_FLAG_TITLE = "Monitor against new checks"
TARGET_FLAG_HELP = (
    "Once a day, when the check library gains new checks, a focused run tests every "
    "web asset this target's completed scans found, with those checks only. "
    "Needs one completed scan."
)


def run_label(count: int) -> str:
    return f"{RUN_LABEL} · {count}"


__all__ = [
    "FOLLOW_UP_STAGES",
    "MAX_SEEDS_PER_RUN",
    "MAX_TEMPLATE_IDS",
    "NEW_CHECKS_KEY",
    "RUN_LABEL",
    "TARGET_FLAG_HELP",
    "TARGET_FLAG_TITLE",
    "TEMPLATES_MARK_KEY",
    "run_label",
]
