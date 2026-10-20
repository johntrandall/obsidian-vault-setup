# obsidian-vault-setup

Make any folder an Obsidian vault, with your chosen plugins already installed, using only Obsidian's
own surfaces. One command for people (Finder button, hotkey, terminal) and for AI agents. macOS.

**The model:** every new vault gets your whole plugin **roster** installed. The vault's **profile**
decides which plugins start switched on. After that you only toggle plugins on and off in
Settings → Community plugins; you never install anything by hand.

**Why "only Obsidian's own surfaces":** a script that copies a template `.obsidian/` folder or edits
`obsidian.json` writes behind a running app's back, and AI agents in particular should not do that. This
tool drives the running app through the official `obsidian` CLI (Obsidian ≥ 1.12), so Obsidian and each
plugin write their own files.

## Use

| Who | How | What happens |
|---|---|---|
| You, in Finder | **Open in Obsidian** button in the Finder toolbar | Opens the vault at the window's git repo root (or the folder). If it is not a vault yet, creates it: roster installed, nothing switched on. Starts Obsidian if needed. |
| You, keyboard | A hotkey, e.g. Hammerspoon (see [Hotkey](#hotkey)) | Same, for the selected folder or the front window. |
| You or an agent | `obsidian-open-vault [<folder>]` | Same, from a terminal. |
| You, clicking a link | `obsidian-vault-setup://open?path=<url-encoded absolute path>` | Same, from anything that can open a URL: a terminal status line, a launcher, a note. The Finder button app is the handler. `obsidian-vault-setup url <folder>` prints the link. Paths outside your home folder are refused. |
| You or an agent | `obsidian-new-vault [<folder>] --profile <p>` | Create a vault (does not look for the git root). |
| Agent | `obsidian-vault-setup apply <vault> --profile <p> [--roster]` | Bring an existing vault to a profile. Idempotent; never switches off what someone switched on. |
| Anyone | `obsidian-vault-setup scan` | Read-only: every registered vault and its plugins. |
| Anyone | `obsidian-vault-setup doctor` | Probe the CLI and every undocumented API. Run this first when something fails. |
| Agent | `obsidian-vault-setup forget <folder>` | Unregister a closed vault (files untouched). |

Log for the Finder button and hotkey: `~/Library/Logs/obsidian-vault-setup.log`.

## Configuration

Profiles, the roster, per-plugin settings and a banned list live in one YAML file, first found of:

1. `$OBSIDIAN_VAULT_SETUP_CONFIG`
2. `$XDG_CONFIG_HOME/obsidian-vault-setup/config.yaml` (default `~/.config/obsidian-vault-setup/config.yaml`)

Start from [`config.example.yaml`](config.example.yaml), which documents every field:

```bash
obsidian-vault-setup init-config     # copies the example into place; never overwrites
```

Then set your name in `track-changes.settings.localAuthorName`, prune the roster, and add profiles.

`core_settings` holds settings of Obsidian's own core plugins that every vault should get, keyed by core
plugin id and the option name Obsidian stores in `.obsidian/<id>.json`. The example switches on the Quick
switcher's "Show all file types", which Obsidian ships off and which hides `.base` files from Cmd+O. A profile
may add its own `core_settings` block.

`always_on` lists community plugins switched on in every vault, whatever its profile: preferences of yours
rather than of a kind of vault. The example puts **Window Title** there, so every window reads
`<vault> · <note>` instead of Obsidian's `<note> - <vault> - Obsidian 1.x` (what the macOS Window menu, the
Dock and the task switcher show). `apply` adds it to an existing vault; `new` and `open` include it.

A plugin's `settings:` are saved through its own `settings` object + `saveSettings()` (the sample-plugin
convention). A plugin that keeps no such pair names its own save call in `settings_save`, a JavaScript snippet
run inside the app with `p` (the loaded plugin) and `s` (the settings) in scope, returning `'OK …'`; Window
Title's is `p.setTemplate(s.template); p.flushSave()`.

`bookmark_bases: true` bookmarks every Obsidian Base (`*.base`) in the vault through `obsidian bookmark`, titled `Base · <name>`, keeping bookmarks that already exist; it runs on every `new`, `open` and `apply`, so a Base created later is bookmarked on the next pass. A profile may set its own `bookmark_bases`.
The config file can be a symlink, e.g. into a repo where you keep it under version control.

## Install

```bash
brew tap johntrandall/tap
brew install obsidian-vault-setup
```

Then, once:

