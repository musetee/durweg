"""Loading a workflow definition, checking its repository is clean, and the snapshot."""

import re
import shutil
import subprocess
from pathlib import Path

from .util import WfError, read_json, sha256_file, write_json

GATE_TYPES = {"json", "sections", "table", "files", "command", "user"}
STEP_ID = re.compile(r"^[a-z0-9][a-z0-9-]*$")
SNAP = ".wf/workflow"


class Workflow:
    def __init__(self, data, root):
        self.data = data
        self.root = Path(root)
        self.id = data["id"]
        self.steps = data["steps"]
        self.by_id = {s["id"]: s for s in self.steps}
        self.order = [s["id"] for s in self.steps]

    def index(self, sid):
        return self.order.index(sid) + 1

    def step(self, sid):
        if sid not in self.by_id:
            raise WfError(f"no step '{sid}' in workflow {self.id} (steps: {', '.join(self.order)})")
        return self.by_id[sid]

    def needs(self, sid):
        return self.by_id[sid]["needs"]

    def has_user(self, sid):
        return any(g["type"] == "user" for g in self.by_id[sid]["gates"])

    def decision_path(self, sid):
        return f"steps/{self.index(sid)}-{sid}.decision.json"

    def dependents(self, sid):
        """Every step that needs `sid`, directly or indirectly."""
        out, frontier = set(), {sid}
        while frontier:
            nxt = {s for s in self.order if set(self.needs(s)) & frontier} - out
            out |= nxt
            frontier = nxt
        return out


def validate(data):
    errs = []
    for key in ("id", "title", "skill", "steps"):
        if key not in data:
            errs.append(f"workflow.json: missing '{key}'")
    if errs:
        raise WfError("; ".join(errs))
    if not isinstance(data["steps"], list) or not data["steps"]:
        raise WfError("workflow.json: 'steps' must be a non-empty list")
    seen = []
    for i, s in enumerate(data["steps"]):
        where = f"step {i + 1}"
        sid = s.get("id")
        if not isinstance(sid, str) or not STEP_ID.match(sid):
            errs.append(f"{where}: id must match {STEP_ID.pattern}")
            continue
        if sid in seen:
            errs.append(f"{where}: duplicate id '{sid}'")
        for key in ("title", "instructions"):
            if not isinstance(s.get(key), str) or not s[key].strip():
                errs.append(f"{sid}: missing '{key}'")
        if not isinstance(s.get("artifacts"), list) or not s["artifacts"]:
            errs.append(f"{sid}: 'artifacts' must be a non-empty list of globs")
        s.setdefault("needs", [seen[-1]] if seen else [])
        for n in s["needs"]:
            if n not in seen:
                errs.append(f"{sid}: needs '{n}', which is not an earlier step")
        gates = s.get("gates")
        if not isinstance(gates, list):
            errs.append(f"{sid}: 'gates' must be a list")
            gates = []
        for g in gates:
            t = g.get("type")
            if t not in GATE_TYPES:
                errs.append(f"{sid}: unknown gate type '{t}'")
            if t == "command":
                argv = g.get("argv")
                if not isinstance(argv, list) or not argv or not all(isinstance(a, str) for a in argv):
                    errs.append(f"{sid}: command gate needs 'argv', a list of strings")
                elif not any(a.startswith("{wf}/") for a in argv):
                    errs.append(f"{sid}: command gate must run a script from the snapshot ({{wf}}/...)")
        seen.append(sid)
    if errs:
        raise WfError("invalid workflow.json:\n  " + "\n  ".join(errs))
    return data


def load(root):
    root = Path(root).expanduser().resolve()
    path = root / "workflow.json"
    if not path.is_file():
        raise WfError(f"no workflow.json in {root}")
    try:
        data = read_json(path)
    except ValueError as e:
        raise WfError(f"{path}: {e}") from e
    return Workflow(validate(data), root)


