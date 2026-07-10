#!/usr/bin/env python3
"""Notification hook — announce when Claude is waiting on the user.

This is the anti-trap: permission prompts and input requests are silent
in the TUI unless you happen to be reading the right region. Speak them.
All notifications are also logged to ~/.cache/jaws-claude/notifications.log.
"""

import jawslib

# Notification types worth interrupting speech for. Anything not listed is
# logged but not spoken.
SPOKEN_TYPES = {
    "permission_prompt",
    "idle_prompt",
    "agent_needs_input",
    "elicitation_dialog",
}


def main():
    data = jawslib.read_stdin_json()
    message = (data.get("message") or "").strip()
    ntype = (data.get("notification_type") or "").strip()
    if not message:
        return

    jawslib.append_capped(
        "notifications.log",
        "=== " + jawslib.stamp() + " " + (ntype or "notification")
        + " ===\n" + message + "\n\n",
    )

    if not ntype or ntype in SPOKEN_TYPES:
        jawslib.say(message)


if __name__ == "__main__":
    jawslib.run(main)
