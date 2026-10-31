"""durweg uninstall: remove what the installer put on this computer, nothing else (plan 2.1).

Reads ~/Durweg/.install.json. Removes: the launchers, the skills Durweg linked or copied (a copy
only when it carries .durweg-owned), the PATH line or entry it added, the platform folder. Keeps:
~/Durweg (settings, your workflows, the library, the runs index) and every run in your projects.
"""

import json
import os
import shutil
import subprocess
from pathlib import Path

from .library import home


def _ours(path, data_dir):
    p = Path(path)
    if p.is_symlink():
        return os.readlink(p).startswith(str(data_dir))
    if p.is_dir():
        return (p / ".durweg-owned").is_file()
    if p.is_file() and p.suffix.lower() == ".cmd":
        return "rem durweg launcher (written by Durweg-Install.bat)" in p.read_text(encoding="utf-8", errors="replace")
    return False


def uninstall(dry_run=False):
    manifest = home() / ".install.json"
    if not manifest.is_file():
        return [f"nothing to do: {manifest} not found (Durweg was not installed by its installer)"]
    m = json.loads(manifest.read_text(encoding="utf-8"))
    data_dir = Path(m["data_dir"])
    done = []
    later = []          # Windows: the running durweg.cmd and its folder go after this command ends
    for p in m.get("launchers", []) + m.get("skills", []):
        if os.path.lexists(p) and _ours(p, data_dir):
            done.append(f"removed {p}")
            if not dry_run and os.name == "nt" and p in m.get("launchers", []):
                later.append(("del", p))
            elif not dry_run:
                if Path(p).is_dir() and not Path(p).is_symlink():
                    shutil.rmtree(p)
                else:
                    Path(p).unlink()
        elif Path(p).exists():
            done.append(f"kept {p} (not Durweg's)")
    for rc in m.get("path_lines", []):
        f = Path(rc)
        if f.is_file():
            lines = f.read_text(encoding="utf-8").splitlines(keepends=True)
            keep = [ln for ln in lines if not ln.rstrip().endswith("# added by Durweg")]
            if len(keep) != len(lines):
                done.append(f"removed the PATH line from {rc}")
                if not dry_run:
                    f.write_text("".join(keep), encoding="utf-8")
    for entry in m.get("path_entries", []):            # Windows: the user PATH in the registry
        if os.name == "nt":
            import winreg
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment", 0, winreg.KEY_ALL_ACCESS) as k:
                value, kind = winreg.QueryValueEx(k, "Path")
                parts = [x for x in value.split(";") if x and os.path.normcase(x) != os.path.normcase(entry)]
                if not dry_run:
                    winreg.SetValueEx(k, "Path", 0, kind, ";".join(parts))
            done.append(f"removed {entry} from your PATH")
    if data_dir.is_dir():
        done.append(f"removed {data_dir}")
        if not dry_run and os.name == "nt":
            later.append(("rmdir", str(data_dir)))
        elif not dry_run:
            shutil.rmtree(data_dir, ignore_errors=True)
    if later:
        steps = " & ".join(f'del /f /q "{p}"' if k == "del" else f'rmdir /s /q "{p}"' for k, p in later)
        subprocess.Popen(f'cmd /c "ping -n 3 127.0.0.1 >nul & {steps}"', shell=False,
                         creationflags=0x00000008 | 0x00000200,     # DETACHED_PROCESS | NEW_PROCESS_GROUP
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, stdin=subprocess.DEVNULL)
        done.append("(on Windows the command itself is removed a moment after this window's command ends)")
    if not dry_run:
        manifest.unlink()
    done.append(f"kept {home()} (settings, your workflows, the library) and the runs in your projects")
    return done
