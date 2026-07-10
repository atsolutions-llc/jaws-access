#!/usr/bin/env python3
"""UserPromptSubmit hook — log the user's side of the conversation.

Keeps messages.log a real transcript (You/Claude alternating) instead of
Claude-only. Prints nothing: stdout from this event would be injected into
Claude's context.
"""

import jawslib


def main():
    data = jawslib.read_stdin_json()
    prompt = (data.get("prompt") or "").strip()
    if prompt:
        jawslib.append_capped(
            "messages.log",
            "=== " + jawslib.stamp() + " You ===\n" + prompt + "\n\n",
        )
    jawslib.update_status(
        data, activity="working on your prompt, sent " + jawslib.stamp())


if __name__ == "__main__":
    jawslib.run(main)
