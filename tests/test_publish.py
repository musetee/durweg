"""Plan v1.1 D5, C7, C8, U3, revision 3: durweg publish, with a fake gh and local bare repositories."""

import json
import os
import subprocess
import sys
import unittest
from pathlib import Path

from helpers import EXAMPLE, ROOT, WfCase, git
import shutil


class PublishCase(WfCase):
    def setUp(self):
        super().setUp()
        self.ghdir = self.tmp / "github"
        self.ghdir.mkdir()
        self.state = self.tmp / "gh.json"
        self.set_state({"login": "tester", "repos": {}, "prs": []})
        bindir = self.tmp / "fakebin"
        bindir.mkdir()
        fake = ROOT / "tests" / "fake_gh.py"
        if os.name == "nt":
            (bindir / "gh.cmd").write_text(f'@"{sys.executable}" "{fake}" %*\r\n')
        else:
            (bindir / "gh").write_text(f'#!/bin/sh\nexec "{sys.executable}" "{fake}" "$@"\n')
            (bindir / "gh").chmod(0o755)
        self._env = {k: os.environ.get(k) for k in ("PATH", "DURWEG_FAKE_GH", "DURWEG_FAKE_GH_DIR")}
        os.environ["PATH"] = str(bindir) + os.pathsep + os.environ["PATH"]
        os.environ["DURWEG_FAKE_GH"] = str(self.state)
        os.environ["DURWEG_FAKE_GH_DIR"] = str(self.ghdir)
        # the workflow is the user's own folder, with things around it that must never be published
        (self.repo / "notes-private.txt").write_text("my private notes")
        (self.repo / "runs").mkdir()
        (self.repo / "runs" / "r.txt").write_text("a run")
        self.wf("library", "add", self.repo)                       # name: mini

    def tearDown(self):
        for k, v in self._env.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
        super().tearDown()

    def set_state(self, st):
        self.state.write_text(json.dumps(st))

    def gh_state(self):
        return json.loads(self.state.read_text())

    def files_in(self, repo):
        url = self.gh_state()["repos"][repo]["url"]
        out = subprocess.run(["git", "--git-dir", url, "ls-tree", "-r", "--name-only", "main"],
                             capture_output=True, text=True).stdout
        return sorted(out.split())

    def show_in(self, repo, path):
        url = self.gh_state()["repos"][repo]["url"]
        return subprocess.run(["git", "--git-dir", url, "show", f"main:{path}"], capture_output=True,
                              text=True, encoding="utf-8").stdout

    def catalogs(self):
        return json.loads((Path(os.environ["DURWEG_HOME"]) / "catalogs.json").read_text())

    def home(self):
        return Path(os.environ["DURWEG_HOME"])


