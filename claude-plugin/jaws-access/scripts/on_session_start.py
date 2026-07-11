#!/usr/bin/env python3
"""SessionStart hook — mute JAWS terminal screen echo for the session.

The factory Windows Terminal scripts only narrate screen changes when
screen echo is ECHO_ALL, so muting it silences the TUI churn completely
while hook-driven SayString announcements keep working. Restored by
on_session_end.py, or manually with the ToggleTerminalSpeech keystroke
(Control+JAWSKey+S).

Logs to notifications.log whether the mute call actually reached JAWS, so
a silent failure is diagnosable from the file afterward.
"""

import jawslib


def main():
    if jawslib.MUTE_MODE == "off":
        return
    ok = jawslib.run_jaws_function("JawsAccessMute")
    if ok is None:
        detail = "mute failed: PowerShell or JAWS unreachable"
    else:
        # JAWS reports success even for unknown functions, so this only
        # means the request was delivered; if the script is not compiled
        # in, JAWS says "Unknown function call" aloud at this moment.
        detail = "terminal speech mute requested"
    jawslib.append_capped(
        "notifications.log",
        "=== " + jawslib.stamp() + " session_start ===\n" + detail + "\n\n",
    )
    if ok is None:
        jawslib.say("Claude session started, but terminal mute failed. "
                    "Press Control JAWSKey S to mute manually.")
    else:
        jawslib.say("Claude session started, terminal speech muted")


if __name__ == "__main__":
    jawslib.run(main)
