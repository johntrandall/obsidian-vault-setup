"""The obsidian-vault-setup:// link: building it, decoding it, and the applet that handles it.

Run: python3 -m pytest tests/   (pytest only; no Obsidian needed — nothing here talks to the app).
The build test needs macOS (osacompile, PlistBuddy) and is skipped elsewhere.
"""
import importlib.util
import os
import pathlib
import plistlib
import subprocess
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parent.parent
BIN = ROOT / "bin" / "obsidian-vault-setup"


def load_tool():
    spec = importlib.util.spec_from_loader("ovs", loader=None)
    mod = importlib.util.module_from_spec(spec)
    mod.__file__ = str(BIN)
    code = compile(BIN.read_text(), str(BIN), "exec")
    exec(code, mod.__dict__)          # defines the functions; main() runs only under __main__
    return mod


@pytest.fixture(scope="module")
def tool():
    return load_tool()


@pytest.fixture
def home(tmp_path):
    (tmp_path / "project").mkdir()
    (tmp_path / "with space").mkdir()
    (tmp_path / "file.md").write_text("x")
    return tmp_path


# --- building the link ---------------------------------------------------

def test_open_url_is_fully_percent_encoded(tool, home):
    folder = home / "with space"
    assert tool.open_url(str(folder)) == (
        "obsidian-vault-setup://open?path=" + str(folder).replace("/", "%2F").replace(" ", "%20"))


def test_open_url_makes_the_path_absolute(tool, home, monkeypatch):
    monkeypatch.chdir(home)
    assert tool.open_url("project").endswith(str(home / "project").replace("/", "%2F"))


# --- decoding and refusing ----------------------------------------------

def test_decode_round_trip(tool, home):
    folder = home / "project"
    assert tool.decode_open_url(tool.open_url(str(folder)), home=str(home)) == str(folder)


def test_decode_keeps_spaces(tool, home):
    folder = home / "with space"
    assert tool.decode_open_url(tool.open_url(str(folder)), home=str(home)) == str(folder)


@pytest.mark.parametrize("url", [
    "obsidian://open?path=%2Ftmp",                     # wrong scheme
    "obsidian-vault-setup://new?path=%2Ftmp",           # wrong host
    "obsidian-vault-setup://open",                      # no path
    "obsidian-vault-setup://open?path=",                # empty path
    "obsidian-vault-setup://open?folder=%2Ftmp",        # wrong parameter
    "not a url at all",
])
def test_decode_refuses_malformed_links(tool, home, url):
    assert tool.decode_open_url(url, home=str(home)) is None


def test_decode_refuses_paths_outside_home(tool, home, tmp_path_factory):
    elsewhere = tmp_path_factory.mktemp("elsewhere")
    assert tool.decode_open_url(tool.open_url(str(elsewhere)), home=str(home)) is None


def test_decode_refuses_home_itself(tool, home):
    assert tool.decode_open_url(tool.open_url(str(home)), home=str(home)) is None


def test_decode_refuses_a_file_and_a_missing_folder(tool, home):
    assert tool.decode_open_url(tool.open_url(str(home / "file.md")), home=str(home)) is None
    assert tool.decode_open_url(tool.open_url(str(home / "nope")), home=str(home)) is None


def test_decode_refuses_dotdot_escape(tool, home, tmp_path_factory):
    outside = tmp_path_factory.mktemp("outside")
    sneaky = str(home / "project" / ".." / ".." / outside.name)
    assert tool.decode_open_url(tool.open_url(sneaky), home=str(home)) is None


def test_decode_refuses_symlink_escape(tool, home, tmp_path_factory):
    outside = tmp_path_factory.mktemp("outside")
    link = home / "escape"
    link.symlink_to(outside)
    assert tool.decode_open_url(tool.open_url(str(link)), home=str(home)) is None


# --- the CLI surface the applet calls ------------------------------------

def interpreter(env):
    """A python that can import yaml UNDER `env`: the installed tool's own venv python first (it bundles
    PyYAML), then pytest's. Checked with the test's env because a HOME override hides a user-site
    PyYAML (~/Library/Python/<ver>/site-packages lives under HOME)."""
    import shutil
    candidates = []
    installed = shutil.which("obsidian-vault-setup")
    if installed:
        first = open(installed).readline()
        if first.startswith("#!"):
            candidates.append(first[2:].strip().split()[0])
    candidates += [sys.executable, "/usr/bin/python3"]
    for c in candidates:
        if os.path.exists(c) and subprocess.run([c, "-c", "import yaml"], capture_output=True, env=env).returncode == 0:
            return c
    pytest.skip("no python with PyYAML found for the CLI tests")


def run(*args, env=None):
    return subprocess.run([interpreter(env), str(BIN), *args], capture_output=True, text=True, env=env)


def test_cli_url_prints_the_link(home):
    r = run("url", str(home / "project"))
    assert r.returncode == 0
    assert r.stdout.strip() == "obsidian-vault-setup://open?path=" + str(home / "project").replace("/", "%2F")


def test_cli_decode_prints_the_folder_and_refuses_with_exit_1(home):
    env = {**os.environ, "HOME": str(home)}
    link = run("url", str(home / "project"), env=env).stdout.strip()
    ok = run("url", "--decode", link, env=env)
    assert (ok.returncode, ok.stdout.strip()) == (0, str(home / "project"))
    bad = run("url", "--decode", "obsidian-vault-setup://open?path=%2Fprivate%2Ftmp", env=env)
    assert (bad.returncode, bad.stdout) == (1, "")


# --- the built applet -----------------------------------------------------

@pytest.mark.skipif(sys.platform != "darwin", reason="osacompile and PlistBuddy are macOS")
def test_install_finder_button_declares_the_scheme(tmp_path):
    env = {**os.environ, "HOME": str(tmp_path)}
    app = tmp_path / "Applications" / "Open in Obsidian.app"
    r = run("install-finder-button", env=env)
    assert r.returncode == 0, r.stdout + r.stderr
    try:
        info = plistlib.loads((app / "Contents" / "Info.plist").read_bytes())
        assert info["CFBundleURLTypes"][0]["CFBundleURLSchemes"] == ["obsidian-vault-setup"]
        assert info["CFBundleIdentifier"] == "com.johnrandall.open-in-obsidian"
        source = subprocess.run(["osadecompile", str(app / "Contents" / "Resources" / "Scripts" / "main.scpt")],
                                capture_output=True, text=True).stdout
        assert "open location" in source and "url --decode" in source
    finally:
        # Unregister the throwaway bundle so LaunchServices does not keep a claim on a deleted path.
        lsregister = ("/System/Library/Frameworks/CoreServices.framework/Frameworks/LaunchServices.framework"
                      "/Support/lsregister")
        if os.path.exists(lsregister):
            subprocess.run([lsregister, "-u", str(app)], check=False)
