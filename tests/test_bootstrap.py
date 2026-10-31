"""install.sh (the bootstrap) with stubs: gh serves a local git repository as musetee/aiagents,
curl serves a fake Claude Code installer, sudo/apt-get only record. HOME is a temp folder."""

import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
GIT_ENV = {"GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t", "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@t"}

GH = """#!/bin/sh
case "$1 $2" in
  "auth status") [ -f "$HOME/no-login" ] && exit 1; exit 0 ;;
  "repo view") exit 0 ;;
  "repo clone") git clone -q "$UPSTREAM" "$4" ;;
  "api repos/musetee/aiagents/commits/"*) ;;
esac
case "$1" in
  api) [ -f "$HOME/no-access" ] && exit 1
       git -C "$UPSTREAM" cat-file -e "${2##*/}^{commit}" ;;
esac
"""
CURL = """#!/bin/sh
echo 'echo claude-installer >> $HOME/calls; mkdir -p $HOME/.local/bin; printf "#!/bin/sh\\necho 9.9-claude-code\\n" > $HOME/.local/bin/claude; chmod +x $HOME/.local/bin/claude'
"""


def git(cwd, *args):
    return subprocess.run(["git", "-C", str(cwd), *args], check=True, capture_output=True, text=True,
                          env=dict(os.environ, **GIT_ENV)).stdout.strip()


@unittest.skipIf(os.name == "nt" or shutil.which("bash") is None, "bash bootstrap: Linux and macOS only")
class Bootstrap(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="bootstrap-"))
        self.addCleanup(shutil.rmtree, self.tmp)
        self.home = self.tmp / "home"
        self.home.mkdir()
        self.bin = self.tmp / "bin"
        self.bin.mkdir()
        self.upstream = self.tmp / "upstream"
        self.upstream.mkdir()
        git(self.upstream, "init", "-q", "-b", "main")
        (self.upstream / "workflow.json").write_text("{}\n")
        (self.upstream / "skills/setup-agents").mkdir(parents=True)
        (self.upstream / "skills/setup-agents/SKILL.md").write_text("---\nname: setup-agents\n---\n")
        git(self.upstream, "add", "-A")
        git(self.upstream, "commit", "-q", "-m", "reviewed")
        self.commit = git(self.upstream, "rev-parse", "HEAD")
        (self.upstream / "later").write_text("x\n")
        git(self.upstream, "add", "-A")
        git(self.upstream, "commit", "-q", "-m", "later")
        for name, text in (("gh", GH), ("curl", CURL), ("sudo", '#!/bin/sh\nexec "$@"\n'),
                           ("apt-get", '#!/bin/sh\necho "apt-get $*" >> "$HOME/calls"\n')):
            p = self.bin / name
            p.write_text(text)
            p.chmod(0o755)

    def run_install(self, commit=None):
        env = {"PATH": f"{self.bin}:/usr/bin:/bin", "HOME": str(self.home), "UPSTREAM": str(self.upstream),
               "DURWEG_AIAGENTS_COMMIT": commit or self.commit, **GIT_ENV}
        return subprocess.run(["bash", str(ROOT / "install.sh")], capture_output=True, text=True, env=env,
                              timeout=60, stdin=subprocess.DEVNULL)

    def calls(self):
        p = self.home / "calls"
        return p.read_text() if p.exists() else ""

    def test_not_a_release(self):
        out = self.run_install(commit="__SET_AT_RELEASE__")
        self.assertEqual(out.returncode, 1)
        self.assertIn("not a release", out.stdout)

    def test_not_logged_in_stops_before_anything(self):
        (self.home / "no-login").touch()
        out = self.run_install()
        self.assertEqual(out.returncode, 1)
        self.assertIn("gh auth login", out.stdout)
        self.assertFalse((self.home / "aiagents").exists())

    def test_no_access_stops_before_anything(self):
        (self.home / "no-access").touch()
        out = self.run_install()
        self.assertEqual(out.returncode, 1)
        self.assertIn("No access to musetee/aiagents", out.stdout)
        self.assertFalse((self.home / "aiagents").exists())

    def test_happy_path_and_rerun(self):
        out = self.run_install()
        self.assertEqual(out.returncode, 0, out.stdout + out.stderr)
        self.assertEqual(git(self.home / "aiagents", "rev-parse", "HEAD"), self.commit, "fixed commit, not the branch tip")
        self.assertTrue((self.home / ".local/bin/durweg").is_symlink())
        self.assertTrue((self.home / "durweg-runs").is_dir())
        self.assertIn("durweg start", out.stdout)
        self.assertEqual(self.calls().count("claude-installer"), 1)
        skills = self.home / ".claude/skills"          # DS-C-001: fresh HOME, no config folder before
        for s in ("run-workflow", "setup-agents"):
            self.assertTrue((skills / s / "SKILL.md").is_file(), s)
        self.assertIn("skills/setup-agents/SKILL.md", out.stdout)
        (skills / "mine").mkdir()
        (skills / "mine/SKILL.md").write_text("user's own\n")
        again = self.run_install()
        self.assertEqual(again.returncode, 0, again.stdout)
        self.assertEqual(self.calls().count("claude-installer"), 1, "Claude Code not installed twice")
        self.assertEqual((skills / "mine/SKILL.md").read_text(), "user's own\n")

    def test_foreign_setup_skill_is_not_touched(self):
        (self.home / ".claude/skills/setup-agents").mkdir(parents=True)
        out = self.run_install()
        self.assertEqual(out.returncode, 1)
        self.assertIn("not Durweg's link", out.stdout)

    def test_changed_clone_is_not_touched(self):
        self.run_install()
        (self.home / "aiagents/workflow.json").write_text('{"changed": 1}\n')
        out = self.run_install()
        self.assertEqual(out.returncode, 1)
        self.assertIn("local changes", out.stdout)
        self.assertIn("changed", (self.home / "aiagents/workflow.json").read_text())

    def test_folder_that_is_not_a_clone(self):
        (self.home / "aiagents").mkdir()
        out = self.run_install()
        self.assertEqual(out.returncode, 1)
        self.assertIn("not a git clone", out.stdout)


if __name__ == "__main__":
    unittest.main()
