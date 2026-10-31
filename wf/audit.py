"""wf audit: compare a run's event log with the agent's own session transcripts (design 3.3).

Result: PASS (0), VIOLATION (1), INSUFFICIENT (2). Gaps that need a person are listed with a
stable id; a person clears them in <run>/audit-notes.md (`## G-xxxxxxxx` + what was checked).
"""

import datetime
import fnmatch
import hashlib
import json
import os
import re
import shlex
from pathlib import Path

from . import workflow
from .state import CHANGING, RunState, replay

OK_LINE = re.compile(r"ok run=(\S+) event=(\d+)")
WF_CALL = re.compile(r"(^|[\s;&|(/])wf\s+(start|begin|propose|confirm|done|reopen|status|render|check|audit)\b"
                     r"|-m\s+wf\.cli\b")
WRITE_TOOLS = {"Write", "Edit", "MultiEdit", "NotebookEdit"}
RISKY = re.compile(r"\b(python3?|perl|node|ruby|awk|rsync|dd|install|ln|truncate|sponge|unzip|tar|"
                   r"git\s+(checkout|restore|apply|stash))\b|\bsed\s+(-\w*i|--in-place)")
PATCH_FILE = re.compile(r"^\*\*\* (?:Add|Update|Delete) File: (.+)$", re.M)
JS_CMD = re.compile(r"\bcmd\s*:\s*(\"(?:[^\"\\]|\\.)*\")")
SYSTEMISH = ("<", "# AGENTS.md instructions")


def _ts(s):
    if not s:
        return None
    try:
        return datetime.datetime.fromisoformat(s.replace("Z", "+00:00"))
    except ValueError:
        return None


def _text(content):
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "\n".join(c.get("text", "") if isinstance(c, dict) else str(c) for c in content)
    return ""


class Stream:
    """All transcript items in one order: ("user", text) / ("call", info) / ("result", text)."""

    def __init__(self):
        self.items = []
        self.spans = []     # (file, first time, last time)

    def add(self, kind, t, **kw):
        kw.update(kind=kind, t=t, pos=len(self.items))
        self.items.append(kw)


def _claude(lines, st):
    ask_ids = set()
    for d in lines:
        typ, t = d.get("type"), _ts(d.get("timestamp"))
        if typ not in ("user", "assistant"):
            continue
        content = (d.get("message") or {}).get("content")
        cwd = d.get("cwd")
        if typ == "user":
            if isinstance(content, str):
                if not d.get("isMeta") and not content.lstrip().startswith(SYSTEMISH):
                    st.add("user", t, text=content)
                continue
            for it in content or []:
                if it.get("type") == "text" and not d.get("isMeta"):
                    if not it["text"].lstrip().startswith(SYSTEMISH):
                        st.add("user", t, text=it["text"])
                elif it.get("type") == "tool_result":
                    txt = _text(it.get("content"))
                    if it.get("tool_use_id") in ask_ids:
                        st.add("user", t, text=txt)
                    st.add("result", t, id=it.get("tool_use_id"), text=txt)
        else:
            for it in content or []:
                if it.get("type") != "tool_use":
                    continue
                name, inp = it.get("name"), it.get("input") or {}
                if name == "AskUserQuestion":
                    ask_ids.add(it.get("id"))
                elif name == "Bash":
                    st.add("call", t, id=it.get("id"), cmds=[inp.get("command", "")], paths=[], cwd=cwd)
                elif name in WRITE_TOOLS:
                    p = inp.get("file_path") or inp.get("notebook_path")
                    st.add("call", t, id=it.get("id"), cmds=[], paths=[p] if p else [], cwd=cwd)


def _codex(lines, st):
    cwd = None
    for d in lines:
        p, t = d.get("payload") or {}, _ts(d.get("timestamp"))
        if d.get("type") in ("session_meta", "turn_context") and p.get("cwd"):
            cwd = p["cwd"]
        if d.get("type") != "response_item":
            continue
        pt = p.get("type")
        if pt == "message" and p.get("role") == "user":
            txt = _text(p.get("content"))
            if not txt.lstrip().startswith(SYSTEMISH):
                st.add("user", t, text=txt)
        elif pt in ("function_call", "custom_tool_call"):
            name = p.get("name", "")
            raw = p.get("arguments") if pt == "function_call" else p.get("input", "")
            cmds, paths = [], []
            if pt == "function_call":
                try:
                    args = json.loads(raw) if isinstance(raw, str) else (raw or {})
                except ValueError:
                    args = {}
                c = args.get("cmd") or args.get("command")
                if isinstance(c, list):
                    c = " ".join(shlex.quote(x) for x in c)
                if c:
                    cmds.append(c)
                if "patch" in name:
                    paths += PATCH_FILE.findall(args.get("input", "") or raw or "")
            else:
                text = raw if isinstance(raw, str) else json.dumps(raw)
                for m in JS_CMD.finditer(text):
                    try:
                        cmds.append(json.loads(m.group(1)))
                    except ValueError:
                        cmds.append(m.group(1))
                paths += PATCH_FILE.findall(text.replace("\\n", "\n"))
            st.add("call", t, id=p.get("call_id"), cmds=cmds, paths=paths, cwd=cwd)
        elif pt in ("function_call_output", "custom_tool_call_output"):
            out = p.get("output")
            if isinstance(out, dict):
                out = out.get("content") or out.get("output") or json.dumps(out)
            st.add("result", t, id=p.get("call_id"), text=_text(out))


