"""Shared helpers for the jaws-access plugin hooks.

Design rules for every hook in this plugin:
  - Fully passive: exit 0 always, never print to stdout (stdout from a hook
    can be fed back into the conversation — we saw a Stop hook loop do
    exactly that).
  - Never block: speech is fire-and-forget via a detached PowerShell process.
  - Never break when JAWS or Windows interop is absent.
"""

import base64
import json
import os
import subprocess
import sys
from datetime import datetime

LOG_DIR = os.path.expanduser("~/.cache/jaws-claude")
LOG_CAP = 500 * 1024      # cap growing logs around this size
LOG_KEEP = 300 * 1024     # ...trimming back to roughly this size
SAY_MAX = 250             # cap spoken announcements at this many characters

# JAWS_CLAUDE_SPEAK: "announce" (default) = short event announcements,
# "full" = speak entire assistant messages, "off" = no speech at all.
SPEAK_MODE = os.environ.get("JAWS_CLAUDE_SPEAK", "announce").lower()

# JAWS_CLAUDE_MUTE: "on" (default) = mute JAWS terminal screen echo while a
# Claude session runs (SessionStart/SessionEnd hooks); "off" = leave it alone.
MUTE_MODE = os.environ.get("JAWS_CLAUDE_MUTE", "on").lower()


def read_stdin_json():
    try:
        return json.load(sys.stdin)
    except Exception:
        return {}


def ensure_dir():
    os.makedirs(LOG_DIR, exist_ok=True)


def write_atomic(name, text):
    ensure_dir()
    path = os.path.join(LOG_DIR, name)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(text)
    os.replace(tmp, path)


def append_capped(name, entry):
    ensure_dir()
    path = os.path.join(LOG_DIR, name)
    with open(path, "a", encoding="utf-8") as f:
        f.write(entry)
    try:
        if os.path.getsize(path) > LOG_CAP:
            with open(path, "r", encoding="utf-8", errors="replace") as f:
                f.seek(os.path.getsize(path) - LOG_KEEP)
                kept = f.read()
            cut = kept.find("\n=== ")
            if cut != -1:
                kept = kept[cut + 1:]
            write_atomic(name, kept)
    except OSError:
        pass


def stamp():
    return datetime.now().strftime("%H:%M:%S")


def response_text(r):
    """Pull human-readable text out of a tool_response of unknown shape."""
    if r is None:
        return ""
    if isinstance(r, str):
        return r
    if isinstance(r, list):
        return "\n".join(t for t in (response_text(x) for x in r) if t)
    if isinstance(r, dict):
        parts = []
        for key in ("text", "stdout", "stderr", "output", "error"):
            v = r.get(key)
            if isinstance(v, str) and v.strip():
                parts.append(v.rstrip())
        if parts:
            return "\n".join(parts)
        if "content" in r:
            return response_text(r["content"])
        try:
            return json.dumps(r, indent=1)[:2000]
        except Exception:
            return str(r)
    return str(r)


def say(text):
    """Speak through JAWS on the Windows host, fire-and-forget.

    Uses the JAWS COM automation object (FreedomSci.JawsApi). The PowerShell
    script is passed via -EncodedCommand (UTF-16LE base64) so no quoting or
    escaping of the message can break it. Silently a no-op if PowerShell
    interop or JAWS is unavailable.
    """
    if SPEAK_MODE == "off" or not text:
        return
    text = " ".join(text.split())
    if len(text) > SAY_MAX:
        text = text[:SAY_MAX] + " , truncated"
    ps_text = text.replace("'", "''")
    _run_powershell(
        "try { $j = New-Object -ComObject FreedomSci.JawsApi; "
        "[void]$j.SayString('" + ps_text + "', $false) } catch {}"
    )


# Friendly speech names for Claude Code permission modes.
MODE_NAMES = {
    "default": "manual approval",
    "acceptEdits": "accept edits",
    "bypassPermissions": "bypass permissions, fully automatic",
    "plan": "plan mode",
}


def update_status(data=None, **fields):
    """Merge fields into state.json and regenerate the speakable status.txt.

    Every hook passes its payload as `data` so permission_mode stays fresh;
    the statusline script contributes model/context/cost fields.
    """
    ensure_dir()
    path = os.path.join(LOG_DIR, "state.json")
    try:
        with open(path, "r", encoding="utf-8") as f:
            state = json.load(f)
    except (OSError, ValueError):
        state = {}
    if data and data.get("permission_mode"):
        state["permission_mode"] = data["permission_mode"]
    for key, value in fields.items():
        if value is not None:
            state[key] = value
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(state, f)
    os.replace(tmp, path)

    lines = []
    mode = state.get("permission_mode")
    if mode:
        lines.append("Permission mode: " + MODE_NAMES.get(mode, mode) + ".")
    activity = state.get("activity")
    if activity:
        lines.append("Activity: " + activity + ".")
    used = state.get("context_used_pct")
    remaining = state.get("context_remaining_pct")
    if used is not None:
        line = "Context: " + str(round(used)) + " percent used"
        if remaining is not None:
            line += ", " + str(round(remaining)) + " percent remaining"
        lines.append(line + ".")
    model = state.get("model")
    if model:
        lines.append("Model: " + model + ".")
    cost = state.get("cost_usd")
    if cost is not None:
        lines.append("Session cost: %.2f dollars." % cost)
    if not lines:
        lines.append("No Claude status recorded yet.")
    write_atomic("status.txt", "\n".join(lines) + "\n")
    return state


def tool_summary(tool_name, tool_input):
    """One spoken phrase for what a tool call is doing."""
    if not isinstance(tool_input, dict):
        tool_input = {}
    detail = (
        tool_input.get("description")
        or tool_input.get("command")
        or tool_input.get("file_path")
        or tool_input.get("url")
        or tool_input.get("pattern")
        or tool_input.get("prompt")
        or ""
    )
    detail = " ".join(str(detail).split())
    if len(detail) > 120:
        detail = detail[:120] + "…"
    if detail:
        return tool_name + ": " + detail
    return tool_name


def _run_powershell(ps):
    encoded = base64.b64encode(ps.encode("utf-16-le")).decode("ascii")
    try:
        subprocess.Popen(
            ["powershell.exe", "-NoProfile", "-NonInteractive",
             "-EncodedCommand", encoded],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
    except Exception:
        pass


def run_jaws_function(func_name):
    """Invoke a JAWS script function by name via the JAWS API.

    Runs in the context of the focused application's scripts, so functions
    defined in WindowsTerminal.jss are only reachable while Windows Terminal
    has focus — hence the manual toggle keystroke as a fallback. Pass the
    BARE name ("JawsAccessMute"): with parentheses appended, JAWS reports
    "unknown function".
    """
    safe = func_name.strip().removesuffix("()").replace("'", "''")
    _run_powershell(
        "try { $j = New-Object -ComObject FreedomSci.JawsApi; "
        "[void]$j.RunFunction('" + safe + "') } catch {}"
    )


def run(main):
    """Wrapper: run a hook main(), guaranteeing passivity."""
    try:
        main()
    except Exception:
        pass
    sys.exit(0)
