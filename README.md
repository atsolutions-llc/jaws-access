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
   `script(1)` and marks every prompt with invisible OSC 133 escape
   sequences (the shell-integration standard Windows Terminal already
   understands — nothing is added to what you see, hear, or read in
   braille). After each command, an extractor uses those marks as prompt
   boundaries, strips the terminal escape codes, and saves that command's
   output to a file.
2. **Claude Code plugin** (`claude-plugin/jaws-access/`) — hooks log every
   Claude reply, every command Claude runs, every file it edits, and every
   notification. A status-line script tracks model, context usage, and
   cost. Hooks also push speech directly through the JAWS API: "Claude is
   done", "Claude needs your permission to use Bash" — and automatically
   silence the terminal's automatic narration while a Claude session runs,
   so the TUI repaint chatter disappears entirely.
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
- Live narration while Claude works: each of Claude's messages — the
  short status sentences ("Let me check the config…") and the final
  reply alike — is spoken as it is written, so a long turn is never a
  silent mystery. Press Control to silence a reading you don't need.
- Immediate spoken alerts when a tool call fails, with the first line of
  the error — the red text a sighted user catches at a glance.
- A significance taxonomy with a verbosity knob: choose whether only
  important events interrupt you, or also file edits, or all activity —
  at the most verbose level, commands and fetches are announced as they
  start, the spoken equivalent of the spinner's "Running one shell
  command…".
- The permission mode spoken as you cycle it with Shift+Tab — "auto mode",
  "plan mode", "manual approval" — instead of a silent change.
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

### Starting from zero: setting up WSL

Skip this section if you already work in WSL. These steps are written for
JAWS users installing WSL for the first time — every step is keyboard-only,
and they note where the process goes silent so you know nothing is stuck.

1. Open PowerShell as administrator: press the **Windows key**, type
   `powershell`, then press **Control+Shift+Enter**. A User Account Control
   dialog appears and JAWS announces it; press **Alt+Y** to accept.
2. On Windows 10, install Windows Terminal first (Windows 11 already has
   it): type `winget install Microsoft.WindowsTerminal` and press Enter.
   This avoids the Microsoft Store interface entirely.
3. Type `wsl --install -d Ubuntu` and press Enter. This installs WSL2 and
   Ubuntu in one step. Expect several minutes of intermittent progress
   messages; JAWS speaks them as they arrive.
4. Restart the computer when the output tells you to.
5. After the restart, Ubuntu finishes setting itself up — a console window
   may open on its own; if not, press the **Windows key**, type `ubuntu`,
   and press Enter. First-run provisioning can take a minute or two with
   no output at all. Silence here is normal.
6. When prompted, type a lowercase username and press Enter. The password
   prompts that follow are **completely silent as you type** — no
   character echo, no stars, nothing for JAWS to speak. That's standard
   Linux behavior, not a stall. Type the password, press Enter, and type
   it once more to confirm.
7. You now have a bash prompt. Update the system and install the basics
   (only `git` is typically missing; the rest confirms prerequisites):

   ```bash
   sudo apt update && sudo apt -y upgrade
   sudo apt install -y git python3
   ```

   `sudo` asks for your password — again with silent typing.
8. Install Claude Code:

   ```bash
   curl -fsSL https://claude.ai/install.sh | bash
   ```
9. Clone this project and run its installer:

   ```bash
   git clone https://github.com/atsolutions-llc/jaws-access.git
   cd jaws-access
   ./install.sh
   ```

The installer's output is plain single-column text, written to be listened
to, and it ends by reading out the two remaining JAWS-side steps.

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
| Control+JAWSKey+S | Toggle terminal speech (the Claude-session mute) manually |
| Shift+Tab | Passed through to Claude Code (cycles the permission mode); the new mode is announced |

Escape closes the virtual viewer. Viewers open at the end of the content,
on the newest line.

## Configuration

