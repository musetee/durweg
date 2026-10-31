"""The method library in ~/Durweg (plan 2.4) and the index of runs.

~/Durweg/library.json   {"format": 1, "workflows": {name: {"path", "source", "url"?, "added",
                                                      "branch"?, "commit"?, "catalog"?}}}
                        (the ?-fields are new in v1.1 and optional: v1.0 files stay valid)
~/Durweg/runs.json      {"format": 1, "runs": [{"run", "path", "workflow", "library", "started"}]}

The library only says where a workflow is. A run never reads it again: `durweg start` snapshots the
workflow into the run, and `check` uses that snapshot. The runs index is a convenience; the run
folders in the projects are the record, and `durweg runs --rebuild <folder>` rebuilds the index.
"""

import os
import re
from pathlib import Path

from . import workflow
from .util import RunLock, WfError, now, read_json, rmtree, write_json

NAME = re.compile(r"^[a-z0-9][a-z0-9-]*$")
GIT_URL = re.compile(r"^(https?://|git@|ssh://)|\.git$")


def home():
    return Path(os.environ.get("DURWEG_HOME") or Path.home() / "Durweg")


def _load(name, key):
    p = home() / name
    if not p.is_file():
        return {"format": 1, key: {} if key == "workflows" else []}
    try:
        data = read_json(p)
    except (OSError, ValueError) as e:
        raise WfError(f"{p} cannot be read ({e}); fix or delete it"
                      + ("; `durweg runs --rebuild <folder>` makes a new index" if key == "runs" else ""))
    data.setdefault(key, {} if key == "workflows" else [])
    return data


class _IndexLock(RunLock):
    """The same O_EXCL lock as a run's, on ~/Durweg/.<name>.lock. Held only for a moment, so a
    second process waits for it (up to WAIT seconds) instead of failing at once."""

    WAIT = 15

    def __init__(self, name):
        self.path = home() / f".{name}.lock"
        self.note = ""

    def __enter__(self):
        import time
        self.path.parent.mkdir(parents=True, exist_ok=True)
        until = time.monotonic() + self.WAIT
        while True:
            try:
                return super().__enter__()
            except WfError:
                if time.monotonic() >= until:
                    raise
                time.sleep(0.05)


def looks_like_path(arg):
    """./x, ../x, /x, ~/x, C:\\x, or anything with a path separator is a path, never a name."""
    return (arg.startswith((".", "/", "~")) or "/" in arg or "\\" in arg
            or bool(re.match(r"^[A-Za-z]:", arg)))


# -- library ----------------------------------------------------------------------------
def add(target, name=None):
    """Plan v1.1 C1 (revision 2), in this order:
    1. a git address -> clone it;  2. <catalog>:<name> -> that catalog only;
    3. anything that looks like a path -> that folder (as in v1.0);
    4. a single word: a folder of that name here, or a catalog entry; both -> refuse, say which to write.
    Returns (name, path, note)."""
    from . import catalog
    home().mkdir(parents=True, exist_ok=True)
    if GIT_URL.search(target):
        return _add_git(target, name or Path(target.rstrip("/")).name.removesuffix(".git"))
    m = catalog.QUALIFIED.match(target)
    if m:
        return _add_from_catalog(m.group(2), name, only=m.group(1))
    if looks_like_path(target):
        return _add_folder(target, name)
    hits, notes = catalog.find(target)
    here = Path(target).is_dir()
    if here and hits:
        raise WfError(f"{target} is both a folder here and a workflow in the catalog"
                      f"{'s' if len(hits) > 1 else ''} {', '.join(c for c, _ in hits)}; write ./{target} "
                      f"for the folder or {hits[0][0]}:{target} for the catalog entry")
    if here:
        return _add_folder(target, name)
    if not hits:
        hint = f" ({'; '.join(notes)})" if notes else ""
        raise WfError(f"no folder named {target} here and no workflow {target} in the catalogs{hint}; "
                      f"`durweg library available` lists what can be installed")
    return _add_from_catalog(target, name, hits=hits, notes=notes)


