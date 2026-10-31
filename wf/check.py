"""wf check: offline re-verification of a whole run (design 3.3)."""

from . import gates, workflow
from .state import RunState, replay
from .util import WfError


def check(run_dir):
    problems, notes = [], []
    try:
        st = RunState(run_dir)
    except (WfError, ValueError, KeyError) as e:
        print(f"FAIL {run_dir}: {e}")
        return 1
    start = st.events[0] if st.events else {}
    manifest = start.get("workflow", {}).get("manifest")
    if not manifest:
        print(f"FAIL {run_dir}: no start event with a snapshot manifest")
        return 1
    problems += workflow.verify_snapshot(run_dir, manifest)
    if problems:
        _report(st, problems, notes)
        return 1
    wf = workflow.load(run_dir / workflow.SNAP)
    rp = replay(wf, st.events)
    problems += rp.violations
    for sid in wf.order:
        if rp.status[sid] != "done":
            problems.append(f"step {sid} is {rp.status[sid]}")
            continue
        ev = rp.done[sid]
        if gates.artifacts_digest(run_dir, wf, sid) != ev.get("artifacts_digest"):
            problems.append(f"step {sid}: artifacts changed after done (event {ev['n']}); "
                            f"reopen the step instead of editing a done step")
        if wf.has_user(sid) and ev.get("proposal_digest") != rp.propose[sid]["proposal_digest"]:
            problems.append(f"step {sid}: done event {ev['n']} records another proposal than event "
                            f"{rp.propose[sid]['n']}")
        problems += [p if p.startswith(f"step {sid}") else f"step {sid}: {p}"
                     for p in gates.evaluate(run_dir, wf, sid, rp)]
    w = start["workflow"]
    if w.get("dev"):
        notes.append("dev run (workflow files were not clean at start): not usable for acceptance")
    refused = [e for e in st.events if e["type"] == "refused"]
    if refused:
        notes.append(f"{len(refused)} refused command(s) in the log")
    if rp.superseded:
        notes.append(f"{len(rp.superseded)} event(s) superseded by reopen")
    _report(st, problems, notes)
    return 1 if problems else 0


def _report(st, problems, notes):
    head = "PASS" if not problems else "FAIL"
    print(f"{head} run={st.id}")
    for p in problems:
        print("  - " + p.replace("\n", "\n    "))
    for n in notes:
        print("  note: " + n)
