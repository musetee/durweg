"""Plan v1.1 C1 / C6: catalogs, install by name, the order in which `library add` reads its argument."""

import json
import os
import shutil
import subprocess
import unittest
from pathlib import Path

from helpers import EXAMPLE, WfCase, git


def bare(src_dir, dest):
    """Commit src_dir and make a bare repository dest (a fake remote)."""
    git(src_dir, "init", "-q", "-b", "main")
    git(src_dir, "add", "-A")
    git(src_dir, "commit", "-q", "-m", "init")
    subprocess.run(["git", "clone", "-q", "--bare", str(src_dir), str(dest)], check=True, capture_output=True)
    return dest


class CatalogCase(WfCase):
    def setUp(self):
        super().setUp()
        self.remotes = self.tmp / "remotes"
        self.remotes.mkdir()
        work = self.tmp / "work-mini"
        shutil.copytree(EXAMPLE, work)
        self.mini_url = str(bare(work, self.remotes / "mini.git"))
        self.pub_url = self.catalog("pub", {"mini": {"title": "Mini", "summary": "a tiny example", "url": self.mini_url}})
        os.environ["DURWEG_PUBLIC_CATALOG"] = self.pub_url
        self.cwd = os.getcwd()
        self.here = self.tmp / "here"
        self.here.mkdir()
        os.chdir(self.here)

    def tearDown(self):
        os.chdir(self.cwd)
        super().tearDown()

    def catalog(self, name, workflows):
        work = self.tmp / f"work-cat-{name}"
        work.mkdir()
        (work / "catalog.json").write_text(json.dumps({"format": 1, "workflows": workflows}))
        return str(bare(work, self.remotes / f"{name}.git"))

    def lib(self):
        return json.loads((Path(os.environ["DURWEG_HOME"]) / "library.json").read_text(encoding="utf-8"))["workflows"]


class Available(CatalogCase):
    def test_lists_public_entries_and_marks_installed(self):
        out = self.wf("library", "available")
        self.assertIn("public:mini", out)
        self.assertIn("a tiny example", out)
        self.assertNotIn("(installed)", out)
        self.wf("library", "add", "mini")
        self.assertIn("(installed)", self.wf("library", "available"))

    def test_offline_shows_the_cache_with_its_date(self):
        self.wf("library", "available")
        shutil.rmtree(self.pub_url)                                  # the remote is gone
        out = self.wf("library", "available")
        self.assertIn("public:mini", out)
        self.assertIn("could not be refreshed", out)
        self.assertIn("showing the copy from", out)

    def test_never_downloaded_and_unreachable(self):
        os.environ["DURWEG_PUBLIC_CATALOG"] = str(self.tmp / "nothing.git")
        out = self.wf("library", "available")
        self.assertIn("catalog public is not available", out)
        self.assertIn("no workflows to show", out)

    def test_invalid_entries_are_skipped(self):
        url = self.catalog("bad", {"ok": {"url": self.mini_url}, "Bad Name": {"url": "x"}, "nourl": {}})
        self.wf("catalog", "add", "bad", url)
        out = self.wf("library", "available")
        self.assertIn("bad:ok", out)
        self.assertIn("skipped invalid entries", out)


class AddByName(CatalogCase):
    def test_name_installs_from_the_catalog_and_runs(self):
        out = self.wf("library", "add", "mini")
        self.assertIn("added mini", out)
        e = self.lib()["mini"]
        self.assertEqual((e["source"], e["catalog"], e["branch"]), ("git", "public", "main"))
        self.assertEqual(len(e["commit"]), 40)
        self.assertTrue(Path(e["path"]).samefile(Path(os.environ["DURWEG_HOME"]) / "workflows" / "mini"))
        self.wf("start", "mini", "cat", "--runs", self.runs)
        self.run = next(self.runs.glob("*_cat"))
        self.full()
        self.assertEqual(self.check()[0], 0)

    def test_qualified_name(self):
        self.assertIn("added mini", self.wf("library", "add", "public:mini"))
        self.assertIn("no workflow nosuch in catalog public", self.wf("library", "add", "public:nosuch", expect=1))
        self.assertIn("no catalog named team", self.wf("library", "add", "team:mini", expect=1))

    def test_same_name_folder_here_is_refused_then_dot_slash_is_the_folder(self):
        shutil.copytree(EXAMPLE, self.here / "mini")
        out = self.wf("library", "add", "mini", expect=1)
        self.assertIn("./mini", out)
        self.assertIn("public:mini", out)
        self.assertNotIn("mini", self.lib() if (Path(os.environ["DURWEG_HOME"]) / "library.json").exists() else {})
        self.wf("library", "add", "./mini")
        self.assertEqual(self.lib()["mini"]["source"], "folder")

    def test_word_that_is_only_a_folder_stays_a_folder(self):
        shutil.copytree(EXAMPLE, self.here / "solo")
        self.wf("library", "add", "solo", "--name", "solo")
        self.assertEqual(self.lib()["solo"]["source"], "folder")

    def test_relative_path_with_slash_is_a_folder_not_a_catalog(self):
        shutil.copytree(EXAMPLE, self.here / "public" / "mini")
        self.wf("library", "add", "public/mini", "--name", "rel")
        self.assertEqual(self.lib()["rel"]["source"], "folder")

    def test_drive_path_is_never_a_catalog_name(self):
        out = self.wf("library", "add", "C:\\x", expect=1)
        self.assertIn("is not a folder", out)

    def test_two_catalogs_with_the_same_name(self):
        team = self.catalog("team", {"mini": {"title": "Mini", "summary": "team copy", "url": self.mini_url}})
        self.wf("catalog", "add", "team", team)
        out = self.wf("library", "add", "mini", expect=1)
        self.assertIn("public:mini", out)
        self.assertIn("team:mini", out)
        self.wf("library", "add", "team:mini")
        self.assertEqual(self.lib()["mini"]["catalog"], "team")

    def test_installed_name_taken_needs_name(self):
        self.wf("library", "add", self.repo)                         # the folder mini is "mini" already
        self.assertIn("choose another with --name", self.wf("library", "add", "public:mini", expect=1))
        self.assertFalse((Path(os.environ["DURWEG_HOME"]) / "workflows" / "mini").exists())
        self.wf("library", "add", "public:mini", "--name", "mini2")
        self.assertEqual(self.lib()["mini2"]["catalog"], "public")

    def test_unknown_word(self):
        out = self.wf("library", "add", "nosuch", expect=1)
        self.assertIn("durweg library available", out)

    def test_invalid_workflow_leaves_nothing_behind(self):
        work = self.tmp / "work-broken"
        work.mkdir()
        (work / "workflow.json").write_text("{}")
        url = str(bare(work, self.remotes / "broken.git"))
        self.wf("catalog", "add", "team", self.catalog("team", {"broken": {"url": url}}))
        self.wf("library", "add", "broken", expect=2)
        self.assertFalse((Path(os.environ["DURWEG_HOME"]) / "workflows" / "broken").exists())

    def test_v10_library_file_still_works(self):
        home = Path(os.environ["DURWEG_HOME"])
        home.mkdir(parents=True, exist_ok=True)
        (home / "library.json").write_text(json.dumps({"format": 1, "workflows": {
            "old": {"path": str(self.repo), "source": "folder", "added": "2026-10-31T10:00:00+01:00"}}}))
        self.assertIn("old", self.wf("library", "list"))
        self.wf("library", "add", "mini", "--name", "new")
        self.assertEqual(set(self.lib()), {"old", "new"})


