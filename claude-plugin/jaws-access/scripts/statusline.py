#!/usr/bin/env python3
"""Claude Code statusLine command (configured in ~/.claude/settings.json).

Receives session JSON on stdin whenever Claude Code refreshes the status
line. Contributes model, context usage, and cost to the shared status
state (state.json / status.txt) that the JAWS SpeakClaudeStatus keystroke
reads, and prints a compact visible status line. Unlike the hooks, this
script is SUPPOSED to print to stdout.
"""

import jawslib


def main():
    data = jawslib.read_stdin_json()
    model = (data.get("model") or {}).get("display_name")
    ctx = data.get("context_window") or {}
    used = ctx.get("used_percentage")
    remaining = ctx.get("remaining_percentage")
    cost = (data.get("cost") or {}).get("total_cost_usd")

    state = jawslib.update_status(
        data,
        model=model,
        context_used_pct=used,
        context_remaining_pct=remaining,
        cost_usd=cost,
    )

    parts = []
    mode = state.get("permission_mode")
    if mode:
        parts.append(jawslib.MODE_NAMES.get(mode, mode))
    if model:
        parts.append(model)
    if used is not None:
        parts.append(str(round(used)) + "% ctx used")
    if cost is not None:
        parts.append("$%.2f" % cost)
    print(" | ".join(parts) if parts else "jaws-access")


if __name__ == "__main__":
    try:
        main()
    except Exception:
        print("jaws-access")
