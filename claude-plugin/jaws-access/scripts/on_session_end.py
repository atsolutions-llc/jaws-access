#!/usr/bin/env python3
"""SessionEnd hook — restore JAWS terminal screen echo after a session.

Logs to notifications.log whether the unmute call actually reached JAWS.
"""

import jawslib


def main():
    jawslib.stop_tailer()
    if jawslib.MUTE_MODE == "off":
        return
    ok = jawslib.run_jaws_function("JawsAccessUnmute")
    if ok is None:
        detail = "unmute failed: PowerShell or JAWS unreachable"
    else:
        # JAWS reports success even for unknown functions; see
        # on_session_start.py.
        detail = "terminal speech restore requested"
    jawslib.append_capped(
        "notifications.log",
        "=== " + jawslib.stamp() + " session_end ===\n" + detail + "\n\n",
    )
    if ok is None:
        jawslib.say("Claude session ended, but terminal speech may still "
                    "be muted. Press Control JAWSKey S to toggle it.")
    else:
        jawslib.say("Claude session ended, terminal speech restored")


if __name__ == "__main__":
    jawslib.run(main)
