"""Sections are discovered from disk."""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from reports.base import Section
from reports.config import SectionConfig
from shared.definitions.reports import SECTION_GROUP_ORDER
from shared.models.report import SectionCatalogEntry, SectionField
from shared.plugins import classes_in_packages

SECTION_DIR = Path(__file__).resolve().parent / "sections"


class SectionRegistrationError(RuntimeError):
    """A section module is invalid or duplicated."""


@dataclass(frozen=True)
class SectionSpec:
    name: str
    title: str
    description: str
    group: str
    order: int
    role: str
    launch_fields: frozenset[str]
    requires: frozenset[str]
    repeatable: bool
    default_enabled: bool
    in_toc: bool
    page_break: str
    section_cls: type[Section]
    config_model: type[SectionConfig]

    @property
    def defaults(self) -> dict:
        return self.config_model().model_dump()

    @property
    def schema(self) -> dict:
        return self.config_model.model_json_schema()

    def instance(self) -> Section:
        return self.section_cls()

    def config(self, raw: dict | None) -> SectionConfig:
        return self.config_model.model_validate(raw or {})


def _classes() -> list[type[Section]]:
    if not SECTION_DIR.is_dir():
        return []
    found: dict[str, type[Section]] = {}
    for obj in classes_in_packages(
        "reports.sections", SECTION_DIR, Section, submodules=("section",)
    ):
        name = getattr(obj, "name", None)
        if not name:
            msg = f"{obj.__qualname__} must set a `name`."
            raise SectionRegistrationError(msg)
        if found.setdefault(name, obj) is not obj:
            msg = f"Duplicate section name {name!r}: {obj.__qualname__}."
            raise SectionRegistrationError(msg)
    return list(found.values())


def _spec(cls: type[Section]) -> SectionSpec:
    if cls.group not in SECTION_GROUP_ORDER:
        msg = f"{cls.name}: unknown group {cls.group!r}."
        raise SectionRegistrationError(msg)
    return SectionSpec(
        name=cls.name,
        title=cls.title,
        description=cls.description,
        group=cls.group,
        order=cls.order,
        role=cls.role,
        launch_fields=frozenset(cls.launch_fields),
        requires=frozenset(cls.requires),
        repeatable=cls.repeatable,
        default_enabled=cls.default_enabled,
        in_toc=cls.in_toc,
        page_break=cls.page_break,
        section_cls=cls,
        config_model=cls.config_model,
    )


@lru_cache(maxsize=1)
def sections() -> dict[str, SectionSpec]:
    specs = [_spec(cls) for cls in _classes()]
    order = {group: index for index, group in enumerate(SECTION_GROUP_ORDER)}
    specs.sort(key=lambda s: (order.get(s.group, 99), s.order, s.title))
    return {spec.name: spec for spec in specs}


def section(name: str) -> SectionSpec | None:
    return sections().get(name)


_TYPE_MAP = {
    "integer": "number",
    "number": "number",
    "boolean": "flag",
    "string": "string",
}


def _fields(spec: SectionSpec) -> list[SectionField]:
    schema = spec.schema
    defaults = spec.defaults
    out: list[SectionField] = []
    for name, prop in (schema.get("properties") or {}).items():
        raw_type = prop.get("type", "string")
        widget = prop.get("widget", "")
        kind = "list" if raw_type == "array" else _TYPE_MAP.get(raw_type, "string")
        out.append(
            SectionField(
                name=name,
                label=prop.get("title") or name.replace("_", " ").capitalize(),
                help=prop.get("description", ""),
                type=kind,
                default=defaults.get(name),
                options=prop.get("options") or [],
                minimum=prop.get("minimum"),
                maximum=prop.get("maximum"),
                widget=widget,
                launch=name in spec.launch_fields,
            )
        )
    return out


def catalog() -> list[SectionCatalogEntry]:
    return [
        SectionCatalogEntry(
            name=spec.name,
            title=spec.title,
            description=spec.description,
            group=spec.group,
            role=spec.role,
            requires=sorted(spec.requires),
            repeatable=spec.repeatable,
            default_enabled=spec.default_enabled,
            always_available=not spec.requires,
            fields=_fields(spec),
            defaults=spec.defaults,
        )
        for spec in sections().values()
    ]
