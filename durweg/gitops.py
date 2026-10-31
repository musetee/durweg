"""git for the library and the catalogs: never asks, never waits for ever, never prints a token.

Plan v1.1 C6: only the credentials already on this computer are used. Every call runs with prompts
switched off (GIT_TERMINAL_PROMPT=0, GCM_INTERACTIVE=never, ssh BatchMode even when the user set
their own ssh command) and a time limit, and does not change any git setting. A failure becomes a short reason a person can act on.
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


_SSH_OPTS = "-o BatchMode=yes -o ConnectTimeout=20"
_FIRST = re.compile(r"""^\s*("[^"]*"|'[^']*'|\S+)(.*)$""", re.S)


def _user_ssh(cwd=None):
    """The ssh command git would use in `cwd`: GIT_SSH_COMMAND, else core.sshCommand as git sees it
    there (repository, includeIf, global, system), else GIT_SSH."""
    cmd = os.environ.get("GIT_SSH_COMMAND", "").strip()
    if cmd:
        return cmd
    if shutil.which("git"):
        # in a repository: what git sees there; without one (git clone does not read the
        # repository it is started from): only the global and system settings
        scopes = [[]] if cwd else [["--global"], ["--system"]]
        for scope in scopes:
            try:
                r = subprocess.run(["git", "config", *scope, "--get", "core.sshCommand"], cwd=cwd,
                                   capture_output=True, text=True, timeout=10, stdin=subprocess.DEVNULL)
            except (OSError, subprocess.TimeoutExpired):
                continue
            if r.returncode == 0 and r.stdout.strip():
                return r.stdout.strip()
    prog = os.environ.get("GIT_SSH", "").strip()
    return f'"{prog}"' if prog else ""


def ssh_command(cwd=None):
    """(command for GIT_SSH_COMMAND, None) or (None, reason). The user's own ssh command keeps its
    key and options, with BatchMode put first (ssh uses the first value it sees for an option).
    A wrapper that is not ssh cannot be made silent, so it is refused for ssh addresses."""
    cmd = _user_ssh(cwd)
    if not cmd:
        return f"ssh {_SSH_OPTS}", None
    m = _FIRST.match(cmd)
    prog, rest = m.group(1), m.group(2)
    base = os.path.basename(prog.strip("\"'").replace("\\", "/")).lower()
    if base in ("ssh", "ssh.exe"):
        return f"{prog} {_SSH_OPTS}{rest}", None
    return None, (f"git is set to use {base} for ssh (GIT_SSH_COMMAND, core.sshCommand or GIT_SSH), "
                  "which Durweg cannot stop from asking questions; use the https address, or plain ssh")


def is_ssh(url):
    u = (url or "").lower()
    return u.startswith(("ssh://", "git+ssh://")) or bool(re.match(r"^[\w.-]+@[\w.-]+:", u))


def env(cwd=None):
    e = dict(os.environ, GIT_TERMINAL_PROMPT="0", GCM_INTERACTIVE="never", GIT_ASKPASS="",
             SSH_ASKPASS="", LC_ALL="C")
    e.pop("SSH_ASKPASS_REQUIRE", None)
    cmd, _ = ssh_command(cwd)
    if cmd:
        e["GIT_SSH_COMMAND"] = cmd
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
    if is_ssh(url):
        cmd, reason = ssh_command(cwd)
        if cmd is None:
            raise GitFailed(reason, "other")
    try:
        r = subprocess.run(["git", *args], cwd=cwd, env=env(cwd), capture_output=True, text=True,
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
