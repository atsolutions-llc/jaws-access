#!/usr/bin/env python3
"""PreToolUse hook (all tools) — record what Claude is doing right now.

This powers the status keystroke's 'Activity' line: the parity feature for
a sighted user glancing at the spinner text. At verbose it also SPEAKS the
phrase as the tool starts — the spoken equivalent of the spinner's
"Running one shell command…".
"""

import jawslib


def main():
    data = jawslib.read_stdin_json()
    tool_name = data.get("tool_name", "a tool")
    phrase = jawslib.friendly_phrase(tool_name, data.get("tool_input"))
    jawslib.update_status(
        data, activity=phrase + ", started " + jawslib.stamp())

    # Notable tools (edits/writes) are announced once, in the past tense,
    # by the PostToolUse hook; announcing them here too would speak every
    # near-instant edit twice. Routine tools are the long-running ones —
    # commands, fetches, subagents — where hearing the start matters.
    tier = jawslib.classify(tool_name)
    if tool_name not in jawslib.NOTABLE_TOOLS and jawslib.should_speak(tier):
        jawslib.say("starting: " + phrase)


if __name__ == "__main__":
    jawslib.run(main)