def load_transcripts(files):
    loaded = []
    for f in files:
        lines = []
        with open(f, encoding="utf-8") as fh:
            for line in fh:
                try:
                    lines.append(json.loads(line))
                except ValueError:
                    pass
        times = [x for x in (_ts(d.get("timestamp")) for d in lines) if x]
        loaded.append((f, lines, min(times) if times else None, max(times) if times else None))
    loaded.sort(key=lambda x: x[2] or datetime.datetime.max.replace(tzinfo=datetime.timezone.utc))
    st = Stream()
    for f, lines, t0, t1 in loaded:
        codex = any(d.get("type") in ("response_item", "session_meta") for d in lines[:50])
        (_codex if codex else _claude)(lines, st)
        st.spans.append((str(f), t0, t1))
    return st


# -- shell writes ----------------------------------------------------------------------
def _segments(cmd):
    return [s for s in re.split(r"&&|\|\||;|\n", cmd) if s.strip()]


def shell_writes(cmd, cwd):
    """(recognized write paths, unrecognized-risky segments) of a shell command."""
    paths, risky = [], []
    m = re.match(r"^\s*cd\s+(\S+)\s*(&&|;)", cmd)
    if m:
        cwd = os.path.join(cwd or "", os.path.expanduser(m.group(1)))
    for seg in _segments(cmd):
        if WF_CALL.search(seg) and not re.search(r"(?<![0-9&])>", seg):
            continue
        found = False
        for m in re.finditer(r"(?<![0-9<&>])>>?\s*([^\s;&|<>]+)", seg):
            if m.group(1) not in ("/dev/null", "&1", "&2"):
                paths.append(m.group(1))
                found = True
        try:
            toks = shlex.split(seg, comments=False)
        except ValueError:
            toks = seg.split()
        if toks:
            head = os.path.basename(toks[0])
            args = [x for x in toks[1:] if not x.startswith("-")]
            if head == "tee" and args:
                paths += args
                found = True
            elif head in ("cp", "mv") and len(args) >= 2:
                paths.append(args[-1])
                if head == "mv":
                    paths += args[:-1]
                found = True
            elif head in ("touch", "rm", "mkdir") and args:
                paths += args
                found = True
        if not found and RISKY.search(seg):
            risky.append(seg.strip()[:200])
    return [(p, cwd) for p in paths], risky


def _resolve(p, cwd):
    p = os.path.expanduser(p.strip("'\""))
    if not os.path.isabs(p):
        p = os.path.join(cwd or os.getcwd(), p)
    return os.path.realpath(p)


# -- audit -----------------------------------------------------------------------------
def gap_id(text):
    return "G-" + hashlib.sha1(text.encode("utf-8")).hexdigest()[:8]


def cleared_gaps(run_dir):
    notes = Path(run_dir) / "audit-notes.md"
    if not notes.is_file():
        return set()
    out, cur, body = set(), None, []
    for line in notes.read_text(encoding="utf-8").splitlines() + ["## END"]:
        m = re.match(r"^##\s+(G-[0-9a-f]{8})\b", line)
        if line.startswith("## "):
            if cur and "".join(body).strip():
                out.add(cur)
            cur, body = (m.group(1) if m else None), []
        else:
            body.append(line)
    return out


