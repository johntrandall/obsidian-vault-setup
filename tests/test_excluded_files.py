"""excluded_files: compiling config entries into Obsidian's Excluded-files strings and merging the blocks.

Run: python3 -m pytest tests/ — nothing here talks to Obsidian.
"""
import importlib.util
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


def test_bare_name_means_folder_at_any_depth(tool):
    assert tool.compile_exclude("node_modules") == "/(^|\\/)node_modules\\//"


def test_bare_name_regex_metacharacters_are_escaped(tool):
    assert tool.compile_exclude(".venv") == "/(^|\\/)\\.venv\\//"
    assert tool.compile_exclude("a+b") == "/(^|\\/)a\\+b\\//"


def test_regex_and_path_entries_pass_as_written(tool):
    assert tool.compile_exclude("/(^|\\/)dist\\//") == "/(^|\\/)dist\\//"
    assert tool.compile_exclude("zArchive/old") == "zArchive/old"


def test_top_level_plus_profile_in_order_without_duplicates(tool):
    manifest = {"excluded_files": ["node_modules", "dist"],
                "profiles": {"core-only": {}, "web": {"excluded_files": ["dist", ".next"]}}}
    assert tool.excluded_files_for(manifest, "core-only") == ["/(^|\\/)node_modules\\//", "/(^|\\/)dist\\//"]
    assert tool.excluded_files_for(manifest, "web") == ["/(^|\\/)node_modules\\//", "/(^|\\/)dist\\//", "/(^|\\/)\\.next\\//"]


def test_no_block_means_nothing_to_apply(tool):
    assert tool.excluded_files_for({"profiles": {"core-only": {}}}, "core-only") == []
