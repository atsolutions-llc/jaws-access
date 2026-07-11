#!/usr/bin/env python3
"""Background narrator — speaks Claude's short status sentences live.

Started by on_session_start.py, stopped by on_session_end.py (pidfile in
~/.cache/jaws-claude/tailer.pid). Tails the session transcript JSONL,
which Claude Code appends in near-real-time DURING a turn, and speaks the
first sentence of each assistant text block as it is written — the small
"Let me check the config…" messages a sighted user reads next to the
spinner between tool calls.

Why the transcript and not a hook: no hook event carries streamed
assistant text. The TUI's reasoning snippets ("I need to check…") come
from thinking blocks, whose content is empty in the transcript, so the
visible text blocks are the closest — and fully faithful — signal.

Safety properties, in the spirit of the other hooks: never crashes
upward, exits when its pidfile is removed or claimed by a newer tailer,
exits after a day with no transcript activity, and survives the file
being rewritten out from under it (e.g. context compaction) by jumping
to the new end rather than re-narrating history.
"""

import json
import os
import re
import sys
import time

import jawslib

POLL_SECONDS = 0.4
IDLE_EXIT_SECONDS = 24 * 60 * 60
PIDFILE_GRACE_SECONDS = 10   # let on_session_start write the pidfile first
SENTENCE_CAP = 200

# When set, spoken text is appended to this file instead of going to JAWS.
# Used by the test harness; never set in normal operation.
DEBUG_FILE = os.environ.get("JAWS_CLAUDE_NARRATE_DEBUG")


def emit(text):
    if DEBUG_FILE:
        with open(DEBUG_FILE, "a", encoding="utf-8") as f:
            f.write(text + "\n")
    else:
        jawslib.say(text)


def first_sentence(text):
    """A speakable first sentence: markdown stripped, length capped.

    Over-long sentences are cut silently at a clause boundary rather than
    flagged with a spoken "truncated" — narration is a live teaser, and
    the full text is always in the viewers and messages.log.
    """
    text = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", text)  # [label](url)
    text = re.sub(r"[`*_#]+", "", text)
    text = " ".join(text.split())
    m = re.match(r"(.+?[.!?])(?:\s|$)", text)
    sentence = m.group(1) if m else text
    if len(sentence) > SENTENCE_CAP:
        cut = sentence[:SENTENCE_CAP]
        for sep in (", ", "; ", ": ", " — ", " "):
            pos = cut.rfind(sep)
            if pos > SENTENCE_CAP // 2:
                cut = cut[:pos]
                break
        sentence = cut.rstrip(",;:— ")
    return sentence


def handle_line(raw):
    try:
        entry = json.loads(raw)
    except ValueError:
        return
    if not isinstance(entry, dict):
        return
    if entry.get("type") != "assistant" or entry.get("isSidechain"):
        return
    content = (entry.get("message") or {}).get("content")
    if not isinstance(content, list):
        return
    for block in content:
        if isinstance(block, dict) and block.get("type") == "text":
            text = (block.get("text") or "").strip()
            if len(text) >= 5:
                emit(first_sentence(text))


def owns_pidfile():
    try:
        with open(jawslib.TAILER_PIDFILE, "r", encoding="utf-8") as f:
            return int(f.read().split()[0]) == os.getpid()
    except (OSError, ValueError, IndexError):
        return False


def main():
    path = sys.argv[1]
    started = time.time()
    last_data = time.time()
    fh = None
    inode = None
    offset = 0
    buf = b""

    while True:
        if time.time() - started > PIDFILE_GRACE_SECONDS and not owns_pidfile():
            return
        if time.time() - last_data > IDLE_EXIT_SECONDS:
            return

        try:
            st = os.stat(path)
        except OSError:
            fh = None
            time.sleep(POLL_SECONDS)
            continue

        if fh is None or st.st_ino != inode:
            # First open, or the file was atomically replaced (compaction):
            # start at the end — history was already heard or is stale.
            try:
                fh = open(path, "rb")
            except OSError:
                time.sleep(POLL_SECONDS)
                continue
            inode = st.st_ino
            fh.seek(0, os.SEEK_END)
            offset = fh.tell()
            buf = b""

        if st.st_size < offset:
            # Truncated in place: same recovery, jump to the new end.
            fh.seek(0, os.SEEK_END)
            offset = fh.tell()
            buf = b""

        chunk = fh.read()
        if chunk:
            last_data = time.time()
            buf += chunk
            offset = fh.tell()
            while b"\n" in buf:
                line, buf = buf.split(b"\n", 1)
                handle_line(line.decode("utf-8", errors="replace"))
        time.sleep(POLL_SECONDS)


if __name__ == "__main__":
    try:
        main()
    except Exception:
        pass
