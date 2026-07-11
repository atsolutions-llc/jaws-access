; JawsAccess-additions.jss — JAWS terminal + Claude Code accessibility
;
; Additions to the factory Windows Terminal scripts. Almost append-only:
; the Claude-session mute needs two small edits inside the factory code,
; described in steps 2 and 3 below. If you would rather skip the hand
; edits, replace the whole file with jaws/WindowsTerminal.jss instead —
; that is the factory file with everything here already merged.
;
; Install (JAWS 2026):
;   1. Focus Windows Terminal and press JAWSKey+0 to open Script Manager.
;      It shows the Windows Terminal script source.
;   2. Add the mute flag to the globals list at the top of the factory
;      file: put a comma after the last entry (usually
;      "int WindowsTerminalLastKeyPressTime") and add a new line:
;          int JawsAccessMuted
;   3. In the factory ReadNewText function, wrap the Say call so it is
;      skipped while muted. Replace:
;          Say(GetNewlyWrittenText(Text,terminal_LastText),OT_NONHIGHLIGHTED_SCREEN_TEXT)
;      with:
;          if !JawsAccessMuted
;              Say(GetNewlyWrittenText(Text,terminal_LastText),OT_NONHIGHLIGHTED_SCREEN_TEXT)
;          EndIf
;      Leave the "terminal_LastText = Text" line after it untouched, so
;      nothing is spoken in a burst when the mute lifts.
;   4. Move to the very end of the file (Ctrl+End) and paste this entire
;      file below the existing code.
;   5. Compile with Ctrl+S.
;   6. Install the key bindings from WindowsTerminal.jkm (the WSL-side
;      install.sh copies it into your JAWS user settings folder).
;
; Reads capture files written on the WSL side (wsl/jaws-terminal.bash and
; the jaws-access Claude Code plugin) into the virtual viewer or speech.
; See the project README for the full picture.

; ---------------------------------------------------------------------------
; Claude-session mute: silence the terminal's automatic narration while a
; Claude Code session runs. JAWS 2026 removed SetScreenEcho — calls compile
; but fail at runtime with "unknown function call" — so the mute is a plain
; script flag: the factory ReadNewText skips its Say while JawsAccessMuted
; is set (steps 2 and 3 above). SayString announcements, typing echo, and
; manual review are unaffected. The flag survives app switches for the
; whole JAWS session, the same way the factory terminal_LastText global
; does.
; ---------------------------------------------------------------------------

void function JawsAccessMute()
; Called by the Claude Code jaws-access plugin over the JAWS API when a
; session starts, and by the ToggleTerminalSpeech script.
    JawsAccessMuted = true
EndFunction

void function JawsAccessUnmute()
    JawsAccessMuted = false
EndFunction

Script ToggleTerminalSpeech()
; Manual override, e.g. if a Claude session ends without restoring speech.
    if JawsAccessMuted
        JawsAccessUnmute()
        SayString("Terminal speech on")
    else
        JawsAccessMute()
        SayString("Terminal speech off")
    EndIf
EndScript

; ---------------------------------------------------------------------------
; Reading the WSL capture files
; ---------------------------------------------------------------------------

string function JawsAccessBackslash()
; A single backslash, however this compiler treats backslashes in string
; literals. The factory code uses "\n" as a newline, so at least some
; escape processing happens; whether "\\" collapses to one character is
; version-dependent. Detect at runtime instead of guessing.
    var string sBS = "\\"
    if StringLength(sBS) == 2
        return StringLeft(sBS, 1)
    EndIf
    return sBS
EndFunction

string function JawsAccessPath(string sDir, string sFile)
; Build \\wsl.localhost\Ubuntu\home\norab\.cache\<sDir>\<sFile> piece by
; piece. Never write this path as one literal: "home\norab" contains "\n",
; which the compiler may turn into a newline. Adjust the distro or user
; segments here if they ever change.
    var string sBS = JawsAccessBackslash()
    var string sP = FormatString("%1%2wsl.localhost", sBS, sBS)
    sP = FormatString("%1%2Ubuntu", sP, sBS)
    sP = FormatString("%1%2home", sP, sBS)
    sP = FormatString("%1%2norab", sP, sBS)
    sP = FormatString("%1%2.cache", sP, sBS)
    sP = FormatString("%1%2%3", sP, sBS, sDir)
    return FormatString("%1%2%3", sP, sBS, sFile)
