---
name: mini
description: A minimal example workflow for Durweg - pick a topic with the user, list points, check them.
---

# mini

## 1. Topic
Write 2-3 topic options to `steps/1-topic.json` as `{"options": [...]}`. Propose, show them to the
user, and record the one they pick with `--set chosen=<option>`.

## 2. Points
Write `steps/2-points.md` with a `## Points` list (3-5 items) and a `## Sources` table with the columns
`point` and `source`.

## 3. Verify
Save what you looked at under `evidence/` and write `steps/3-verify.json`:
`{"topic": <the chosen topic>, "checked": [<every point>]}`.
