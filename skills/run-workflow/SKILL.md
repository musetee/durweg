---
name: run-workflow
description: Run a user's workflow step by step with the durweg tool - begin each step, write its files, pass its gates, let the user confirm where the workflow asks, never skip or merge steps. Use whenever a skill or the user says to run a workflow with durweg, or a project has a runs/ directory with .wf/state.json.
---

# run-workflow: follow a workflow with `durweg`

A workflow is a fixed way of working that the user wrote down. `durweg` keeps the order, checks each
step's gates and records what happened, so the user can trust that every step was really done.
Work only through these commands; they print `ok run=<id> event=<n>` when they succeed.
Before the first run, `durweg config` shows the language to talk to the user in (`zh` Chinese,
`en` English). If it says `not set yet`, ask the user once, in the language they are writing in,
whether they want Chinese or English, then `durweg config language zh|en`. Commands, file names and
step ids stay as they are.

Start a run with `durweg start <name or folder> <name-of-this-run>`: a name from the library
(`durweg library list`), or a folder (`./folder`); the run goes into `./runs/`.
When the user asks what workflows exist or wants one they do not have yet: `durweg library available`
lists what the catalogs offer; `durweg library add <name>` (or `<catalog>:<name>` when it says so)
installs it. If a command says it has no access, tell the user that sentence; do not log in for them.

## The loop, for every step

1. `durweg begin <run> <step>` prints the step's instructions, its files and its gates. Do the work
   only after this: files written before `begin` count as a violation.
2. Write the step's files exactly where it says (`steps/…`, evidence folders).
3. If the step has a **user** gate:
   1. `durweg propose <run> <step>` freezes what you will show.
   2. Show the user exactly that version and ask. Do not change it while waiting.
   3. When they answer: `durweg confirm <run> <step> --quote "<their exact words>" --set key=value`
      for each decision their answer makes (for example `--set chosen=B`). Copy their words
      verbatim; never write a quote they did not say, never confirm for them.
   4. If they ask for changes instead: change the files, `durweg propose` again, show the new
      version, and confirm when they agree with it.
4. `durweg done <run> <step>`. If it refuses, read the reasons, fix the files, and run it again.
   Do not edit `.wf/` or a `*.decision.json` file by hand.

## Rules

- One step at a time, in order. `begin` refuses a step whose earlier steps are not done.
- To change a step that is already done (the user wants to change an earlier answer, or a new
  candidate has to go through an earlier step): `durweg reopen <run> <step> --reason "<why>"`. Reopen
  already starts that step again: do not `begin` it. The steps after it go back to pending and are
  done again with `begin`; do not edit done files in place.
- When a command is refused, stop and fix that first: do not run the next command of a batch as if
  it had worked (put dependent commands on one line joined with `&&`).
- When the user is away, stop at a user gate: say where you stopped (`durweg status <run>`) and wait.
- At the end: `durweg check <run>`, then `durweg render <run>` for a readable `run.md`. Report what
  `check` printed, including refusals and notes, not only "done".
- Call `durweg` plainly (one command per line or joined with `&&`): no comments, `$( )`, loops or
  background `&` around it, or the audit cannot count the call.
- Always pass the run folder to the commands that change it.

## Publishing

When the user wants to share one of their own workflows (`durweg publish`), it goes in two steps,
and only the user decides:

1. `durweg publish <name>` shows the files, the GitHub repository and what happens with a catalog,
   and lists what is still to answer. It publishes nothing.
2. Ask the user each open question (public or private; the license if the folder has none; whether
   to propose it to the public catalog, or to make or use their private catalog; a case page from
   `~/Durweg/cases/` only if they name one). Run `durweg publish <name>` again with their answers
   (`--public`/`--private`, `--license`, `--catalog yes|no`, `--case`) and show the user the list.
3. Only after the user says yes to that list: the same command with `--yes`. Tell them the lines it
   prints. If it says `gh` is missing or not logged in, tell them that sentence; do not log in for them.
