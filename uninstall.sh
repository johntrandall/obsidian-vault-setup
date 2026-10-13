#!/bin/bash
# Remove the symlinks and the Finder button app installed by install.sh (moved to Trash).
set -uo pipefail
for name in obsidian-vault-setup obsidian-new-vault obsidian-open-vault; do
  [ -L "$HOME/.local/bin/$name" ] && rm "$HOME/.local/bin/$name"
done
[ -d "$HOME/Applications/Open in Obsidian.app" ] && trash "$HOME/Applications/Open in Obsidian.app"
echo "removed. Drag the button off the Finder toolbar if you added it."
