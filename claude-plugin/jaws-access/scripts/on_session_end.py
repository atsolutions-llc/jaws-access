#!/usr/bin/env python3
"""SessionEnd hook — restore JAWS terminal screen echo after a session.

Logs to notifications.log whether the unmute call actually reached JAWS.
"""

import jawslib


def main():
    if jawslib.MUTE_MODE == "off":
        return
    ok = jawslib.run_jaws_function("JawsAccessUnmute")
    if ok:
        detail = "terminal speech restored"
    elif ok is False:
        detail = "unmute failed: JAWS did not run JawsAccessUnmute"
    else:
        detail = "unmute failed: PowerShell or JAWS unreachable"
    jawslib.append_capped(
        "notifications.log",
        "=== " + jawslib.stamp() + " session_end ===\n" + detail + "\n\n",
    )
    if ok:
        jawslib.say("Claude session ended, terminal speech restored")
    else:
        jawslib.say("Claude session ended, but terminal speech may still "
                    "be muted. Press Control JAWSKey S to toggle it.")


if __name__ == "__main__":
    jawslib.run(main)
