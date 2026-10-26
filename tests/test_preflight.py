"""preflight: the read-only walk that reports unreadable directories and symlinks out of the vault.

Run: python3 -m pytest tests/ — nothing here talks to Obsidian.
"""
import importlib.util
import os
import pathlib
import stat

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


def test_clean_vault_has_no_findings(tool, tmp_path):
    (tmp_path / "notes").mkdir()
    (tmp_path / "notes" / "a.md").write_text("x")
    (tmp_path / "inside-link").symlink_to(tmp_path / "notes")      # a symlink that stays inside is fine
    assert tool.preflight(str(tmp_path)) == []


def test_symlink_out_of_the_vault_is_reported(tool, tmp_path):
    outside = tmp_path.parent / (tmp_path.name + "-outside")
    outside.mkdir()
    (tmp_path / "working-logs").symlink_to(outside)
    (tmp_path / "f.txt").symlink_to(outside / "missing.txt")      # dangling, still outside
    findings = tool.preflight(str(tmp_path))
    assert any(f.startswith("symlink outside vault: working-logs -> ") for f in findings)
    assert any(f.startswith("symlink outside vault: f.txt -> ") for f in findings)


@pytest.mark.skipif(os.geteuid() == 0, reason="root reads everything")
def test_unreadable_directory_is_reported(tool, tmp_path):
    locked = tmp_path / "sub" / "locked"
    locked.mkdir(parents=True)
    locked.chmod(0)
    try:
        findings = tool.preflight(str(tmp_path))
    finally:
        locked.chmod(stat.S_IRWXU)
    assert findings == ["unreadable directory: sub/locked"]


def test_git_is_not_walked(tool, tmp_path):
    (tmp_path / ".git" / "objects").mkdir(parents=True)
    (tmp_path / ".git" / "objects" / "out").symlink_to("/")
    assert tool.preflight(str(tmp_path)) == []


def test_budget_stops_the_walk_and_says_so(tool, tmp_path):
    for i in range(50):
        (tmp_path / f"d{i}").mkdir()
    findings = tool.preflight(str(tmp_path), budget=-1)
    assert len(findings) == 1 and findings[0].startswith("pre-flight stopped after -1 s at ")
