[← README](../README.md) · [中文 README](../README_cn.md)

# Installing Durweg: instructions for an AI agent

This page is for an AI agent (Claude Code, Codex, Antigravity …) that a user asked to install
Durweg on their computer. Follow it step by step. Run the commands yourself; the installer asks no
questions when the settings below are given.

## 1. Decide two things

- **Language** for Durweg: `zh` if the user writes to you in Chinese, otherwise `en`.
- **Which kind of computer** you are running on:

| You find | It is | Go to |
| :--- | :--- | :--- |
| `uname -s` says `Linux`, and `/proc/version` contains `microsoft` | WSL on Windows | 2a |
| `uname -s` says `Linux` | Linux | 2a |
| `uname -s` says `Darwin` | Mac | 2a |
| PowerShell, or a bash on Windows (Git Bash: `uname -s` starts with `MINGW` or `MSYS`) | Windows itself | 2b |

## 2a. Linux, Mac, WSL

Run, with the language from step 1:

```
curl -fsSL https://raw.githubusercontent.com/musetee/durweg/main/install.sh | DURWEG_LANG=zh DURWEG_NO_START=1 bash
```

- **Mac, "macOS is installing its developer tools":** a window opened for the user. Tell them to
  finish it, then run the command again.
- **Linux, "sudo asks for your password":** you cannot type the user's password. Tell the user to run
  the line the installer prints for the missing programs (in Claude Code: `! sudo apt-get install …`),
  then run the command again.

## 2b. Windows itself

In PowerShell (from a bash on Windows, put the lines into `powershell.exe -NoProfile -Command "…"`):

```
$f = Join-Path $env:TEMP 'Durweg-Install.bat'
Invoke-WebRequest -UseBasicParsing https://github.com/musetee/durweg/releases/latest/download/Durweg-Install.bat -OutFile $f
$env:DURWEG_LANG = 'zh'; $env:DURWEG_TARGET = 'windows'; $env:DURWEG_NO_START = '1'; $env:DURWEG_NO_PAUSE = '1'
cmd /c $f
```

This installs Durweg on Windows itself (Python too, if it is missing). Install into WSL only when the
user asks for it: then set `DURWEG_TARGET = 'wsl'`; if WSL is not set up yet, Windows asks the user
for administrator approval and a restart, which only the user can do.

## 3. Check

- Linux, Mac, WSL: `~/.local/bin/durweg --version`
- Windows: `& "$env:LOCALAPPDATA\Durweg\bin\durweg.cmd" --version`

It prints `durweg` and a version number. If the installer stopped instead, show the user its last
lines (they say what to fix); do not change Durweg's files by hand.

## 4. Tell the user

Say that Durweg is installed, and that they should **start you again** (a new session), because an
agent reads its skills when it starts. Then they can say: "Run write-your-method with durweg."