class Catalogs(CatalogCase):
    def test_public_can_be_switched_off_and_on_but_not_removed(self):
        self.assertIn("switched off", self.wf("catalog", "remove", "public"))
        self.assertIn("public           off", self.wf("catalog", "list"))
        self.assertIn("no catalog is switched on", self.wf("library", "available"))
        self.assertIn("switched off", self.wf("library", "add", "public:mini", expect=1))
        self.wf("catalog", "add", "public")
        self.assertIn("public:mini", self.wf("library", "available"))

    def test_add_list_remove_other(self):
        team = self.catalog("team", {"mini": {"url": self.mini_url}})
        self.wf("catalog", "add", "team", team)
        self.assertIn("a catalog named team exists", self.wf("catalog", "add", "team", team, expect=1))
        self.assertIn("team             on", self.wf("catalog", "list"))
        self.wf("library", "add", "team:mini", "--name", "tm")
        self.wf("catalog", "remove", "team")
        self.assertFalse((Path(os.environ["DURWEG_HOME"]) / "catalogs" / "team").exists())
        self.assertIn("tm", self.lib())                                 # installed workflows stay

    def test_bad_names_and_addresses(self):
        self.assertIn("at least 2", self.wf("catalog", "add", "c", "x.git", expect=1))
        self.assertIn("kept for the public catalog", self.wf("catalog", "add", "public", "other.git", expect=1))
        self.assertIn("not a git address", self.wf("catalog", "add", "team", "some/folder", expect=1))
        self.assertIn("needs a name", self.wf("catalog", "add", expect=1))

    def test_unreachable_catalog_is_not_added_and_never_prompts(self):
        out = self.wf("catalog", "add", "team", "https://user:secret@127.0.0.1:9/x.git", expect=1)
        self.assertIn("was not added", out)
        self.assertNotIn("secret", out)
        self.assertNotIn("team", self.wf("catalog", "list"))

    def test_wrong_format_is_refused(self):
        work = self.tmp / "work-wrong"
        work.mkdir()
        (work / "catalog.json").write_text(json.dumps({"workflows": []}))
        url = str(bare(work, self.remotes / "wrong.git"))
        self.assertIn("not format 1", self.wf("catalog", "add", "wrong", url, expect=1))


class GitReasons(unittest.TestCase):
    def test_reasons_and_redaction(self):
        from durweg import gitops
        self.assertEqual(gitops.redact("fatal: https://u:tok@github.com/a/b"), "fatal: https://github.com/a/b")
        r, k = gitops._reason("fatal: could not read Username for 'https://github.com'", "https://github.com/a/b")
        self.assertEqual(k, "auth")
        self.assertIn("gh auth setup-git", r)
        r, k = gitops._reason("remote: Repository not found.", "git@gitlab.example:a/b.git")
        self.assertEqual(k, "auth")
        self.assertIn("this host", r)
        self.assertEqual(gitops._reason("Could not resolve host: github.com", "")[1], "offline")
        self.assertEqual(gitops._reason("something odd", "")[1], "other")
        e = gitops.env()
        self.assertEqual((e["GIT_TERMINAL_PROMPT"], e["GCM_INTERACTIVE"]), ("0", "never"))


if __name__ == "__main__":
    unittest.main()