def audit(run_dir, transcripts):
    st = RunState(run_dir)
    wf = workflow.load(run_dir / workflow.SNAP)
    rp = replay(wf, st.events)
    violations = list(rp.violations)
    gaps = []
    stream = load_transcripts(transcripts)
    rd = str(Path(run_dir).resolve())

    # 1. every state-changing event is a successful wf call in the transcripts
    pos = {}
    for it in stream.items:
        if it["kind"] == "result":
            for m in OK_LINE.finditer(it["text"]):
                if m.group(1) == st.id:
                    pos.setdefault(int(m.group(2)), it["pos"])
    for ev in st.events:
        if ev["type"] not in CHANGING or ev["n"] in pos:
            continue
        t = _ts(ev.get("t"))
        slack = datetime.timedelta(seconds=1)
        covered = [f for f, a, b in stream.spans if a and b and t and a - slack <= t <= b + slack]
        what = f"event {ev['n']} ({ev['type']} {ev.get('step', '')}, {ev.get('t')})"
        if covered:
            violations.append(f"{what}: no successful wf call in {covered[0]}, which covers that time")
        else:
            gaps.append(f"{what}: not covered by the given transcripts")
    seen = sorted(pos.items())
    for (n1, p1), (n2, p2) in zip(seen, seen[1:]):
        if p2 < p1:
            violations.append(f"events {n1} and {n2} appear in the transcripts in the opposite order")

    # 2. confirmations: the user's words after the bound proposal, before the confirm
    for ev in st.events:
        if ev["type"] != "confirm":
            continue
        p, c = pos.get(ev.get("proposal_event")), pos.get(ev["n"])
        if p is None or c is None:
            continue
        quote = " ".join(ev["quote"].split())
        heard = any(it["kind"] == "user" and quote in " ".join(it["text"].split())
                    for it in stream.items[p + 1:c])
        if not heard:
            violations.append(f"confirm event {ev['n']} ({ev['step']}): the quote “{ev['quote']}” is not in "
                              f"a user message between propose event {ev['proposal_event']} and the confirm")
        elif (rp.done.get(ev["step"]) or {}).get("confirm_event") == ev["n"]:
            extra = f"; --set {ev['set']} matches what the user meant" if ev.get("set") else ""
            gaps.append(f"confirm event {ev['n']} ({ev['step']}): check that the version shown after propose "
                        f"event {ev['proposal_event']} is the proposal and that the user answered this "
                        f"step{extra}")

    # 3. writes: only inside an active round of the owning step
    rounds = _rounds(wf, st, pos)
    for it in stream.items:
        if it["kind"] != "call":
            continue
        targets = [(p, it.get("cwd")) for p in it["paths"]]
        for cmd in it["cmds"]:
            w, risky = shell_writes(cmd, it.get("cwd"))
            targets += w
            if risky and (rd in cmd or st.id in cmd or "steps/" in cmd or ".wf" in cmd):
                gaps.append(f"unrecognized shell command that may write the run: {cmd.strip()[:200]}")
        for raw, cwd in targets:
            ap = _resolve(raw, cwd)
            if not (ap == rd or ap.startswith(rd + os.sep)):
                continue
            rel = os.path.relpath(ap, rd)
            _check_write(wf, rel, it["pos"], rounds, violations, gaps)

    # report
    gaps = list(dict.fromkeys(gaps))
    cleared = cleared_gaps(run_dir)
    if violations:
        result, rc = "VIOLATION", 1
    elif gaps:
        result, rc = "INSUFFICIENT", 2
    else:
        result, rc = "PASS", 0
    print(f"{result} run={st.id} ({len(stream.items)} transcript items from {len(transcripts)} file(s))")
    for v in violations:
        print("  violation: " + v)
    for g in gaps:
        gid = gap_id(g)
        print(f"  {'cleared' if gid in cleared else 'gap'} {gid}: {g}")
    if gaps and not violations:
        left = [g for g in gaps if gap_id(g) not in cleared]
        print(f"  {len(gaps) - len(left)} of {len(gaps)} gap(s) cleared in audit-notes.md"
              + ("" if left else " - all gaps checked by a person"))
    return rc


def _rounds(wf, st, pos):
    """Per step: list of (start_pos, end_pos, propose positions, final) for its rounds."""
    out = {s: [] for s in wf.order}
    open_ = {}
    end = float("inf")
    for ev in st.events:
        s, p = ev.get("step"), pos.get(ev["n"])
        if ev["type"] in ("begin", "reopen") and p is not None:
            if ev["type"] == "reopen":
                for d in [s] + list(ev.get("reset", [])):
                    if d in open_:
                        r = open_.pop(d)
                        r["end"] = p
                        out[d].append(r)
            open_[s] = {"start": p, "end": end, "proposes": [], "done": None}
        elif ev["type"] == "propose" and s in open_ and p is not None:
            open_[s]["proposes"].append((ev["n"], p))
        elif ev["type"] == "done" and s in open_ and p is not None:
            r = open_.pop(s)
            r["end"], r["done"] = p, ev
            out[s].append(r)
    for s, r in open_.items():
        out[s].append(r)
    return out


def _check_write(wf, rel, wpos, rounds, violations, gaps):
    if rel.startswith(".wf" + os.sep) or rel == ".wf":
        violations.append(f"{rel} written outside wf (transcript item {wpos})")
        return
    for sid in wf.order:
        if rel == wf.decision_path(sid):
            violations.append(f"{rel}: the decision file was written outside `wf confirm` (item {wpos})")
            return
    owners = [sid for sid in wf.order if any(fnmatch.fnmatch(rel, g) for g in wf.step(sid)["artifacts"])]
    for sid in owners:
        inside = [r for r in rounds[sid] if r["start"] < wpos < r["end"]]
        if not inside:
            violations.append(f"{rel} (step {sid}) written outside any active round of {sid} (item {wpos})")
            continue
        r = inside[0]
        if r["done"] and wf.has_user(sid):
            ce = r["done"].get("confirm_event")
            bound = [pp for n, pp in r["proposes"]]
            # the proposal bound by the final confirm is the last propose before done
            if bound and wpos > bound[-1]:
                violations.append(f"{rel} (step {sid}) changed after the proposal that the user confirmed "
                                  f"(item {wpos}, confirm event {ce})")