def _add_from_catalog(wf_name, name, only=None, hits=None, notes=None):
    from . import catalog
    if hits is None:
        hits, notes = catalog.find(wf_name, only=only)
        if not hits:
            hint = f" ({'; '.join(notes)})" if notes else ""
            raise WfError(f"no workflow {wf_name} in catalog {only}{hint}")
    if len(hits) > 1:
        raise WfError(f"{wf_name} is in more than one catalog; write one of: "
                      + ", ".join(f"{c}:{wf_name}" for c, _ in hits))
    cid, entry = hits[0]
    got = _add_git(entry["url"], name or wf_name, catalog_id=cid)
    note = "; ".join(x for x in [got[2]] + list(notes or []) if x) or None
    return got[0], got[1], note


def _add_git(url, name, catalog_id=None):
    """Clone into a folder of this call's own, check it, and only then, under the library lock,
    move it into place and register it. A failure removes only what this call created."""
    import uuid
    from . import gitops
    gitops.need_git("adding a workflow from a git address")
    _check_name(name)
    if name in entries():
        raise WfError(f"a workflow named {name} is in the library already "
                      f"({entries()[name]['path']}); choose another with --name")
    dest = home() / "workflows" / name
    if dest.exists():
        raise WfError(f"{dest} exists already")
    dest.parent.mkdir(parents=True, exist_ok=True)
    stage = dest.parent / f".add-{name}-{uuid.uuid4().hex[:12]}"
    try:
        try:
            gitops.clone(url, stage)
        except gitops.GitFailed as e:
            raise WfError(f"git clone of {gitops.redact(url)} failed: {e}")
        workflow.load(stage)                      # validates workflow.json
        branch, commit = gitops.head_state(stage)
        entry = {"path": str(dest), "source": "git", "url": url, "added": now(),
                 "branch": branch, "commit": commit}
        if catalog_id:
            entry["catalog"] = catalog_id
        with _IndexLock("library"):
            data = _load("library.json", "workflows")
            if name in data["workflows"]:
                raise WfError(f"a workflow named {name} is in the library already "
                              f"({data['workflows'][name]['path']}); choose another with --name")
            if dest.exists():
                raise WfError(f"{dest} exists already")
            os.replace(stage, dest)
            try:
                data["workflows"][name] = entry
                write_json(home() / "library.json", data)
            except BaseException:
                os.replace(dest, stage)           # ours: we moved it there a moment ago
                raise
    finally:
        rmtree(stage)                             # only this call's own folder
    return name, dest, None


def _add_folder(target, name):
    # normalised and absolute, but links are kept: the example registered through
    # .../durweg/current/... follows updates (a run's snapshot keeps its own copy anyway)
    path = Path(os.path.normpath(Path(target).expanduser().absolute()))
    if not path.is_dir():
        raise WfError(f"{target} is not a folder")
    wf = workflow.load(path)                       # validates workflow.json
    name = name or (wf.id if NAME.match(wf.id) else path.name.lower())
    _check_name(name)
    _register(name, {"path": str(path), "source": "folder", "added": now()})
    return name, path, None


def _register(name, entry):
    with _IndexLock("library"):
        data = _load("library.json", "workflows")
        if name in data["workflows"]:
            raise WfError(f"a workflow named {name} is in the library already "
                          f"({data['workflows'][name]['path']}); choose another with --name")
        data["workflows"][name] = entry
        write_json(home() / "library.json", data)


def _check_name(name):
    if not NAME.match(name or ""):
        raise WfError(f"library names use lower-case letters, digits and -: {name!r}; choose one with --name")


def remove(name):
    with _IndexLock("library"):
        data = _load("library.json", "workflows")
        if name not in data["workflows"]:
            raise WfError(f"no workflow named {name} in the library")
        entry = data["workflows"].pop(name)
        write_json(home() / "library.json", data)
    return entry["path"]


def entries():
    return _load("library.json", "workflows")["workflows"]


