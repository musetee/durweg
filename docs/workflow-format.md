[← README](../README.md) · [中文](workflow-format_cn.md)

# Writing a workflow

A workflow is a folder with `workflow.json` and a skill folder that says how each step is done.
It does not have to be a git repository. When it is inside one, `durweg start` records the commit and
refuses files that are not committed (use `--dev` while writing one; such runs are marked and cannot
be used for acceptance). Either way the run keeps a locked copy of the workflow. Complete example:
[`examples/mini`](../examples/mini). Schema: [`schema/workflow.schema.json`](../schema/workflow.schema.json).

## workflow.json

| Field | Meaning |
|---|---|
| `id`, `title` | name of the workflow |
| `platforms` | optional: `linux`, `macos`, `windows` (WSL counts as linux); default all three. `durweg start` refuses an unsupported system before it creates anything (exit 3) |
| `skill` | the skill folder; copied whole into each run, so a later edit does not change a running run |
| `snapshot` | extra files to copy, e.g. gate scripts (`tools/check.py`) and modules they import |
| `steps[].id` | lower-case id, used in commands (`durweg begin <run> <id>`) |
| `steps[].instructions` | `path#anchor` of the step's section in the skill; `durweg begin` prints it |
| `steps[].needs` | steps that must be done first; default: the previous step |
| `steps[].artifacts` | globs of **every** file the step writes or its gates read; changing any of them after `done` fails `durweg check` |
| `steps[].gates` | conditions checked by `durweg done` and again by `durweg check` |

## Gates

| Type | Parameters | Passes when |
|---|---|---|
| `json` | `file`, `schema` (type, required, properties, items, minItems, maxItems, minLength, enum, uniqueItems) | • the file is valid JSON and fits the schema<br>• no string is empty or a placeholder (`TODO`, `TBD`, `…`, `-`, `?`) |
| `sections` | `file`, `headings: [{title, min_items, max_items, min_chars}]` | • each heading (`#` style, exact text) appears once, outside code blocks<br>• its list has the right number of non-empty items |
| `table` | `file`, `under`, `columns`, `min_rows`, `max_rows`, `unique` | the first table under the heading has exactly these columns, enough rows, no empty cells, no duplicates in `unique` columns |
| `files` | `glob`, `min_count` | enough matching files, none empty |
| `command` | `argv` (list, no shell; `{run}`, `{wf}`, `{step}` are replaced), `timeout` (default 60 s) | • the script, run from the run's snapshot (`{wf}/…`) in the run folder, exits 0<br>• it gets `WF_RUN`, `WF_SNAPSHOT`, `WF_STATE`, `WF_STEP`; output goes to `.wf/gates/` |
| `user` | — | • the user confirmed the proposal of this round (`durweg propose` → `durweg confirm`)<br>• the proposal has not changed since; the decision file holds the `--set` values |

Gate scripts check saved evidence only; they must not go online. Decisions from the user's answer
are in `steps/<n>-<id>.decision.json` as `{"confirm_event": n, "values": {...}}`.

## Check

`durweg check <run>` replays the run's event log and re-checks every gate and every file digest
against the copy of the workflow locked at `durweg start`: `PASS` or `FAIL`. It reads only the run
folder, so it still works after the workflow was changed or moved. It cannot tell a log that was
rebuilt by hand around valid files; comparing a run with the agent's own session files is the
optional plugin [durweg-audit](https://github.com/musetee/durweg-audit).

## When to write a gate script

Most steps need no script: the user looks at the result (`user` gate), and `json`, `sections`,
`table` and `files` check that the result is there and complete. Write a `command` script only when
all three are true: a mistake cannot be seen in the result (for example whether something was really
looked up), the mistake costs a lot, and the workflow runs again and again. Scripts get
`WF_RUN`, `WF_SNAPSHOT`, `WF_STATE`, `WF_STEP` and `DURWEG_PLATFORM` (to call the platform's own checks).

## Library

`durweg library add <what> [--name name]` registers a workflow under a name. `<what>` is read in
this order:

1. a git address (`https://…`, `git@…`, `ssh://…`, `….git`): cloned into `~/Durweg/workflows/`;
2. `<catalog>:<name>` (for example `public:human-readme`): that workflow from that catalog, cloned;
3. anything that looks like a path (`./x`, `/x`, `~/x`, `C:\x`, anything with a slash): that folder,
   which stays where it is;
4. a single word: a folder of that name in the current folder, or a workflow of that name in a
   catalog. If both exist, nothing is added and it tells you to write `./<word>` or
   `<catalog>:<word>`; if several catalogs have the name, it asks for `<catalog>:<word>`.

Then `durweg start <name> <name-of-this-run>`; `start` only ever looks in the library, never in a
catalog. `durweg library list` shows names, systems and whether the folder still exists;
`durweg library available` shows what the catalogs offer; `durweg runs` lists the runs started on
this computer (`--rebuild <folder>` scans a folder if the index was lost).

## Catalogs

A catalog is a git repository with one file, `catalog.json`, that lists workflows other people can
install by name:

```json
{"format": 1, "workflows": {
  "human-readme": {"title": "A README for people", "summary": "one line on what it is for",
                   "url": "https://github.com/<owner>/durweg-human-readme.git"}}}
```

Names use lower-case letters, digits and `-`; entries without a `url` are skipped. The public
catalog (`public`) is always known; `durweg catalog remove public` switches it off and
`durweg catalog add public` switches it on again. Another catalog, such as your own private one:
`durweg catalog add <name> <git address>` (the name has at least 2 characters), `durweg catalog list`,
`durweg catalog remove <name>` (workflows installed from it stay in the library). Durweg keeps a copy
of each catalog in `~/Durweg/catalogs/`; when it cannot download a catalog it shows that copy and
says from when it is.

git is only ever run with the credentials already on the computer and never asks for a password:
a private GitHub repository needs `gh auth login` and `gh auth setup-git` once.

