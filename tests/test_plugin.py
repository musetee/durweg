"""Durweg as the Claude Code plugin (plan durweg-dev 20261101_durweg-claude-plugin.md, 4.1–4.6)."""

import json
import os
import shutil
import subprocess
import sys
import tarfile
import tempfile
import unittest
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
EXAMPLE = "write-your-method"


class PluginCopy(unittest.TestCase):
    """A copy of the plugin (durweg/, bin/, examples/, skills/, .claude-plugin/) run as a
    subprocess with its own HOME and DURWEG_HOME, as Claude Code would run it from its cache."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="durweg-plugin-")).resolve()   # durweg records real paths (macOS /private, Windows long names)
        self.plugin = self.tmp / "cache" / "durweg" / "durweg" / "1.0.0"
        for part in ("durweg", "bin", "examples", "skills", ".claude-plugin"):
            shutil.copytree(ROOT / part, self.plugin / part,
                            ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
        self.home = self.tmp / "Durweg"
        self.fail_installer = self.tmp / "installer.sh"
        self.fail_installer.write_text("echo installer-was-run; exit 9\n")
        self.env = {k: v for k, v in os.environ.items() if k != "DURWEG_PLUGIN"}
        self.env.update(HOME=str(self.tmp / "home"), USERPROFILE=str(self.tmp / "home"),
                        DURWEG_HOME=str(self.home),
                        DURWEG_PUBLIC_CATALOG=str(self.tmp / "no-public-catalog.git"),
                        DURWEG_UPDATE_INSTALLER=str(self.fail_installer))

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def run_durweg(self, *args, plugin=None, cwd=None, expect=0):
        root = plugin or self.plugin
        r = subprocess.run([sys.executable, str(root / "bin" / "durweg"), *args], env=self.env,
                           cwd=str(cwd or self.tmp), capture_output=True, text=True, encoding="utf-8")
        if expect is not None:
            self.assertEqual(r.returncode, expect, f"durweg {' '.join(args)}\n{r.stdout}\n{r.stderr}")
        return r

    def library(self):
        return json.loads((self.home / "library.json").read_text(encoding="utf-8"))["workflows"]

    def example_path(self, plugin=None):
        return str((plugin or self.plugin) / "examples" / EXAMPLE)

    # 4.3 ---------------------------------------------------------------------------------------
    def test_first_run_makes_the_library_with_the_example(self):
        self.run_durweg("library", "list")
        e = self.library()[EXAMPLE]
        self.assertEqual(e["source"], "plugin-example")
        self.assertEqual(os.path.normpath(e["path"]), os.path.normpath(self.example_path()))

    def test_example_follows_the_plugin_folder_after_an_update(self):
        self.run_durweg("library", "list")
        newer = self.plugin.parent / "1.0.1"
        self.plugin.rename(newer)
        self.run_durweg("library", "list", plugin=newer)
        self.assertEqual(os.path.normpath(self.library()[EXAMPLE]["path"]),
                         os.path.normpath(self.example_path(newer)))

    def test_an_example_from_elsewhere_is_left_alone(self):
        self.home.mkdir(parents=True)
        own = {"path": str(self.tmp / "mine"), "source": "folder", "added": "x"}
        (self.home / "library.json").write_text(json.dumps({"format": 1, "workflows": {EXAMPLE: own}}))
        self.run_durweg("library", "list")
        self.assertEqual(self.library()[EXAMPLE], own)

    def test_a_removed_example_is_not_put_back(self):
        self.run_durweg("library", "list")
        self.run_durweg("library", "remove", EXAMPLE)
        self.run_durweg("library", "list")
        self.assertNotIn(EXAMPLE, self.library())

    def test_a_broken_library_is_reported_and_kept(self):
        self.home.mkdir(parents=True)
        (self.home / "library.json").write_text("{broken")
        r = self.run_durweg("config")
        self.assertIn("could not set up the example", r.stderr)
        self.assertEqual((self.home / "library.json").read_text(), "{broken")

    # 4.4 ---------------------------------------------------------------------------------------
    def test_update_leaves_durweg_to_claude_code_and_never_runs_the_installer(self):
        self.run_durweg("library", "list")
        (self.home / ".install.json").write_text(json.dumps({"version": "v1.0.0"}))   # both installs
        r = self.run_durweg("update")
        self.assertIn("/plugin update durweg", r.stdout)
        self.assertNotIn("installer-was-run", r.stdout + r.stderr)
        self.assertIn("comes with the Durweg plugin", r.stdout)
        self.assertNotIn("some were not updated", r.stderr)

    def test_the_example_cannot_be_published(self):
        self.run_durweg("library", "list")
        r = self.run_durweg("publish", EXAMPLE, expect=1)
        self.assertIn("comes with Durweg", r.stderr)
        self.assertNotIn("installed from git", r.stderr)

    # the example runs ----------------------------------------------------------------------------
    def test_the_example_starts(self):
        proj = self.tmp / "project"
        proj.mkdir()
        r = self.run_durweg("start", EXAMPLE, "first", cwd=proj)
        self.assertIn("ok run=", r.stdout)
        run = next((proj / "runs").iterdir())
        self.run_durweg("status", str(run), cwd=proj)

    # 4.5, 4.6 ------------------------------------------------------------------------------------
    def test_version_names_the_plugin_and_changes_nothing(self):
        r = self.run_durweg("--version")
        self.assertIn("(Claude Code plugin)", r.stdout)
        self.assertFalse(self.home.exists())

    def test_config_says_when_the_language_is_not_set(self):
        self.assertIn("not set yet", self.run_durweg("config").stdout)
        self.run_durweg("config", "language", "zh")
        out = self.run_durweg("config").stdout
        self.assertIn("language: zh", out)
        self.assertNotIn("not set yet", out)

    # 4.2 ---------------------------------------------------------------------------------------
    def test_without_claude_plugin_folder_it_is_not_the_plugin(self):
        shutil.rmtree(self.plugin / ".claude-plugin")
        self.assertNotIn("plugin", self.run_durweg("--version").stdout)
        self.run_durweg("config")
        self.assertFalse((self.home / "library.json").exists())

    def test_durweg_plugin_0_turns_it_off(self):
        self.env["DURWEG_PLUGIN"] = "0"
        self.assertNotIn("plugin", self.run_durweg("--version").stdout)


class ReleasePackage(unittest.TestCase):
    """The installer's packages never carry .claude-plugin (CP-R-001): git archive, as
    tools/build-release.sh makes them, and tools/package.py."""

    def test_git_archive_leaves_out_the_plugin(self):
        if shutil.which("git") is None or not (ROOT / ".git").exists():
            self.skipTest("needs the git checkout")
        tmp = Path(tempfile.mkdtemp(prefix="durweg-archive-"))
        try:
            repo = tmp / "repo"
            subprocess.run(["git", "clone", "-q", "--no-hardlinks", str(ROOT), str(repo)], check=True)
            # the working tree's .gitattributes and .claude-plugin, committed in the clone
            for name in (".gitattributes", ".claude-plugin"):
                src, dst = ROOT / name, repo / name
                if src.is_dir():
                    shutil.rmtree(dst, ignore_errors=True)
                    shutil.copytree(src, dst)
                else:
                    shutil.copy2(src, dst)
            env = dict(os.environ, GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@t",
                       GIT_COMMITTER_NAME="t", GIT_COMMITTER_EMAIL="t@t")
            subprocess.run(["git", "-C", str(repo), "add", "-A", ".gitattributes", ".claude-plugin"],
                           check=True, env=env)
            subprocess.run(["git", "-C", str(repo), "commit", "-q", "--allow-empty", "-m", "t"],
                           check=True, env=env)
            for fmt in ("tar.gz", "zip"):
                out = tmp / f"p.{fmt}"
                subprocess.run(["git", "-C", str(repo), "archive", f"--format={fmt}", "--prefix=d/",
                                "-o", str(out), "HEAD"], check=True)
                if fmt == "zip":
                    names = zipfile.ZipFile(out).namelist()
                else:
                    with tarfile.open(out) as t:
                        names = t.getnames()
                self.assertTrue(any(n.startswith("d/durweg/") for n in names))
                self.assertFalse([n for n in names if ".claude-plugin" in n or ".gitattributes" in n], fmt)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_package_py_leaves_out_the_plugin(self):
        sys.path.insert(0, str(ROOT / "tools"))
        try:
            import package
        finally:
            sys.path.pop(0)
        names = [rel for _, rel in package.files()]
        self.assertTrue(any(n.startswith("durweg/") for n in names))
        self.assertFalse([n for n in names if n.startswith(".claude-plugin") or n == ".gitattributes"])


class Manifests(unittest.TestCase):
    def test_plugin_and_marketplace_agree_with_the_version(self):
        from durweg import __version__
        pj = json.loads((ROOT / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8"))
        mj = json.loads((ROOT / ".claude-plugin" / "marketplace.json").read_text(encoding="utf-8"))
        self.assertEqual(pj["name"], "durweg")
        self.assertEqual(pj["version"], __version__)
        for d in pj["skills"]:
            self.assertTrue((ROOT / d).is_dir(), d)
        self.assertTrue(mj.get("description"))
        self.assertEqual([p["name"] for p in mj["plugins"]], ["durweg"])
        self.assertEqual(mj["plugins"][0]["source"], "./")


if __name__ == "__main__":
    unittest.main()
