#!/usr/bin/env python3
"""PostToolUse hook (all tools) — log what Claude did, clear activity.

Bash commands get logged with their full output; file modifications
(Edit/Write/NotebookEdit) get logged as one-line entries. Everything
updates the status state so 'Activity' reflects the finished call.
"""

import jawslib

FILE_TOOLS = {"Edit", "Write", "MultiEdit", "NotebookEdit"}


def main():
    data = jawslib.read_stdin_json()
    tool_name = data.get("tool_name", "")
    tool_input = data.get("tool_input") or {}

    spoken = None
    if tool_name == "Bash":
        command = tool_input.get("command", "").strip()
        if command:
            description = tool_input.get("description", "").strip()
            output = jawslib.response_text(data.get("tool_response")).strip()
            if not output:
                output = "(no output)"
            entry = "=== " + jawslib.stamp() + " $ " + command + " ===\n"
            if description:
                entry += "[" + description + "]\n"
            entry += output + "\n\n"
            jawslib.append_capped("commands.log", entry)
            jawslib.write_atomic("last-tool.txt", entry)
            spoken = "finished: " + jawslib.friendly_phrase(
                tool_name, tool_input)
    elif tool_name in FILE_TOOLS:
        file_path = tool_input.get("file_path") or tool_input.get(
            "notebook_path") or ""
        if file_path:
            verb = "wrote" if tool_name == "Write" else "edited"
            entry = ("=== " + jawslib.stamp() + " " + verb + " "
                     + file_path + " ===\n\n")
            jawslib.append_capped("commands.log", entry)
            jawslib.write_atomic("last-tool.txt", entry)
            spoken = "Claude " + verb + " " + jawslib._basename(file_path)

    jawslib.update_status(
        data,
        activity="finished " + jawslib.friendly_phrase(tool_name, tool_input)
        + " at " + jawslib.stamp(),
    )

    tier = jawslib.classify(tool_name)
    if spoken and jawslib.should_speak(tier):
        jawslib.say(spoken)


if __name__ == "__main__":
    jawslib.run(main)
