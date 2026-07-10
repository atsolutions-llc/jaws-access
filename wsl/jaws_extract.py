#!/usr/bin/env python3
"""Extract the last command's output from a script(1) session log.

Called synchronously from PROMPT_COMMAND (see jaws-terminal.bash) as:

    jaws_extract.py <session-log> "<output of `history 1`>"

At the moment PROMPT_COMMAND runs, the new prompt has NOT been printed yet,
so the last "<jaws>" sentinel line in the log is the prompt where the command
was typed, and everything after it is that command's output.

Writes into the log's directory (~/.cache/jaws-term/):
    last-command.txt  the command line (from bash history, not screen echo)
    last-output.txt   cleaned output of that command
    last-full.txt     "$ command" + output, for the JAWS virtual viewer
    history.log       running log of recent commands + outputs (size-capped)

JAWS reads these over \\\\wsl.localhost\\<distro>\\... — see jaws/ scripts.
"""

import os
import re
import sys
from datetime import datetime

TOKEN = os.environ.get("JAWS_TOKEN", "<jaws>")
TAIL_BYTES = 256 * 1024          # how much of the session log to examine
HISTORY_CAP = 500 * 1024         # cap history.log around this size
HISTORY_KEEP = 300 * 1024        # ...trimming back to roughly this size

# Terminal escape sequences: OSC, CSI, DCS/PM/APC strings, charset selection,
# and remaining two-character escapes.
ESCAPES = re.compile(
    r"\x1b\][^\x07\x1b]*(?:\x07|\x1b\\)"
    r"|\x1b\[[0-9;:?!\"'<=>]*[ -/]*[@-~]"
    r"|\x1b[PX^_][^\x1b]*\x1b\\"
    r"|\x1b[()][0-9A-Za-z]"
    r"|\x1b[@-~]"
)
CONTROL = re.compile(r"[\x00-\x07\x0b-\x1f\x7f]")  # after \r/\b handling


def apply_carriage_returns(line: str) -> str:
    """Emulate \\r: later segments overwrite the line from column 0."""
    buf: list = []
    for seg in line.split("\r"):
        chars = list(seg)
        if len(chars) >= len(buf):
            buf = chars
        else:
            buf[: len(chars)] = chars
    return "".join(buf)


def apply_backspaces(line: str) -> str:
    out: list = []
    for ch in line:
        if ch == "\x08":
            if out:
                out.pop()
        else:
            out.append(ch)
    return "".join(out)


def clean(raw: str) -> list:
    """Escape-strip and control-char-process raw pty data into text lines."""
    raw = ESCAPES.sub("", raw)
    lines = []
    for line in raw.split("\n"):
        line = apply_carriage_returns(line)
        line = apply_backspaces(line)
        line = CONTROL.sub("", line)
        lines.append(line)
    return lines


def is_prompt(line: str) -> bool:
    return line.startswith(TOKEN + " ") or line == TOKEN


def parse_history_arg(arg: str):
    """'  123  git status' -> (123, 'git status')."""
    parts = arg.strip().split(None, 1)
    try:
        num = int(parts[0])
    except (ValueError, IndexError):
        return None, ""
    return num, parts[1] if len(parts) > 1 else ""


def write_atomic(path: str, text: str) -> None:
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(text)
    os.replace(tmp, path)


def append_history(path: str, entry: str) -> None:
    with open(path, "a", encoding="utf-8") as f:
        f.write(entry)
    try:
        if os.path.getsize(path) > HISTORY_CAP:
            with open(path, "r", encoding="utf-8", errors="replace") as f:
                f.seek(os.path.getsize(path) - HISTORY_KEEP)
                kept = f.read()
            # Trim to the next entry boundary so we don't keep a half entry
            cut = kept.find("\n=== ")
            if cut != -1:
                kept = kept[cut + 1:]
            write_atomic(path, kept)
    except OSError:
        pass


def main() -> int:
    if len(sys.argv) < 3:
        return 0
    log_path, hist_arg = sys.argv[1], sys.argv[2]
    out_dir = os.path.dirname(log_path)
    hist_num, command = parse_history_arg(hist_arg)
    if hist_num is None:
        return 0

    # Per-session state: last seen history number. First run of a session
    # only records state (the history entry predates this session).
    state_path = os.path.join(
        out_dir, "state-" + os.path.basename(log_path) + ".txt"
    )
    prev_num = None
    if os.path.exists(state_path):
        try:
            prev_num = int(open(state_path).read().strip())
        except (OSError, ValueError):
            prev_num = None
    write_atomic(state_path, str(hist_num))
    if prev_num is None:
        return 0

    try:
        size = os.path.getsize(log_path)
        with open(log_path, "rb") as f:
            if size > TAIL_BYTES:
                f.seek(size - TAIL_BYTES)
            raw = f.read().decode("utf-8", errors="replace")
    except OSError:
        return 0

    lines = clean(raw)
    prompt_idx = [i for i, ln in enumerate(lines) if is_prompt(ln)]
    if not prompt_idx:
        return 0
    region = lines[prompt_idx[-1] + 1:]
    # Drop trailing blank lines
    while region and not region[-1].strip():
        region.pop()
    output = "\n".join(region)

    ran_new_command = hist_num != prev_num
    if not ran_new_command and not output.strip():
        return 0  # Enter on an empty prompt — keep the previous capture
    if not output.strip():
        output = "(no output)"

    write_atomic(os.path.join(out_dir, "last-command.txt"), command + "\n")
    write_atomic(os.path.join(out_dir, "last-output.txt"), output + "\n")
    write_atomic(
        os.path.join(out_dir, "last-full.txt"),
        "$ " + command + "\n\n" + output + "\n",
    )
    stamp = datetime.now().strftime("%H:%M:%S")
    append_history(
        os.path.join(out_dir, "history.log"),
        "=== " + stamp + " $ " + command + " ===\n" + output + "\n\n",
    )
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:
        sys.exit(0)  # never disturb the shell