```bash
obsidian-vault-setup init-config            # writes ~/.config/obsidian-vault-setup/config.yaml from the example
$EDITOR ~/.config/obsidian-vault-setup/config.yaml
obsidian-vault-setup install-finder-button  # builds ~/Applications/Open in Obsidian.app
obsidian-vault-setup doctor
```

Command-drag **Open in Obsidian** from `~/Applications` into a Finder window's toolbar. On its first click,
macOS asks to let it control Finder; click OK.

Without Homebrew: `git clone https://github.com/johntrandall/obsidian-vault-setup.git && ./obsidian-vault-setup/install.sh`
(needs `python3` with PyYAML).

Requirements: macOS, Obsidian ≥ 1.12 with **Settings → General → Command line interface** switched on,
and Obsidian running (the tool drives the running app).

### Hotkey

Any launcher can call `obsidian-vault-setup open --launch --notify <folder>`. With Hammerspoon, a module
that asks Finder for the selected folder and runs that command via `hs.task`, bound with
`hs.hotkey.bind({"cmd","alt"}, "O", …)`, gives the same behaviour as the toolbar button.

### Clickable link

`install-finder-button` registers the `obsidian-vault-setup://` URL scheme on the button app (it writes
`CFBundleURLTypes` into the app's Info.plist and runs `lsregister`). A click on
`obsidian-vault-setup://open?path=%2FUsers%2Fme%2Fdev%2Fproject` then does what the button does for that
folder: open its vault, or create one. The handler accepts only `open?path=` with an existing directory
under your home folder, so a crafted link cannot point the tool elsewhere. Unlike `obsidian://open?path=`,
which Obsidian answers with "Vault not found" for any folder that is not already a registered vault, this
link works for every project. `obsidian-vault-setup url <folder>` prints it; `url --decode <link>` prints
the folder a link resolves to (nothing and exit 1 when refused), which is what the handler calls. A relative path (`dev/project`, or `~/dev/project`) is taken under your home folder: the short form the link-bridge `/vault-setup` page forwards.

## Tests

`python3 -m pytest tests/` — the link builder and decoder, the `url` CLI, the `core_settings` merge, the
`always_on` list and the `settings_save` hook code, and (on macOS) that `install-finder-button` builds an
applet declaring the scheme. Nothing in the suite talks to Obsidian.


## How each step is done

| Step | Surface | Documented? |
|---|---|---|
| Register + open a new vault | `electron.ipcRenderer.sendSync('vault-open', path, false)` via `obsidian eval` | **No**: `vault-open-ipc` |
| Open an existing vault | `open -a Obsidian <folder>` (Obsidian opens the registered vault containing it) | macOS standard |
| Restricted mode off | `obsidian plugins:restrict off` | Yes |
| Install a plugin | `obsidian plugin:install id=<id>` (no `enable`, returns before the download lands; polled) | Yes |
| GitHub-only plugin | BRAT `betaPlugins.addPlugin()` via `obsidian eval` (none on the roster today) | **No**: `brat-addplugin` |
| Plugin settings | the plugin's own `settings` + `saveSettings()` via `obsidian eval` | **No**: `plugin-settings` |
| Plugin settings, plugin without `saveSettings` | the save call the config names in `settings_save` (Window Title: `setTemplate` + `flushSave`) via `obsidian eval` | **No**: `plugin-settings-hook` |
| Bookmark the vault's Bases | `obsidian bookmark file=<path>.base title="Base · <name>"` for each `*.base` (text contains `views:`) not already in `.obsidian/bookmarks.json` (read only) | Yes |
| Core-plugin settings | `app.internalPlugins.getPluginById(id).instance.options` + `saveData(options)` via `obsidian eval` | **No**: `core-plugin-settings` |
| Enable / disable | `obsidian plugin:enable` / `plugin:disable` | Yes |
| Identity check | `obsidian plugin id=<id>` → author must match the manifest | Yes |
| Unregister | `electron.ipcRenderer.sendSync('vault-remove', path)` via `obsidian eval` | **No**: `vault-remove-ipc` |

## Undocumented APIs

Convention: `undocumented-api-usage` skill. Each id below has a `UNDOCUMENTED-API(<id>)` comment at its
call site in `bin/obsidian-vault-setup`; `doctor` probes all but `brat-addplugin` without changing anything.

| Id | Call | Found in | Verified on | Breaks as | Fallback | Confidence |
|---|---|---|---|---|---|---|
| `vault-open-ipc` | `ipcRenderer.sendSync('vault-open', path, false)` → `true` | `obsidian-1.14.4.asar`, main process `ipcMain.on("vault-open", …)`; the vault switcher's "Open folder as vault" sends it | app 1.14.4, 2026-10-13 | eval error, or not `true`; vault missing from `obsidian vaults` | Vault switcher → Open folder as vault, then `apply` | Verified (5 vaults) |
| `vault-remove-ipc` | `ipcRenderer.sendSync('vault-remove', path)` → `true` | same file, `ipcMain.on("vault-remove", …)`; refuses (`false`) while the vault is open | app 1.14.4, 2026-10-13 | `false` while open; error | Vault switcher → ••• → Remove from list | Verified (4 vaults) |
| `plugin-settings` | `app.plugins.plugins[id].settings` + `await saveSettings()` | Obsidian sample-plugin convention, not a public contract | Track Changes 2.2.0, 2026-10-13 | `NOT LOADED` / `NO saveSettings`; value reverts after reload | Settings → Community plugins → plugin | Verified (survives disable/enable) |
| `plugin-settings-hook` | the per-plugin snippet in the config's `settings_save`, run with `p` = loaded plugin, `s` = settings; Window Title 0.1.1: `p.setTemplate(s.template); p.flushSave()` → `data.json` `{version:1, template}` | the plugin's own `main.ts` (`setTemplate`, `flushSave`, `SettingsStore`) | Window Title 0.1.1 on app 1.14.4, 2026-10-19 | TypeError (method renamed) or a return that is not `OK …` → HAND-OFF line | Settings → Community plugins → Window Title → Template | Verified (template saved, title updated in both windows) |
| `core-plugin-settings` | `app.internalPlugins.getPluginById(id)`: `instance.options` + `await saveData(options)` → `.obsidian/<id>.json` | `obsidian-1.14.4.asar`, `InternalPlugin.saveData(e){ vault.writeConfigJson(this.instance.id, e) }`; what the Settings pane calls | app 1.14.4, 2026-10-19 | `NO CORE PLUGIN` / `NO saveData`; `.obsidian/<id>.json` unchanged (note: `saveData()` without the argument writes nothing) | Settings → the core plugin's pane | Verified (`switcher.showAllFileTypes`, 5 vaults) |
| `brat-addplugin` | `betaPlugins.addPlugin(repo, false, false, false, '', false, enableAfterInstall)` | BRAT 2.2.0 `main.js` | BRAT 2.2.0, 2026-10-13 | `BRAT not loaded`, TypeError, plugin never lands | `obsidian://brat?plugin=<owner/repo>`, click Add Plugin | Verified (1 plugin) |

Verified app version is pinned in the code as `VERIFIED_APP_VERSION`; `doctor` warns when it differs.

## Gotchas (Verified 2026-10-13)

- **The CLI prints nothing, exit 0, when the working directory is inside a registered vault that is not
  open.** Without `vault=`, it targets the vault containing the cwd. If a parent folder (say `~/dev`) is
  itself registered as a vault, `obsidian help` run anywhere below it is silent. The tool runs the CLI from `/`.
- **`vault=<name>` is not honoured either (Observed 2026-10-20, app 1.14.4, run from `/`):** `eval`, `plugins:enabled` and `plugin id=` all answered for the frontmost window whatever vault was named. Bring the target to the front first (`open -a Obsidian <folder>`, or the `vault-open` IPC for a closed vault) and confirm `app.vault.getName()` before writing. `plugin id=` also reports the directory's version, not the installed manifest.
- **Calls that name no vault are unreliable even from `/`:** they target the active window, and were observed
  to hang for over a minute and return nothing. The tool sends every vault-agnostic call (`vaults`, `version`,
  the registration `eval`) through a named vault that is open and answers within 8 s (fixed in v0.1.1).
- The CLI exits 0 on errors (`Vault not found.`), so the tool reads the text.
- Plugin ids are not unique: the directory's `bases-kanban` and `show-hidden-files` are different plugins
  from the ones published under those ids earlier. Every install is checked against the config's `expected_author`.
- `obsidian://open?path=` cannot register a folder ("vault not found"); since 1.13 every URI also asks
  for confirmation.
- Obsidian has no machine-wide plugin install. Every vault holds its own copy.

## Provenance

Written 2026-10-13 with Claude Code. Supersedes the author's earlier scripts that copied a template
`.obsidian/` and edited `obsidian.json` directly.