class Publish(PublishCase):
    def test_dry_run_shows_files_and_questions_and_touches_nothing(self):
        out = self.wf("publish", "mini")
        self.assertIn("workflow.json", out)
        self.assertIn("skills/mini/SKILL.md", out)
        self.assertIn("README.md  (written by Durweg)", out)
        self.assertIn("public or private?", out)
        self.assertIn("which license?", out)
        self.assertNotIn("notes-private", out)
        self.assertNotIn("runs/", out)
        self.assertIn("nothing was published yet", out)
        self.assertEqual(self.gh_state()["repos"], {})
        self.assertFalse((self.home() / "publish").exists())
        self.assertIn("answer first", self.wf("publish", "mini", "--yes", expect=1))

    def test_public_publish_exact_files_then_new_version(self):
        out = self.wf("publish", "mini", "--public", "--license", "MIT", "--catalog", "no")
        self.assertIn("create the public repository tester/durweg-mini", out)
        out = self.wf("publish", "mini", "--public", "--license", "MIT", "--catalog", "no", "--yes")
        self.assertIn("created tester/durweg-mini (public)", out)
        self.assertEqual(self.gh_state()["repos"]["tester/durweg-mini"]["visibility"], "PUBLIC")
        files = self.files_in("tester/durweg-mini")
        self.assertIn("workflow.json", files)
        self.assertIn("README.md", files)
        self.assertIn("LICENSE", files)
        self.assertFalse([f for f in files if "notes-private" in f or f.startswith("runs/") or ".durweg" in f], files)
        lic = self.show_in("tester/durweg-mini", "LICENSE")
        self.assertIn("tester", lic)
        self.assertNotIn("[year]", lic)
        lib = json.loads((self.home() / "library.json").read_text())["workflows"]["mini"]
        self.assertEqual(lib["source"], "folder")                    # C8: still your folder
        self.assertIn("durweg-mini", lib["published"])
        # change the folder and publish again: a new commit, the same repository, no new create
        (self.repo / "skills/mini/SKILL.md").write_text("better\n")
        out = self.wf("publish", "mini", "--license", "MIT", "--catalog", "no", "--yes")
        self.assertIn("pushed a new version", out)
        self.assertEqual(self.show_in("tester/durweg-mini", "skills/mini/SKILL.md"), "better\n")
        creates = [c for c in self.gh_state()["calls"] if c[:2] == ["repo", "create"]]
        self.assertEqual(len(creates), 1)

    def test_case_only_when_named_and_dropped_when_not(self):
        cases = self.home() / "cases"
        cases.mkdir(parents=True)
        (cases / "mini_r1.html").write_text("<html>case</html>")
        self.wf("publish", "mini", "--public", "--license", "none", "--catalog", "no", "--case", cases / "mini_r1.html", "--yes")
        self.assertIn("case/mini_r1.html", self.files_in("tester/durweg-mini"))
        self.assertNotIn("LICENSE", self.files_in("tester/durweg-mini"))
        self.wf("publish", "mini", "--license", "none", "--catalog", "no", "--yes")
        self.assertNotIn("case/mini_r1.html", self.files_in("tester/durweg-mini"))
        other = self.tmp / "elsewhere.html"
        other.write_text("x")
        self.assertIn("--case is a page in", self.wf("publish", "mini", "--case", other, expect=1))

    def test_someone_elses_repository_is_never_pushed_to(self):
        st = self.gh_state()
        subprocess.run(["git", "init", "-q", "--bare", str(self.ghdir / "x.git")], check=True)
        st["repos"]["tester/durweg-mini"] = {"visibility": "PUBLIC", "viewerPermission": "ADMIN",
                                            "url": str(self.ghdir / "x.git")}
        self.set_state(st)
        out = self.wf("publish", "mini", "--public", "--license", "MIT", "--catalog", "no", "--yes", expect=1)
        self.assertIn("exists on GitHub already and was not made by `durweg publish`", out)
        self.assertEqual(self.files_in("tester/durweg-mini"), [])

    def test_failed_push_is_finished_by_a_rerun_without_a_second_create(self):
        from durweg import gitops
        real = gitops.run

        def run(args, *a, **kw):
            if args[:2] == ["push", "-q"] and not getattr(run, "done", False):
                run.done = True
                raise gitops.GitFailed("cannot connect (offline?)", "offline")
            return real(args, *a, **kw)
        gitops.run = run
        try:
            self.assertIn("cannot connect", self.wf("publish", "mini", "--private", "--license", "MIT",
                                                    "--catalog", "no", "--yes", expect=1))
        finally:
            gitops.run = real
        out = self.wf("publish", "mini", "--license", "MIT", "--catalog", "no", "--yes")
        self.assertIn("pushed", out)
        self.assertIn("workflow.json", self.files_in("tester/durweg-mini"))
        self.assertEqual(len([c for c in self.gh_state()["calls"] if c[:2] == ["repo", "create"]]), 1)

    def test_visibility_is_never_changed(self):
        self.wf("publish", "mini", "--public", "--license", "MIT", "--catalog", "no", "--yes")
        self.assertIn("does not change that", self.wf("publish", "mini", "--private", expect=1))
        st = self.gh_state()
        st["repos"]["tester/durweg-mini"]["visibility"] = "PRIVATE"         # changed on GitHub meanwhile
        self.set_state(st)
        self.assertIn("does not push to it", self.wf("publish", "mini", "--license", "MIT", "--catalog", "no", expect=1))

    def test_only_own_folders_and_gh_needed(self):
        bare = self.tmp / "other.git"
        subprocess.run(["git", "clone", "-q", "--bare", str(self.repo), str(bare)], check=True)
        self.wf("library", "add", bare, "--name", "theirs")
        self.assertIn("publish only workflows in your own folders", self.wf("publish", "theirs", expect=1))
        st = self.gh_state()
        st["login"] = None
        self.set_state(st)
        self.assertIn("gh auth login", self.wf("publish", "mini", expect=1))
        os.environ["PATH"] = str(self.tmp / "nowhere")
        try:
            self.assertIn("needs the GitHub command gh", self.wf("publish", "mini", expect=1))
        finally:
            os.environ["PATH"] = self._env["PATH"]