def resolve(arg):
    """(path, library name or None) for the WORKFLOW argument of `durweg start`."""
    if looks_like_path(arg):
        return Path(os.path.normpath(Path(arg).expanduser().absolute())), None
    found = entries().get(arg)
    if not found:
        names = ", ".join(sorted(entries())) or "none yet"
        raise WfError(f"no workflow named {arg} in the library (library: {names}); "
                      f"for a folder write ./{arg}")
    return Path(found["path"]), arg


# -- runs index -------------------------------------------------------------------------
def record_run(run_dir, workflow_id, library_name, started):
    try:
        home().mkdir(parents=True, exist_ok=True)
        with _IndexLock("runs"):
            data = _load("runs.json", "runs")
            data["runs"] = [r for r in data["runs"] if r.get("path") != str(run_dir)]
            data["runs"].append({"run": Path(run_dir).name, "path": str(run_dir), "workflow": workflow_id,
                                 "library": library_name, "started": started})
            write_json(home() / "runs.json", data)
        return None
    except WfError as e:
        return f"note: the run was started, but the runs index was not updated ({e})"


def rebuild(folder):
    found = []
    for state in Path(folder).expanduser().resolve().rglob(".wf/state.json"):
        try:
            ev = read_json(state)["events"][0]
        except (OSError, ValueError, KeyError, IndexError):
            continue
        found.append({"run": state.parent.parent.name, "path": str(state.parent.parent),
                      "workflow": ev.get("workflow", {}).get("id"), "library": ev.get("library"),
                      "started": ev.get("t")})
    home().mkdir(parents=True, exist_ok=True)
    with _IndexLock("runs"):
        try:
            data = _load("runs.json", "runs")
        except WfError:
            data = {"format": 1, "runs": []}
        known = {r.get("path") for r in data["runs"]}
        data["runs"] += [r for r in found if r["path"] not in known]
        write_json(home() / "runs.json", data)
    return len(found)


def runs():
    return _load("runs.json", "runs")["runs"]


# -- source lock (plan v1.1 C4, revision 2 B) ------------------------------------------------
def source_lock(path):
    """One lock per workflow folder, by its real path (normcase on Windows), kept outside any
    folder that an update swaps: ~/Durweg/.locks/<sha256 of the path, 16>.lock. `durweg start`
    holds it while it loads and snapshots the workflow; an update holds it while it swaps."""
    import hashlib
    key = os.path.normcase(os.path.realpath(str(path)))
    return _IndexLock("locks/" + hashlib.sha256(key.encode("utf-8")).hexdigest()[:16])


# -- update (plan v1.1 C2, C3, C4) -----------------------------------------------------------
def managed(entry):
    """A clone Durweg made and may update: source git, inside ~/Durweg/workflows/."""
    if entry.get("source") != "git":
        return False
    try:
        p = Path(os.path.realpath(entry["path"]))
        return (home() / "workflows").resolve() in p.parents
    except (OSError, KeyError):
        return False


def _remote_default(dest, url):
    from . import gitops
    out = gitops.run(["ls-remote", "--symref", "origin", "HEAD"], cwd=dest, url=url)
    for line in out.splitlines():
        if line.startswith("ref:") and line.rstrip().endswith("HEAD"):
            ref = line.split()[1]
            return ref[len("refs/heads/"):] if ref.startswith("refs/heads/") else ref
    return None


