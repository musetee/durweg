"""wf audit against session transcripts (design 3.3, 7.2)."""

import json
import unittest

from helpers import Transcript, WfCase


class Audit(WfCase):
    def test_good_run_only_manual_gaps(self):
        self.start()
        self.full()
        rc, out = self.audit()
        self.assertEqual(rc, 2, out)              # confirm meaning is for a person: INSUFFICIENT
        self.assertNotIn("violation", out)
        self.assertIn("check that the version shown", out)

    def test_gaps_cleared_in_notes(self):
        self.start()
        self.full()
        out = self.audit()[1]
        ids = [w.split()[1].rstrip(":") for w in out.splitlines() if w.strip().startswith("gap ")]
        (self.run / "audit-notes.md").write_text(
            "".join(f"## {i}\nChecked the session at the propose: the user saw the options.\n" for i in ids))
        rc, out = self.audit()
        self.assertEqual(rc, 2)
        self.assertIn("all gaps checked by a person", out)

    def test_user_chose_non_recommended(self):
        self.start()
        self.step_topic(options=("cats", "dogs", "birds"), answer="the third one", chosen="birds")
        self.step_points()
        self.step_verify(topic="birds")
        rc, out = self.audit()
        self.assertEqual(rc, 2, out)
        self.assertIn("--set {'chosen': 'birds'}", out)

    def test_user_corrects_proposal_then_repropose(self):
        self.start()
        self.wf("begin", self.run, "topic")
        self.put("steps/1-topic.json", {"options": ["cats", "dogs"]})
        self.wf("propose", self.run, "topic")
        self.tr.user("add birds")
        self.put("steps/1-topic.json", {"options": ["cats", "dogs", "birds"]})
        self.wf("propose", self.run, "topic")
        self.tr.user("yes, birds")
        self.wf("confirm", self.run, "topic", "--quote", "yes, birds", "--set", "chosen=birds")
        self.wf("done", self.run, "topic")
        self.step_points()
        self.step_verify(topic="birds")
        rc, out = self.audit()
        self.assertEqual(rc, 2, out)
        self.assertNotIn("violation", out)

    def test_answer_through_question_tool(self):
        self.start()
        self.wf("begin", self.run, "topic")
        self.put("steps/1-topic.json", {"options": ["cats", "dogs"]})
        self.wf("propose", self.run, "topic")
        self.tr.ask("Which topic?", "dogs")
        self.wf("confirm", self.run, "topic", "--quote", "dogs", "--set", "chosen=dogs")
        self.wf("done", self.run, "topic")
        self.assertNotIn("violation", self.audit()[1])

    def test_quote_not_said(self):
        self.start()
        self.wf("begin", self.run, "topic")
        self.put("steps/1-topic.json", {"options": ["cats", "dogs"]})
        self.wf("propose", self.run, "topic")
        self.wf("confirm", self.run, "topic", "--quote", "dogs please", "--set", "chosen=dogs")
        rc, out = self.audit()
        self.assertEqual(rc, 1)
        self.assertIn("is not in a user message", out)

    def test_old_round_quote_reused(self):
        self.start()
        self.step_topic(answer="dogs please")
        self.wf("reopen", self.run, "topic", "--reason", "again")
        self.wf("propose", self.run, "topic")
        self.wf("confirm", self.run, "topic", "--quote", "dogs please", "--set", "chosen=dogs")
        rc, out = self.audit()
        self.assertEqual(rc, 1, out)

    def test_quote_before_propose_does_not_count(self):
        self.start()
        self.wf("begin", self.run, "topic")
        self.tr.user("dogs please")
        self.put("steps/1-topic.json", {"options": ["cats", "dogs"]})
        self.wf("propose", self.run, "topic")
        self.wf("confirm", self.run, "topic", "--quote", "dogs please", "--set", "chosen=dogs")
        self.assertEqual(self.audit()[0], 1)

    def test_failed_call_passed_off_as_success(self):
        self.start()
        self.step_topic()
        self.wf("begin", self.run, "points")
        self.put("steps/2-points.md", self.POINTS.replace("- fluffy\n", ""))
        self.wf("done", self.run, "points", expect=1)          # refused in the transcript
        ev = [e for e in self.events() if e["type"] != "refused"]
        ev.append({"t": ev[-1]["t"], "type": "done", "step": "points", "round": 1,
                   "artifacts_digest": "forged", "files": []})
        for i, e in enumerate(ev):
            e["n"] = i + 1
        self.set_events(ev)
        rc, out = self.audit()
        self.assertEqual(rc, 1, out)
        self.assertIn("no successful wf call", out)

    def test_truncated_transcript_is_insufficient(self):
        self.start()
        self.full()
        lines = self.tr.lines
        cut = len(lines) // 2
        later = Transcript(self.tmp / "later.jsonl", self.tmp)
        later.lines = lines[cut:]
        later.path.write_text("\n".join(json.dumps(x) for x in later.lines) + "\n")
        # move the start event earlier than any transcript line
        ev = self.events()
        ev[0]["t"] = "2020-01-01T00:00:00+00:00"
        self.set_events(ev)
        rc, out = self.audit(later.path)
        self.assertNotEqual(rc, 0, out)
        self.assertIn("not covered", out)

    def test_two_session_files_cover_the_run(self):
        self.start()
        self.step_topic()
        first = list(self.tr.lines)
        self.tr = Transcript(self.tmp / "resumed.jsonl", self.tmp)
        self.step_points()
        self.step_verify()
        (self.tmp / "first.jsonl").write_text("\n".join(json.dumps(x) for x in first) + "\n")
        rc, out = self.audit(self.tmp / "first.jsonl", self.tmp / "resumed.jsonl")
        self.assertEqual(rc, 2, out)
        self.assertNotIn("violation", out)

    def test_write_before_begin(self):
        self.start()
        self.put("steps/1-topic.json", {"options": ["cats", "dogs"]})   # before begin
        self.wf("begin", self.run, "topic")
        self.wf("propose", self.run, "topic")
        self.tr.user("dogs")
        self.wf("confirm", self.run, "topic", "--quote", "dogs", "--set", "chosen=dogs")
        self.wf("done", self.run, "topic")
        rc, out = self.audit()
        self.assertEqual(rc, 1)
        self.assertIn("outside any active round", out)

    def test_rewrite_after_reopen_is_fine(self):
        self.start()
        self.step_topic()
        self.wf("reopen", self.run, "topic", "--reason", "user adds birds")
        self.put("steps/1-topic.json", {"options": ["cats", "dogs", "birds"]})
        self.wf("propose", self.run, "topic")
        self.tr.user("birds then")
        self.wf("confirm", self.run, "topic", "--quote", "birds then", "--set", "chosen=birds")
        self.wf("done", self.run, "topic")
        rc, out = self.audit()
        self.assertNotIn("violation", out)

    def test_change_after_answer_outside_wf(self):
        """Agent edits the proposal after the user answered, and wf never sees it (bypass)."""
        self.start()
        self.step_topic()
        # simulate: a Write to the proposal between propose and done, then the file put back
        lines = self.tr.lines
        idx = max(i for i, l in enumerate(lines)
                  if "wf done" in json.dumps(l) and "topic" in json.dumps(l) and l["type"] == "assistant")
        sneaky = {"type": "assistant", "timestamp": lines[idx]["timestamp"], "cwd": str(self.tmp),
                  "message": {"role": "assistant", "content": [{"type": "tool_use", "id": "toolu_x",
                              "name": "Write", "input": {"file_path": str(self.run / "steps/1-topic.json")}}]}}
        lines.insert(idx, sneaky)
        self.tr.path.write_text("\n".join(json.dumps(x) for x in lines) + "\n")
        rc, out = self.audit()
        self.assertEqual(rc, 1, out)
        self.assertIn("changed after the proposal", out)

    def test_decision_file_written_by_hand(self):
        self.start()
        self.step_topic()
        self.tr.write(self.run / "steps/1-topic.decision.json")
        rc, out = self.audit()
        self.assertEqual(rc, 1)
        self.assertIn("outside `wf confirm`", out)

    def test_state_edited_by_shell(self):
        self.start()
        self.step_topic()
        self.tr.bash(f"cat x > {self.run}/.wf/state.json", "")
        self.assertEqual(self.audit()[0], 1)

    def test_unrecognized_shell_write_is_a_gap(self):
        self.start()
        self.step_topic()
        self.tr.bash(f"python3 - <<'EOF'\nopen('{self.run}/steps/2-points.md','w')\nEOF", "")
        rc, out = self.audit()
        self.assertEqual(rc, 2)
        self.assertIn("unrecognized shell command", out)

    def test_read_only_commands_are_not_gaps(self):
        self.start()
        self.step_topic()
        self.tr.bash(f"cat {self.run}/steps/1-topic.json; ls {self.run}", "{}")
        out = self.audit()[1]
        self.assertNotIn("unrecognized", out)


