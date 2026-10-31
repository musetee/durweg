"""wf commands, state machine, gates and check (design 7.2)."""

import json
import os
import socket
import subprocess
import sys
import unittest
from pathlib import Path

from helpers import WfCase, git


class GoodRun(WfCase):
    def test_full_run_passes_check(self):
        self.start()
        self.full()
        rc, out = self.check()
        self.assertEqual(rc, 0, out)
        self.assertIn("PASS", out)

    def test_render_marks_trial(self):
        self.start("t", "--trial")
        self.full()
        self.wf("render", self.run)
        text = (self.run / "run.md").read_text()
        self.assertIn("Trial run", text)
        self.assertIn("dogs please", text)
        self.assertEqual(self.check()[0], 0)

    def test_decision_file_written_by_confirm(self):
        self.start()
        self.step_topic()
        dec = json.loads((self.run / "steps/1-topic.decision.json").read_text())
        self.assertEqual(dec["values"], {"chosen": "dogs"})


class StartRules(WfCase):
    def test_dirty_workflow_refused(self):
        (self.repo / "skills/mini/SKILL.md").write_text("changed\n")
        out = self.wf("start", self.repo, "x", "--runs", self.runs, expect=1)
        self.assertIn("not committed and clean", out)

    def test_untracked_snapshot_file_refused(self):
        (self.repo / "skills/mini/extra.md").write_text("new\n")
        self.wf("start", self.repo, "x", "--runs", self.runs, expect=1)

    def test_dev_run_is_marked(self):
        (self.repo / "skills/mini/SKILL.md").write_text("changed\n")
        self.wf("start", self.repo, "x", "--runs", self.runs, "--dev")
        self.run = next(self.runs.glob("*_x"))
        self.assertTrue(self.events()[0]["workflow"]["dev"])

    def test_same_slug_same_day_refused(self):
        self.start()
        out = self.wf("start", self.repo, "demo", "--runs", self.runs, expect=1)
        self.assertIn("demo-2", out)

    def test_command_script_must_be_in_snapshot(self):
        wfj = json.loads((self.repo / "workflow.json").read_text())
        wfj["snapshot"] = []
        (self.repo / "workflow.json").write_text(json.dumps(wfj))
        git(self.repo, "commit", "-qam", "drop snapshot")
        out = self.wf("start", self.repo, "x", "--runs", self.runs, expect=1)
        self.assertIn("not in the snapshot", out)


class Order(WfCase):
    def test_skip_a_step_refused(self):
        self.start()
        out = self.wf("begin", self.run, "points", expect=1)
        self.assertIn("needs topic", out)

    def test_two_active_refused(self):
        self.start()
        self.wf("begin", self.run, "topic")
        self.wf("begin", self.run, "points", expect=1)

    def test_begin_done_step_refused_use_reopen(self):
        self.start()
        self.full()
        out = self.wf("begin", self.run, "topic", expect=1)
        self.assertIn("reopen", out)
        self.assertEqual(self.check()[0], 0, "a normal finished run still passes")

    def test_done_without_begin_refused(self):
        self.start()
        self.wf("done", self.run, "topic", expect=1)

    def test_refusals_are_logged(self):
        self.start()
        self.wf("begin", self.run, "points", expect=1)
        self.assertEqual(self.events()[-1]["type"], "refused")


