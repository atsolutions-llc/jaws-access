#!/usr/bin/env python3
"""PreToolUse hook (all tools) — record what Claude is doing right now.

This powers the status keystroke's 'Activity' line: the parity feature for
a sighted user glancing at the spinner text.
"""

import jawslib


def main():
    data = jawslib.read_stdin_json()
    summary = jawslib.tool_summary(
        data.get("tool_name", "a tool"), data.get("tool_input"))
    jawslib.update_status(
        data, activity="running " + summary + ", started " + jawslib.stamp())


if __name__ == "__main__":
    jawslib.run(main)
