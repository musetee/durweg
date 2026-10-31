"""Small helpers: hashing, atomic writes, local time, the per-run lock."""

import datetime
import hashlib
import json
import os
import socket
from pathlib import Path


class WfError(Exception):
    """A refusal or error to show the user; the command exits 1."""


def now():
    return datetime.datetime.now().astimezone().isoformat(timespec="seconds")


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def sha256_json(obj):
    data = json.dumps(obj, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(data.encode("utf-8")).hexdigest()


def write_atomic(path, text):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.tmp{os.getpid()}")
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(text)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)


def write_json(path, obj):
    write_atomic(path, json.dumps(obj, indent=2, ensure_ascii=False) + "\n")


def read_json(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _alive(pid):
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


class RunLock:
    """`.wf/lock`, created with O_EXCL. A lock left by a dead process on this host is taken over."""

    def __init__(self, run_dir):
        self.path = Path(run_dir) / ".wf" / "lock"
        self.note = ""

    def __enter__(self):
        me = {"pid": os.getpid(), "host": socket.gethostname(), "t": now()}
        for _ in range(2):
            try:
                fd = os.open(self.path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o644)
            except FileExistsError:
                try:
                    holder = read_json(self.path)
                except (OSError, ValueError):
                    holder = {}
                if holder.get("host") == me["host"] and isinstance(holder.get("pid"), int) \
                        and not _alive(holder["pid"]):
                    self.path.unlink(missing_ok=True)
                    self.note = f"took over a stale lock left by pid {holder['pid']} ({holder.get('t')})"
                    continue
                raise WfError(f"run is locked by pid {holder.get('pid')} on {holder.get('host')} "
                              f"since {holder.get('t')} ({self.path})")
            with os.fdopen(fd, "w") as f:
                json.dump(me, f)
            return self
        raise WfError(f"could not take the lock {self.path}")

    def __exit__(self, *exc):
        self.path.unlink(missing_ok=True)
        return False
