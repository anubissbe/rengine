from __future__ import annotations

import zipfile

import pytest

from shared.definitions.vulnerabilities import (
    DAST_ROOT,
    EXCLUDED_TAGS,
    WEAK_MATCHER_PATHS,
)
from shared.services.vuln_templates import _extract
from stages.vulnerability_scan.scanners.base import Coverage
from stages.vulnerability_scan.scanners.nuclei import (
    _note_gaps,
    _unloaded,
    _unloaded_row,
)
from tools.nuclei.client import _drop_record
from tools.nuclei.parser import parse_finding

pytestmark = pytest.mark.pipeline

# read off https://api.pdtm.sh/api/v1/tools/nuclei/ignore on 2026-09-13
IGNORE_TAGS = {"dos", "local", "fuzz", "bruteforce", "txt-service"}
IGNORE_FILE_COUNT = 14


def test_ignore_list_matches_the_measured_one() -> None:
    assert EXCLUDED_TAGS == IGNORE_TAGS
    assert len(WEAK_MATCHER_PATHS) == IGNORE_FILE_COUNT
    assert "dast/vulnerabilities/sqli/time-based-sqli.yaml" in WEAK_MATCHER_PATHS


def test_dast_root_is_a_prefix() -> None:
    assert DAST_ROOT.endswith("/")


@pytest.mark.parametrize(
    ("selected", "loaded", "expected"),
    [(6218, 6170, 48), (6182, 6182, 0), (None, 10, 0), (10, None, 0), (10, 12, 0)],
)
def test_unloaded_counts_only_a_real_shortfall(selected, loaded, expected) -> None:
    coverage = Coverage(group="Standard rate")
    coverage.templates_selected = selected
    coverage.templates_loaded = loaded
    assert _unloaded(coverage) == expected


def test_unloaded_checks_are_reported_once_for_the_run() -> None:
    coverage = Coverage(group="Standard rate")
    coverage.templates_selected = 6218
    coverage.templates_loaded = 6170
    _note_gaps(coverage, budget_hit=False)
    assert coverage.status == "completed"
    assert coverage.error is None
    row = _unloaded_row(_unloaded(coverage))
    assert row.status == "skipped"
    assert row.group == "Library"
    assert "48 selected checks did not load" in (row.error or "")


def test_a_full_load_reports_nothing() -> None:
    coverage = Coverage(group="Standard rate")
    coverage.templates_selected = 6182
    coverage.templates_loaded = 6182
    _note_gaps(coverage, budget_hit=False)
    assert coverage.error is None


def test_a_suppressed_honeypot_is_recorded_as_a_dropped_host() -> None:
    line = "[WRN] Potential honeypot detected: 10.0.0.1 (matched 37 distinct templates)"
    record = _drop_record(line)
    assert record == {
        "host": "10.0.0.1",
        "reason": "flagged as a honeypot, matching 37 distinct checks. Findings suppressed.",
    }


def test_an_unresponsive_host_still_parses() -> None:
    line = (
        "[INF] Skipped 127.0.0.1:1 from target list as found unresponsive "
        'permanently: cause="port closed or filtered"'
    )
    record = _drop_record(line)
    assert record is not None
    assert record["host"] == "127.0.0.1:1"


def test_a_host_skipped_after_repeated_errors_is_a_drop() -> None:
    line = (
        "[INF] Skipped example.com:443 from target list as found unresponsive 30 times"
    )
    record = _drop_record(line)
    assert record == {
        "host": "example.com:443",
        "reason": "unresponsive 30 times in a row",
    }


def test_an_unrelated_line_is_not_a_drop() -> None:
    assert _drop_record("[INF] Templates loaded for current scan: 6182") is None


def _archive(path, entries: dict[str, str]):
    with zipfile.ZipFile(path, "w") as bundle:
        for name, body in entries.items():
            bundle.writestr(name, body)
    return path


def test_payload_files_are_extracted_beside_the_checks(tmp_path) -> None:
    archive = _archive(
        tmp_path / "t.zip",
        {
            "nuclei-templates/http/cves/CVE-1.yaml": "id: a\n",
            "nuclei-templates/helpers/wordlists/numbers.txt": "1\n2\n",
            "nuclei-templates/helpers/payloads/citrix_paddings.txt": "aa\n",
            "nuclei-templates/workflows/w.yaml": "id: w\n",
            "nuclei-templates/profiles/p.yaml": "id: p\n",
        },
    )
    destination = tmp_path / "official"
    written = _extract(archive, destination)

    assert written == 1
    assert (destination / "http/cves/CVE-1.yaml").is_file()
    assert (destination / "helpers/wordlists/numbers.txt").is_file()
    assert (destination / "helpers/payloads/citrix_paddings.txt").is_file()
    assert not (destination / "workflows").exists()
    assert not (destination / "profiles").exists()


def test_a_fuzzing_finding_is_keyed_without_its_payload() -> None:
    base = {
        "template-id": "xss-reflect",
        "info": {"name": "x", "severity": "medium", "tags": ["dast"]},
        "url": "https://a.example/search?q=hello",
        "is_fuzzing_result": True,
        "fuzzing_parameter": "q",
        "fuzzing_position": "query",
        "matcher-name": "body",
    }
    one = parse_finding(
        {**base, "matched-at": "https://a.example/search?q=%3Cscript%3E1"}
    )
    two = parse_finding({**base, "matched-at": "https://a.example/search?q=%3Cimg%3E2"})
    assert one is not None
    assert two is not None
    assert one.fingerprint == two.fingerprint
    assert one.matched_at != two.matched_at


def test_an_oast_finding_is_keyed_without_the_callback_url() -> None:
    base = {
        "template-id": "blind-ssrf",
        "info": {"name": "x", "severity": "high", "tags": ["oast"]},
        "url": "https://a.example/fetch?u=http://aaa.oast.pro",
        "matcher-name": "dns",
        "interaction": {"protocol": "dns"},
    }
    one = parse_finding(
        {**base, "matched-at": "https://a.example/fetch?u=http://aaa.oast.pro"}
    )
    two = parse_finding(
        {**base, "matched-at": "https://a.example/fetch?u=http://bbb.oast.pro"}
    )
    assert one is not None
    assert two is not None
    assert one.fingerprint == two.fingerprint


def test_a_long_host_is_capped_to_the_column() -> None:
    record = {
        "template-id": "t",
        "info": {"name": "x", "severity": "low"},
        "matched-at": "a" * 1800,
        "interaction": {"raw": "x\x00y"},
    }
    finding = parse_finding(record)
    assert finding is not None
    assert len(finding.host or "") <= 500
    assert "\x00" not in str(finding.interaction)
