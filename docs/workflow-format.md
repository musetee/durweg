[← README](../README.md)

# Writing a workflow

A workflow is a git repository with `workflow.json` at its root and a skill folder that says how
each step is done. `wf start` refuses a workflow whose files are not committed (use `--dev` while
writing one; such runs are marked and cannot be used for acceptance). Complete example:
[`examples/mini`](../examples/mini). Schema: [`schema/workflow.schema.json`](../schema/workflow.schema.json).

## workflow.json

| Field | Meaning |
|---|---|
| `id`, `title` | name of the workflow |
| `skill` | the skill folder; copied whole into each run, so a later edit does not change a running run |
| `snapshot` | extra files to copy, e.g. gate scripts (`tools/check.py`) and modules they import |
| `steps[].id` | lower-case id, used in commands (`wf begin <run> <id>`) |
| `steps[].instructions` | `path#anchor` of the step's section in the skill; `wf begin` prints it |
| `steps[].needs` | steps that must be done first; default: the previous step |
| `steps[].artifacts` | globs of **every** file the step writes or its gates read; changing any of them after `done` fails `wf check` |
| `steps[].gates` | conditions checked by `wf done` and again by `wf check` |

## Gates

| Type | Parameters | Passes when |
|---|---|---|
| `json` | `file`, `schema` (type, required, properties, items, minItems, maxItems, minLength, enum, uniqueItems) | • the file is valid JSON and fits the schema<br>• no string is empty or a placeholder (`TODO`, `TBD`, `…`, `-`, `?`) |
| `sections` | `file`, `headings: [{title, min_items, max_items, min_chars}]` | • each heading (`#` style, exact text) appears once, outside code blocks<br>• its list has the right number of non-empty items |
| `table` | `file`, `under`, `columns`, `min_rows`, `max_rows`, `unique` | the first table under the heading has exactly these columns, enough rows, no empty cells, no duplicates in `unique` columns |
| `files` | `glob`, `min_count` | enough matching files, none empty |
| `command` | `argv` (list, no shell; `{run}`, `{wf}`, `{step}` are replaced), `timeout` (default 60 s) | • the script, run from the run's snapshot (`{wf}/…`) in the run folder, exits 0<br>• it gets `WF_RUN`, `WF_SNAPSHOT`, `WF_STATE`, `WF_STEP`; output goes to `.wf/gates/` |
| `user` | — | • the user confirmed the proposal of this round (`wf propose` → `wf confirm`)<br>• the proposal has not changed since; the decision file holds the `--set` values |

Gate scripts check saved evidence only; they must not go online. Decisions from the user's answer
are in `steps/<n>-<id>.decision.json` as `{"confirm_event": n, "values": {...}}`.

## Check and audit

- `wf check <run>`: replays the event log and re-checks every gate and file digest. `PASS` or `FAIL`.
  It cannot tell a log that was rebuilt by hand around valid files; that is what audit is for.
- `wf audit <run> --transcript <files>`: compares the log with the agent's own session files
  (Claude Code: `~/.claude/projects/<project>/<session>.jsonl`; Codex:
  `~/.codex/sessions/…/rollout-*.jsonl`). Pass every session of the run, resumed ones too.
  - `PASS` (exit 0): nothing left to check.
  - `VIOLATION` (exit 1): a step's file written outside its step, a quote the user never said, an
    event with no successful `wf` call, a proposal changed after the user answered, `.wf/` edited.
  - `INSUFFICIENT` (exit 2): a person has to look. Each gap has an id; write what you checked
    under `## G-xxxxxxxx` in `<run>/audit-notes.md`, and audit reports it as cleared. Every
    confirmation is such a gap: a person checks what the user was shown and what the answer meant.