Set these in your environment (e.g. in `.bashrc` before starting `claude`):

- `JAWS_CLAUDE_SPEAK` — `announce` (default): short announcements plus
  spoken permission prompts. `full`: speak Claude's entire reply when it
  finishes. `off`: no speech.
- `JAWS_CLAUDE_MUTE` — `on` (default): mute the terminal's automatic
  narration during Claude sessions, restore it after. `off`: never mute.
- `JAWS_CLAUDE_NARRATE` — `full` (default): a background tailer follows
  the session transcript and speaks each of Claude's text messages the
  moment it is written, including the short status sentences between
  tool calls. `first`: speak only the first sentence of each message.
  `off`: no live narration. Speech is queued, so readings are never cut
  off by other announcements; a Control tap silences the current one.
  (Claude's internal reasoning is not available outside the TUI; this
  narrates exactly what Claude visibly says.)
- `JAWS_CLAUDE_VERBOSITY` — how much tool activity is spoken as it happens,
  based on a significance taxonomy (adapted from
  [claude-sonar](https://github.com/vylasaven/claude-sonar)): every event
  is classified as noise (file reads, searches), routine (commands,
  fetches), notable (file edits and writes), or important (failures,
  permission prompts, session events). `quiet` (default) speaks important
  only. `normal` adds notable — brief phrases like "Claude edited
  parser.py". `verbose` adds routine, announced both as they start
  ("starting: List repository files") and as they finish — the spoken
  version of the TUI's spinner text. Failures are spoken at every level,
  with the first line of the error. Logging and the status keystroke are
  always complete regardless — verbosity only decides what interrupts you.

## Runtime files

Everything lands under `~/.cache/`, readable from Windows at
`\\wsl.localhost\<distro>\home\<user>\.cache\`.

- `jaws-term/` — `last-command.txt`, `last-output.txt`, `last-full.txt`,
  `history.log` (size-capped), raw `session-*.log` recordings.
- `jaws-claude/` — `messages.log`, `last-message.txt`, `commands.log`,
  `last-tool.txt`, `notifications.log`, `status.txt`, `state.json`,
  `tailer.pid` (the live-narration daemon), `jss-version.txt` (which JAWS
  script build is loaded, written on demand).

The logs double as a permanent, greppable record of your sessions — useful
well beyond accessibility.

## Troubleshooting

- **JAWS says "unknown function" when Claude starts or exits** — the JAWS
  API's `RunFunction` takes a bare function name; passing `Name()` with
  parentheses causes exactly this. Current plugin code strips them.
- **Compile error: CreateObjectEx requires between 2 and 3 parameters** —
  older snippets called it with one argument; both calls in the shipped
  `.jss` use the two-argument form.
- **Viewers say nothing was captured** — in a *new* terminal, run a command
  and check that `~/.cache/jaws-term/last-full.txt` updates. If it doesn't,
  confirm `.bashrc` sources `jaws-terminal.bash` as its last line.
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
- Command output that contains raw OSC 133 escape bytes (for example,
  cat-ing an unfiltered terminal recording) confuses the prompt-boundary
  detection.
- Claude replies are captured when they finish, not streamed word-by-word.

## Roadmap

- Braille filtering: on prompt lines, show only the typed command on the
  braille display (anchored on the known prompt shape).
- Per-tab capture scoping.
- A picker for "output of the Nth previous command".
- Capturing edit diffs, plan-mode plans, and todo lists as separate views.
- Digest mode: batch routine announcements and deliver one spoken summary
  when the turn completes (another good claude-sonar idea).

## A note on the JAWS script file

This repository contains only its own code. The factory Windows Terminal
scripts that `jaws/JawsAccess-additions.jss` extends are copyright Freedom
Scientific Inc. and ship with every JAWS installation — that's why the
install step is "paste the additions at the end of the file Script Manager
shows you" rather than replacing it. If you keep a locally merged copy for
convenience, don't redistribute it.
