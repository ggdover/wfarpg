#!/usr/bin/env bash
# The play demo for Windows, as one file: dist/wfarpg.exe, with everything packed into it.
#   game/tools/export_windows.sh            (from anywhere; GODOT=... to use another Godot 4.7)
# The first time, it fetches Godot's export templates for this version (1.3 GB, checked against the release's
# SHA-512) and keeps only the Windows ones.
set -euo pipefail

GODOT="${GODOT:-$HOME/.local/bin/godot}"
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
OUT="$ROOT/dist/wfarpg.exe"

version="$("$GODOT" --version | cut -d. -f1-4)"    # 4.7.2.stable.official.ed1daf0bf -> 4.7.2.stable
templates="${XDG_DATA_HOME:-$HOME/.local/share}/godot/export_templates/$version"
if [[ ! -f "$templates/windows_release_x86_64.exe" ]]; then
	tag="${version%.stable}-stable"                     # 4.7.2-stable
	url="https://github.com/godotengine/godot/releases/download/$tag"
	tpz="Godot_v${tag}_export_templates.tpz"
	tmp="$(mktemp -d)"
	trap 'rm -rf "$tmp"' EXIT
	echo "Fetching Godot's export templates for $version..."
	curl -fL --progress-bar -o "$tmp/$tpz" "$url/$tpz"
	curl -fsSL -o "$tmp/SHA512-SUMS.txt" "$url/SHA512-SUMS.txt"
	(cd "$tmp" && grep " $tpz\$" SHA512-SUMS.txt | sha512sum -c -)
	mkdir -p "$templates"
	unzip -joq "$tmp/$tpz" 'templates/version.txt' 'templates/windows_*_x86_64*.exe' -d "$templates"
	rm -rf "$tmp"
fi

mkdir -p "$ROOT/dist"
"$GODOT" --headless --path "$ROOT/game" --export-release Windows "$OUT"
ls -lh "$OUT"
