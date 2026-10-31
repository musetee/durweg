"""The run's event log (.wf/state.json) and the state machine that replays it.

Statuses are never stored: they are always derived by replaying the events, so `durweg check`
validates exactly the transitions the commands enforce (design 3.1).
"""

from pathlib import Path

from .util import WfError, read_json, write_json

STATE = ".wf/state.json"
CHANGING = {"start", "begin", "propose", "confirm", "done", "reopen"}


class Replay:
    def __init__(self, wf):
        self.wf = wf
        self.status = {s: "pending" for s in wf.order}
        self.round = {s: 0 for s in wf.order}
        self.active = None
        self.propose = {}      # step -> latest propose event of the current round
        self.confirm = {}      # step -> latest confirm event of the current round
        self.done = {}         # step -> done event that made the step done (current)
        self.superseded = []   # event numbers made void by reopen
        self.round_events = {s: [] for s in wf.order}   # events of the current round
        self.violations = []

    # -- the rules -----------------------------------------------------------------
    def why_not(self, ev):
        """None if `ev` is a legal next event, else the reason it is not."""
        t, s = ev["type"], ev.get("step")
        if t == "start":
            return "start must be the first event"
        if s not in self.status:
            return f"unknown step '{s}'"
        st = self.status[s]
        if t == "begin":
            if st != "pending":
                return (f"step {s} is {st}; a done step is redone only with `durweg reopen`"
                        if st == "done" else f"step {s} is already active")
            if self.active:
                return f"step {self.active} is active; finish it (done) first"
            missing = [n for n in self.wf.needs(s) if self.status[n] != "done"]
            if missing:
                return f"step {s} needs {', '.join(missing)} done first"
            return None
        if t in ("propose", "confirm", "done") and self.active != s:
            return f"step {s} is not active (active: {self.active or 'none'})"
        if t == "propose":
            return None if self.wf.has_user(s) else f"step {s} has no user gate; nothing to propose"
        if t == "confirm":
            if not self.wf.has_user(s):
                return f"step {s} has no user gate"
            p = self.propose.get(s)
            if not p:
                return f"step {s}: no `durweg propose` in this round; propose, show it to the user, then confirm"
            if ev.get("proposal_event") != p["n"]:
                return f"step {s}: confirm must bind the latest proposal (event {p['n']})"
            return None
        if t == "done":
            if self.wf.has_user(s):
                p, c = self.propose.get(s), self.confirm.get(s)
                if not c:
                    return f"step {s}: the user has not confirmed in this round"
                if c["proposal_event"] != p["n"]:
                    return (f"step {s}: proposed again (event {p['n']}) after the last confirm; "
                            f"show the new proposal and confirm again")
                if ev.get("confirm_event") != c["n"]:
                    return f"step {s}: done must reference the latest confirm (event {c['n']})"
            return None
        if t == "reopen":
            if st != "done":
                return f"step {s} is {st}; only a done step can be reopened"
            if self.active and self.active not in self.wf.dependents(s):
                return (f"step {self.active} is active and does not depend on {s}; "
                        f"finish {self.active} first")
            return None
        return f"unknown event type '{t}'"

    def apply(self, ev):
        t, s = ev["type"], ev.get("step")
        if t == "begin":
            self.status[s] = "active"
            self.active = s
            self.round[s] += 1
            self._new_round(s, ev)
        elif t == "propose":
            self.propose[s] = ev
            self.round_events[s].append(ev["n"])
        elif t == "confirm":
            self.confirm[s] = ev
            self.round_events[s].append(ev["n"])
        elif t == "done":
            self.status[s] = "done"
            self.active = None
            self.done[s] = ev
            self.round_events[s].append(ev["n"])
        elif t == "reopen":
            reset = sorted(self.wf.dependents(s), key=self.wf.order.index)
            for d in [s] + reset:
                self.superseded += self.round_events[d]
            for d in reset:
                if self.status[d] != "pending":
                    self.status[d] = "pending"
                self.done.pop(d, None)
                self.propose.pop(d, None)
                self.confirm.pop(d, None)
                self.round_events[d] = []
            self.done.pop(s, None)
            self.status[s] = "active"
            self.active = s
            self.round[s] += 1
            self._new_round(s, ev)

    def _new_round(self, s, ev):
        self.propose.pop(s, None)
        self.confirm.pop(s, None)
        self.round_events[s] = [ev["n"]]


def replay(wf, events, strict=True):
    """Replay the log. strict: an illegal event is recorded as a violation and skipped."""
    r = Replay(wf)
    if not events or events[0].get("type") != "start":
        r.violations.append("the first event is not start")
    for i, ev in enumerate(events):
        if ev.get("n") != i + 1:
            r.violations.append(f"event {i + 1}: numbered {ev.get('n')}")
        if ev["type"] == "start" and i == 0:
            continue
        if ev["type"] == "refused":
            continue
        why = r.why_not(ev)
        if why:
            r.violations.append(f"event {ev.get('n')} ({ev['type']} {ev.get('step', '')}): {why}")
            if strict:
                continue
        r.apply(ev)
        if ev["type"] in ("begin", "reopen") and ev.get("round") not in (None, r.round[ev["step"]]):
            r.violations.append(f"event {ev['n']}: round {ev.get('round')} recorded, "
                                f"{r.round[ev['step']]} by replay")
    return r


class RunState:
    def __init__(self, run_dir):
        self.dir = Path(run_dir).resolve()
        self.path = self.dir / STATE
        if not self.path.is_file():
            raise WfError(f"{run_dir} is not a wf run (no {STATE})")
        self.data = read_json(self.path)
        self.events = self.data["events"]

    @property
    def id(self):
        return self.data["run"]

    @property
    def start(self):
        return self.events[0]

    def append(self, ev):
        ev["n"] = len(self.events) + 1
        self.events.append(ev)
        write_json(self.path, self.data)
        return ev["n"]
