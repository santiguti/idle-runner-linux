#!/usr/bin/env bash
# Installs Idle Runner for the current user and adds it to the application menu.
# Run it from the extracted IdleRunner folder. Installing again upgrades the program and keeps config.toml and logs/.
set -euo pipefail

src="$(dirname "$(readlink -f "$0")")"
data="${XDG_DATA_HOME:-$HOME/.local/share}"
dest="$data/idle-runner"
desktop="$data/applications/idle-runner.desktop"

if [ "$src" != "$dest" ]; then
    mkdir -p "$dest"
    # Drop the old program files, but not the user's settings and logs.
    find "$dest" -mindepth 1 -maxdepth 1 ! -name config.toml ! -name logs -exec rm -rf {} +
    for entry in "$src"/* "$src"/.[!.]*; do
        [ -e "$entry" ] || continue
        case "$(basename "$entry")" in config.toml | logs) continue ;; esac
        cp -a "$entry" "$dest/"
    done
fi

mkdir -p "$(dirname "$desktop")"
cat > "$desktop" <<DESKTOP
[Desktop Entry]
Type=Application
Name=Idle Runner
Comment=Idle Slayer bot
Exec="$dest/IdleRunner"
Icon=$dest/_internal/idle_runner/ui/assets/icon.png
Terminal=false
Categories=Game;
DESKTOP

echo "Installed in $dest"
echo "To uninstall: rm -rf \"$dest\" \"$desktop\""
