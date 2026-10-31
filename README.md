[English](README.md) · [中文](README_cn.md)

# Durweg

Durweg makes AI agents (Claude Code, Codex) work by your own method, the same way every time, so
their output is stable. A skill tells an agent how to work but not whether it did: it can skip a
step, decide for you, or leave no trace. Durweg runs your method step by step, stops the agent at
each step's checks, asks you where your method says so, and keeps a record you can check.

## Install

You need no GitHub account. The installer asks for your language first, then sets everything up
and starts your agent with a first example. If no agent is installed yet, it asks whether to
install Claude Code or Codex; you log in to it once in your browser.

- **Windows:** download [`Durweg-Install.bat`](https://github.com/musetee/durweg/releases/latest/download/Durweg-Install.bat) and double-click it.
  1. Choose the language.
  2. Choose where Durweg goes: **Windows**, or **WSL** (Linux inside Windows; take it if you also
     want workflows that need Linux).
  3. Without WSL yet, it installs WSL first: approve the administrator prompt, restart, open
     "Ubuntu" from the Start menu once to choose a Linux user name and password, then double-click
     the file again. It remembers your choices.
  4. "Windows protected your PC": click **More info → Run anyway**.
- **macOS:** download [`Durweg-Install-macOS.zip`](https://github.com/musetee/durweg/releases/latest/download/Durweg-Install-macOS.zip), unzip it, double-click `Durweg-Install.command`.
  The first time macOS may block it: open System Settings → Privacy & Security and allow it. If macOS
  installs its developer tools first, double-click the file again when that has finished.
- **Linux:** open a terminal and paste
  `curl -fsSL https://raw.githubusercontent.com/musetee/durweg/v1.0.0/install.sh | bash`

Done looks like this: your agent starts and walks you through **write down your method**: you
describe one piece of work you do the same way every time, confirm the steps, and get your own
workflow, which you then run once.

## Every day

Tell your agent which workflow to run, for example "Run weekly-report with durweg." It goes step by
step, stops where a step's check fails, and asks you where your method says you decide. To see what
you have: "Show me my durweg workflows" (it runs `durweg library list`).

## Where your files are

- `~/Durweg/` (on Windows `C:\Users\<you>\Durweg`): your settings (`config.json`, the language),
  your workflows (`workflows/`) and the list of them (`library.json`).
- Each run is a folder under `runs/` in the project folder you started it from: `steps/` holds what
  each step delivered, `run.md` a readable summary (`durweg render <run>`), `.wf/` the record and the
  locked copy of the workflow (do not edit it).

## Example: write down your method

This is the first thing the installer starts; it shows what Durweg is for. You tell the agent how
you do one piece of work (say, the weekly status report: collect, write, approve); it writes your
steps down, shows them to you, and builds a workflow `weekly-report` from exactly the steps you
confirmed. It puts the workflow into your library and runs it once with you. From then on: "Run
weekly-report with durweg."

## What you can do

- Write a workflow by hand: [docs/workflow-format.md](docs/workflow-format.md).
- Check a run: `durweg check <run folder>`.
- Change the language: `durweg config language en` (or `zh`). To install somewhere else (on Windows: also
  into WSL), run the installer again and type `c` when it shows your last choices.
- Remove Durweg (keeps `~/Durweg` and your runs): `durweg uninstall`.
- Compare a run with the agent's session files: the optional plugin [durweg-audit](https://github.com/musetee/durweg-audit).

## Common problems

- **Windows 10: the Claude login does not work in the installer window.** Windows 10's old console
  cannot show modern command-line programs well. Install Windows Terminal (Microsoft Store) if you do
  not have it, open it, and run the installer there: open a **Command Prompt** tab (the ˅ next to
  the tabs), drag `Durweg-Install.bat` into it and press Enter. In a PowerShell tab, type `& ` first,
  then drag the file in and press Enter.

License: [MIT](LICENSE).
