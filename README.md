# workflow-platform (temporary name)

For people who have a fixed way of doing a kind of work and want AI agents (Claude Code, Codex) to
follow it the same way every time. You write the workflow down once; `wf` makes the agent go
through it step by step, stops it at each step's checks, asks you where the workflow says so, and
keeps a record that can be checked afterwards.

Status: first version, local only, not released. Design and review:
`~/projects/aiagents-dev/plans/20261031_workflow-platform.md`.

## Install

Needs Python 3.10 or newer and git.

1. Open a terminal (on Windows: PowerShell, then `wsl`).
2. Link `wf` and the agent skill `run-workflow`:
   ```bash
   bash ~/projects/workflow-platform/tools/install.sh
   ```
3. Check it: `wf --help` prints the commands. Start a new agent session so it sees the skill.

## Example: the mini workflow

This shows a whole run of the three-step example in [`examples/mini`](examples/mini): you pick a
topic, the agent lists points and checks them. It makes a run folder under `runs/`.

1. In a project folder, tell the agent: "Run the workflow `~/projects/workflow-platform/examples/mini`
   with wf." It starts with `wf start ~/projects/workflow-platform/examples/mini demo`.
2. At step 1 it shows you two or three topics and asks; answer in your own words.
3. When it is finished it runs `wf check runs/<date>_demo` and reports `PASS` or what is missing.

Where your files are: `runs/<date>_<slug>/` holds the step files (`steps/`), the evidence the
steps saved, `run.md` (a readable summary made by `wf render`) and `.wf/` (the event log and the
locked copy of the workflow; do not edit it).

## What you can do

- Write your own workflow: [docs/workflow-format.md](docs/workflow-format.md).
- See what an agent did, step by step: `wf status <run>`, `wf render <run>`.
- Check a finished run: `wf check <run>`; compare it with the agent's session log:
  `wf audit <run> --transcript <session files>` ([docs/workflow-format.md#check-and-audit](docs/workflow-format.md#check-and-audit)).

## Tests

`python3 -m unittest discover -s tests`