class PublicCatalogPR(PublishCase):
    def setUp(self):
        super().setUp()
        work = self.tmp / "catwork"
        work.mkdir()
        (work / "catalog.json").write_text(json.dumps({"format": 1, "workflows": {}}))
        git(work, "init", "-q", "-b", "main")
        git(work, "add", "-A")
        git(work, "commit", "-q", "-m", "c")
        up = self.ghdir / "musetee__durweg-workflows.git"
        subprocess.run(["git", "clone", "-q", "--bare", str(work), str(up)], check=True)
        st = self.gh_state()
        st["repos"]["musetee/durweg-workflows"] = {"visibility": "PUBLIC", "viewerPermission": "READ", "url": str(up)}
        self.set_state(st)
        os.environ["DURWEG_PUBLIC_CATALOG"] = "https://github.com/musetee/durweg-workflows.git"

    def test_pull_request_from_a_fork(self):
        out = self.wf("publish", "mini", "--public", "--license", "MIT")
        self.assertIn("propose it to the public catalog", out)
        out = self.wf("publish", "mini", "--public", "--license", "MIT", "--catalog", "yes", "--yes")
        self.assertIn("pull request to the public catalog", out)
        st = self.gh_state()
        self.assertEqual(st["prs"], [{"repo": "musetee/durweg-workflows", "head": "tester:add-mini", "title": "Add mini"}])
        cat = subprocess.run(["git", "--git-dir", st["repos"]["tester/durweg-workflows"]["url"], "show",
                              "add-mini:catalog.json"], capture_output=True, text=True).stdout
        self.assertIn("durweg-mini", json.loads(cat)["workflows"]["mini"]["url"])

    def test_no_license_no_public_catalog(self):
        out = self.wf("publish", "mini", "--public", "--license", "none", "--catalog", "yes", expect=1)
        self.assertIn("only workflows with a LICENSE", out)


