from __future__ import annotations

import re
from pathlib import Path

import pytest

from shared.definitions.oast import (
    DEFAULT_WAIT_SECONDS,
    INTERACTION_LABELS,
    INTERACTION_RAW_LABELS,
    MAX_WAIT_SECONDS,
    MIN_WAIT_SECONDS,
    OAST_MODE_HELP,
    OAST_MODE_LABELS,
    PUBLIC_ACK,
    OastMode,
)

pytestmark = pytest.mark.grammar

MIRROR = Path("/app/frontend-config/oast.ts")


def _enum_values(text: str, name: str) -> set[str]:
    block = re.search(rf"export enum {name} \{{(.*?)\}}", text, re.S)
    assert block, f"{name} is missing from the mirror"
    return set(re.findall(r"= '([^']+)'", block.group(1)))


def _block(text: str, name: str) -> str:
    found = re.search(rf"export const {name}[^=]*= \{{(.*?)\n\}};", text, re.S)
    assert found, f"{name} is missing from the mirror"
    return found.group(1)


def _strings(text: str, name: str) -> list[str]:
    return re.findall(r"'((?:[^'\\]|\\.)*)'", _block(text, name))


def _keys(text: str, name: str) -> set[str]:
    """Keys as prettier leaves them: quoted only when not an identifier."""
    return {
        (k or q)
        for k, q in re.findall(r"(?:^|\n)\s*(?:(\w+)|'([^']+)'):", _block(text, name))
    }


def _number(text: str, name: str) -> int:
    found = re.search(rf"export const {name} = (\d+);", text)
    assert found, f"{name} is missing from the mirror"
    return int(found.group(1))


def test_the_frontend_mirror_carries_every_mode():
    text = MIRROR.read_text()
    assert _enum_values(text, "OastMode") == {m.value for m in OastMode}


def test_the_frontend_mirror_carries_every_label_and_help_line():
    text = MIRROR.read_text()
    labels = _strings(text, "OAST_MODE_LABELS")
    assert set(labels) >= set(OAST_MODE_LABELS.values())
    helps = " ".join(_strings(text, "OAST_MODE_HELP"))
    for line in OAST_MODE_HELP.values():
        assert line in helps, line


def test_the_frontend_mirror_carries_the_bounds_and_the_acknowledgement():
    text = MIRROR.read_text()
    assert _number(text, "DEFAULT_WAIT_SECONDS") == DEFAULT_WAIT_SECONDS
    assert _number(text, "MIN_WAIT_SECONDS") == MIN_WAIT_SECONDS
    assert _number(text, "MAX_WAIT_SECONDS") == MAX_WAIT_SECONDS
    assert PUBLIC_ACK in text


def test_the_frontend_mirror_carries_the_interaction_labels():
    text = MIRROR.read_text()
    assert _keys(text, "INTERACTION_LABELS") == set(INTERACTION_LABELS)
    assert set(_strings(text, "INTERACTION_LABELS")) >= set(INTERACTION_LABELS.values())
    assert _keys(text, "INTERACTION_RAW_LABELS") == set(INTERACTION_RAW_LABELS)
    assert set(_strings(text, "INTERACTION_RAW_LABELS")) >= set(
        INTERACTION_RAW_LABELS.values()
    )
