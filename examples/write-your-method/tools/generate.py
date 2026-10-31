#!/usr/bin/env python3
"""Step 3 of write-your-method (action): build the user's workflow from the confirmed design.

  generate.py RUN

Reads RUN/steps/2-steps.json and writes RUN/generated/<name>/ (workflow.json and
skills/<name>/SKILL.md). Deterministic: the same design always gives the same files, so every
step and every user confirmation of the design is in the workflow exactly as confirmed.
Standard library only (it runs from the run's snapshot).
"""
import json
import shutil
import sys
from pathlib import Path


def build(run):
    design = json.loads((run / "steps/2-steps.json").read_text(encoding="utf-8"))
    name, title, steps = design["name"], design["title"], design["steps"]
    out = run / "generated" / name
    if out.exists():
        shutil.rmtree(out)
    (out / "skills" / name).mkdir(parents=True)
    wf_steps, skill = [], []
    for n, s in enumerate(steps, 1):
        result = f"steps/{n}-{s['id']}.md"
        gates = [{"type": "sections", "file": result, "headings": [{"title": "Result", "min_chars": 20}]}]
        if s.get("user"):
            gates.append({"type": "user"})
        wf_steps.append({"id": s["id"], "title": s["title"],
                         "instructions": f"skills/{name}/SKILL.md#{n}-{s['id']}",
                         "artifacts": [result], "gates": gates})
        skill += [f"## {n}. {s['id']}", "", f"**{s['title']}**", "",
                  f"Do: {s['do']}", "", f"Deliver: {s['deliver']}", "",
                  f"Write `{result}` with a `## Result` section that holds what this step delivered."]
        if s.get("user"):
            skill += ["", "The user decides here: write the result, `durweg propose`, show it to the user, "
                          "and `durweg confirm` with their own words when they agree."]
        skill.append("")
    workflow = {"id": name, "title": title, "skill": f"skills/{name}", "steps": wf_steps}
    (out / "workflow.json").write_text(json.dumps(workflow, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    head = ["---", f"name: {name}",
            f"description: {title} - the user's own method, run step by step with Durweg.", "---", "",
            f"# {title}", "",
            "Run it with durweg (skill run-workflow): `durweg start " + name + " <name-of-this-run>`, then for "
            "each step `durweg begin`, do the step, write its file, and `durweg done`. Talk to the user in "
            "the language set in ~/Durweg/config.json.", ""]
    (out / "skills" / name / "SKILL.md").write_text("\n".join(head + skill), encoding="utf-8")
    return out


def main(argv):
    if len(argv) != 1:
        sys.exit(__doc__)
    out = build(Path(argv[0]).resolve())
    print(f"generated {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
