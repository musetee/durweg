"""git for the library and the catalogs: never asks, never waits for ever, never prints a token.

Plan v1.1 C6: only the credentials already on this computer are used. Every call runs with prompts
switched off (GIT_TERMINAL_PROMPT=0, GCM_INTERACTIVE=never, ssh BatchMode) and a time limit, and
does not change any git setting. A failure becomes a short reason a person can act on.
"""

import os
import re
import shutil
import subprocess

from .util import WfError

TIMEOUT = 60
_CRED = re.compile(r"(?i)\b(https?://)[^/\s@]+@")


def redact(text):
    """https://user:token@host/... -> https://host/..."""
    return _CRED.sub(r"\1", text or "")


def env():
    e = dict(os.environ, GIT_TERMINAL_PROMPT="0", GCM_INTERACTIVE="never", GIT_ASKPASS="",
             SSH_ASKPASS="", LC_ALL="C")
    e.pop("SSH_ASKPASS_REQUIRE", None)
    if not e.get("GIT_SSH_COMMAND"):
        e["GIT_SSH_COMMAND"] = "ssh -o BatchMode=yes -o ConnectTimeout=20"
    return e


class GitFailed(WfError):
    def __init__(self, reason, kind):
        super().__init__(reason)
        self.kind = kind            # no-git | auth | offline | timeout | other


def need_git(what):
    if shutil.which("git") is None:
        raise GitFailed(f"{what} needs git, which is not installed", "no-git")


def _reason(stderr, url):
    s = (stderr or "").lower()
    if any(k in s for k in ("could not resolve host", "could not resolve hostname", "network is unreachable",
                            "failed to connect", "connection timed out", "connection refused",
                            "temporary failure in name resolution")):
        return "cannot connect (offline?)", "offline"
    if any(k in s for k in ("authentication failed", "could not read username", "terminal prompts disabled",
                            "permission denied", "repository not found", "access denied",
                            "invalid username or password")) or re.search(r"\b40[13]\b", s):
        if "github.com" in (url or "").lower():
            return ("no access: for a private GitHub repository run `gh auth login` and "
                    "`gh auth setup-git` once"), "auth"
        return "no access: set up git credentials for this host as its documentation says", "auth"
    last = [ln for ln in redact(stderr).strip().splitlines() if ln.strip()]
    return (last[-1][:200] if last else "git failed"), "other"


def run(args, cwd=None, url=None, timeout=TIMEOUT):
    """Run git; returns stdout. Raises GitFailed with a readable reason."""
    need_git("this")
    try:
        r = subprocess.run(["git", *args], cwd=cwd, env=env(), capture_output=True, text=True,
                           timeout=timeout, stdin=subprocess.DEVNULL)
    except subprocess.TimeoutExpired:
        raise GitFailed(f"no answer within {timeout} s (offline, or waiting for a login?)", "timeout")
    if r.returncode != 0:
        reason, kind = _reason(r.stderr, url)
        raise GitFailed(reason, kind)
    return r.stdout


def clone(url, dest):
    run(["clone", "-q", "--", url, str(dest)], url=url)


def head_state(repo):
    """(branch or None, commit) of a clone."""
    commit = run(["rev-parse", "HEAD"], cwd=repo).strip()
    try:
        branch = run(["symbolic-ref", "-q", "--short", "HEAD"], cwd=repo).strip() or None
    except GitFailed:
        branch = None
    return branch, commit
