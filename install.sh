#!/bin/bash
# Install obsidian-vault-setup from a git checkout (Homebrew users: `brew install johntrandall/tap/obsidian-vault-setup`).
# Links the commands into ~/.local/bin and builds the Finder button. Idempotent. Uninstall: ./uninstall.sh
set -euo pipefail
REPO="$(cd "$(dirname "$0")" && pwd)"
BIN="$HOME/.local/bin"
mkdir -p "$BIN"
python3 -c 'import yaml' 2>/dev/null || { echo "python3 needs PyYAML: pip3 install pyyaml"; exit 1; }
for name in obsidian-vault-setup obsidian-new-vault obsidian-open-vault; do
  ln -sfn "$REPO/bin/obsidian-vault-setup" "$BIN/$name"
done
echo "linked: $BIN/{obsidian-vault-setup,obsidian-new-vault,obsidian-open-vault}"
"$REPO/bin/obsidian-vault-setup" install-finder-button
echo
echo "Next: obsidian-vault-setup init-config   (then edit ~/.config/obsidian-vault-setup/config.yaml)"