class Confirmation(WfCase):
    def test_confirm_without_propose_refused(self):
        self.start()
        self.wf("begin", self.run, "topic")
        self.put("steps/1-topic.json", {"options": ["a", "b"]})
        self.wf("confirm", self.run, "topic", "--quote", "ok", expect=1)

    def test_change_after_propose_refuses_confirm(self):
        self.start()
        self.wf("begin", self.run, "topic")
        self.put("steps/1-topic.json", {"options": ["a", "b"]})
        self.wf("propose", self.run, "topic")
        self.put("steps/1-topic.json", {"options": ["a", "c"]})
        out = self.wf("confirm", self.run, "topic", "--quote", "ok", expect=1)
        self.assertIn("proposal changed", out)

    def test_change_after_confirm_refuses_done(self):
        self.start()
        self.wf("begin", self.run, "topic")
        self.put("steps/1-topic.json", {"options": ["a", "b"]})
        self.wf("propose", self.run, "topic")
        self.wf("confirm", self.run, "topic", "--quote", "ok", "--set", "chosen=a")
        self.put("steps/1-topic.json", {"options": ["a", "z"]})
        out = self.wf("done", self.run, "topic", expect=1)
        self.assertIn("proposal changed", out)

    def test_repropose_after_confirm_needs_new_confirm(self):
        self.start()
        self.wf("begin", self.run, "topic")
        self.put("steps/1-topic.json", {"options": ["a", "b"]})
        self.wf("propose", self.run, "topic")
        self.wf("confirm", self.run, "topic", "--quote", "ok", "--set", "chosen=a")
        self.put("steps/1-topic.json", {"options": ["a", "c"]})
        self.wf("propose", self.run, "topic")
        self.wf("done", self.run, "topic", expect=1)
        self.wf("confirm", self.run, "topic", "--quote", "yes c", "--set", "chosen=c")
        self.wf("done", self.run, "topic")

    def test_user_correction_path(self):
        """User corrects the proposal: edit, propose again, show, confirm (design 3.1)."""
        self.start()
        self.wf("begin", self.run, "topic")
        self.put("steps/1-topic.json", {"options": ["a", "b"]})
        self.wf("propose", self.run, "topic")
        self.put("steps/1-topic.json", {"options": ["a", "b", "own"]})
        self.wf("propose", self.run, "topic")
        self.wf("confirm", self.run, "topic", "--quote", "right", "--set", "chosen=own")
        self.wf("done", self.run, "topic")

    def test_bad_set_refused(self):
        self.start()
        self.wf("begin", self.run, "topic")
        self.put("steps/1-topic.json", {"options": ["a", "b"]})
        self.wf("propose", self.run, "topic")
        self.wf("confirm", self.run, "topic", "--quote", "ok", "--set", "no-equals", expect=1)

    def test_propose_on_step_without_user_gate_refused(self):
        self.start()
        self.step_topic()
        self.wf("begin", self.run, "points")
        self.put("steps/2-points.md", self.POINTS)
        self.wf("propose", self.run, "points", expect=1)