def update_one(name, entry):
    """(status, detail, new_fields): status updated | unchanged | skipped | failed.
    The new version is prepared in a copy of the clone, checked, and only then swapped in under
    the library lock and the folder's source lock; anything that goes wrong leaves the old one."""
    import shutil
    import uuid
    from . import gitops
    if entry.get("source") != "git":
        return "skipped", "your own folder: Durweg does not change it", {}
    if not managed(entry):
        return "skipped", "not a folder Durweg cloned (outside ~/Durweg/workflows)", {}
    if shutil.which("git") is None:
        return "skipped", "needs git, which is not installed", {}
    dest, url = Path(entry["path"]), entry.get("url", "")
    if not (dest / ".git").exists():
        return "failed", f"{dest} is missing or not a git clone", {}
    try:
        branch, head = gitops.head_state(dest)
        want = entry.get("branch") or branch
        fill = {"branch": want, "commit": head} if not entry.get("branch") or not entry.get("commit") else {}
        if branch is None:
            return "skipped", "not on a branch (detached HEAD); Durweg does not move it", fill
        if branch != want:
            return "skipped", f"on branch {branch}, not {want}; Durweg does not switch branches", fill
        if gitops.run(["status", "--porcelain", "--untracked-files=all"], cwd=dest).strip():
            return "skipped", "has changes that are not committed; Durweg does not overwrite them", fill
        default = _remote_default(dest, url)
        if default and default != want:
            return "skipped", (f"the remote's default branch is now {default}, not {want}: "
                               f"`durweg library remove {name}` and add it again"), fill
        gitops.run(["fetch", "-q", "origin", want], cwd=dest, url=url)
        new = gitops.run(["rev-parse", f"refs/remotes/origin/{want}"], cwd=dest).strip()
        if new == head:
            return "unchanged", head[:7], fill
        ancestor = subprocess_ok(dest, "merge-base", "--is-ancestor", head, new)
        if not ancestor:
            ahead = subprocess_ok(dest, "merge-base", "--is-ancestor", new, head)
            return "skipped", ("has commits that are not on the remote" if ahead else
                               "has commits that differ from the remote (diverged)") \
                + "; Durweg does not reset it", fill
    except gitops.GitFailed as e:
        status = "skipped" if e.kind in ("offline", "timeout", "auth", "no-git") else "failed"
        return status, gitops.redact(str(e)), {}

    stage = dest.parent / f".update-{name}-{uuid.uuid4().hex[:12]}"
    try:
        shutil.copytree(dest, stage, symlinks=True)          # keeps the clone's own git settings
        gitops.run(["merge", "-q", "--ff-only", f"refs/remotes/origin/{want}"], cwd=stage)
        workflow.load(stage)                                  # an invalid new version is never swapped in
        _, staged = gitops.head_state(stage)
        with _IndexLock("library"), source_lock(dest):
            _, now_head = gitops.head_state(dest)
            if now_head != head:
                return "skipped", "changed while it was being updated; try again", {}
            old = dest.parent / f".old-{name}-{uuid.uuid4().hex[:12]}"
            os.replace(dest, old)
            try:
                os.replace(stage, dest)
            except OSError:
                os.replace(old, dest)
                raise
            rmtree(old)
            data = _load("library.json", "workflows")
            if name in data["workflows"]:
                data["workflows"][name].update({"branch": want, "commit": staged, "updated": now()})
                write_json(home() / "library.json", data)
        return "updated", f"{head[:7]} -> {staged[:7]}", {}
    except gitops.GitFailed as e:
        return "failed", gitops.redact(str(e)), {}
    except WfError as e:
        return "failed", f"the new version is not valid, the old one is kept ({e})", {}
    except OSError as e:
        return "failed", f"could not swap the folder, the old one is kept ({e}); try again later", {}
    finally:
        rmtree(stage)


def subprocess_ok(cwd, *args):
    from . import gitops
    try:
        gitops.run(list(args), cwd=cwd)
        return True
    except gitops.GitFailed:
        return False


def update(names=None):
    """Update the given library entries (all when None). Returns [(name, status, detail)]."""
    items = entries()
    if names:
        missing = [n for n in names if n not in items]
        if missing:
            raise WfError(f"no workflow named {', '.join(missing)} in the library")
        items = {n: items[n] for n in names}
    out = []
    for name in sorted(items):
        status, detail, fill = update_one(name, items[name])
        if fill:
            with _IndexLock("library"):
                data = _load("library.json", "workflows")
                if name in data["workflows"]:
                    for k, v in fill.items():
                        data["workflows"][name].setdefault(k, v)
                        if data["workflows"][name][k] is None:
                            data["workflows"][name][k] = v
                    write_json(home() / "library.json", data)
        out.append((name, status, detail))
    return out
