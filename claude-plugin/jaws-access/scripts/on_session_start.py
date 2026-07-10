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
    if ok:
        detail = "terminal speech muted"
    elif ok is False:
        detail = ("mute failed: JAWS did not run JawsAccessMute — is the "
                  "Windows Terminal script compiled and the terminal focused?")
    else:
        detail = "mute failed: PowerShell or JAWS unreachable"
    jawslib.append_capped(
        "notifications.log",
        "=== " + jawslib.stamp() + " session_start ===\n" + detail + "\n\n",
    )
    if ok:
        jawslib.say("Claude session started, terminal speech muted")
    else:
        jawslib.say("Claude session started, but terminal mute failed. "
                    "Press Control JAWSKey S to mute manually.")


if __name__ == "__main__":
    jawslib.run(main)
