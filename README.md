# Durweg

Durweg makes AI agents (Claude Code, Codex) work by your own method, the same way every time, so
their output is stable. A skill tells an agent how to work but not whether it did: it can skip a
step, decide for you, or leave no trace. Durweg runs your method step by step, stops the agent at
each step's checks, asks you where your method says so, and keeps a record you can check.

Status: first version, private (`musetee/durweg`). Design and reviews: the private log
`aiagents-dev` (`plans/20261031_workflow-platform.md`, `plans/20261031_durweg-setup-workflow.md`).

## Install on a new computer

The first workflow Durweg runs sets up the computer itself: herdr with Claude Code and Codex, ending
with one real handoff between them. It is for Linux or WSL with apt (Ubuntu); on Windows, use WSL.
Both repositories are private: your GitHub account needs access to `musetee/durweg` and
`musetee/aiagents`.

1. Open a terminal. On Windows: open PowerShell and run `wsl`.
2. Install Git and the GitHub CLI (sudo asks for your Linux password):
   ```bash
   sudo apt-get update && sudo apt-get install -y git gh
   ```
3. Log in to GitHub (a browser opens; this also lets git use the login):
   ```bash
   gh auth login --hostname github.com --git-protocol https --web && gh auth setup-git
   ```
4. Get Durweg and run its installer. It checks your access, installs Python, `durweg`, Claude Code and
   the setup workflow, and stops with a message if anything is missing:
   ```bash
   gh repo clone musetee/durweg ~/durweg && bash ~/durweg/install.sh
   ```
5. Open a **new** terminal, run `claude` (the first start asks you to log in), and paste the text
   the installer printed at the end. It starts the setup workflow.

The workflow then asks you three things on the way: which agents to install (Claude Code and Codex
by default), to log in to Codex, and to open herdr with both agents and continue there (it gives you
the exact text). Done looks like this: you see Claude send a test message to Codex and Codex answer
it, and `durweg check` prints `PASS`.

## Every day

Tell an agent which workflow to run: "Run the workflow `<folder>` with durweg." It starts a run with
`durweg start <folder> <name>`, goes step by step, and asks you where the workflow says so. To see where
a run stands: `durweg status <run folder>`.

## Where your files are

Each run is a folder: the setup workflow's is under `~/durweg-runs/`; other runs are under
`runs/` in the project folder you started them from. In a run folder, `steps/` holds what each step
wrote, `evidence/` what was saved as proof, `run.md` a readable summary (`durweg render <run>`), and
`.wf/` the event log and the locked copy of the workflow (do not edit it).

## Example: the mini workflow

This shows a whole run of the three-step example in [`examples/mini`](examples/mini): you pick a
topic, the agent lists points and checks them. It makes a run folder under `runs/`.

1. In a project folder, tell the agent: "Run the workflow `~/durweg/examples/mini` with durweg."
2. At step 1 it shows you two or three topics and asks; answer in your own words.
3. When it is finished it runs `durweg check runs/<date>_<name>` and reports `PASS` or what is missing.

## What you can do

- Write your own workflow: [docs/workflow-format.md](docs/workflow-format.md).
- See what an agent did, step by step: `durweg status <run>`, `durweg render <run>`.
- Check a finished run: `durweg check <run>`.

## Tests

`python3 -m unittest discover -s tests`
