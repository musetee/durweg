"""Small helpers: hashing, atomic writes, local time, the per-run lock."""

import datetime
import hashlib
import json
import os
import socket
from pathlib import Path


class WfError(Exception):
    """A refusal or error to show the user; the command exits 1."""


class DefinitionError(WfError):
    """workflow.json is not valid; the command exits 2."""
    exit_code = 2


class UnsupportedPlatform(WfError):
    """The workflow does not support this operating system; the command exits 3."""
    exit_code = 3


def current_platform():
    """linux (also WSL), macos or windows."""
    import sys
    if sys.platform.startswith("win"):
        return "windows"
    if sys.platform == "darwin":
        return "macos"
    return "linux"


def plugin_root():
    """The folder of this Durweg when it runs as the Claude Code plugin, else None.
    The plugin is the repository with .claude-plugin/plugin.json; the installer's package leaves
    .claude-plugin out (.gitattributes export-ignore, tools/package.py). DURWEG_PLUGIN=0|1 overrides
    the check (tests; plan CP-R-002)."""
    root = Path(__file__).resolve().parent.parent
    flag = os.environ.get("DURWEG_PLUGIN", "")
    if flag == "0":
        return None
    if flag == "1":
        return root
    return root if (root / ".claude-plugin" / "plugin.json").is_file() else None


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
    """Whether a process with this pid is running. Never signals it: on Windows os.kill(pid, 0)
    would terminate the process, so there OpenProcess + GetExitCodeProcess is used instead."""
    if pid <= 0:
        return False
    if os.name == "nt":
        import ctypes
        from ctypes import wintypes
        k32 = ctypes.WinDLL("kernel32", use_last_error=True)
        k32.OpenProcess.restype = wintypes.HANDLE
        k32.OpenProcess.argtypes = (wintypes.DWORD, wintypes.BOOL, wintypes.DWORD)
        k32.GetExitCodeProcess.argtypes = (wintypes.HANDLE, ctypes.POINTER(wintypes.DWORD))
        k32.CloseHandle.argtypes = (wintypes.HANDLE,)
        handle = k32.OpenProcess(0x1000, False, pid)        # PROCESS_QUERY_LIMITED_INFORMATION
        if not handle:
            return ctypes.get_last_error() == 5             # access denied: it exists
        try:
            code = wintypes.DWORD()
            if not k32.GetExitCodeProcess(handle, ctypes.byref(code)):
                return True                                 # cannot tell: treat as alive
            return code.value == 259                        # STILL_ACTIVE
        finally:
            k32.CloseHandle(handle)
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    except OSError:
        return False
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
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(me, f)
            return self
        raise WfError(f"could not take the lock {self.path}")

    def __exit__(self, *exc):
        self.path.unlink(missing_ok=True)
        return False


def rmtree(path):
    """shutil.rmtree that also removes read-only files (git objects on Windows); no error if absent."""
    import shutil
    import stat

    def again(func, p, _exc):
        try:
            os.chmod(p, stat.S_IWRITE)
            func(p)
        except OSError:
            pass
    if Path(path).exists():
        import sys
        if sys.version_info >= (3, 12):
            shutil.rmtree(path, onexc=again)
        else:
            shutil.rmtree(path, onerror=again)