EndFunction

string function JawsAccessReadFile(string sPath)
; Read a UTF-8 text file from the WSL share. Returns an empty string if the
; file is missing or COM is unavailable. ADODB.Stream is used instead of
; FileSystemObject.OpenTextFile because the capture files are UTF-8.
; CreateObjectEx's second parameter is CreateNew: false reuses a running
; instance if one exists.
    var object oFSO = CreateObjectEx("Scripting.FileSystemObject", false)
    if !oFSO
        return ""
    EndIf
    if !oFSO.FileExists(sPath)
        return ""
    EndIf
    var object oStream = CreateObjectEx("ADODB.Stream", false)
    if !oStream
        return ""
    EndIf
    oStream.Type = 2 ; adTypeText
    oStream.Charset = "utf-8"
    oStream.Open()
    oStream.LoadFromFile(sPath)
    var string sText = oStream.ReadText(-1) ; adReadAll
    oStream.Close()
    return sText
EndFunction

void function JawsAccessShowFile(string sPath, string sTitle, string sEmptyMsg)
; Pour a capture file into the virtual viewer, cursor at the end (newest
; content), matching the factory VirtualizeWindow behavior. Esc closes.
    var string sText = JawsAccessReadFile(sPath)
    if !sText
        SayString(sEmptyMsg)
        return
    EndIf
    SayString(sTitle)
    UserBufferClear()
    UserBufferAddText(sText)
    UserBufferActivate()
    JAWSBottomOfFile()
    SayLine()
EndFunction

void function JawsAccessWriteVersion()
; Deploy verification. ReloadAllScripts has twice been observed to return
; without actually loading a freshly compiled .jsb, and RunFunction's
; return value proves nothing — so after every recompile the WSL side
; calls this and then reads jss-version.txt to confirm which build is
; live. Bump the string whenever the script source changes.
    var object oFSO = CreateObjectEx("Scripting.FileSystemObject", false)
    if !oFSO
        return
    EndIf
    var object oFile = oFSO.CreateTextFile(
        JawsAccessPath("jaws-claude", "jss-version.txt"), true)
    oFile.WriteLine("2026-07-11.3")
    oFile.Close()
EndFunction

void function JawsAccessSpeakFile(string sPath, string sEmptyMsg)
    var string sText = JawsAccessReadFile(sPath)
    if !sText
        SayString(sEmptyMsg)
        return
    EndIf
    SayString(sText)
EndFunction

; ---------------------------------------------------------------------------
; Terminal capture keystrokes
; ---------------------------------------------------------------------------

Script ShowLastCommandOutput()
    JawsAccessShowFile(JawsAccessPath("jaws-term", "last-full.txt"),
        "Last command output",
        "No command output captured yet. Is jaws-terminal.bash sourced in your bashrc?")
EndScript

Script ShowTerminalHistory()
    JawsAccessShowFile(JawsAccessPath("jaws-term", "history.log"),
        "Terminal history, oldest first",
        "No terminal history captured yet.")
EndScript

Script SpeakLastCommand()
    JawsAccessSpeakFile(JawsAccessPath("jaws-term", "last-command.txt"),
        "No command captured yet.")
EndScript

; ---------------------------------------------------------------------------
; Claude Code keystrokes (fed by the jaws-access plugin)
; ---------------------------------------------------------------------------

Script ShowClaudeMessages()
    JawsAccessShowFile(JawsAccessPath("jaws-claude", "messages.log"),
        "Claude conversation, oldest first",
        "No Claude messages logged yet. Is Claude running with the jaws-access plugin?")
EndScript

Script ShowClaudeCommands()
    JawsAccessShowFile(JawsAccessPath("jaws-claude", "commands.log"),
        "Commands Claude ran, oldest first",
        "No Claude commands logged yet.")
EndScript

