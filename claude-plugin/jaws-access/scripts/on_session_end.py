#!/usr/bin/env python3
"""SessionEnd hook — restore JAWS terminal screen echo after a session."""

import jawslib


def main():
    if jawslib.MUTE_MODE == "off":
        return
    jawslib.run_jaws_function("JawsAccessUnmute")
    jawslib.say("Claude session ended, terminal speech restored")


if __name__ == "__main__":
    jawslib.run(main)
