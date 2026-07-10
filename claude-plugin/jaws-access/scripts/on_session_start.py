#!/usr/bin/env python3
"""SessionStart hook — mute JAWS terminal screen echo for the session.

The factory Windows Terminal scripts only narrate screen changes when
screen echo is ECHO_ALL, so muting it silences the TUI churn completely
while hook-driven SayString announcements keep working. Restored by
on_session_end.py, or manually with the ToggleTerminalSpeech keystroke
(Control+JAWSKey+S).
"""

import jawslib


def main():
    if jawslib.MUTE_MODE == "off":
        return
    jawslib.run_jaws_function("JawsAccessMute")
    jawslib.say("Claude session started, terminal speech muted")


if __name__ == "__main__":
    jawslib.run(main)