Script SpeakClaudeStatus()
; Speak the session status a sighted user reads off the status line and
; mode indicator: permission mode, current activity, context usage, model,
; cost. Maintained by the plugin hooks plus the statusline script.
    JawsAccessSpeakFile(JawsAccessPath("jaws-claude", "status.txt"),
        "No Claude status recorded yet. Is Claude running with the jaws-access plugin?")
EndScript

Script SpeakLastClaudeMessage()
    JawsAccessSpeakFile(JawsAccessPath("jaws-claude", "last-message.txt"),
        "No Claude message logged yet.")
EndScript

Script ShowLastClaudeMessage()
    JawsAccessShowFile(JawsAccessPath("jaws-claude", "last-message.txt"),
        "Latest Claude message",
        "No Claude message logged yet.")
EndScript

; ---------------------------------------------------------------------------
; Shift+Tab: announce the Claude Code permission mode
;
; Claude Code cycles its permission mode on Shift+Tab but exposes no event
; for it: no hook fires on the change and the statusline payload carries no
; mode field (both are open Claude Code feature requests, #6227 and #31579,
; verified absent in 2.1.207). So this is the one place the project reads
; the screen: pass the keystroke through, wait for the TUI to redraw, then
; look for the mode indicator Claude draws under its input box. Default
; mode draws no indicator, so "nothing found" is announced as manual
; approval — which also means pressing Shift+Tab outside Claude announces
; "manual approval" after a second; harmless, and the keystroke still
; reaches the application first in every case.
;
; If a Claude Code update changes the indicator wording, update the
; needles in JawsAccessModeOnScreen below.
; ---------------------------------------------------------------------------

string function JawsAccessModeOnScreen()
; The permission-mode indicator currently visible in the terminal, as a
; speakable phrase (matching the plugin's status.txt wording), or an empty
; string when no indicator is on screen.
    var string sText = StringLower(GetTextInConsoleWindow())
    if StringContains(sText, "accept edits on")
        return "accept edits"
    EndIf
    if StringContains(sText, "plan mode on")
        return "plan mode"
    EndIf
    if StringContains(sText, "bypass permissions on")
        return "bypass permissions, fully automatic"
    EndIf
    if StringContains(sText, "auto mode on")
        return "auto mode"
    EndIf
    return ""
EndFunction

Script AnnounceClaudeMode()
; Bound to Shift+Tab. The keystroke is always passed through; the
; announcement waits until the indicator actually changes (up to about
; 1.6 seconds) so a slow redraw is not read as the old mode.
    if GetObjectClassName() != TerminalClassName
        TypeCurrentScriptKey()
        return
    EndIf
    var string sBefore = JawsAccessModeOnScreen()
    TypeCurrentScriptKey()
    var string sAfter = sBefore
    var int i = 0
    while i < 8 && sAfter == sBefore
        Delay(2)
        sAfter = JawsAccessModeOnScreen()
        i = i + 1
    EndWhile
    if sAfter
        SayString(sAfter)
    else
        SayString("manual approval")
    EndIf
EndScript

; ---------------------------------------------------------------------------
; Scrollback virtualization
; The factory VirtualizeWindow script only captures the VISIBLE ranges of the
; UIA text pattern. The same pattern exposes DocumentRange, which covers the
; whole buffer including scrollback — text the JAWS cursor can never reach.
; ---------------------------------------------------------------------------

Script ShowScrollbackInViewer()
    if GetObjectClassName() != TerminalClassName
        SayString("Not in a terminal pane")
        return
    EndIf
    if !WindowsTerminalTextProvider
        WindowsTerminalTextProvider = FSUIAGetFocusedElement().GetTextPattern()
    EndIf
    if !WindowsTerminalTextProvider
        SayString("Terminal text is unavailable")
        return
    EndIf
    var object oRange = WindowsTerminalTextProvider.DocumentRange
    if !oRange
        SayString("Scrollback is unavailable")
        return
    EndIf
    var string sText = StringTrimTrailingBlanks(oRange.GetText(-1))
    if !sText
        SayMessage(OT_ERROR,cmsgNoTextToVirtualize_L,cmsgNoTextToVirtualize_S)
        return
    EndIf
    SayString("Full terminal buffer")
    UserBufferClear()
    UserBufferAddText(sText)
    UserBufferActivate()
    JAWSBottomOfFile()
    SayLine()
EndScript