class Gates(WfCase):
    def setUp(self):
        super().setUp()
        self.start()

    def topic_with(self, doc):
        self.wf("begin", self.run, "topic")
        self.put("steps/1-topic.json", doc)
        self.wf("propose", self.run, "topic")
        self.wf("confirm", self.run, "topic", "--quote", "ok", "--set", "chosen=a")
        return self.wf("done", self.run, "topic", expect=None)

    def test_json_too_few(self):
        self.assertIn("fewer than 2", self.topic_with({"options": ["a"]}))

    def test_json_too_many(self):
        self.assertIn("more than 3", self.topic_with({"options": ["a", "b", "c", "d"]}))

    def test_json_placeholder(self):
        self.assertIn("placeholder", self.topic_with({"options": ["a", "TODO"]}))

    def test_json_duplicates(self):
        self.assertIn("not unique", self.topic_with({"options": ["a", "a"]}))

    def test_json_missing_key(self):
        self.assertIn("missing 'options'", self.topic_with({"opts": ["a", "b"]}))

    def points_with(self, text):
        self.step_topic()
        self.wf("begin", self.run, "points")
        self.put("steps/2-points.md", text)
        return self.wf("done", self.run, "points", expect=None)

    def test_sections_count(self):
        out = self.points_with(self.POINTS.replace("- fluffy\n", ""))
        self.assertIn("need at least 3", out)

    def test_sections_empty_item(self):
        out = self.points_with(self.POINTS.replace("- fluffy", "- TBD"))
        self.assertIn("placeholder item", out)

    def test_sections_duplicate_heading(self):
        out = self.points_with(self.POINTS + "\n## Points\n- x\n")
        self.assertIn("appears 2 times", out)

    def test_sections_in_code_block_do_not_count(self):
        text = "```\n## Points\n- a\n- b\n- c\n```\n## Sources\n| point | source |\n|---|---|\n| a | b |\n"
        self.assertIn("no heading 'Points'", self.points_with(text))

    def test_table_missing(self):
        out = self.points_with("## Points\n- a\n- b\n- c\n\n## Sources\nnone\n")
        self.assertIn("no table", out)

    def test_table_wrong_columns(self):
        out = self.points_with(self.POINTS.replace("| point | source |", "| point | where |"))
        self.assertIn("columns", out)

    def test_table_empty_cell(self):
        out = self.points_with(self.POINTS.replace("| loyal | book |", "| loyal | - |"))
        self.assertIn("empty or placeholder cell", out)

    def test_files_empty(self):
        self.step_topic()
        self.step_points()
        self.wf("begin", self.run, "verify")
        self.put("evidence/a.txt", "")
        self.put("steps/3-verify.json", {"topic": "dogs", "checked": ["loyal", "loud", "fluffy"]})
        self.assertIn("empty", self.wf("done", self.run, "verify", expect=1))

    def test_command_fails(self):
        self.step_topic()
        self.step_points()
        self.wf("begin", self.run, "verify")
        self.put("evidence/a.txt", "x\n")
        self.put("steps/3-verify.json", {"topic": "cats", "checked": ["loyal", "loud", "fluffy"]})
        out = self.wf("done", self.run, "verify", expect=1)
        self.assertIn("the user chose 'dogs'", out)


class AfterDone(WfCase):
    def test_artifact_changed_after_done(self):
        self.start()
        self.full()
        (self.run / "steps/2-points.md").write_text(self.POINTS + "- extra\n")
        rc, out = self.check()
        self.assertEqual(rc, 1)
        self.assertIn("artifacts changed after done", out)

    def test_evidence_replaced_after_done(self):
        self.start()
        self.full()
        (self.run / "evidence/a.txt").write_text("another, still valid\n")
        self.assertEqual(self.check()[0], 1)

    def test_evidence_added_after_done(self):
        self.start()
        self.full()
        (self.run / "evidence/b.txt").write_text("new\n")
        self.assertEqual(self.check()[0], 1)

    def test_decision_file_edited(self):
        self.start()
        self.full()
        p = self.run / "steps/1-topic.decision.json"
        d = json.loads(p.read_text())
        d["values"]["chosen"] = "cats"
        p.write_text(json.dumps(d))
        rc, out = self.check()
        self.assertEqual(rc, 1)
        self.assertIn("decision", out)

    def test_snapshot_changed(self):
        self.start()
        self.full()
        (self.run / ".wf/workflow/tools/verify_points.py").write_text("import sys; sys.exit(0)\n")
        rc, out = self.check()
        self.assertEqual(rc, 1)
        self.assertIn("snapshot", out)

    def test_snapshot_changed_mid_run_blocks_commands(self):
        self.start()
        (self.run / ".wf/workflow/workflow.json").write_text("{}")
        self.wf("begin", self.run, "topic", expect=1)

    def test_repo_update_does_not_reach_run(self):
        self.start()
        (self.repo / "skills/mini/SKILL.md").write_text("# mini\n\n## 1. Topic\nNEW TEXT\n")
        git(self.repo, "commit", "-qam", "update skill")
        out = self.wf("begin", self.run, "topic")
        self.assertNotIn("NEW TEXT", out)
        self.assertIn("2-3 topic options", out)

    def test_incomplete_run_fails_check(self):
        self.start()
        self.step_topic()
        rc, out = self.check()
        self.assertEqual(rc, 1)
        self.assertIn("step points is pending", out)


