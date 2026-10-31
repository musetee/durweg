---
name: run-workflow
description: Run a user's workflow step by step with the wf tool - begin each step, write its files, pass its gates, let the user confirm where the workflow asks, never skip or merge steps. Use whenever a skill or the user says to run a workflow with wf, or a project has a runs/ directory with .wf/state.json.
---

# run-workflow: follow a workflow with `wf`

A workflow is a fixed way of working that the user wrote down. `wf` keeps the order, checks each
step's gates and records what happened, so the user can trust that every step was really done.
Work only through these commands; they print `ok run=<id> event=<n>` when they succeed.

## The loop, for every step

1. `wf begin <run> <step>` prints the step's instructions, its files and its gates. Do the work
   only after this: files written before `begin` count as a violation.
2. Write the step's files exactly where it says (`steps/…`, evidence folders).
3. If the step has a **user** gate:
   1. `wf propose <run> <step>` freezes what you will show.
   2. Show the user exactly that version and ask. Do not change it while waiting.
   3. When they answer: `wf confirm <run> <step> --quote "<their exact words>" --set key=value`
      for each decision their answer makes (for example `--set chosen=B`). Copy their words
      verbatim; never write a quote they did not say, never confirm for them.
   4. If they ask for changes instead: change the files, `wf propose` again, show the new
      version, and confirm when they agree with it.
4. `wf done <run> <step>`. If it refuses, read the reasons, fix the files, and run it again.
   Do not edit `.wf/` or a `*.decision.json` file by hand.

## Rules

- One step at a time, in order. `begin` refuses a step whose earlier steps are not done.
- To change a step that is already done (the user wants to change an earlier answer, or a new
  candidate has to go through an earlier step): `wf reopen <run> <step> --reason "<why>"`. The
  steps after it go back to pending and are done again; do not edit done files in place.
- When the user is away, stop at a user gate: say where you stopped (`wf status <run>`) and wait.
- At the end: `wf check <run>`, then `wf render <run>` for a readable `run.md`. Report what
  `check` printed, including refusals and notes, not only "done".
- Start a run with `wf start <workflow-folder> <slug> [--trial]`; always pass the run folder to the
  commands that change it.
