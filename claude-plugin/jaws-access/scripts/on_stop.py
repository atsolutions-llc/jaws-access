#!/usr/bin/env python3
"""Stop hook — log Claude's finished response and announce completion.

Uses the last_assistant_message field from the hook payload; falls back to
parsing the transcript JSONL if a Claude Code version doesn't provide it.
Appends to ~/.cache/jaws-claude/messages.log, rewrites last-message.txt,
then announces through JAWS ("announce" mode) or speaks the whole message
("full" mode) per the JAWS_CLAUDE_SPEAK environment variable.
"""

import json

import jawslib


def last_message_from_transcript(path):
    if not path:
        return ""
    best = ""
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            for line in f:
                try:
                    entry = json.loads(line)
                except ValueError:
                    continue
                if entry.get("type") != "assistant":
                    continue
                content = (entry.get("message") or {}).get("content")
                if isinstance(content, list):
                    texts = [
                        b.get("text", "") for b in content
                        if isinstance(b, dict) and b.get("type") == "text"
                    ]
                    text = "\n".join(t for t in texts if t).strip()
                elif isinstance(content, str):
                    text = content.strip()
                else:
                    text = ""
                if text:
                    best = text
    except OSError:
        return ""
    return best


def main():
    data = jawslib.read_stdin_json()
    message = (data.get("last_assistant_message") or "").strip()
    if not message:
        message = last_message_from_transcript(data.get("transcript_path"))
    if not message:
        return

    entry = "=== " + jawslib.stamp() + " Claude ===\n" + message + "\n\n"
    jawslib.append_capped("messages.log", entry)
    jawslib.write_atomic("last-message.txt", message + "\n")
    jawslib.update_status(
        data, activity="idle, finished responding at " + jawslib.stamp())

    if jawslib.SPEAK_MODE == "full":
        jawslib.say(message)
    else:
        jawslib.say("Claude is done")


if __name__ == "__main__":
    jawslib.run(main)
