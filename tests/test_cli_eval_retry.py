"""cli_eval: the Obsidian CLI sometimes answers an empty line to `eval`; one or two retries hide that.

Run: python3 -m pytest tests/ — the CLI is stubbed.
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


def test_empty_reply_is_retried_then_the_answer_is_returned(tool, monkeypatch):
    replies = iter(["", "=> OK {}"])
    monkeypatch.setattr(tool, "cli", lambda *a, vault=None, timeout=60: next(replies))
    monkeypatch.setattr(tool.time, "sleep", lambda s: None)
    assert tool.cli_eval("1", "v") == "OK {}"


def test_persistently_empty_reply_is_returned_after_the_retries(tool, monkeypatch):
    calls = []
    monkeypatch.setattr(tool, "cli", lambda *a, vault=None, timeout=60: calls.append(1) or "")
    monkeypatch.setattr(tool.time, "sleep", lambda s: None)
    assert tool.cli_eval("1", "v") == ""
    assert len(calls) == 3


def test_a_real_answer_is_not_retried(tool, monkeypatch):
    calls = []
    monkeypatch.setattr(tool, "cli", lambda *a, vault=None, timeout=60: calls.append(1) or "=> NOT LOADED")
    assert tool.cli_eval("1", "v") == "NOT LOADED"
    assert len(calls) == 1
