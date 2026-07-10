# JAWS Access for the Terminal and Claude Code

Scripts that make a WSL2 terminal — and AI pair-programming with
[Claude Code](https://claude.com/claude-code) — genuinely usable with the
JAWS screen reader.

## The problem

Terminals are one of the last truly hostile environments for screen reader
users. JAWS can only read what is currently visible, so anything that
scrolls off screen is gone. Command output arrives as an undifferentiated
stream of speech. And modern TUI applications like Claude Code repaint the
entire screen constantly, turning JAWS into a firehose of noise while the
information you actually need — *what did Claude say? what commands did it
run? is it waiting on me?* — is buried somewhere in a viewport you can't
efficiently review.

## The idea

**Capture output at the source instead of scraping the screen.**

The shell and Claude Code both know exactly what happened — so they write
it to files as it happens. On the Windows side, small JAWS scripts read
those files over `\\wsl.localhost\` and present them in the virtual viewer
(a fully navigable, searchable text buffer) or as speech, on a keystroke.
Nothing depends on what happens to be visible in the terminal, and nothing
is ever lost to scrollback.

Three cooperating layers:

1. **Shell capture** (`wsl/`) — your `.bashrc` records the session with
   `script(1)` and tags every prompt with a `<jaws>` sentinel token. After
   each command, an extractor strips the terminal escape codes and saves
   that command's output to a file.
2. **Claude Code plugin** (`claude-plugin/jaws-access/`) — hooks log every
   Claude reply, every command Claude runs, every file it edits, and every
   notification. A status-line script tracks model, context usage, and
   cost. Hooks also push speech directly through the JAWS API: "Claude is
   done", "Claude needs your permission to use Bash" — and automatically
   silence JAWS screen echo while a Claude session runs, so the TUI repaint
   chatter disappears entirely.
3. **JAWS scripts** (`jaws/`) — keystrokes inside Windows Terminal that open
   the captured content in the virtual viewer or speak it.

## What you get

- The last command's complete output in the virtual viewer — even if it was
  ten thousand lines that scrolled past in a second.
- A rolling history of recent commands and their outputs.
- A two-sided transcript of your Claude conversation (your prompts and
  Claude's replies), and a separate log of every command Claude executed
  and every file it touched.
- Spoken announcements the moment Claude finishes or needs your input — no
  more silently-stuck permission prompts.
- A status keystroke that answers what a sighted user gets by glancing at
  the screen: permission mode, what Claude is doing *right now*, context
  window usage, model, and session cost.
- Silence. While Claude works, the terminal's automatic narration is muted;
  your typing echo, manual review, and all of the above keep working.

## Requirements

- Windows with JAWS 2026 (2023 or later will likely work) and Windows
  Terminal.
- WSL2 with bash, `python3`, and `script` (present by default on Ubuntu).
- Claude Code, for the plugin half.
- No dependencies beyond the Python standard library; `jq` not required.

## Installation

### WSL side (automated)

```bash
./install.sh
```

Safe to re-run. It sources the capture layer from your `.bashrc`, aliases
`claude` to load the plugin, wires the status line into
`~/.claude/settings.json`, and copies the JAWS keymap into your JAWS user
settings folder on the Windows side.

### JAWS side (two manual steps)

1. Focus Windows Terminal and press **JAWSKey+0** to open Script Manager,
   which shows the Windows Terminal script source. Move to the very end of
   the file (**Control+End**), paste the entire contents of
   `jaws/JawsAccess-additions.jss` below the existing code, and compile
   with **Control+S**. The additions are strictly append-only — nothing in
   the factory script is edited, so all standard behavior is preserved.
2. Restart JAWS so the keymap loads.

Optional polish: press **JAWSKey+D** in the terminal and add a dictionary
entry replacing `<jaws>` with nothing, so the prompt token is never spoken.

If your WSL distro or username differ from the defaults, adjust the
`JawsAccessPath` function in `jaws/JawsAccess-additions.jss` — the path is
deliberately built from segments there (see Troubleshooting for why).

### Smoke test

Open a new terminal, run any command, press **Control+JAWSKey+O** — you
should land in the virtual viewer reading that command's output. Then start
`claude`, ask it something, and listen for "Claude is done."

## Keystrokes (in Windows Terminal)

| Keystroke | Action |
| --- | --- |
| Control+JAWSKey+O | Last command's output in the virtual viewer |
| Control+JAWSKey+H | Rolling terminal history in the virtual viewer |
| Control+JAWSKey+K | Speak the last command line |
| Control+JAWSKey+M | Claude conversation transcript in the virtual viewer |
| Control+JAWSKey+B | Commands Claude ran and files it edited, in the virtual viewer |
| Control+JAWSKey+L | Speak Claude's latest reply |
| Control+Shift+JAWSKey+L | Claude's latest reply in the virtual viewer |
| Control+JAWSKey+U | Speak session status: mode, current activity, context, model, cost |
| Control+JAWSKey+V | Entire terminal buffer including scrollback, in the virtual viewer |
| Control+JAWSKey+S | Toggle terminal speech (screen echo) manually |

Escape closes the virtual viewer. Viewers open at the end of the content,
on the newest line.

## Configuration

Set these in your environment (e.g. in `.bashrc` before starting `claude`):

- `JAWS_CLAUDE_SPEAK` — `announce` (default): short announcements plus
  spoken permission prompts. `full`: speak Claude's entire reply when it
  finishes. `off`: no speech.
- `JAWS_CLAUDE_MUTE` — `on` (default): mute JAWS screen echo during Claude
  sessions, restore it after. `off`: never touch screen echo.
- `JAWS_TOKEN` — the prompt sentinel, default `<jaws>`.

## Runtime files

Everything lands under `~/.cache/`, readable from Windows at
`\\wsl.localhost\<distro>\home\<user>\.cache\`.

- `jaws-term/` — `last-command.txt`, `last-output.txt`, `last-full.txt`,
  `history.log` (size-capped), raw `session-*.log` recordings.
- `jaws-claude/` — `messages.log`, `last-message.txt`, `commands.log`,
  `last-tool.txt`, `notifications.log`, `status.txt`, `state.json`.

The logs double as a permanent, greppable record of your sessions — useful
well beyond accessibility.

## Troubleshooting

- **JAWS says "unknown function" when Claude starts or exits** — the JAWS
  API's `RunFunction` takes a bare function name; passing `Name()` with
  parentheses causes exactly this. Current plugin code strips them.
- **Compile error: CreateObjectEx requires between 2 and 3 parameters** —
  older snippets called it with one argument; both calls in the shipped
  `.jss` use the two-argument form.
- **Viewers say nothing was captured** — confirm the prompt starts with
  `<jaws>` in a *new* terminal, and that `~/.cache/jaws-term/last-full.txt`
  updates after running a command.
- **Terminal stuck silent after a crashed Claude session** — press
  Control+JAWSKey+S to restore speech.
- **Paths in the `.jss`** — never collapse `JawsAccessPath` into a single
  string literal: `home\norab` contains `\n`, which the JAWS script
  compiler may interpret as a newline. The path is built from segments at
  runtime for exactly this reason.

## Known limitations

- Full-screen programs (vim, less, the Claude TUI itself) redraw the screen
  rather than print lines, so the *shell* capture of them is garbled. Claude
  output is captured cleanly through the plugin instead.
- Repainting progress bars can leave minor residue in captured output.
- With several terminal tabs, the `last-*` files reflect whichever tab most
  recently finished a command, and the Claude-session mute covers the whole
  Windows Terminal application, not a single tab.
- Command output containing lines that start with `<jaws> ` confuses the
  prompt-boundary detection.
- Claude replies are captured when they finish, not streamed word-by-word.

## Roadmap

- Braille filtering: on prompt lines, show only the typed command on the
  braille display (the sentinel token is the detection anchor).
- Per-tab capture scoping.
- A picker for "output of the Nth previous command".
- Capturing edit diffs, plan-mode plans, and todo lists as separate views.

## A note on the JAWS script file

This repository contains only its own code. The factory Windows Terminal
scripts that `jaws/JawsAccess-additions.jss` extends are copyright Freedom
Scientific Inc. and ship with every JAWS installation — that's why the
install step is "paste the additions at the end of the file Script Manager
shows you" rather than replacing it. If you keep a locally merged copy for
convenience, don't redistribute it.
