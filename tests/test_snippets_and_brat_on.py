"""0.1.12: CSS snippets every vault gets, and BRAT left on with update-at-startup. Run: python3 -m pytest tests/
— nothing here talks to Obsidian.
"""
import importlib.util
import json
import os
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


MANIFEST = {
    "profiles": {"core-only": {"plugins": []},
                 "review": {"plugins": ["track-changes"], "snippets": [{"name": "wide", "enabled": False}, "review-marks"]}},
    "plugins": {"track-changes": {"install": "brat", "repo": "johntrandall/obsidian-track-changes"},
                "window-title": {"source": "directory"}},
    "snippets": ["wide", {"name": "console", "file": "css/console.css"}],
}


def test_snippets_merge_top_level_then_profile_by_name(tool):
    got = tool.snippets_for(MANIFEST, "review")
    by_name = {s["name"]: s for s in got}
    assert list(by_name) == ["wide", "console", "review-marks"]
    assert by_name["wide"] == {"name": "wide", "file": "snippets/wide.css", "enabled": False}   # the profile's entry wins
    assert by_name["console"]["file"] == "css/console.css" and by_name["console"]["enabled"] is True
    assert tool.snippets_for(MANIFEST, "core-only") == [
        {"name": "wide", "file": "snippets/wide.css", "enabled": True},
        {"name": "console", "file": "css/console.css", "enabled": True}]
    assert tool.snippets_for({"profiles": {"p": {}}}, "p") == []


def test_snippet_source_is_beside_the_real_config_file(tool, tmp_path):
    real = tmp_path / "repo" / "obsidian-plugins.yaml"
    real.parent.mkdir()
    real.write_text("")
    link = tmp_path / "config.yaml"
    link.symlink_to(real)
    entry = {"name": "wide", "file": "snippets/wide.css", "enabled": True}
    assert tool.snippet_source(entry, str(link)) == str(tmp_path / "repo" / "snippets" / "wide.css")
    assert tool.snippet_source({"name": "x", "file": "/abs/x.css", "enabled": True}, str(link)) == "/abs/x.css"


def test_snippet_code_writes_only_when_absent_and_reloads(tool):
    code = tool.snippet_code("wide", ".wide{max-width:100%}")
    assert "'/'+\"wide\"+'.css'" in code
    assert "if(!had) await app.vault.adapter.write(path," in code          # never over an existing file
    assert json.dumps(".wide{max-width:100%}") in code
    assert "requestLoadSnippets" in code
    assert "OK " in code


def test_apply_snippet_reports_missing_source_and_enables(tool, tmp_path, monkeypatch):
    css = tmp_path / "wide.css"
    css.write_text(".wide{}")
    calls = []
    monkeypatch.setattr(tool, "cli_eval", lambda code, vault: calls.append(("eval", vault)) or 'OK {"written":true}')
    monkeypatch.setattr(tool, "cli", lambda *a, **k: calls.append(("cli",) + a) or "")
    monkeypatch.setattr(tool.time, "sleep", lambda s: None)
    entry = {"name": "wide", "file": str(css), "enabled": True}
    assert tool.apply_snippet("v", entry) == 'OK {"written":true} enabled'
    assert ("cli", "snippet:enable", "name=wide") in calls
    entry_off = {"name": "wide", "file": str(css), "enabled": False}
    assert tool.apply_snippet("v", entry_off).endswith("(left off)")
    missing = {"name": "gone", "file": str(tmp_path / "gone.css"), "enabled": True}
    assert tool.apply_snippet("v", missing).startswith("NO SOURCE")


def test_brat_auto_update_defaults_on(tool):
    assert tool.brat_auto_update_for({}) is True
    assert tool.brat_auto_update_for({"brat_auto_update": False}) is False


def test_brat_plugins_present_from_config_or_brat_list(tool, tmp_path, monkeypatch):
    monkeypatch.setattr(tool, "installed_plugins", lambda vault: {"window-title": "1.0.0"})
    assert tool.brat_plugins_present(MANIFEST, "v", str(tmp_path)) is False
    monkeypatch.setattr(tool, "installed_plugins", lambda vault: {"track-changes": "2.3.0-jtr.3"})
    assert tool.brat_plugins_present(MANIFEST, "v", str(tmp_path)) is True
    monkeypatch.setattr(tool, "installed_plugins", lambda vault: {})
    d = tmp_path / ".obsidian" / "plugins" / "obsidian42-brat"
    d.mkdir(parents=True)
    (d / "data.json").write_text(json.dumps({"pluginList": ["johntrandall/obsidian-plugin-base-bookmarks"]}))
    assert tool.brat_plugins_present(MANIFEST, "v", str(tmp_path)) is True
    (d / "data.json").write_text(json.dumps({"pluginList": []}))
    assert tool.brat_plugins_present(MANIFEST, "v", str(tmp_path)) is False


def test_version_is_0_1_15(tool):
    assert tool.__version__ == "0.1.15"


