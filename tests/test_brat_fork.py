"""BRAT-installed plugins: the registry read that tells a fork build from a directory build, and the eval
wrong-vault guard. Run: python3 -m pytest tests/ — nothing here talks to Obsidian.
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


def _brat_data(vault, plugins):
    d = vault / ".obsidian" / "plugins" / "obsidian42-brat"
    d.mkdir(parents=True)
    (d / "data.json").write_text(json.dumps({"pluginList": plugins}))


def test_repo_in_brat_list_is_registered(tool, tmp_path):
    _brat_data(tmp_path, ["johntrandall/obsidian-track-changes"])
    assert tool.brat_registered(str(tmp_path), "johntrandall/obsidian-track-changes") is True


def test_repo_missing_or_no_brat_is_not_registered(tool, tmp_path):
    assert tool.brat_registered(str(tmp_path), "johntrandall/obsidian-track-changes") is False
    _brat_data(tmp_path, ["someone/else"])
    assert tool.brat_registered(str(tmp_path), "johntrandall/obsidian-track-changes") is False


def test_eval_is_wrapped_in_a_vault_name_guard(tool, monkeypatch):
    sent = []
    monkeypatch.setattr(tool, "cli", lambda *a, **k: sent.append(a) or "=> OK")
    assert tool.cli_eval("1+1", "my-vault") == "OK"
    code = sent[0][1][len("code="):]
    assert code.startswith('(app.vault.getName()!=="my-vault" ? \'WRONG VAULT \'+app.vault.getName() : (1+1))')
