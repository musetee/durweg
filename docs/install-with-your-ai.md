[← README](../README.md) · [中文 README](../README_cn.md)

# Installing Durweg: instructions for an AI agent

This page is for an AI agent (Claude Code, Codex, Antigravity …) that a user asked to install
Durweg on their computer. Follow it step by step and run the commands yourself. With the settings
below the installer asks no questions; `DURWEG_AGENT=own` matters only when the installer cannot
find you on the PATH: then it gives Claude Code and Codex the skills instead of installing another
agent.

## 1. Decide three things

- **Language** for Durweg: `zh` if the user writes to you in Chinese, otherwise `en`.
- **Which kind of computer you run on:**

| You find | It is | Go to |
| :--- | :--- | :--- |
| `uname -s` says `Linux`, and `/proc/version` contains `microsoft` | WSL on Windows | 2a |
| `uname -s` says `Linux` | Linux | 2a |
| `uname -s` says `Darwin` | Mac | 2a |
| PowerShell, or a bash on Windows (Git Bash: `uname -s` starts with `MINGW` or `MSYS`) | Windows itself | 2b |

- **Where Durweg goes:** where you run. If you run on Windows itself and the user wants Durweg in
  WSL, do not install from Windows: ask the user to open "Ubuntu" from the Start menu, start their
  agent there, and send you (that agent) the same request; then follow 2a there.

## 2a. Linux, Mac, WSL

Run, with the language from step 1:

```
curl -fsSL https://raw.githubusercontent.com/musetee/durweg/main/install.sh | DURWEG_LANG=zh DURWEG_NO_START=1 DURWEG_AGENT=own bash
```

- **Mac, "macOS is installing its developer tools":** a window opened for the user. Tell them to
  finish it, then run the command again.
- **Linux, a program is missing (python3, curl or tar) and sudo needs a password:** you cannot type
  it. Check yourself which of the three are missing (`command -v python3 curl tar`). On Debian or
  Ubuntu give the user the complete line to run in their own terminal, for example
  `sudo apt-get update && sudo apt-get install -y python3 curl` with only the missing ones (in
  Claude Code they can type it after `!`); on other systems name the missing programs and their
  package manager. Then run the command again.

## 2b. Windows itself

In PowerShell (from a bash on Windows, put the lines into `powershell.exe -NoProfile -Command "…"`):

```
$f = Join-Path $env:TEMP 'Durweg-Install.bat'
Invoke-WebRequest -UseBasicParsing https://github.com/musetee/durweg/releases/latest/download/Durweg-Install.bat -OutFile $f
$env:DURWEG_LANG = 'zh'; $env:DURWEG_TARGET = 'windows'; $env:DURWEG_AGENT = 'own'
$env:DURWEG_NO_START = '1'; $env:DURWEG_NO_PAUSE = '1'
cmd /c $f
```

This installs Durweg on Windows itself, and Python too if it is missing.

## 3. Check

- Linux, Mac, WSL: `~/.local/bin/durweg --version`
- Windows: `& "$env:LOCALAPPDATA\Durweg\bin\durweg.cmd" --version`

It prints `durweg` and a version number. If the installer stopped instead, show the user its last
lines (they say what to fix); do not change Durweg's files by hand.

## 4. Tell the user

Say that Durweg is installed, and that they should **start you again** (a new session, in the same
place: on Windows, or in WSL), because an agent reads its skills when it starts. Then they can say:
"Run write-your-method with durweg."
