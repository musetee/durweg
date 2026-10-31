"""durweg update: Durweg itself to the newest release, then the catalogs and workflows (plan v1.1
C5, U1).

The platform is updated by the installer of the target release, run in its update mode: it
keeps the last choices (language, where Durweg is installed) and asks nothing, installs nothing
new for agents, opens no browser and starts no agent, and leaves the library to `durweg update`.
The installer checks the package by sha256, unpacks it into its own folder, tries it, and only
then switches; the previous version stays when anything fails (V1-C-006).

Tests and release candidates:
    DURWEG_UPDATE_LATEST=<version>        do not ask GitHub which version is the newest
    DURWEG_UPDATE_INSTALLER=<path>        use this installer instead of the release's
    DURWEG_UPDATE_RELEASES=<url>          where "latest" redirects to (default: the GitHub page)
DURWEG_SOURCE / DURWEG_SHA256 pass through to the installer.
"""

import os
import re
import subprocess
import sys
import tempfile
import urllib.request
from pathlib import Path

from . import __version__
from .util import current_platform, read_json

REPO = "musetee/durweg"
RELEASES = f"https://github.com/{REPO}/releases/latest"
RAW = f"https://raw.githubusercontent.com/{REPO}"
TAG = re.compile(r"^v(\d+)\.(\d+)\.(\d+)$")
TIMEOUT = 30


def _home():
    from .library import home
    return home()


def installed():
    """The installer's manifest (~/Durweg/.install.json), or None when Durweg was not installed by
    an installer (a source checkout, for example)."""
    p = _home() / ".install.json"
    try:
        return read_json(p) if p.is_file() else None
    except (OSError, ValueError):
        return None


def current_version(manifest):
    v = (manifest or {}).get("version")
    return v if isinstance(v, str) and v else f"v{__version__}"


def key(version):
    m = TAG.match(version or "")
    return tuple(int(x) for x in m.groups()) if m else None


def latest():
    """The newest published release's tag; raises OSError (offline, not found) or ValueError."""
    if os.environ.get("DURWEG_UPDATE_LATEST"):
        return os.environ["DURWEG_UPDATE_LATEST"]
    url = os.environ.get("DURWEG_UPDATE_RELEASES") or RELEASES
    req = urllib.request.Request(url, method="HEAD", headers={"User-Agent": "durweg-update"})
    with urllib.request.urlopen(req, timeout=TIMEOUT) as r:         # follows the redirect to .../tag/<v>
        final = r.geturl()
    tag = final.rstrip("/").rsplit("/", 1)[-1]
    if not key(tag):
        raise ValueError(f"no release tag in {final}")
    return tag


def _installer(version, folder):
    """Path of the target release's installer for this computer, downloaded into `folder`."""
    own = os.environ.get("DURWEG_UPDATE_INSTALLER")
    if own:
        return Path(own)
    name = "Durweg-Install.bat" if current_platform() == "windows" else "install.sh"
    dest = Path(folder) / name
    req = urllib.request.Request(f"{RAW}/{version}/{name}", headers={"User-Agent": "durweg-update"})
    with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
        dest.write_bytes(r.read())
    return dest


def _language():
    try:
        lang = read_json(_home() / "config.json").get("language")
    except (OSError, ValueError, AttributeError):
        lang = None
    return lang if lang in ("en", "zh") else "en"


def run_installer(version):
    """Run the target release's installer in update mode; returns (exit code, its output)."""
    env = dict(os.environ, DURWEG_UPDATE="1", DURWEG_VERSION=version, DURWEG_LANG=_language(),
               DURWEG_AGENT="skip", DURWEG_NO_START="1", DURWEG_NO_BROWSER="1", DURWEG_NO_PAUSE="1")
    with tempfile.TemporaryDirectory(prefix="durweg-update-") as tmp:
        script = _installer(version, tmp)
        if current_platform() == "windows":
            env["DURWEG_TARGET"] = "windows"
            cmd = ["cmd.exe", "/d", "/c", str(script)]
        else:
            cmd = ["bash", str(script)]
        r = subprocess.run(cmd, env=env, stdin=subprocess.DEVNULL, capture_output=True, text=True,
                           encoding="utf-8", errors="replace", timeout=900)
    return r.returncode, (r.stdout or "") + (r.stderr or "")


def platform():
    """(status, detail): updated | unchanged | skipped | failed."""
    manifest = installed()
    if manifest is None:
        return "skipped", "this Durweg was not installed by the installer (no ~/Durweg/.install.json)"
    have = current_version(manifest)
    try:
        want = latest()
    except (OSError, ValueError) as e:
        return "skipped", f"cannot ask GitHub for the newest version ({e})"
    if key(want) is None:
        return "skipped", f"{want} is not a release version"
    if key(have) is not None and key(want) <= key(have):
        return "unchanged", f"{have} is the newest"
    try:
        rc, out = run_installer(want)
    except (OSError, subprocess.SubprocessError) as e:
        return "failed", f"the installer of {want} could not be run ({e}); {have} is kept"
    if rc != 0:
        tail = [ln.strip() for ln in out.splitlines() if ln.strip()][-3:]
        return "failed", f"the installer of {want} stopped ({' / '.join(tail)}); {have} is kept"
    now = current_version(installed())
    if now != want:
        return "failed", f"the installer finished but {now} is installed, not {want}"
    return "updated", f"{have} -> {want}"


def launcher():
    """The durweg command the installer wrote (the new version after an update)."""
    m = installed() or {}
    for p in m.get("launchers") or []:
        if Path(p).exists():
            return p
    return None


def main_update():
    status, detail = platform()
    print(f"Durweg                  {status:9} {detail}")
    sys.stdout.flush()
    if status == "updated" and launcher():
        # the new version updates the library: its code, not this process's old one
        cmd = [launcher(), "library", "update"]
        if current_platform() == "windows":
            cmd = ["cmd.exe", "/d", "/c", *cmd]
        rc = subprocess.run(cmd, stdin=subprocess.DEVNULL).returncode
    else:
        from .cli import _update
        rc = _update(None)
    return 1 if status == "failed" else rc