class Reopen(WfCase):
    def test_reopen_ancestor_of_active(self):
        self.start()
        self.step_topic()
        self.wf("begin", self.run, "points")
        out = self.wf("reopen", self.run, "topic", "--reason", "user changes topic")
        self.assertIn("back to pending: points", out)
        # the old confirmation is void: done needs a new propose + confirm
        self.wf("done", self.run, "topic", expect=1)
        self.put("steps/1-topic.json", {"options": ["dogs", "birds"]})
        self.wf("propose", self.run, "topic")
        self.wf("confirm", self.run, "topic", "--quote", "dogs", "--set", "chosen=dogs")
        self.wf("done", self.run, "topic")
        self.step_points()
        self.step_verify()
        self.assertEqual(self.check()[0], 0)

    def test_reopen_middle_resets_downstream_only(self):
        self.start()
        self.full()
        self.wf("reopen", self.run, "points", "--reason", "new point")
        st = self.wf("status", self.run)
        self.assertIn("[x] 1 topic", st)
        self.assertIn("[>] 2 points", st)
        self.assertIn("[ ] 3 verify", st)

    def test_reopen_needs_done(self):
        self.start()
        self.wf("reopen", self.run, "topic", "--reason", "x", expect=1)

    def test_reopen_unrelated_while_active_refused(self):
        wfj = json.loads((self.repo / "workflow.json").read_text())
        wfj["steps"][2]["needs"] = ["topic"]          # verify does not need points
        (self.repo / "workflow.json").write_text(json.dumps(wfj))
        git(self.repo, "commit", "-qam", "dag")
        self.start()
        self.step_topic()
        self.step_points()
        self.wf("begin", self.run, "verify")
        out = self.wf("reopen", self.run, "points", "--reason", "x", expect=1)
        self.assertIn("does not depend", out)

    def test_old_round_confirm_not_reused(self):
        self.start()
        self.step_topic()
        self.wf("reopen", self.run, "topic", "--reason", "again")
        # same file, same digest as before - still needs a propose in this round
        self.wf("confirm", self.run, "topic", "--quote", "dogs please", expect=1)


class LogIntegrity(WfCase):
    def test_hand_inserted_event_is_a_violation(self):
        self.start()
        self.step_topic()
        ev = self.events()
        ev.append({"n": len(ev) + 1, "t": ev[-1]["t"], "type": "done", "step": "verify"})
        self.set_events(ev)
        rc, out = self.check()
        self.assertEqual(rc, 1)
        self.assertIn("not active", out)

    def test_forged_history_passes_check_but_not_audit(self):
        """Design 3.3: check cannot see a log rebuilt around valid artifacts; audit must."""
        self.start()
        self.full()
        good = self.events()
        # rebuild the run without any transcript evidence of the later calls
        self.tr.lines = self.tr.lines[:3]
        self.tr.path.write_text("\n".join(json.dumps(x) for x in self.tr.lines) + "\n")
        self.assertEqual(self.check()[0], 0)
        self.set_events(good)
        rc, out = self.audit()
        self.assertNotEqual(rc, 0, out)


class Concurrency(WfCase):
    def test_lock_held_refused(self):
        self.start()
        (self.run / ".wf/lock").write_text(json.dumps({"pid": os.getppid(), "host": socket.gethostname(), "t": "x"}))
        out = self.wf("begin", self.run, "topic", expect=1)
        self.assertIn("locked", out)

    def test_stale_lock_taken_over(self):
        self.start()
        (self.run / ".wf/lock").write_text(json.dumps({"pid": 999999, "host": socket.gethostname(), "t": "x"}))
        out = self.wf("begin", self.run, "topic")
        self.assertIn("stale lock", out)

    def test_status_with_two_open_runs_asks(self):
        self.start("a")
        self.wf("start", self.repo, "b", "--runs", self.runs)
        cwd = os.getcwd()
        os.chdir(self.tmp)
        try:
            out = self.wf("status", expect=1)
        finally:
            os.chdir(cwd)
        self.assertIn("more than one", out)

    def test_resume_after_interruption(self):
        self.start()
        self.wf("begin", self.run, "topic")
        self.put("steps/1-topic.json", {"options": ["a", "b"]})
        # a crash leaves a lock behind; the next command continues the same round
        (self.run / ".wf/lock").write_text(json.dumps({"pid": 999999, "host": socket.gethostname(), "t": "x"}))
        self.wf("propose", self.run, "topic")
        self.assertIn("round 1", self.wf("status", self.run))


