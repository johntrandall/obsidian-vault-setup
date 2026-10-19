"""core_settings: merging the config blocks and the eval code that saves a core plugin's options.

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


MANIFEST = {
    "core_settings": {"switcher": {"showAllFileTypes": True, "showAttachments": True}},
    "profiles": {
        "core-only": {"plugins": []},
        "review": {"plugins": [], "core_settings": {"switcher": {"showAttachments": False},
                                                     "file-explorer": {"showUnsupportedFiles": True}}},
    },
}


def test_top_level_block_applies_to_every_profile(tool):
    assert tool.core_settings_for(MANIFEST, "core-only") == {"switcher": {"showAllFileTypes": True, "showAttachments": True}}


def test_profile_block_overrides_key_by_key_and_adds_plugins(tool):
    merged = tool.core_settings_for(MANIFEST, "review")
    assert merged["switcher"] == {"showAllFileTypes": True, "showAttachments": False}
    assert merged["file-explorer"] == {"showUnsupportedFiles": True}


def test_no_blocks_means_nothing_to_apply(tool):
    assert tool.core_settings_for({"profiles": {"p": {"plugins": []}}}, "p") == {}


def test_example_config_switches_on_show_all_file_types(tool):
    import yaml
    manifest = yaml.safe_load((ROOT / "config.example.yaml").read_text())
    assert tool.core_settings_for(manifest, "core-only")["switcher"]["showAllFileTypes"] is True


def test_save_code_passes_the_options_object_to_saveData(tool, monkeypatch):
    """saveData() with no argument writes nothing (Verified 2026-10-19): the code must pass instance.options."""
    seen = {}
    monkeypatch.setattr(tool, "cli_eval", lambda code, vault: seen.update(code=code, vault=vault) or "OK")
    assert tool.apply_core_settings("events", "switcher", {"showAllFileTypes": True}) == "OK"
    assert seen["vault"] == "events"
    assert 'getPluginById("switcher")' in seen["code"]
    assert "saveData(p.instance.options)" in seen["code"]
    assert 'Object.assign(p.instance.options,{"showAllFileTypes": true})' in seen["code"]
