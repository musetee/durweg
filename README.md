[English](README.md) · [中文](README_cn.md)

# Durweg

**Durweg turns the way you always do a piece of work into a workflow that AI agents (Claude Code, Codex) follow step by step every time, without skipping steps or deciding for you, so their output is stable.**

Given only instructions (a skill), an agent can skip a step or decide for you, and afterwards you
cannot tell. With Durweg each step must pass its checks before the next one starts, the agent stops
and asks you where your method says you decide, and every run leaves a record you can check.

## 💻 System requirements

| Your computer | What it needs |
| :--- | :--- |
| **Windows** | • Windows 10 or 11<br>• Python 3.9 or newer; if it is missing, the installer installs Python 3.12 for you |
| **Mac** | • Python 3.9 or newer at `/usr/bin/python3`; it comes with Apple's developer tools (Command Line Tools), which the installer asks macOS to install if they are missing<br>• Older developer tools bring Python 3.7 or 3.8; check with `/usr/bin/python3 --version` and, if it is older than 3.9, update them in System Settings → General → Software Update |
| **Linux** | • Python 3.9 or newer, `curl` and `tar`<br>• On Debian or Ubuntu the installer installs what is missing (sudo asks for your password) |

## 🧭 Install

You need no GitHub account. You need an account for Claude Code or Codex (use counts against your
own plan); if neither is on your computer yet, the installer installs one. If you have Antigravity, it gets
Durweg too.

**Run the installer** (pick the row for your computer):

| Your computer | What to do |
| :--- | :--- |
| **Windows**<br>(with or without WSL) | • Download [`Durweg-Install.bat`](https://github.com/musetee/durweg/releases/latest/download/Durweg-Install.bat) and double-click it in Windows<br>• To install into WSL, use it too and choose WSL in the installer; you do not open WSL or type commands yourself |
| **Mac** | Download [`Durweg-Install-macOS.zip`](https://github.com/musetee/durweg/releases/latest/download/Durweg-Install-macOS.zip), unzip it and double-click `Durweg-Install.command` |
| **Linux**<br>(not WSL on Windows) | In a terminal, run:<br>`curl -fsSL https://raw.githubusercontent.com/musetee/durweg/v1.0.1/install.sh \| bash` |

The installer asks for your language first (on Windows also where to install: Windows or WSL),
sets everything up, opens this page in your browser, starts your agent and walks you through the [example](#-example-write-down-your-method).
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

## 🚀 Example: write down your method

This example shows how Durweg turns one of your fixed ways of working into a workflow: taking the
weekly status report, you make your own workflow `weekly-report`, run it once, and finally write it up as a case page
to keep or share. The installer
walks you through it the first time; to make another one later, follow these steps.

1. **Open a terminal** (step 1 of "Every day").
2. **Make a practice folder and go into it:** `mkdir -p ~/projects/first-method && cd ~/projects/first-method`.
   The record of this run goes there.
3. **Start your agent** (step 3 of "Every day").
4. **Tell it:** "Run write-your-method with durweg." Then answer its questions on how you do the
   weekly report (collect, write, approve and send), and confirm the steps it shows you.
5. **Write it up as a case (optional):** at the end it asks whether to write a case. If you want
   one, tell it what you would tell others; it turns your method, the steps, your own words at each
   confirmation and the first run's result into one web page in `~/Durweg/cases/`. Double-click it
   to open it in your browser, or send it to someone.

Done looks like this: the agent tells you the check result is `PASS`, and "Show me my durweg
workflows" lists `weekly-report`. From then on: "Run weekly-report with durweg."

**A real case:** with this guide the workflow `human-readme` was written (the way the README of the AIagents
project was made), and then used to rewrite Durweg's own README. The method, the steps, the user's
own words at each step and the lessons are on this case page (in Chinese):
[A README for people · Durweg case](https://claude.ai/artifact/LGnCog4wnBmgMAWJg1Xmi4).
To use the workflow yourself: [durweg-human-readme](https://github.com/musetee/durweg-human-readme).

## 🙋 I want to …

| I want to | How |
| :--- | :--- |
| Write a workflow by hand | [workflow format](docs/workflow-format.md) |
| Check a run | `durweg check <run folder>` |
| Change the language | `durweg config language en` (or `zh`) |
| Install somewhere else (on Windows: into WSL) | Run the installer again and type `c` when it asks whether to change Durweg |
| Compare a run with the agent's own session files | The optional plugin [durweg-audit](https://github.com/musetee/durweg-audit) |
| Find my settings, cases and run records | [Where your files are](docs/files.md) |
| Install a ready-made workflow | Tell your agent "Show me the durweg workflows I can install", then `durweg library add <name>` ([catalogs](docs/workflow-format.md#catalogs)) |
| Update Durweg and the workflows you installed | `durweg update` ([updating](docs/update.md)) |
| Share a workflow of yours (on GitHub, public or private) | Tell your agent "Publish <name> with durweg" ([publishing](docs/publish.md)) |
| Remove Durweg | `durweg uninstall`: keeps `~/Durweg` and your runs ([uninstall](docs/uninstall.md)) |

## 🛠️ Common problems

- **Windows 10: the Claude login does not work in the installer window.** Run the installer in
  Windows Terminal instead: open a Command Prompt tab, drag `Durweg-Install.bat` into it and press
  Enter ([step by step](docs/troubleshooting.md#windows-10-the-claude-login-does-not-work-in-the-installer-window)).
- **You installed another agent after Durweg (say Codex first, Claude Code later):** the new agent
  cannot use Durweg yet. Run the installer again and press Enter when it asks whether to change
  Durweg; it sets Durweg up for every agent on the computer.
- **Your agent is installed, but the installer says none was found:** your agent is not where the
  system looks (for example you start it with a script). Choose **3** at "which one should be
  installed": Durweg sets itself up for Claude Code and Codex; start your agent as usual and tell it
  "Run write-your-method with durweg."
- **Mac: the installer says Durweg needs Python 3.9 or newer, though your Mac has a newer one:** an
  older Python (for example Anaconda's 3.8) comes first in Terminal. Stop it from starting on its
  own, then run the installer again; no need to reinstall Python
  ([step by step](docs/troubleshooting.md#mac-the-installer-says-durweg-needs-python-39-or-newer)).

## 💬 Questions during installation

| Question | What to choose |
| :--- | :--- |
| **Language** | The language your agent will use; change it later with `durweg config language` |
| **Where to install** (Windows) | • Usually **Windows**<br>• **WSL** (Linux inside Windows) if you also want workflows that need Linux |
| **No WSL yet** | • Approve the administrator prompt and restart<br>• Open "Ubuntu" from the Start menu once to choose a Linux user name and password<br>• Double-click the installer again; it remembers your choices |
| **"Windows protected your PC"** | Click **More info → Run anyway** |
| **macOS blocked the installer** | • Open System Settings → Privacy & Security and allow it<br>• If macOS installs its developer tools first, double-click the file again when that has finished |
| **Claude Code or Codex** | • Asked only when no agent is found; press Enter for Claude Code, then log in to it once in your browser<br>• You already have an agent and start it your own way (for example with a script): choose **3**; nothing new is installed |
| **Asked on a second run whether to change Durweg** | • Enter: keep the last choices (update or repair)<br>• `c`: choose again and install Durweg anew |

## 🙏 Special thanks

Thanks to [moraywang95-svg](https://github.com/moraywang95-svg) and [Qizhe-Xu](https://github.com/Qizhe-Xu) for helping me shape the idea of Durweg, testing it and giving feedback while it was being made 😊

---

License: [MIT](LICENSE).
