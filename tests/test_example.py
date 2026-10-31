"""The first-run example write-your-method (plan 2.7, V1-R-005), driven through the CLI."""

import json
import os
import shutil
import subprocess
import sys
import unittest
from pathlib import Path

from helpers import ROOT, WfCase

EXAMPLE = ROOT / "examples" / "write-your-method"

METHOD = """## Task
Write the weekly status report for my team.

## How I do it
- collect what each person finished
- write the summary and the risks
- send it after I read it once more

## Where it goes wrong
- I forget the risks

## Where I decide
- whether it is ready to send
"""

DESIGN = {"name": "weekly-report", "title": "Weekly status report", "steps": [
    {"id": "collect", "title": "Collect the work", "do": "Ask each person", "deliver": "a list", "user": False},
    {"id": "write", "title": "Write it", "do": "Summary and risks", "deliver": "the draft", "user": False},
    {"id": "approve", "title": "Approve and send", "do": "I read it", "deliver": "sent report", "user": True}]}


class Example(WfCase):
    def setUp(self):
        super().setUp()
        self.src = self.tmp / "write-your-method"
        shutil.copytree(EXAMPLE, self.src)                  # a plain folder: no git needed

    def tool(self, name, run):
        r = subprocess.run([sys.executable, str(run / ".wf/workflow/tools" / name), str(run)],
                           capture_output=True, text=True, env=os.environ.copy())
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        return r.stdout

    def user_step(self, run, step, write, quote="yes"):
        self.wf("begin", run, step)
        write()
        self.wf("propose", run, step)
        self.wf("confirm", run, step, "--quote", quote)

    def through_build(self):
        self.wf("start", self.src, "first", "--runs", self.runs)
        run = self.run = next(self.runs.glob("*_first"))
        self.user_step(run, "describe", lambda: self.put("steps/1-method.md", METHOD))
        self.wf("done", run, "describe")
        self.user_step(run, "design", lambda: self.put("steps/2-steps.json", DESIGN))
        self.wf("done", run, "design")
        self.wf("begin", run, "build")
        self.tool("generate.py", run)
        return run

    def build_done(self, run, expect=0):
        self.wf("propose", run, "build")
        self.wf("confirm", run, "build", "--quote", "looks right")
        return self.wf("done", run, "build", expect=expect)

    def test_whole_example_and_the_new_workflow(self):
        run = self.through_build()
        self.build_done(run)
        self.wf("begin", run, "register")
        out = self.tool("register.py", run)
        lib_path = Path(os.environ["DURWEG_HOME"]) / "workflows" / "weekly-report"
        self.assertIn(str(lib_path), out)
        self.wf("library", "add", lib_path, "--name", "weekly-report")
        self.wf("done", run, "register")
        # try: run the generated workflow once
        self.wf("begin", run, "try")
        self.wf("start", "weekly-report", "try-1", "--runs", self.runs)
        new = next(self.runs.glob("*_try-1"))
        for n, s in enumerate(DESIGN["steps"], 1):
            self.wf("begin", new, s["id"])
            p = new / f"steps/{n}-{s['id']}.md"
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(f"## Result\nThe {s['title'].lower()} step is finished and written down here.\n",
                         encoding="utf-8")
            if s["user"]:
                self.wf("propose", new, s["id"])
                self.wf("confirm", new, s["id"], "--quote", "send it")
            self.wf("done", new, s["id"])
        self.assertIn("PASS", self.wf("check", new))
        self.put("steps/5-try.json", {"run": str(new), "check": "PASS"})
        self.wf("propose", run, "try")
        self.wf("confirm", run, "try", "--quote", "it worked")
        self.wf("done", run, "try")
        # case: one page from the run's own record, a copy in ~/Durweg/cases
        self.wf("begin", run, "case")
        self.put("steps/6-lessons.md", "## Lessons\nWrite the risks <first> & keep it short.\n")
        out = self.tool("make_case.py", run)
        page = (run / "case/weekly-report.html").read_text(encoding="utf-8")
        for words in ("looks right", "it worked", "send it", "Collect the work",
                      "Write the risks &lt;first&gt; &amp; keep it short."):
            self.assertIn(words, page)
        self.assertNotIn(str(self.tmp), page)               # no paths of this computer
        copy = Path(os.environ["DURWEG_HOME"]) / "cases" / f"weekly-report_{run.name}.html"
        self.assertIn(str(copy), out)
        self.assertEqual(copy.read_text(encoding="utf-8"), page)
        self.wf("propose", run, "case")
        self.wf("confirm", run, "case", "--quote", "keep it")
        self.wf("done", run, "case")
        self.assertIn("PASS", self.wf("check", run))
        copy.unlink()                                       # the user moved the copy away
        self.wf("reopen", new, "approve", "--reason", "later change in the try run")
        self.assertIn("PASS", self.wf("check", run))
        # later changes in the library do not change the example's own history
        (lib_path / "workflow.json").write_text("{}", encoding="utf-8")
        self.assertIn("PASS", self.wf("check", run))

    def through_try(self):
        run = self.through_build()
        self.build_done(run)
        self.wf("begin", run, "register")
        self.tool("register.py", run)
        self.wf("done", run, "register")
        self.wf("begin", run, "try")
        self.put("steps/5-try.json", {"run": str(run), "check": "PASS"})
        self.wf("propose", run, "try")
        self.wf("confirm", run, "try", "--quote", "fine")
        self.wf("done", run, "try")
        self.wf("begin", run, "case")
        return run

    def test_no_case_is_fine(self):
        run = self.through_try()
        self.put("steps/6-case.json", {"made": False})
        self.wf("propose", run, "case")
        self.wf("confirm", run, "case", "--quote", "no thanks")
        self.wf("done", run, "case")
        self.assertIn("PASS", self.wf("check", run))

    def test_case_edited_by_hand_fails(self):
        run = self.through_try()
        self.put("steps/6-lessons.md", "## Lessons\nIt helped.\n")
        self.tool("make_case.py", run)
        p = run / "case/weekly-report.html"
        p.write_text(p.read_text(encoding="utf-8").replace("fine", "brilliant"), encoding="utf-8")
        rec = json.loads((run / "steps/6-case.json").read_text(encoding="utf-8"))
        rec["sha256"] = __import__("hashlib").sha256(p.read_bytes()).hexdigest()
        self.put("steps/6-case.json", rec)
        self.wf("propose", run, "case")
        self.wf("confirm", run, "case", "--quote", "ok")
        self.assertIn("edited by hand", self.wf("done", run, "case", expect=1))

    def edit_generated(self, run, fn):
        p = run / "generated/weekly-report/workflow.json"
        w = json.loads(p.read_text(encoding="utf-8"))
        fn(w)
        p.write_text(json.dumps(w), encoding="utf-8")

    def test_missing_user_gate_fails(self):
        run = self.through_build()
        self.edit_generated(run, lambda w: w["steps"][2].__setitem__("gates", w["steps"][2]["gates"][:1]))
        self.assertIn("user confirmation is missing", self.build_done(run, expect=1))

    def test_missing_step_fails(self):
        run = self.through_build()
        self.edit_generated(run, lambda w: w["steps"].pop(1))
        self.assertIn("differ from the confirmed design", self.build_done(run, expect=1))

    def test_missing_instruction_fails(self):
        run = self.through_build()
        skill = run / "generated/weekly-report/skills/weekly-report/SKILL.md"
        skill.write_text(skill.read_text(encoding="utf-8").replace("## 2. write", "## 2. other"), encoding="utf-8")
        self.assertIn("not found", self.build_done(run, expect=1))

    def test_bad_design_name_fails(self):
        self.wf("start", self.src, "bad", "--runs", self.runs)
        run = self.run = next(self.runs.glob("*_bad"))
        self.user_step(run, "describe", lambda: self.put("steps/1-method.md", METHOD))
        self.wf("done", run, "describe")
        self.user_step(run, "design", lambda: self.put("steps/2-steps.json", dict(DESIGN, name="Weekly Report")))
        self.assertIn("lower-case", self.wf("done", run, "design", expect=1))

    def test_chinese_method(self):
        run = self.through_build()
        self.build_done(run)
        d = dict(DESIGN, title="每周汇报", steps=[dict(s, title=f"第{i}步") for i, s in enumerate(DESIGN["steps"], 1)])
        self.wf("reopen", run, "design", "--reason", "中文标题")
        self.put("steps/2-steps.json", d)
        self.wf("propose", run, "design")
        self.wf("confirm", run, "design", "--quote", "好")
        self.wf("done", run, "design")
        self.wf("begin", run, "build")
        self.tool("generate.py", run)
        self.build_done(run)


if __name__ == "__main__":
    unittest.main()