if __name__ == "__main__":
    unittest.main()


class CommandGate(WfCase):
    def edit_gate(self, **kw):
        w = json.loads((self.repo / "workflow.json").read_text())
        w["steps"][2]["gates"][1].update(kw)
        (self.repo / "workflow.json").write_text(json.dumps(w))

    def to_verify(self):
        self.step_topic()
        self.step_points()
        self.wf("begin", self.run, "verify")
        self.put("evidence/a.txt", "x\n")
        self.put("steps/3-verify.json", {"topic": "dogs", "checked": ["loyal", "loud", "fluffy"]})

    def test_timeout(self):
        (self.repo / "tools/verify_points.py").write_text("import time\ntime.sleep(5)\n")
        self.edit_gate(timeout=1)
        git(self.repo, "commit", "-qam", "slow gate")
        self.start()
        self.to_verify()
        self.assertIn("timed out", self.wf("done", self.run, "verify", expect=1))

    def test_cannot_start(self):
        self.edit_gate(argv=["{wf}/tools/verify_points.py", "{run}"])   # not executable
        git(self.repo, "commit", "-qam", "no interpreter")
        self.start()
        self.to_verify()
        self.assertIn("could not start", self.wf("done", self.run, "verify", expect=1))


class RunArgument(WfCase):
    def test_changing_commands_need_run(self):
        self.start()
        for cmd in ("begin", "propose", "done"):
            with self.assertRaises(SystemExit):
                main([cmd, "topic"])


from durweg.cli import main  # noqa: E402