def snapshot_sources(wf):
    """Relative paths (files) that go into the snapshot."""
    root = wf.root
    files = {"workflow.json"}
    skill = root / wf.data["skill"]
    if not skill.is_dir():
        raise WfError(f"skill folder {skill} does not exist")
    for p in skill.rglob("*"):
        if p.is_file() and "__pycache__" not in p.parts and p.suffix != ".pyc":
            files.add(str(p.relative_to(root)))
    for extra in wf.data.get("snapshot", []):
        if not (root / extra).is_file():
            raise WfError(f"snapshot file {extra} does not exist")
        files.add(extra)
    for s in wf.steps:
        for g in s["gates"]:
            if g["type"] == "command":
                for a in g["argv"]:
                    if a.startswith("{wf}/") and a[5:] not in files:
                        raise WfError(f"{s['id']}: command gate runs {a[5:]}, which is not in the "
                                      f"snapshot (list it under 'snapshot' in workflow.json)")
    return sorted(files)


def _git(root, *args):
    return subprocess.run(["git", "-C", str(root), *args], capture_output=True, text=True)


def repo_state(wf, files, dev):
    """Return (commit, dirty-list). Refuse a dirty or untracked definition unless dev."""
    top = _git(wf.root, "rev-parse", "--show-toplevel")
    if top.returncode != 0:
        if dev:
            return None, ["not a git repository"]
        raise WfError(f"{wf.root} is not a git repository; commit the workflow first (or --dev)")
    head = _git(wf.root, "rev-parse", "--verify", "-q", "HEAD")
    commit = head.stdout.strip() if head.returncode == 0 else None
    st = _git(wf.root, "status", "--porcelain", "--untracked-files=all", "--", *files)
    dirty = [line for line in st.stdout.splitlines() if line.strip()]
    if commit is None:
        dirty.append("no commit yet")
    if dirty and not dev:
        raise WfError("workflow files are not committed and clean (use --dev for a run that "
                      "cannot be used for acceptance):\n  " + "\n  ".join(dirty))
    return commit, dirty


def make_snapshot(wf, run_dir, files):
    dest = Path(run_dir) / SNAP
    manifest = {}
    for rel in files:
        target = dest / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(wf.root / rel, target)
        manifest[rel] = sha256_file(target)
    write_json(dest.parent / "manifest.json", manifest)
    return manifest


def verify_snapshot(run_dir, manifest):
    """Problems if a snapshot file is missing, changed, or extra."""
    dest = Path(run_dir) / SNAP
    problems = []
    for rel, digest in manifest.items():
        p = dest / rel
        if not p.is_file():
            problems.append(f"snapshot file {rel} is missing")
        elif sha256_file(p) != digest:
            problems.append(f"snapshot file {rel} changed since start")
    if dest.is_dir():
        for p in dest.rglob("*"):
            if p.is_file() and "__pycache__" not in p.parts and str(p.relative_to(dest)) not in manifest:
                problems.append(f"snapshot has an extra file {p.relative_to(dest)}")
    return problems


def load_snapshot(run_dir, manifest):
    problems = verify_snapshot(run_dir, manifest)
    if problems:
        raise WfError("the workflow snapshot does not match: " + "; ".join(problems))
    return load(Path(run_dir) / SNAP)


def slug(title):
    t = re.sub(r"[^\w\- ]", "", title.strip().lower())
    return t.replace(" ", "-")


def instructions(snap_root, ref):
    """The text of `path#anchor` from the snapshot: that section of the markdown file."""
    path, _, anchor = ref.partition("#")
    p = Path(snap_root) / path
    if not p.is_file():
        return f"(instructions file {path} not in the snapshot)"
    lines = p.read_text(encoding="utf-8").splitlines()
    if not anchor:
        return "\n".join(lines)
    start, level = None, None
    for i, line in enumerate(lines):
        m = re.match(r"^(#{1,6})\s+(.*?)\s*#*\s*$", line)
        if not m:
            continue
        if start is None and slug(m.group(2)) == anchor:
            start, level = i, len(m.group(1))
        elif start is not None and len(m.group(1)) <= level:
            return "\n".join(lines[start:i]).rstrip()
    if start is None:
        return f"(section #{anchor} not found in {path})"
    return "\n".join(lines[start:]).rstrip()
