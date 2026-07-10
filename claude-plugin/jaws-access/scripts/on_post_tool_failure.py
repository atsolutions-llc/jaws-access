#!/usr/bin/env python3
"""PostToolUseFailure hook — a tool call failed; this is always important.

Failures are the events a sighted user catches from a glance at red text
and a screen reader user historically discovers only much later. Logged
with the full error, spoken immediately with its first line, at every
verbosity level.
"""

import jawslib


def main():
    data = jawslib.read_stdin_json()
    tool_name = data.get("tool_name", "a tool")
    tool_input = data.get("tool_input") or {}
    phrase = jawslib.friendly_phrase(tool_name, tool_input)

    error = jawslib.response_text(data.get("tool_response")).strip()
    if not error:
        error = str(data.get("error") or "").strip()
    first_line = error.splitlines()[0][:150] if error else "no error text"

    entry = ("=== " + jawslib.stamp() + " FAILED " + phrase + " ===\n"
             + (error or "(no error text)") + "\n\n")
    jawslib.append_capped("commands.log", entry)
    jawslib.write_atomic("last-tool.txt", entry)
    jawslib.update_status(
        data, activity="failed " + phrase + " at " + jawslib.stamp())

    if jawslib.should_speak(jawslib.classify(tool_name, failed=True)):
        jawslib.say("Failed: " + phrase + ". " + first_line)


if __name__ == "__main__":
    jawslib.run(main)