def test_dropdown_lookup_failure_on_a_watchbill_home_is_a_handoff(tool, tmp_path, monkeypatch):
    monkeypatch.setattr(tool, "watchbill_system_name", lambda path: None)
    monkeypatch.setattr(tool.shutil, "which", lambda name: "/usr/local/bin/watchbill")
    monkeypatch.setattr(tool, "is_watchbill_home", lambda path: True)
    assert tool.watchbill_dropdown(str(tmp_path)).startswith("card-lane dropdown: this folder is a watchbill home")
    monkeypatch.setattr(tool, "is_watchbill_home", lambda path: False)
    assert tool.watchbill_dropdown(str(tmp_path)) is None


FIXTURES = ROOT / "tests" / "fixtures" / "decisions-dropdown"   # copied from watchbill's contract fixtures (2026-10-30)


def test_dropdown_parser_reads_every_contract_fixture(tool):
    files = sorted(FIXTURES.glob("*.txt"))
    assert len(files) == 8
    for f in files:
        ok, result, text = tool.parse_dropdown_line(f.read_text())
        assert text, f.name
        if f.name.startswith("ok-"):
            assert ok and result in ("OK written", "OK unchanged", "OK rewritten"), f.name
        else:
            assert not ok and result.startswith("SKIP "), f.name
    ok, result, text = tool.parse_dropdown_line((FIXTURES / "skip-wrong-vault.txt").read_text())
    assert result == "SKIP WRONG VAULT claude-notes"
    assert tool.parse_dropdown_line("") == (False, "", "no output")


def test_watchbill_dropdown_reports_ok_or_handoff(tool, tmp_path, monkeypatch):
    class R:
        def __init__(self, rc, out, err=""): self.returncode, self.stdout, self.stderr = rc, out, err
    monkeypatch.setattr(tool, "watchbill_system_name", lambda path: "events")
    monkeypatch.setattr(tool.subprocess, "run", lambda *a, **k: R(0, (FIXTURES / "ok-written.txt").read_text()))
    assert tool.watchbill_dropdown(str(tmp_path)).startswith("OK written: ")
    monkeypatch.setattr(tool.subprocess, "run", lambda *a, **k: R(0, (FIXTURES / "skip-plugin-not-loaded.txt").read_text()))
    assert tool.watchbill_dropdown(str(tmp_path)).startswith("card-lane dropdown SKIP plugin not loaded: ")
    monkeypatch.setattr(tool.subprocess, "run", lambda *a, **k: R(2, "", "watchbill: no system named events"))
    assert "exit 2" in tool.watchbill_dropdown(str(tmp_path))
    monkeypatch.setattr(tool, "watchbill_system_name", lambda path: None)
    assert tool.watchbill_dropdown(str(tmp_path)) is None


def test_watchbill_system_name_from_find_row(tool, tmp_path, monkeypatch):
    class R:
        def __init__(self, rc, out): self.returncode, self.stdout = rc, out
    monkeypatch.setattr(tool.shutil, "which", lambda name: "/usr/local/bin/watchbill")
    row = f"events  {os.path.realpath(str(tmp_path))}\n   ║ INTAKE: how to hand it work\n"
    monkeypatch.setattr(tool.subprocess, "run", lambda *a, **k: R(0, row))
    assert tool.watchbill_system_name(str(tmp_path)) == "events"
    monkeypatch.setattr(tool.subprocess, "run", lambda *a, **k: R(1, ""))
    assert tool.watchbill_system_name(str(tmp_path)) is None


def test_watchbill_home_prefers_the_watchbill_system_profile(tool, tmp_path, monkeypatch):
    monkeypatch.setattr(tool.shutil, "which", lambda name: None)
    (tmp_path / "dev-docs" / "substantive").mkdir(parents=True)
    both = {"profiles": {"core-only": {}, "review-repo": {}, "watchbill-system": {}}}
    assert tool.default_profile_for(str(tmp_path), None, both) == "watchbill-system"
    only_review = {"profiles": {"core-only": {}, "review-repo": {}}}
    assert tool.default_profile_for(str(tmp_path), None, only_review) == "review-repo"


def test_default_profile_is_review_repo_for_a_watchbill_home(tool, tmp_path, monkeypatch):
    manifest = {"profiles": {"core-only": {}, "review-repo": {}}}
    monkeypatch.setattr(tool.shutil, "which", lambda name: None)       # no watchbill CLI: the board folder decides
    assert tool.default_profile_for(str(tmp_path), None, manifest) == "core-only"
    (tmp_path / "dev-docs" / "substantive").mkdir(parents=True)
    assert tool.default_profile_for(str(tmp_path), None, manifest) == "review-repo"
    assert tool.default_profile_for(str(tmp_path), "agent-mcp", manifest) == "agent-mcp"      # a named profile wins
    assert tool.default_profile_for(str(tmp_path), None, {"profiles": {"core-only": {}}}) == "core-only"


def test_watchbill_home_by_registry_lookup(tool, tmp_path, monkeypatch):
    monkeypatch.setattr(tool.shutil, "which", lambda name: "/usr/local/bin/watchbill")
    class R:
        def __init__(self, rc, out): self.returncode, self.stdout = rc, out
    monkeypatch.setattr(tool.subprocess, "run", lambda *a, **k: R(0, f"sys  {os.path.realpath(str(tmp_path))}\n"))
    assert tool.is_watchbill_home(str(tmp_path)) is True
    monkeypatch.setattr(tool.subprocess, "run", lambda *a, **k: R(1, ""))
    assert tool.is_watchbill_home(str(tmp_path)) is False
