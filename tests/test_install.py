"""install.sh (Linux, macOS, WSL) and durweg uninstall, in a sandbox HOME with a package built from
this working tree (plan 2.1, V1-R-002). No network: DURWEG_SOURCE points at the local package."""

import hashlib
import json
import os
import shutil
import subprocess
import tarfile
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SKIP = {".git", "dist", "__pycache__", "runs"}


def build_package(dest, version):
    pkg = Path(dest) / f"durweg-{version}.tar.gz"
    with tarfile.open(pkg, "w:gz") as tar:
        for p in sorted(ROOT.rglob("*")):
            rel = p.relative_to(ROOT)
            if any(part in SKIP for part in rel.parts) or p.suffix == ".pyc":
                continue
            tar.add(p, arcname=f"durweg-{version}/{rel.as_posix()}", recursive=False)
    sha = hashlib.sha256(pkg.read_bytes()).hexdigest()
    (pkg.parent / (pkg.name + ".sha256")).write_text(f"{sha}  {pkg.name}\n")
    return pkg, sha


@unittest.skipIf(os.name == "nt" or shutil.which("bash") is None, "install.sh: Linux and macOS")
class Install(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="durweg install "))     # a space in every path
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.home = self.tmp / "家 home"
        self.home.mkdir()
        self.pkg, self.sha = build_package(self.tmp, "v9.0.0")

    def install(self, version="v9.0.0", pkg=None, **env):
        e = {"HOME": str(self.home), "PATH": "/usr/bin:/bin", "SHELL": "/bin/bash",
             "DURWEG_VERSION": version, "DURWEG_SOURCE": str(pkg or self.pkg), "DURWEG_NO_START": "1",
             "DURWEG_AGENT": "skip"}
        e.update(env)
        return subprocess.run(["bash", str(ROOT / "install.sh")], capture_output=True, text=True, env=e,
                              stdin=subprocess.DEVNULL, timeout=120)

    def durweg(self, *args):
        return subprocess.run([str(self.home / ".local/bin/durweg"), *map(str, args)], capture_output=True,
                              text=True, env={"HOME": str(self.home), "PATH": "/usr/bin:/bin"})

    def test_fresh_install_and_rerun(self):
        r = self.install(DURWEG_LANG="zh")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("Durweg 装好了", r.stdout)
        self.assertEqual(self.durweg("--version").returncode, 0)
        self.assertEqual(json.loads((self.home / "Durweg/config.json").read_text())["language"], "zh")
        m = json.loads((self.home / "Durweg/.install.json").read_text())
        self.assertEqual(m["sha256"], self.sha)
        lib = self.durweg("library", "list").stdout
        self.assertIn("write-your-method", lib)
        self.assertIn("/durweg/current/examples/write-your-method", lib)      # follows updates
        again = self.install()                                                 # remembers the language
        self.assertEqual(again.returncode, 0, again.stdout)
        self.assertIn("装好了", again.stdout)
        self.assertEqual((self.home / ".bashrc").read_text().count("# added by Durweg"), 1)

    def test_no_terminal_means_english(self):
        r = self.install()
        self.assertIn("no terminal to ask in: English", r.stdout)
        self.assertIn("Durweg is installed", r.stdout)

    def test_update_switches_and_old_runs_still_check(self):
        self.install()
        proj = self.tmp / "proj"
        proj.mkdir()
        start = subprocess.run([str(self.home / ".local/bin/durweg"), "start", "write-your-method", "a",
                                "--runs", str(proj / "runs")], capture_output=True, text=True,
                               env={"HOME": str(self.home), "PATH": "/usr/bin:/bin"})
        self.assertEqual(start.returncode, 0, start.stderr)
        (self.tmp / "v2").mkdir()
        pkg2, _ = build_package(self.tmp / "v2", "v9.1.0")
        r = self.install(version="v9.1.0", pkg=pkg2)
        self.assertEqual(r.returncode, 0, r.stdout)
        cur = os.readlink(self.home / ".local/share/durweg/current")
        self.assertTrue(cur.endswith("v9.1.0"), cur)
        run = next((proj / "runs").iterdir())
        st = self.durweg("status", run)
        self.assertEqual(st.returncode, 0, st.stderr)

    def test_damaged_download_keeps_the_current_version(self):
        self.install()
        before = os.readlink(self.home / ".local/share/durweg/current")
        r = self.install(version="v9.2.0", DURWEG_SHA256="0" * 64)
        self.assertEqual(r.returncode, 1)
        self.assertIn("damaged", r.stdout)
        self.assertEqual(os.readlink(self.home / ".local/share/durweg/current"), before)
        self.assertEqual(self.durweg("--version").returncode, 0)

    def test_foreign_command_and_skill_are_kept(self):
        (self.home / ".local/bin").mkdir(parents=True)
        (self.home / ".local/bin/durweg").write_text("#!/bin/sh\necho other\n")
        r = self.install()
        self.assertEqual(r.returncode, 1)
        self.assertIn("belongs to another program", r.stdout)
        (self.home / ".local/bin/durweg").unlink()
        own = self.home / ".claude/skills/write-your-method"
        own.mkdir(parents=True)
        (own / "SKILL.md").write_text("mine\n")
        r = self.install()
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertIn("not Durweg's", r.stdout)
        self.assertEqual((own / "SKILL.md").read_text(), "mine\n")
        self.assertTrue((self.home / ".claude/skills/run-workflow").is_symlink())

    def test_uninstall_removes_only_ours(self):
        own = self.home / ".claude/skills/mine"
        own.mkdir(parents=True)
        self.install()
        (self.home / "Durweg/workflows/my-method").mkdir()
        out = self.durweg("uninstall").stdout
        self.assertIn("kept", out)
        self.assertFalse((self.home / ".local/bin/durweg").exists())
        self.assertFalse((self.home / ".claude/skills/run-workflow").exists())
        self.assertFalse((self.home / ".local/share/durweg").exists())
        self.assertNotIn("# added by Durweg", (self.home / ".bashrc").read_text())
        self.assertTrue(own.is_dir())
        self.assertTrue((self.home / "Durweg/config.json").is_file())
        self.assertTrue((self.home / "Durweg/workflows/my-method").is_dir())


if __name__ == "__main__":
    unittest.main()