class Portable(WfCase):
    """Core lifecycle that must work on Linux, macOS and Windows alike (CI on all three)."""

    def test_live_lock_is_never_taken_over(self):
        from durweg.util import _alive
        self.assertTrue(_alive(os.getpid()))
        self.start()
        (self.run / ".wf/lock").write_text(json.dumps({"pid": os.getpid(), "host": socket.gethostname(), "t": "x"}))
        self.assertIn("locked", self.wf("begin", self.run, "topic", expect=1))

    def test_dead_process_lock_is_recovered(self):
        from durweg.util import _alive
        p = subprocess.Popen([sys.executable, "-c", "pass"])
        p.wait()
        self.assertFalse(_alive(p.pid))
        self.start()
        (self.run / ".wf/lock").write_text(json.dumps({"pid": p.pid, "host": socket.gethostname(), "t": "x"}))
        self.assertIn("stale lock", self.wf("begin", self.run, "topic"))

    def test_spaces_and_chinese_in_paths(self):
        self.runs = self.tmp / "我的 项目" / "runs"
        self.start()
        self.full()
        rc, out = self.check()
        self.assertEqual(rc, 0, out)
        self.wf("render", self.run)
        self.assertIn("dogs please", (self.run / "run.md").read_text(encoding="utf-8"))

    def test_chinese_quote_and_values(self):
        self.start()
        self.step_topic(options=("猫", "狗"), answer="就要狗，谢谢", chosen="狗")
        dec = json.loads((self.run / "steps/1-topic.decision.json").read_text(encoding="utf-8"))
        self.assertEqual(dec["values"]["chosen"], "狗")

    def test_version(self):
        from helpers import ROOT
        r = subprocess.run([sys.executable, str(ROOT / "bin" / "durweg"), "--version"], capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("durweg 1.0", r.stdout)


class GitOptional(WfCase):
    """Plan V1-R-003: a workflow folder without git works; git rules apply only inside a work tree."""

    def plain_copy(self, where):
        from helpers import EXAMPLE
        import shutil as sh
        sh.copytree(EXAMPLE, where)
        return where

    def run_plain(self, src, slug="plain"):
        self.wf("start", src, slug, "--runs", self.runs)
        self.run = next(self.runs.glob(f"*_{slug}"))
        self.full()
        return self.check()

    def test_folder_without_git(self):
        src = self.plain_copy(self.tmp / "plain")
        rc, out = self.run_plain(src)
        self.assertEqual(rc, 0, out)
        self.assertNotIn("dev run", out)
        start = self.events()[0]["workflow"]
        self.assertEqual(start["source_kind"], "files")
        self.assertIsNone(start["commit"])
        self.assertEqual(len(start["digest"]), 64)

    def test_no_git_installed(self):
        src = self.plain_copy(self.tmp / "nogit")
        old = os.environ["PATH"]
        empty = self.tmp / "empty-bin"
        empty.mkdir()
        os.environ["PATH"] = str(empty)                    # no git; durweg runs gates with sys.executable
        try:
            import shutil as sh
            self.assertIsNone(sh.which("git"))
            rc, out = self.run_plain(src, "nogit")
        finally:
            os.environ["PATH"] = old
        self.assertEqual(rc, 0, out)

    def test_source_moved_or_changed_later(self):
        src = self.plain_copy(self.tmp / "moving")
        self.assertEqual(self.run_plain(src, "mv")[0], 0)
        (src / "workflow.json").write_text("{}")
        src.rename(self.tmp / "moved-away")
        rc, out = self.check()
        self.assertEqual(rc, 0, out)                                 # the run's snapshot decides

    def test_untracked_inside_an_upper_git_repo_is_refused(self):
        outer = self.tmp / "project"
        outer.mkdir()
        git(outer, "init", "-q", "-b", "main")
        (outer / "README").write_text("x\n")
        git(outer, "add", "-A")
        git(outer, "commit", "-q", "-m", "x")
        src = self.plain_copy(outer / "methods" / "mini")
        out = self.wf("start", src, "inner", "--runs", self.runs, expect=1)
        self.assertIn("not committed and clean", out)


class Platforms(WfCase):
    """Plan 2.2: platforms in workflow.json; refused before the run folder exists."""

    def set_platforms(self, value):
        w = json.loads((self.repo / "workflow.json").read_text())
        w["platforms"] = value
        (self.repo / "workflow.json").write_text(json.dumps(w))
        git(self.repo, "commit", "-qam", "platforms")

    def start_rc(self):
        from durweg.cli import main as m
        import contextlib, io
        err = io.StringIO()
        with contextlib.redirect_stderr(err), contextlib.redirect_stdout(io.StringIO()):
            rc = m(["start", str(self.repo), "p", "--runs", str(self.runs)])
        return rc, err.getvalue()

    def test_supported_here(self):
        from durweg.util import current_platform
        self.set_platforms([current_platform()])
        self.assertEqual(self.start_rc()[0], 0)

    def test_unsupported_is_refused_before_the_run(self):
        from durweg.util import current_platform
        other = [p for p in ("linux", "macos", "windows") if p != current_platform()]
        self.set_platforms(other[:1])
        rc, err = self.start_rc()
        self.assertEqual(rc, 3, err)
        self.assertIn("supports", err)
        self.assertFalse(self.runs.exists() and any(self.runs.iterdir()))

    def test_definition_errors_exit_2(self):
        for bad in ([], ["linux", "linux"], ["beos"], "linux"):
            self.set_platforms(bad)
            rc, err = self.start_rc()
            self.assertEqual(rc, 2, (bad, err))

    def test_windows_hint_for_wsl(self):
        from durweg import workflow, util
        self.set_platforms(["linux"])
        wf = workflow.load(self.repo)
        orig = util.current_platform
        workflow.current_platform = lambda: "windows"
        try:
            with self.assertRaises(util.UnsupportedPlatform) as cm:
                workflow.check_platform(wf)
        finally:
            workflow.current_platform = orig
        self.assertIn("WSL", str(cm.exception))
