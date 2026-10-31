---
name: write-your-method
description: Durweg's first-run example - help the user write down one way they do a kind of work, turn it into steps, build a Durweg workflow from it, put it in their library, run it once, and write it up as a case page to keep or share. Use when the user starts Durweg for the first time or asks to turn their own method into a workflow.
---

# write-your-method: from "how I do it" to a workflow you can run

Run it with durweg (skill run-workflow): `durweg start write-your-method my-first-method`, then step
by step. Talk to the user in the language set in `~/Durweg/config.json` (`"language": "zh"` is
Chinese, `"en"` English); file names, step ids and commands stay in English. Ask one thing at a
time; the method is the user's: write down what they say, do not invent their method for them.

## 1. Describe
Ask the user which piece of work they want to do the same way every time (a weekly report, reviewing
a paper, preparing a lesson, ...), then how they do it, step by step, where it usually goes wrong,
and where they always want to decide themselves.

**File:** `steps/1-method.md` with these four headings (keep the English headings, write the
content in the user's language):
- `## Task`: one or two sentences;
- `## How I do it`: a list, at least two items, in their order;
- `## Where it goes wrong`: a list (may be empty);
- `## Where I decide`: a list (may be empty).

`durweg propose`, show it, and `durweg confirm` with the user's words when it is right.

## 2. Design
Turn the method into steps. Each step does one thing and delivers something the user can look at.
A step where the user decides gets `"user": true`. Do not add check scripts: the user's own look
is the check (Durweg's rule: write a script only when a mistake cannot be seen in the result, costs
a lot, and the work repeats often).

**File:** `steps/2-steps.json`:
`{"name": "<lower-case-name>", "title": "<the method's title>", "steps": [{"id": "<lower-case-id>",
"title": "...", "do": "...", "deliver": "...", "user": true|false}]}` with 2 to 12 steps. The name
becomes how the user runs it (`durweg start <name> ...`): short, lower-case letters, digits and -.

Show the user the steps as a numbered list (title, what it delivers, whether they decide there),
`durweg propose`, and confirm with their words.

## 3. Build
`python3 RUN/.wf/workflow/tools/generate.py RUN` (RUN is this run's folder) builds
`generated/<name>/` from the confirmed design: `workflow.json` and the skill. Do not edit the
generated files by hand; to change something, `durweg reopen RUN design`.

Show the user the mapping (step number, id, title, whether they decide there), `durweg propose`,
and confirm with their words.

## 4. Register
`python3 RUN/.wf/workflow/tools/register.py RUN` copies the workflow into `~/Durweg/workflows/<name>/`
and writes `steps/4-register.json`; then run the command it prints:
`durweg library add "<that folder>" --name <name>`. If the name is taken, choose another
(`durweg reopen RUN design`).

## 5. Try
Ask the user whether to run their new workflow once now. When they agree:
`durweg start <name> try-1` (in the same project folder), go through it with them step by step as
its skill says, and finish with `durweg check <that run>`.

**File:** `steps/5-try.json`: `{"run": "<the new run's folder>", "check": "PASS"}` (only after
check printed PASS). `durweg propose`, show the user both results, and confirm with their words.

## 6. Case
Ask the user whether they are happy with their new workflow and want this run written up as a
case: one web page they can keep, or send to others to share what they learned. It holds their
method, the steps, their own words at each confirmation and the first run's result, all taken
from this run's record.

- **No:** write `steps/6-case.json` as `{"made": false}`, `durweg propose`, and confirm with their
  words.
- **Yes:** ask what they would tell someone who wants to do the same (what worked, what to watch
  for) and write it, in their words, to `steps/6-lessons.md` under `## Lessons`. Then
  `python3 RUN/.wf/workflow/tools/make_case.py RUN` builds `case/<name>.html`, keeps a copy in
  `~/Durweg/cases/` and writes `steps/6-case.json`. Do not edit the page by hand; to change the
  lessons, edit `steps/6-lessons.md` and run make_case.py again. Tell the user where the copy is
  (they open it by double-clicking), `durweg propose`, and confirm with their words.

At the end: `durweg check RUN` for this run too, and tell the user how to use their workflow from
now on: "Run <name> with durweg."
