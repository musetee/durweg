"""install.sh (Linux, macOS, WSL) and durweg uninstall, in a sandbox HOME with a package built from
this working tree (plan 2.1, V1-R-002). No network: DURWEG_SOURCE points at the local package."""

import hashlib
import json
import re
import os
import shutil
import subprocess
import tarfile
import tempfile
import time
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
             "DURWEG_AGENT": "skip", "DURWEG_PUBLIC_CATALOG": str(self.tmp / "no-catalog.git")}
        e.update(env)
        return subprocess.run(["bash", str(ROOT / "install.sh")], capture_output=True, text=True, env=e,
                              stdin=subprocess.DEVNULL, timeout=120)

    def fake_agent(self, name="claude", works=True):
        b = self.home / ".local/bin"
        b.mkdir(parents=True, exist_ok=True)
        f = b / name
        f.write_text("#!/bin/sh\n" + ("echo 9.9 fake\n" if works else "exit 1\n"))
        f.chmod(0o755)

    def manifest(self):
        return json.loads((self.home / "Durweg/.install.json").read_text(encoding="utf-8"))

    def durweg(self, *args, **env):
        e = {"HOME": str(self.home), "PATH": "/usr/bin:/bin", "DURWEG_PUBLIC_CATALOG": str(self.tmp / "no-catalog.git")}
        e.update(env)
        return subprocess.run([str(self.home / ".local/bin/durweg"), *map(str, args)], capture_output=True,
                              text=True, env=e, stdin=subprocess.DEVNULL, timeout=300)

    # -- durweg update (plan v1.1 C5, U1) --------------------------------------------------------
    def package(self, version):
        folder = self.tmp / version
        folder.mkdir()
        return build_package(folder, version)[0]

    def update(self, latest, pkg=None, **env):
        e = {"DURWEG_UPDATE_LATEST": latest, "DURWEG_UPDATE_INSTALLER": str(ROOT / "install.sh")}
        if pkg:
            e["DURWEG_SOURCE"] = str(pkg)
        e.update(env)
        return self.durweg("update", **e)

    def test_durweg_update_to_a_newer_release_keeps_the_choices(self):
        self.assertEqual(self.install(DURWEG_LANG="zh").returncode, 0)
        pkg2 = self.package("v9.1.0")
        r = self.update("v9.1.0", pkg2)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertRegex(r.stdout, r"Durweg +updated +v9\.0\.0 -> v9\.1\.0")
        self.assertEqual(self.manifest()["version"], "v9.1.0")
        data = self.home / ".local/share/durweg"
        self.assertEqual(os.readlink(data / "current"), str(data / "v9.1.0"))
        self.assertEqual(json.loads((self.home / "Durweg/config.json").read_text(encoding="utf-8"))["language"], "zh")
        self.assertIn("summary:", r.stdout)                         # the library was updated afterwards
        self.assertEqual(r.stdout.count("summary:"), 1)             # once, not again inside the installer
        self.assertNotIn("Durweg 装好了", r.stdout)                  # the installer's own output stays inside
        r = self.update("v9.1.0")
        self.assertRegex(r.stdout, r"Durweg +unchanged +v9\.1\.0 is the newest")
        r = self.update("v9.0.5")
        self.assertIn("unchanged", r.stdout)                        # never downgrades

    def test_durweg_update_failure_keeps_the_version(self):
        self.assertEqual(self.install().returncode, 0)
        pkg2 = self.package("v9.1.0")
        r = self.update("v9.1.0", pkg2, DURWEG_SHA256="0" * 64)
        self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
        self.assertRegex(r.stdout, r"Durweg +failed .*sha256.*v9\.0\.0 is kept")
        self.assertEqual(self.manifest()["version"], "v9.0.0")
        self.assertEqual(self.durweg("--version").returncode, 0)

    def test_durweg_update_offline_is_skipped(self):
        self.assertEqual(self.install().returncode, 0)
        r = self.durweg("update", DURWEG_UPDATE_RELEASES="http://127.0.0.1:9/latest")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertRegex(r.stdout, r"Durweg +skipped +cannot ask GitHub")
        self.assertIn("summary:", r.stdout)

    def test_rerun_updates_git_workflows_quietly(self):
        self.assertEqual(self.install().returncode, 0)
        r = self.install()
        self.assertNotIn("summary:", r.stdout)                     # only the example (a folder): nothing to say
        work = self.tmp / "wf"
        shutil.copytree(ROOT / "examples" / "mini", work)
        g = lambda *a: subprocess.run(["git", "-C", str(work), *a], check=True, capture_output=True,
                                      env={"PATH": "/usr/bin:/bin", "HOME": str(self.home), "GIT_AUTHOR_NAME": "t",
                                           "GIT_AUTHOR_EMAIL": "t@t", "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@t"})
        g("init", "-q", "-b", "main"); g("add", "-A"); g("commit", "-q", "-m", "v1")
        bare = self.tmp / "mini.git"
        subprocess.run(["git", "clone", "-q", "--bare", str(work), str(bare)], check=True, capture_output=True)
        self.assertEqual(self.durweg("library", "add", bare).returncode, 0)
        (work / "skills/mini/SKILL.md").write_text("changed\n")
        g("commit", "-q", "-am", "v2"); g("push", "-q", str(bare), "main")
        r = self.install()
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertRegex(r.stdout, r"mini +updated")

    def test_fresh_install_and_rerun(self):
        r = self.install(DURWEG_LANG="zh")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("Durweg 装好了", r.stdout)
        self.assertEqual(self.durweg("--version").returncode, 0)
        self.assertEqual(json.loads((self.home / "Durweg/config.json").read_text(encoding="utf-8"))["language"], "zh")
        m = json.loads((self.home / "Durweg/.install.json").read_text(encoding="utf-8"))
        self.assertEqual(m["sha256"], self.sha)
        lib = self.durweg("library", "list").stdout
        self.assertIn("write-your-method", lib)
        self.assertIn("/durweg/current/examples/write-your-method", lib)      # follows updates
        again = self.install()                                                 # remembers the language
        self.assertEqual(again.returncode, 0, again.stdout)
        self.assertIn("装好了", again.stdout)
        self.assertEqual((self.home / ".bashrc").read_text(encoding="utf-8").count("# added by Durweg"), 1)

    def test_guide_opens_in_the_browser(self):
        seen = self.tmp / "opened"
        opener = self.tmp / "opener"
        opener.write_text(f'#!/bin/sh\nprintf "%s" "$1" > "{seen}"\n')
        opener.chmod(0o755)
        r = self.install(DURWEG_LANG="zh", DURWEG_NO_START="", DURWEG_OPEN_CMD=str(opener),
                         DURWEG_GUIDE="https://example.org/durweg/")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("教程：https://example.org/durweg/README_cn.md", r.stdout)
        for _ in range(100):                     # the browser is opened in the background (V1-C-011)
            if seen.exists() and seen.read_text():
                break
            time.sleep(0.05)
        self.assertEqual(seen.read_text(), "https://example.org/durweg/README_cn.md")
        seen.unlink()
        r = self.install(DURWEG_LANG="en", DURWEG_OPEN_CMD=str(opener))       # DURWEG_NO_START: no browser
        self.assertIn("Guide: https://github.com/musetee/durweg/blob/v9.0.0/README.md", r.stdout)
        self.assertFalse(seen.exists())

    def test_slow_browser_does_not_hold_up_the_installer(self):          # V1-C-011
        seen = self.tmp / "opened"
        opener = self.tmp / "opener"
        opener.write_text(f'#!/bin/sh\nsleep 6\nprintf "%s" "$1" > "{seen}"\n')
        opener.chmod(0o755)
        import time
        t0 = time.monotonic()
        r = self.install(DURWEG_NO_START="", DURWEG_OPEN_CMD=str(opener))
        took = time.monotonic() - t0
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertLess(took, 5, "the installer waited for the browser")
        for _ in range(100):
            if seen.exists():
                break
            time.sleep(0.1)
        self.assertTrue(seen.exists(), "the guide was not opened in the background")

    def test_own_agent_gets_the_skills_and_is_not_started(self):        # tester report
        r = self.install(DURWEG_LANG="zh", DURWEG_AGENT="own")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        for d in (".claude/skills", ".codex/skills"):
            for s in ("run-workflow", "write-your-method"):
                self.assertTrue((self.home / d / s / "SKILL.md").is_file(), f"{d}/{s}")
        self.assertIn("照你平常的方式启动 agent", r.stdout)
        self.assertEqual(len(self.manifest()["skills"]), 4)
        u = self.durweg("uninstall")
        self.assertEqual(u.returncode, 0, u.stdout + u.stderr)
        self.assertFalse((self.home / ".codex/skills/run-workflow").exists())

    def test_antigravity_counts_and_gets_the_skills(self):
        self.fake_agent("agy")
        r = self.install(DURWEG_AGENT="")                  # agy runs: no question, nothing installed
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertNotIn("No AI agent found", r.stdout)
        for s in ("run-workflow", "write-your-method"):
            self.assertTrue((self.home / ".gemini/config/skills" / s / "SKILL.md").is_file(), s)
        u = self.durweg("uninstall")
        self.assertEqual(u.returncode, 0, u.stdout + u.stderr)
        self.assertFalse((self.home / ".gemini/config/skills/run-workflow").exists())

    def test_antigravity_settings_folder_alone_gets_the_skills(self):
        (self.home / ".gemini/antigravity-cli").mkdir(parents=True)  # agy started from its own place
        r = self.install()
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertTrue((self.home / ".gemini/config/skills/run-workflow/SKILL.md").is_file())
        self.assertFalse((self.home / ".claude/skills/run-workflow").exists())

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
        self.fake_agent()
        own = self.home / ".claude/skills/write-your-method"
        own.mkdir(parents=True)
        (own / "SKILL.md").write_text("mine\n")
        r = self.install()
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertIn("not Durweg's", r.stdout)
        self.assertEqual((own / "SKILL.md").read_text(encoding="utf-8"), "mine\n")
        self.assertTrue((self.home / ".claude/skills/run-workflow").is_symlink())

    def test_uninstall_removes_only_ours(self):
        self.fake_agent()
        own = self.home / ".claude/skills/mine"
        own.mkdir(parents=True)
        self.install()
        (self.home / "Durweg/workflows/my-method").mkdir()
        out = self.durweg("uninstall").stdout
        self.assertIn("kept", out)
        self.assertFalse((self.home / ".local/bin/durweg").exists())
        self.assertFalse(os.path.lexists(self.home / ".claude/skills/run-workflow"))
        self.assertFalse((self.home / ".local/share/durweg").exists())
        self.assertNotIn("# added by Durweg", (self.home / ".bashrc").read_text(encoding="utf-8"))
        self.assertTrue(own.is_dir())
        self.assertTrue((self.home / "Durweg/config.json").is_file())
        self.assertTrue((self.home / "Durweg/workflows/my-method").is_dir())


    # ---- V1-C regressions ----
    def test_paths_with_spaces_stay_whole_and_uninstall(self):        # V1-C-001
        self.fake_agent()
        self.assertEqual(self.install().returncode, 0)
        want = [str(self.home / ".claude/skills/run-workflow"), str(self.home / ".claude/skills/write-your-method")]
        self.assertEqual(self.manifest()["skills"], want)
        self.durweg("uninstall")
        for w in want:
            self.assertFalse(os.path.lexists(w), w)

    def test_rerun_keeps_the_path_record(self):                         # V1-C-002
        self.install()
        self.assertTrue(self.manifest()["path_lines"])
        r = self.install(PATH=f"{self.home}/.local/bin:/usr/bin:/bin")  # PATH now has it
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertTrue(self.manifest()["path_lines"])
        self.durweg("uninstall")
        self.assertNotIn("# added by Durweg", (self.home / ".bashrc").read_text(encoding="utf-8"))

    def test_rerun_repairs_a_damaged_same_version(self):                # V1-C-003
        self.install()
        bad = self.home / ".local/share/durweg/v9.0.0/durweg/__init__.py"
        bad.write_text("raise RuntimeError('damaged')\n")
        self.assertNotEqual(self.durweg("--version").returncode, 0)
        r = self.install()
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertEqual(self.durweg("--version").returncode, 0)

    def test_failed_switch_keeps_the_previous_copy(self):               # V1-C-006
        self.install()
        r = self.install(DURWEG_TEST_FAIL_SWITCH="1")
        self.assertEqual(r.returncode, 1, r.stdout)
        self.assertIn("previous version is kept", r.stdout)
        self.assertEqual(self.durweg("--version").returncode, 0)

    def test_settings_folder_alone_is_no_agent(self):                   # V1-C-004
        (self.home / ".claude").mkdir()
        r = self.install()
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertEqual(self.manifest()["skills"], [])
        self.assertFalse(os.path.lexists(self.home / ".claude/skills/run-workflow"))

    def test_agent_that_does_not_run_after_install(self):               # V1-C-004
        stub = self.tmp / "stubbin"
        stub.mkdir()
        (stub / "curl").write_text("#!/bin/sh\necho 'echo installed'\n")    # installer "succeeds", installs nothing
        (stub / "curl").chmod(0o755)
        r = self.install(DURWEG_AGENT="claude", PATH=f"{stub}:/usr/bin:/bin")
        self.assertEqual(r.returncode, 1, r.stdout)
        self.assertIn("does not run", r.stdout)

    def test_broken_agent_command_is_not_counted(self):
        self.fake_agent(works=False)
        r = self.install()
        self.assertEqual(self.manifest()["skills"], [])


if __name__ == "__main__":
    unittest.main()


class WindowsLauncher(unittest.TestCase):
    def test_every_wsl_call_skips_the_shell(self):
        """wsl.exe without -e hands its words to bash, which breaks on paths like Durweg(1)."""
        text = (ROOT / "Durweg-Install.bat").read_text(encoding="utf-8")
        calls = [l.strip() for l in text.splitlines() if re.search(r"&\s*wsl\.exe\b", l)]
        self.assertTrue(calls)
        for line in calls:
            self.assertRegex(line, r"&\s*wsl\.exe\s+-e\s", line)

