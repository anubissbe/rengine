"""The site tree: what a folder row claims is what its token opens."""

from __future__ import annotations

import pytest

from app.services.endpoint_tree import (
    _MAX_GROUP_TOKEN,
    _MIN_GROUP,
    _emit_group,
    _fold_layouts,
    _Node,
    anomaly_for,
    archive_only_for,
)

pytestmark = pytest.mark.api


def _folder(name: str, *inner: str, rows: int = 1) -> _Node:
    node = _Node(key=f"h/{name}/", name=name, path=f"/{name}/", host="h", depth=1)
    for child in inner:
        kid = _Node(
            key=f"h/{name}/{child}/",
            name=child,
            path=f"/{name}/{child}/",
            host="h",
            depth=2,
        )
        kid.subtree = rows
        node.children[child] = kid
    node.subtree = rows * len(inner)
    return node


def _parent() -> _Node:
    return _Node(key="h/", name="h", path="/", host="h", depth=0)


def _group_of(count: int):
    kids = [_folder(f"f{i}", "assets", "index") for i in range(count)]
    folded = _fold_layouts(_parent(), kids)
    return folded[0], folded[1:]


def test_siblings_sharing_a_layout_fold_into_one_row():
    group, rest = _group_of(5)
    assert _emit_group(group).folders == 5
    assert rest == []


def test_a_group_counts_only_the_folders_its_token_names():
    group, rest = _group_of(_MAX_GROUP_TOKEN + 5)
    node = _emit_group(group)
    assert node.folders == _MAX_GROUP_TOKEN
    assert node.query.count(",") + 1 == node.folders
    assert node.subtree_count == 2 * node.folders
    assert len(rest) == 5, "the folders past the cap stay their own rows"


def test_too_few_siblings_are_not_grouped():
    kids = [_folder(f"f{i}", "assets", "index") for i in range(_MIN_GROUP - 1)]
    assert _fold_layouts(_parent(), kids) == kids


def test_siblings_with_nothing_in_common_are_not_grouped():
    kids = [_folder(f"f{i}", f"only{i}", f"other{i}") for i in range(6)]
    assert _fold_layouts(_parent(), kids) == kids


class TestAnomaly:
    def test_a_few_open_answers_behind_a_wall_are_named(self):
        assert anomaly_for(walled=8, opened=1, errors=0, verified=9) == (
            "1 of 9 answers without auth"
        )

    def test_an_open_folder_is_not_an_anomaly(self):
        assert anomaly_for(walled=1, opened=40, errors=0, verified=41) is None

    def test_a_rare_server_error_is_named(self):
        assert anomaly_for(walled=0, opened=0, errors=1, verified=40) == (
            "1 of 40 returns a server error"
        )

    def test_errors_everywhere_are_not_an_anomaly(self):
        assert anomaly_for(walled=0, opened=0, errors=30, verified=40) is None

    def test_a_small_sample_earns_no_error_sentence(self):
        assert anomaly_for(walled=0, opened=0, errors=1, verified=4) is None


class TestArchiveOnly:
    def test_a_folder_seen_only_in_an_archive(self):
        assert archive_only_for({"archive"}, {"4xx": 3}) is True

    def test_an_answering_folder_is_not_archive_only(self):
        assert archive_only_for({"archive"}, {"2xx": 1}) is False

    def test_a_crawled_folder_is_not_archive_only(self):
        assert archive_only_for({"archive", "katana"}, {"4xx": 3}) is False

    def test_no_source_is_not_archive_only(self):
        assert archive_only_for(set(), {}) is False
