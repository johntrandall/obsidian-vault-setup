"""always_on (plugins switched on in every vault) and settings_save (a plugin's own save call).

Run: python3 -m pytest tests/ — nothing here talks to Obsidian.
"""
import importlib.util
import pathlib

import pytest

ROOT = pathlib.Path(__file__).resolve().parent.parent
BIN = ROOT / "bin" / "obsidian-vault-setup"


@pytest.fixture(scope="module")
def tool():
    spec = importlib.util.spec_from_loader("ovs2", loader=None)
    mod = importlib.util.module_from_spec(spec)
    mod.__file__ = str(BIN)
    exec(compile(BIN.read_text(), str(BIN), "exec"), mod.__dict__)
    return mod


MANIFEST = {
    "always_on": ["window-title"],
    "profiles": {"core-only": {"plugins": []}, "review": {"plugins": ["track-changes", "window-title"]}},
    "plugins": {
        "window-title": {"expected_author": "gorky", "source": "directory", "roster": True,
                         "settings": {"template": "{{vault}} · {{title}}"},
                         "settings_save": "p.setTemplate(s.template); p.flushSave(); return 'OK '+p.template;"},
        "track-changes": {"expected_author": "Phil Baum", "source": "directory", "roster": True,
                          "settings": {"localAuthorName": "John Randall"}},
        "calendar-bases": {"expected_author": "Edrick Leong", "source": "directory", "roster": True},
    },
    "banned": {"inkling": {"reason": "corrupts files"}},
}


def test_always_on_is_switched_on_in_every_profile(tool):
    assert tool.plugins_to_enable(MANIFEST, "core-only") == ["window-title"]
    assert tool.plugins_to_enable(MANIFEST, "review") == ["window-title", "track-changes"]


def test_extras_come_after_and_duplicates_are_dropped(tool):
    assert tool.plugins_to_enable(MANIFEST, "core-only", ["calendar-bases", "window-title"]) == \
        ["window-title", "calendar-bases"]


def test_no_always_on_block_means_the_profile_list_alone(tool):
    manifest = {k: v for k, v in MANIFEST.items() if k != "always_on"}
    assert tool.plugins_to_enable(manifest, "review") == ["track-changes", "window-title"]


def test_banned_and_unknown_ids_are_refused_even_from_always_on(tool):
    with pytest.raises(SystemExit, match="banned"):
        tool.plugins_to_enable({**MANIFEST, "always_on": ["inkling"]}, "core-only")
    with pytest.raises(SystemExit, match="not in the config"):
        tool.plugins_to_enable({**MANIFEST, "always_on": ["nope"]}, "core-only")


def test_default_settings_code_merges_and_calls_saveSettings(tool):
    code = tool.settings_code("track-changes", {"localAuthorName": "John Randall"})
    assert "app.plugins.plugins[\"track-changes\"]" in code
    assert "await p.saveSettings()" in code and "NO saveSettings" in code
    assert '"localAuthorName": "John Randall"' in code


def test_settings_save_hook_replaces_the_saveSettings_path(tool):
    hook = MANIFEST["plugins"]["window-title"]["settings_save"]
    code = tool.settings_code("window-title", {"template": "{{vault}} · {{title}}"}, hook)
    assert "saveSettings" not in code
    assert "const s={\"template\": \"{{vault}} \\u00b7 {{title}}\"}" in code
    assert "p.setTemplate(s.template); p.flushSave(); return 'OK '+p.template;" in code
    assert code.startswith("(async()=>{const p=app.plugins.plugins[\"window-title\"]; if(!p) return 'NOT LOADED';")
    assert code.endswith("})()")


def test_example_config_switches_window_title_on_everywhere(tool):
    import yaml
    example = yaml.safe_load((ROOT / "config.example.yaml").read_text())
    assert example["always_on"] == ["window-title"]
    wt = example["plugins"]["window-title"]
    assert wt["expected_author"] == "gorky" and wt["roster"] is True
    assert "setTemplate" in wt["settings_save"]
    assert tool.plugins_to_enable(example, "core-only") == ["window-title"]