class PrivateCatalog(PublishCase):
    def priv(self, *extra, expect=0):
        return self.wf("publish", "mini", "--private", "--license", "MIT", *extra, expect=expect)

    def test_first_private_publish_offers_a_private_catalog(self):
        self.assertIn("make a private catalog tester/durweg-workflows-private", self.priv())
        out = self.priv("--catalog", "yes", "--yes")
        self.assertIn("added mini to your private catalog private", out)
        st = self.gh_state()
        self.assertEqual(st["repos"]["tester/durweg-workflows-private"]["visibility"], "PRIVATE")
        c = self.catalogs()
        self.assertEqual(c["private_default"], "private")
        self.assertEqual(c["catalogs"]["private"]["repo"], "tester/durweg-workflows-private")
        self.assertIn("private:mini", self.wf("library", "available"))
        # another computer: add the private catalog, install by name (here: under another name)
        self.wf("library", "add", "private:mini", "--name", "mini-copy")

    def test_declined_is_remembered(self):
        self.priv("--catalog", "no", "--yes")
        self.assertTrue(self.catalogs()["private_declined"])
        (self.repo / "skills/mini/SKILL.md").write_text("v2\n")
        out = self.priv()
        self.assertNotIn("make a private catalog", out)
        self.assertIn("you chose no private catalog", out)
        self.priv("--yes")
        self.assertNotIn("tester/durweg-workflows-private", self.gh_state()["repos"])
        out = self.wf("catalog", "create-private")
        self.assertIn("would make the private repository", out)
        self.assertNotIn("tester/durweg-workflows-private", self.gh_state()["repos"])
        out = self.wf("catalog", "create-private", "--yes")
        self.assertIn("your private catalog is private", out)
        self.assertNotIn("private_declined", self.catalogs())

    def existing(self, visibility, permission):
        st = self.gh_state()
        subprocess.run(["git", "init", "-q", "--bare", "-b", "main", str(self.ghdir / "p.git")], check=True)
        st["repos"]["tester/durweg-workflows-private"] = {"visibility": visibility, "viewerPermission": permission,
                                                         "url": str(self.ghdir / "p.git")}
        self.set_state(st)

    def test_existing_public_repository_is_refused(self):
        self.existing("PUBLIC", "ADMIN")
        out = self.priv()
        self.assertIn("cannot be your private catalog: it is not private", out)
        self.assertNotIn("still to answer", out)
        out = self.priv("--yes")
        self.assertIn("created tester/durweg-mini (private)", out)          # the workflow still goes out
        self.assertNotIn("private_default", self.catalogs() if (self.home() / "catalogs.json").exists() else {})

    def test_existing_read_only_repository_is_refused(self):
        self.existing("PRIVATE", "READ")
        self.assertIn("you may not write to it", self.priv())

    def test_existing_private_repository_needs_a_yes(self):
        self.existing("PRIVATE", "ADMIN")
        work = self.tmp / "pw"
        work.mkdir()
        (work / "catalog.json").write_text(json.dumps({"format": 1, "workflows": {}}))
        git(work, "init", "-q", "-b", "main"); git(work, "add", "-A"); git(work, "commit", "-q", "-m", "c")
        git(work, "push", "-q", str(self.ghdir / "p.git"), "main")
        self.assertIn("use your existing private repository", self.priv())
        self.assertIn("added mini to your private catalog", self.priv("--catalog", "yes", "--yes"))

    def test_private_catalog_made_public_later_is_not_written(self):
        self.priv("--catalog", "yes", "--yes")
        st = self.gh_state()
        st["repos"]["tester/durweg-workflows-private"]["visibility"] = "PUBLIC"
        self.set_state(st)
        (self.repo / "skills/mini/SKILL.md").write_text("v2\n")
        out = self.priv("--yes")
        self.assertIn("pushed a new version", out)
        self.assertIn("not added to your private catalog private: it is not private", out)

    def test_added_catalog_is_never_a_write_target(self):
        work = self.tmp / "tw"
        work.mkdir()
        (work / "catalog.json").write_text(json.dumps({"format": 1, "workflows": {}}))
        git(work, "init", "-q", "-b", "main"); git(work, "add", "-A"); git(work, "commit", "-q", "-m", "c")
        team = self.tmp / "team.git"
        subprocess.run(["git", "clone", "-q", "--bare", str(work), str(team)], check=True)
        self.wf("catalog", "add", "team", team)
        self.assertIn("make a private catalog", self.priv())             # not "added to team"
        self.assertNotIn("private_default", self.catalogs())


