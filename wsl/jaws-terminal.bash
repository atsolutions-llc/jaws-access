# jaws-terminal.bash — JAWS terminal accessibility: prompt token + full-session
# capture + last-command-output extraction.
#
# Install: add this line at the END of ~/.bashrc (after any PS1 customization):
#   source ~/jaws-scripting/wsl/jaws-terminal.bash
#
# What it does:
#   1. Records the entire terminal session with script(1) to ~/.cache/jaws-term/
#   2. Prepends the "<jaws>" sentinel token to the prompt (plus OSC 133 marks
#      that Windows Terminal understands for its own shell integration)
#   3. After every command, extracts that command's output into
#      ~/.cache/jaws-term/last-output.txt (and friends), which the JAWS script
#      reads over \\wsl.localhost\ into the virtual viewer.

# Interactive shells only
case $- in *i*) ;; *) return ;; esac

JAWS_TERM_DIR="$HOME/.cache/jaws-term"
# The extractor lives next to this file, wherever the repo was cloned.
JAWS_EXTRACTOR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/jaws_extract.py"
mkdir -p "$JAWS_TERM_DIR"

# --- 1. Session recorder -----------------------------------------------------
# Re-exec this shell under script(1) so every byte the terminal shows is
# logged. The exported JAWS_TERM_LOG guard stops the inner shell (which
# re-reads .bashrc) from recording again, and stops nested bash sessions from
# double-recording.
if [ -z "$JAWS_TERM_LOG" ] && [ -t 0 ] && command -v script >/dev/null 2>&1; then
    # Prune session logs older than 2 days
    find "$JAWS_TERM_DIR" -name 'session-*.log' -mtime +2 -delete 2>/dev/null
    export JAWS_TERM_LOG="$JAWS_TERM_DIR/session-$(date +%Y%m%d-%H%M%S)-$$.log"
    exec script -q -f "$JAWS_TERM_LOG"
fi

# --- 2. Prompt marks ---------------------------------------------------------
# OSC 133 prompt-start/end marks: invisible escape sequences that Windows
# Terminal understands (shell integration) and that survive verbatim in the
# script(1) log, where the extractor uses them as prompt boundaries. Nothing
# is added to what you see, hear, or read in braille.
PS1="\[\e]133;A\a\]${PS1}\[\e]133;B\a\]"

# --- 3. Per-command extraction -----------------------------------------------
# Runs after every command, synchronously and BEFORE the next prompt prints —
# that ordering is what makes "everything after the last sentinel line in the
# log" exactly equal to the last command's output. Costs ~40ms per prompt.
# The typed command comes from bash history (reliable) rather than from the
# screen echo (mangled by line editing / tab completion).
__jaws_extract() {
    [ -n "$JAWS_TERM_LOG" ] || return 0
    [ -f "$JAWS_EXTRACTOR" ] || return 0
    local hist
    hist=$(HISTTIMEFORMAT='' builtin history 1)
    python3 "$JAWS_EXTRACTOR" "$JAWS_TERM_LOG" "$hist" >/dev/null 2>&1
}
case ";${PROMPT_COMMAND:-};" in
    *";__jaws_extract;"*) ;;
    *) PROMPT_COMMAND="__jaws_extract${PROMPT_COMMAND:+;$PROMPT_COMMAND}" ;;
esac