class CodexTranscript(WfCase):
    """A Codex rollout: exec tool with JS calling exec_command; user messages as response items."""

    def codex_file(self):
        lines = [{"timestamp": "2020-01-01T00:00:00Z", "type": "session_meta",
                  "payload": {"cwd": str(self.tmp)}}]
        import datetime
        t0 = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(seconds=3)
        k = 0

        def ts():
            nonlocal k
            k += 1
            return (t0 + datetime.timedelta(milliseconds=k)).isoformat().replace("+00:00", "Z")
        lines[0]["timestamp"] = ts()
        for item in self.tr.lines:
            if item["type"] == "user" and isinstance(item["message"]["content"], str):
                lines.append({"timestamp": ts(), "type": "response_item", "payload": {
                    "type": "message", "role": "user",
                    "content": [{"type": "input_text", "text": item["message"]["content"]}]}})
            elif item["type"] == "assistant":
                tu = item["message"]["content"][0]
                if tu["name"] == "Bash":
                    js = "text(await tools.exec_command({cmd:%s}));" % json.dumps(tu["input"]["command"])
                else:
                    rel = tu["input"]["file_path"]
                    js = "text(await tools.exec_command({cmd:%s}));" % json.dumps(f"cat > {rel} <<'EOF'\n{{}}\nEOF")
                lines.append({"timestamp": ts(), "type": "response_item", "payload": {
                    "type": "custom_tool_call", "call_id": tu["id"], "name": "exec", "input": js}})
            elif item["type"] == "user":
                tr = item["message"]["content"][0]
                lines.append({"timestamp": ts(), "type": "response_item", "payload": {
                    "type": "custom_tool_call_output", "call_id": tr["tool_use_id"],
                    "output": [{"type": "input_text", "text": "Output:\n" + tr["content"]}]}})
        path = self.tmp / "rollout.jsonl"
        path.write_text("\n".join(json.dumps(x) for x in lines) + "\n")
        return path

    def test_codex_good_run(self):
        self.start()
        self.full()
        rc, out = self.audit(self.codex_file())
        self.assertEqual(rc, 2, out)
        self.assertNotIn("violation", out)

    def test_codex_write_before_begin(self):
        self.start()
        self.put("steps/1-topic.json", {"options": ["cats", "dogs"]})
        self.wf("begin", self.run, "topic")
        rc, out = self.audit(self.codex_file())
        self.assertEqual(rc, 1, out)


if __name__ == "__main__":
    unittest.main()