class ReviewRegressions3(PublishCase):
    """agy V11-C-011, 012, 013."""

    def private_repo(self, files):
        work = self.tmp / "pw"
        work.mkdir()
        for k, v in files.items():
            (work / k).write_text(v)
        git(work, "init", "-q", "-b", "main"); git(work, "add", "-A"); git(work, "commit", "-q", "-m", "c")
        bare = self.ghdir / "tester__durweg-workflows-private.git"
        subprocess.run(["git", "clone", "-q", "--bare", str(work), str(bare)], check=True)
        st = self.gh_state()
        st["repos"]["tester/durweg-workflows-private"] = {"visibility": "PRIVATE", "viewerPermission": "ADMIN",
                                                         "url": str(bare)}
        self.set_state(st)
        return bare

    def tree(self, bare):
        return sorted(subprocess.run(["git", "--git-dir", str(bare), "ls-tree", "-r", "--name-only", "main"],
                                     capture_output=True, text=True).stdout.split())

    def test_c011_existing_repository_without_catalog_is_not_used_or_written(self):
        bare = self.private_repo({"notes.txt": "mine"})
        out = self.wf("publish", "mini", "--private", "--license", "MIT")
        self.assertIn("cannot be your private catalog: it holds no valid catalog.json", out)
        self.assertNotIn("still to answer", out)
        self.wf("publish", "mini", "--private", "--license", "MIT", "--catalog", "yes", "--yes")
        self.assertEqual(self.tree(bare), ["notes.txt"])                    # never written to
        self.assertNotIn("private_default", self.catalogs() if (self.home() / "catalogs.json").exists() else {})
        self.assertIn("cannot be your private catalog", self.wf("catalog", "create-private", "--yes", expect=1))

    def test_c011_broken_catalog_json_is_refused_without_a_traceback(self):
        bare = self.private_repo({"catalog.json": "{not valid json"})
        out = self.wf("publish", "mini", "--private", "--license", "MIT", "--catalog", "yes", "--yes")
        self.assertNotIn("Traceback", out)
        self.assertIn("no valid catalog.json", out)
        self.assertNotIn("private_default", self.catalogs() if (self.home() / "catalogs.json").exists() else {})
        self.assertEqual(self.tree(bare), ["catalog.json"])

    def test_c011_create_private_adopts_an_existing_one_only_with_yes(self):
        self.private_repo({"catalog.json": json.dumps({"format": 1, "workflows": {}})})
        out = self.wf("catalog", "create-private")
        self.assertIn("would use your existing private repository", out)
        self.assertFalse((self.home() / "catalogs.json").exists() and "private_default" in self.catalogs())
        self.assertIn("your private catalog is private", self.wf("catalog", "create-private", "--yes"))
        self.assertEqual(self.catalogs()["private_default"], "private")

    def upstream(self):
        work = self.tmp / "catwork"
        work.mkdir()
        (work / "catalog.json").write_text(json.dumps({"format": 1, "workflows": {}}))
        git(work, "init", "-q", "-b", "main"); git(work, "add", "-A"); git(work, "commit", "-q", "-m", "c")
        up = self.ghdir / "musetee__durweg-workflows.git"
        subprocess.run(["git", "clone", "-q", "--bare", str(work), str(up)], check=True)
        st = self.gh_state()
        st["repos"]["musetee/durweg-workflows"] = {"visibility": "PUBLIC", "viewerPermission": "READ", "url": str(up)}
        self.set_state(st)
        os.environ["DURWEG_PUBLIC_CATALOG"] = "https://github.com/musetee/durweg-workflows.git"
        return work, up

    def test_c012_pull_request_starts_from_the_newest_catalog_and_reruns_update_it(self):
        work, up = self.upstream()
        pub = ("--public", "--license", "MIT", "--catalog", "yes", "--yes")
        self.wf("publish", "mini", *pub)                                 # makes the fork
        cat = json.loads((work / "catalog.json").read_text())             # the owner merges another one
        cat["workflows"]["other"] = {"title": "o", "summary": "o", "url": "https://github.com/x/y.git"}
        (work / "catalog.json").write_text(json.dumps(cat))
        git(work, "commit", "-q", "-am", "other"); git(work, "push", "-q", str(up), "main")
        copy = self.tmp / "mini2"
        shutil.copytree(EXAMPLE, copy)
        self.wf("library", "add", copy, "--name", "mini2")
        self.wf("publish", "mini2", *pub)
        fork = self.gh_state()["repos"]["tester/durweg-workflows"]["url"]
        shown = subprocess.run(["git", "--git-dir", fork, "show", "add-mini2:catalog.json"],
                               capture_output=True, text=True).stdout
        self.assertEqual(sorted(json.loads(shown)["workflows"]), ["mini2", "other"])
        out = self.wf("publish", "mini", *pub)                            # again: the branch is replaced
        self.assertIn("updated the open pull request", out)
        self.assertNotIn("did not work", out)

    @unittest.skipIf(os.name == "nt", "the executable bit is a POSIX file mode")
    def test_c013_scripts_stay_executable(self):
        script = self.repo / "skills" / "mini" / "check.sh"
        script.write_text("#!/bin/sh\nexit 0\n")
        script.chmod(0o755)
        self.wf("publish", "mini", "--public", "--license", "MIT", "--catalog", "no", "--yes")
        url = self.gh_state()["repos"]["tester/durweg-mini"]["url"]
        line = subprocess.run(["git", "--git-dir", url, "ls-tree", "main", "skills/mini/check.sh"],
                              capture_output=True, text=True).stdout
        self.assertTrue(line.startswith("100755"), line)

    def test_c013_readme_md_even_when_only_readme_cn_exists(self):
        (self.repo / "README_cn.md").write_text("中文说明\n", encoding="utf-8")
        self.wf("publish", "mini", "--public", "--license", "MIT", "--catalog", "no", "--yes")
        files = self.files_in("tester/durweg-mini")
        self.assertIn("README.md", files)
        self.assertIn("README_cn.md", files)
