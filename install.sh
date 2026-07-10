#!/usr/bin/env bash
# install.sh — set up the WSL side of jaws-scripting, plus everything on the
# Windows side that can be automated from here (the JAWS keymap file).
#
# Safe to re-run: every step checks before it changes anything.
# Output is plain single-column text, written to be listened to.

set -u

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BASHRC="$HOME/.bashrc"
SETTINGS="$HOME/.claude/settings.json"
MARKER="jaws-scripting/wsl/jaws-terminal.bash"

ok()   { echo "ok: $*"; }
skip() { echo "already done: $*"; }
warn() { echo "warning: $*"; }

echo "Installing jaws-scripting WSL components from $REPO_DIR"
echo ""

# 1. Prerequisites -----------------------------------------------------------
if ! command -v python3 >/dev/null 2>&1; then
    echo "error: python3 is required and was not found. Install it and re-run."
    exit 1
fi
ok "python3 found"

if ! command -v script >/dev/null 2>&1; then
    echo "error: the script command (package bsdutils/util-linux) was not found."
    exit 1
fi
ok "script command found"

if command -v powershell.exe >/dev/null 2>&1; then
    ok "PowerShell interop available, JAWS speech announcements will work"
else
    warn "powershell.exe not reachable. Capture and viewers will work, but speech announcements will not."
fi

# 2. Cache directories -------------------------------------------------------
mkdir -p "$HOME/.cache/jaws-term" "$HOME/.cache/jaws-claude"
ok "capture directories exist under ~/.cache"

# 3. bashrc: capture layer + claude alias ------------------------------------
if grep -q "$MARKER" "$BASHRC" 2>/dev/null; then
    skip "capture layer already sourced in ~/.bashrc"
else
    {
        echo ""
        echo "# JAWS terminal accessibility (keep as last lines — must run after PS1 setup)"
        echo "source $REPO_DIR/wsl/jaws-terminal.bash"
        echo "alias claude='command claude --plugin-dir $REPO_DIR/claude-plugin/jaws-access'"
    } >> "$BASHRC"
    ok "added capture layer and claude alias to ~/.bashrc"
fi

# 4. Claude Code status line -------------------------------------------------
STATUSLINE_CMD="python3 $REPO_DIR/claude-plugin/jaws-access/scripts/statusline.py"
python3 - "$SETTINGS" "$STATUSLINE_CMD" <<'PYEOF'
import json, os, sys
path, cmd = sys.argv[1], sys.argv[2]
settings = {}
if os.path.exists(path):
    try:
        with open(path) as f:
            settings = json.load(f)
    except ValueError:
        print("warning: %s is not valid JSON, statusLine not configured" % path)
        sys.exit(0)
existing = settings.get("statusLine", {}).get("command", "")
if "jaws-access" in existing:
    print("already done: statusLine points at the jaws-access script")
elif existing:
    print("warning: a different statusLine is configured, left untouched: " + existing)
else:
    settings["statusLine"] = {"type": "command", "command": cmd}
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        json.dump(settings, f, indent=2)
    print("ok: statusLine configured in ~/.claude/settings.json")
PYEOF

# 5. JAWS keymap on the Windows side ----------------------------------------
JKM_INSTALLED=0
for enu in /mnt/c/Users/*/AppData/Roaming/Freedom\ Scientific/JAWS/*/Settings/enu; do
    [ -d "$enu" ] || continue
    if cp "$REPO_DIR/jaws/WindowsTerminal.jkm" "$enu/WindowsTerminal.jkm" 2>/dev/null; then
        ok "keymap installed to $enu"
        JKM_INSTALLED=1
    else
        warn "could not write keymap to $enu"
    fi
done
if [ "$JKM_INSTALLED" -eq 0 ]; then
    warn "no JAWS user settings folder found under /mnt/c/Users. Copy jaws/WindowsTerminal.jkm there manually."
fi

# 6. What remains manual -----------------------------------------------------
echo ""
echo "WSL side is installed. Two manual steps remain on the JAWS side:"
echo "1. Add the script: focus Windows Terminal, press JAWSKey+0 to open"
echo "   Script Manager, move to the end of the file with Control+End, paste"
echo "   the contents of jaws/JawsAccess-additions.jss below the existing"
echo "   code, and compile with Control+S."
echo "2. Restart JAWS so it loads the keymap installed above."
echo ""
echo "Then open a NEW terminal, run any command, and press Control+JAWSKey+O."
echo "You should land in the virtual viewer reading that command's output."
