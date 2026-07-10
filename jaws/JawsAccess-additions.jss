; JawsAccess-additions.jss — JAWS terminal + Claude Code accessibility
;
; APPEND-ONLY additions to the factory Windows Terminal scripts. Nothing in
; the factory file needs to be edited.
;
; Install (JAWS 2026):
;   1. Focus Windows Terminal and press JAWSKey+0 to open Script Manager.
;      It shows the Windows Terminal script source.
;   2. Move to the very end of the file (Ctrl+End) and paste this entire
;      file below the existing code.
;   3. Compile with Ctrl+S.
;   4. Install the key bindings from WindowsTerminal.jkm (the WSL-side
;      install.sh copies it into your JAWS user settings folder).
;
; If the compiler rejects the globals section below (some versions may not
; accept a second globals block), delete these two lines here and add
; JawsAccessSavedEcho and JawsAccessMuted to the globals list at the top of
; the factory file instead.
;
; Reads capture files written on the WSL side (wsl/jaws-terminal.bash and
; the jaws-access Claude Code plugin) into the virtual viewer or speech.
; See the project README for the full picture.

globals
    int JawsAccessSavedEcho,
    int JawsAccessMuted

; ---------------------------------------------------------------------------
; Claude-session mute: silence the terminal's automatic screen-echo chatter
; while a Claude Code session runs. The factory ReadNewText loop only speaks
; when screen echo is ECHO_ALL, so this silences exactly that. SayString
; announcements, typing echo, and manual review are unaffected.
; ---------------------------------------------------------------------------

void function JawsAccessMute()
; Called by the Claude Code jaws-access plugin over the JAWS API when a
; session starts, and by the ToggleTerminalSpeech script.
    if !JawsAccessMuted
        JawsAccessSavedEcho = GetScreenEcho()
        JawsAccessMuted = true
    EndIf
    SetScreenEcho(ECHO_NONE)
EndFunction

void function JawsAccessUnmute()
    if JawsAccessMuted
        SetScreenEcho(JawsAccessSavedEcho)
        JawsAccessMuted = false
    EndIf
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

void function FocusChangedEvent(handle hwndFocus, handle hwndPrevFocus)
; Switching apps reloads this app's settings, which would undo a runtime
; mute. Re-apply it on the way back in while a Claude session is active
; (JawsAccessMuted survives app switches), then chain to default handling.
    if JawsAccessMuted
        SetScreenEcho(ECHO_NONE)
    EndIf
    FocusChangedEvent(hwndFocus, hwndPrevFocus)
EndFunction

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
