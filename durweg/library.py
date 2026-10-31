"""The method library in ~/Durweg (plan 2.4) and the index of runs.

~/Durweg/library.json   {"format": 1, "workflows": {name: {"path", "source", "url"?, "added"}}}
~/Durweg/runs.json      {"format": 1, "runs": [{"run", "path", "workflow", "library", "started"}]}

The library only says where a workflow is. A run never reads it again: `durweg start` snapshots the
workflow into the run, and `check` uses that snapshot. The runs index is a convenience; the run
folders in the projects are the record, and `durweg runs --rebuild <folder>` rebuilds the index.
"""

import os
import re
import shutil
import subprocess
from pathlib import Path

from . import workflow
from .util import RunLock, WfError, now, read_json, write_json

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
    """The same O_EXCL lock as a run's, on ~/Durweg/.<name>.lock."""

    def __init__(self, name):
        self.path = home() / f".{name}.lock"
        self.note = ""


def looks_like_path(arg):
    """./x, ../x, /x, ~/x, C:\\x, or anything with a path separator is a path, never a name."""
    return (arg.startswith((".", "/", "~")) or "/" in arg or "\\" in arg
            or bool(re.match(r"^[A-Za-z]:", arg)))


# -- library ----------------------------------------------------------------------------
def add(target, name=None):
    home().mkdir(parents=True, exist_ok=True)
    if GIT_URL.search(target):
        if shutil.which("git") is None:
            raise WfError("adding a workflow from a git address needs git, which is not installed; "
                          "download the folder instead and add the folder")
        name = name or Path(target.rstrip("/")).name.removesuffix(".git")
        _check_name(name)
        dest = home() / "workflows" / name
        if dest.exists():
            raise WfError(f"{dest} exists already")
        dest.parent.mkdir(parents=True, exist_ok=True)
        r = subprocess.run(["git", "clone", "-q", target, str(dest)], capture_output=True, text=True)
        if r.returncode != 0:
            raise WfError(f"git clone failed: {r.stderr.strip()[:200]}")
        path, source = dest, "git"
    else:
        # normalised and absolute, but links are kept: the example registered through
        # .../durweg/current/... follows updates (a run's snapshot keeps its own copy anyway)
        path, source = Path(os.path.normpath(Path(target).expanduser().absolute())), "folder"
        if not path.is_dir():
            raise WfError(f"{target} is not a folder")
    wf = workflow.load(path)                       # validates workflow.json
    name = name or (wf.id if NAME.match(wf.id) else path.name.lower())
    _check_name(name)
    with _IndexLock("library"):
        data = _load("library.json", "workflows")
        if name in data["workflows"]:
            raise WfError(f"a workflow named {name} is in the library already "
                          f"({data['workflows'][name]['path']}); choose another with --name")
        entry = {"path": str(path), "source": source, "added": now()}
        if source == "git":
            entry["url"] = target
        data["workflows"][name] = entry
        write_json(home() / "library.json", data)
    return name, path


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
