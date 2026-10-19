"""bookmark_bases: finding a vault's Bases, titling them, and skipping the ones already bookmarked.

Run: python3 -m pytest tests/ — nothing here talks to Obsidian (the CLI call is stubbed).
"""
import importlib.util
import json
import pathlib

import pytest

ROOT = pathlib.Path(__file__).resolve().parent.parent
BIN = ROOT / "bin" / "obsidian-vault-setup"


@pytest.fixture(scope="module")
def tool():
    spec = importlib.util.spec_from_loader("ovs", loader=None)
    mod = importlib.util.module_from_spec(spec)
    mod.__file__ = str(BIN)
    exec(compile(BIN.read_text(), str(BIN), "exec"), mod.__dict__)
    return mod


@pytest.fixture
def vault(tmp_path):
    (tmp_path / "events").mkdir()
    (tmp_path / "events" / "_events.base").write_text("views:\n  - type: table\n    name: all\n")
    (tmp_path / "dev-docs" / "decisions").mkdir(parents=True)
    (tmp_path / "dev-docs" / "decisions" / "_decisions.base").write_text("filters:\n  and: []\nviews: []\n")
    (tmp_path / "docker").mkdir()
    (tmp_path / "docker" / "Dockerfile.base").write_text("FROM debian\n")          # not a Base
    (tmp_path / "node_modules" / "x").mkdir(parents=True)
    (tmp_path / "node_modules" / "x" / "_hidden.base").write_text("views: []\n")   # pruned
    (tmp_path / ".obsidian").mkdir()
    return tmp_path


def test_bases_in_finds_real_bases_only(tool, vault):
    assert tool.bases_in(str(vault)) == ["dev-docs/decisions/_decisions.base", "events/_events.base"]


def test_title_drops_underscore_and_extension(tool):
    assert tool.base_title("events/_events.base", ["events/_events.base"]) == "Base · events"


def test_title_disambiguates_duplicate_stems_with_the_shortest_distinct_folder_suffix(tool):
    rels = ["a/_decisions.base", "b/_decisions.base"]
    assert tool.base_title("a/_decisions.base", rels) == "Base · a/decisions"
    # same parent folder name on both sides (the watchbill vault, 2026-10-19): one more folder tells them apart,
    # and a folder named like the stem stands in for the stem
    rels = ["dev-docs/decisions/_decisions.base", "plugin/other/decisions/_decisions.base"]
    assert tool.base_title("dev-docs/decisions/_decisions.base", rels) == "Base · dev-docs/decisions"
    assert tool.base_title("plugin/other/decisions/_decisions.base", rels) == "Base · other/decisions"
    rels = ["x/_notes.base", "y/sub/_notes.base"]
    assert tool.base_title("y/sub/_notes.base", rels) == "Base · sub/notes"


def test_bases_under_a_templates_folder_are_not_bases(tool, tmp_path):
    (tmp_path / "templates" / "decisions").mkdir(parents=True)
    (tmp_path / "templates" / "decisions" / "_decisions.base").write_text("views: []\n")
    (tmp_path / "real").mkdir()
    (tmp_path / "real" / "_real.base").write_text("views: []\n")
    assert tool.bases_in(str(tmp_path)) == ["real/_real.base"]


def test_missing_skips_bookmarks_already_present_including_nested_groups(tool, vault):
    (vault / ".obsidian" / "bookmarks.json").write_text(json.dumps({"items": [
        {"type": "group", "title": "Bases", "items": [{"type": "file", "path": "events/_events.base", "title": "x"}]}]}))
    assert tool.missing_base_bookmarks(str(vault)) == [("dev-docs/decisions/_decisions.base", "Base · decisions")]


def test_missing_with_no_bookmarks_file_lists_every_base(tool, vault):
    assert [rel for rel, _ in tool.missing_base_bookmarks(str(vault))] == tool.bases_in(str(vault))


def test_bookmark_bases_calls_the_cli_per_missing_base(tool, vault, monkeypatch):
    calls = []
    monkeypatch.setattr(tool, "cli", lambda *args, vault=None, timeout=60: calls.append((args, vault)) or "Bookmarked: x")
    lines = tool.bookmark_bases("v", str(vault))
    assert [c[0] for c in calls] == [("bookmark", "file=dev-docs/decisions/_decisions.base", "title=Base · decisions"),
                                     ("bookmark", "file=events/_events.base", "title=Base · events")]
    assert all(c[1] == "v" for c in calls) and all(l.startswith("bookmarked") for l in lines)


def test_bookmark_bases_for_profile_override(tool):
    manifest = {"bookmark_bases": True, "profiles": {"p": {"plugins": []}, "q": {"plugins": [], "bookmark_bases": False}}}
    assert tool.bookmark_bases_for(manifest, "p") is True
    assert tool.bookmark_bases_for(manifest, "q") is False
    assert tool.bookmark_bases_for({"profiles": {"p": {}}}, "p") is False
