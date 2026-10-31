[English](README.md) · [中文](README_cn.md)

# Durweg

**Durweg turns the way you always do a piece of work into a workflow that AI agents (Claude Code, Codex) follow step by step every time, without skipping steps or deciding for you, so their output is stable.**

Given only instructions (a skill), an agent can skip a step or decide for you, and afterwards you
cannot tell. With Durweg each step must pass its checks before the next one starts, the agent stops
and asks you where your method says you decide, and every run leaves a record you can check.

## 🧭 Install

You need no GitHub account. You need an account for Claude Code or Codex (use counts against your
own plan); if neither is on your computer yet, the installer installs one.

**Run the installer** (pick the row for your computer):

| Your computer | What to do |
| :--- | :--- |
| **Windows**<br>(with or without WSL) | • Download [`Durweg-Install.bat`](https://github.com/musetee/durweg/releases/latest/download/Durweg-Install.bat) and double-click it in Windows<br>• To install into WSL, use it too and choose WSL in the installer; you do not open WSL or type commands yourself |
| **Mac** | Download [`Durweg-Install-macOS.zip`](https://github.com/musetee/durweg/releases/latest/download/Durweg-Install-macOS.zip), unzip it and double-click `Durweg-Install.command` |
| **Linux**<br>(not WSL on Windows) | In a terminal, run:<br>`curl -fsSL https://raw.githubusercontent.com/musetee/durweg/v1.0.0/install.sh \| bash` |

The installer asks for your language first (on Windows also where to install: Windows or WSL),
sets everything up, starts your agent and walks you through the [example](#-example-write-down-your-method).
What to answer at each question on the way: see [Questions during installation](#-questions-during-installation)
at the end of this page.

## 📅 Every day

1. **Open a terminal.** Windows: open Windows Terminal (if Durweg is in WSL, open "Ubuntu" from the
   Start menu). Mac or Linux: open Terminal.
2. **Go to your project folder:** `cd ~/projects/my-project` (on Windows itself, for example
   `cd C:\Users\<you>\projects\my-project`). Each run is kept in a `runs/` folder there.
3. **Start your agent:** type `claude` (Claude Code) or `codex` (Codex) and press Enter.
4. **Tell it what to do:**
   - Run a workflow: "Run weekly-report with durweg." It goes step by step, stops where a step's
     check fails, and asks you where your method says you decide.
   - Make a new workflow: "Run write-your-method with durweg." (the guide from the
     [example](#-example-write-down-your-method)).
   - See what you have: "Show me my durweg workflows."

## 📁 Where your files are

| What | Where | What is in it |
| :--- | :--- | :--- |
| **Your settings and workflows** | `~/Durweg/` | • `config.json`: the settings, with the language<br>• `workflows/`: your workflows<br>• `library.json`: the list of them |
| **The record of each run** | under `runs/` in the project folder you started it from, one folder per run | • `steps/`: what each step delivered<br>• `run.md`: a readable summary (`durweg render <run>`)<br>• `.wf/`: the record and the locked copy of the workflow (do not edit it) |

**Finding them in Windows:**

| Durweg is installed | How to find them |
| :--- | :--- |
| **on Windows itself** | `~/Durweg` is `C:\Users\<you>\Durweg` |
| **in WSL** | • In File Explorer's left pane: **Linux → Ubuntu → home → <your Linux user name>**<br>• Or run `explorer.exe .` in the WSL terminal to open the current folder |

On a Mac and on Linux they are in your home folder.

## 🚀 Example: write down your method

This example shows how Durweg turns one of your fixed ways of working into a workflow: taking the
weekly status report, you make your own workflow `weekly-report` and run it once. The installer
walks you through it the first time; to make another one later, follow these steps.

1. **Open a terminal** (step 1 of "Every day").
2. **Make a practice folder and go into it:** `mkdir -p ~/projects/first-method && cd ~/projects/first-method`.
   The record of this run goes there.
3. **Start your agent** (step 3 of "Every day").
4. **Tell it:** "Run write-your-method with durweg." Then answer its questions on how you do the
   weekly report (collect, write, approve and send), and confirm the steps it shows you.

Done looks like this: the agent tells you the check result is `PASS`, and "Show me my durweg
workflows" lists `weekly-report`. From then on: "Run weekly-report with durweg."

## 🙋 I want to …

| I want to | How |
| :--- | :--- |
| Write a workflow by hand | [workflow format](docs/workflow-format.md) |
| Check a run | `durweg check <run folder>` |
| Change the language | `durweg config language en` (or `zh`) |
| Install somewhere else (on Windows: into WSL) | Run the installer again and type `c` when it asks whether to change Durweg |
| Compare a run with the agent's own session files | The optional plugin [durweg-audit](https://github.com/musetee/durweg-audit) |
| Remove Durweg | `durweg uninstall`: keeps `~/Durweg` and your runs ([uninstall](docs/uninstall.md)) |

## 🛠️ Common problems

- **Windows 10: the Claude login does not work in the installer window.** Run the installer in
  Windows Terminal instead: open a Command Prompt tab, drag `Durweg-Install.bat` into it and press
  Enter ([step by step](docs/troubleshooting.md#windows-10-the-claude-login-does-not-work-in-the-installer-window)).
- **You installed another agent after Durweg (say Codex first, Claude Code later):** the new agent
  cannot use Durweg yet. Run the installer again and press Enter when it asks whether to change
  Durweg; it sets Durweg up for every agent on the computer.

## 💬 Questions during installation

| Question | What to choose |
| :--- | :--- |
| **Language** | The language your agent will use; change it later with `durweg config language` |
| **Where to install** (Windows) | • Usually **Windows**<br>• **WSL** (Linux inside Windows) if you also want workflows that need Linux |
| **No WSL yet** | • Approve the administrator prompt and restart<br>• Open "Ubuntu" from the Start menu once to choose a Linux user name and password<br>• Double-click the installer again; it remembers your choices |
| **"Windows protected your PC"** | Click **More info → Run anyway** |
| **macOS blocked the installer** | • Open System Settings → Privacy & Security and allow it<br>• If macOS installs its developer tools first, double-click the file again when that has finished |
| **Claude Code or Codex** | • Asked only when neither is installed; press Enter for Claude Code<br>• Log in to it once in your browser afterwards |
| **Asked on a second run whether to change Durweg** | • Enter: keep the last choices (update or repair)<br>• `c`: choose again and install Durweg anew |

---

License: [MIT](LICENSE).
