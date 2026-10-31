"""Plan v1.1 C2-C4: durweg library update, and update vs start."""

import contextlib
import io
import json
import os
import threading
import time
from pathlib import Path

from helpers import git, main
from test_catalog import CatalogCase


class UpdateCase(CatalogCase):
    def setUp(self):
        super().setUp()
        self.wf("library", "add", "mini")
        self.dest = Path(os.environ["DURWEG_HOME"]) / "workflows" / "mini"
        self.work = self.tmp / "work-mini"

    def publish(self, rel="skills/mini/SKILL.md", text=None, msg="change"):
        """A new commit on the fake remote's main."""
        p = self.work / rel
        p.write_text(text if text is not None else p.read_text(encoding="utf-8") + "\nmore\n", encoding="utf-8")
        git(self.work, "commit", "-q", "-am", msg)
        git(self.work, "push", "-q", self.mini_url, "HEAD:main")
        return self.rev(self.work)

    def rev(self, repo, ref="HEAD"):
        import subprocess
        return subprocess.run(["git", "-C", str(repo), "rev-parse", ref], capture_output=True, text=True).stdout.strip()

    def line(self, out, name="mini"):
        return next(ln for ln in out.splitlines() if ln.startswith(name + " "))


class Update(UpdateCase):
    def test_unchanged_then_updated_twice_and_origin_kept(self):
        self.assertIn("unchanged", self.line(self.wf("library", "update")))
        new = self.publish()
        out = self.wf("library", "update")
        self.assertIn("updated", self.line(out))
        self.assertIn("summary: 1 updated", out)
        self.assertEqual(self.rev(self.dest), new)
        self.assertEqual(self.lib()["mini"]["commit"], new)
        import subprocess
        origin = subprocess.run(["git", "-C", str(self.dest), "remote", "get-url", "origin"],
                                capture_output=True, text=True).stdout.strip()
        self.assertEqual(origin, self.mini_url)
        newer = self.publish(msg="again")
        self.assertIn("updated", self.line(self.wf("library", "update", "mini")))
        self.assertEqual(self.rev(self.dest), newer)
        self.assertEqual([p.name for p in self.dest.parent.iterdir() if p.name.startswith(".")], [])
        self.wf("start", "mini", "after", "--runs", self.runs)
        self.run = next(self.runs.glob("*_after"))
        self.assertEqual(self.events()[0]["workflow"]["commit"], newer)
        self.full()
        self.assertEqual(self.check()[0], 0)

    def test_old_run_unaffected(self):
        self.wf("start", "mini", "before", "--runs", self.runs)
        self.run = next(self.runs.glob("*_before"))
        self.publish()
        self.wf("library", "update")
        self.full()
        self.assertEqual(self.check()[0], 0)

    def test_folder_entries_are_not_touched(self):
        self.wf("library", "add", self.repo, "--name", "own")
        self.assertIn("your own folder", self.line(self.wf("library", "update"), "own"))

    def test_local_states_are_skipped(self):
        (self.dest / "skills" / "mini" / "SKILL.md").write_text("edited\n")
        self.assertIn("not committed", self.line(self.wf("library", "update")))
        git(self.dest, "checkout", "-q", "--", ".")
        git(self.dest, "checkout", "-q", "-b", "mine")
        self.assertIn("on branch mine, not main", self.line(self.wf("library", "update")))
        git(self.dest, "checkout", "-q", "--detach", "main")
        self.assertIn("detached", self.line(self.wf("library", "update")))
        git(self.dest, "checkout", "-q", "main")
        (self.dest / "local.txt").write_text("x")
        git(self.dest, "add", "local.txt")
        git(self.dest, "commit", "-q", "-m", "local")
        self.assertIn("not on the remote", self.line(self.wf("library", "update")))
        self.publish()
        self.assertIn("diverged", self.line(self.wf("library", "update")))
        out = self.wf("library", "update")
        self.assertIn("summary: 0 updated, 0 unchanged, 1 skipped, 0 failed", out)

    def test_default_branch_renamed(self):
        git(self.work, "push", "-q", self.mini_url, "HEAD:trunk")
        git(Path(self.mini_url), "symbolic-ref", "HEAD", "refs/heads/trunk")
        self.assertIn("default branch is now trunk", self.line(self.wf("library", "update")))

    def test_unreachable_is_skipped_not_failed(self):
        git(self.dest, "remote", "set-url", "origin", "https://127.0.0.1:9/x.git")
        home = Path(os.environ["DURWEG_HOME"])
        lib = json.loads((home / "library.json").read_text())
        lib["workflows"]["mini"]["url"] = "https://user:tok@127.0.0.1:9/x.git"
        (home / "library.json").write_text(json.dumps(lib))
        out = self.wf("library", "update")
        self.assertIn("skipped", self.line(out))
        self.assertNotIn("tok", out)

    def test_invalid_new_version_keeps_the_old(self):
        old = self.rev(self.dest)
        self.publish("workflow.json", "{}")
        self.assertIn("not valid, the old one is kept", self.line(self.wf("library", "update")))
        self.assertEqual(self.rev(self.dest), old)
        self.wf("start", "mini", "still", "--runs", self.runs)

    def test_swap_failure_keeps_the_old(self):
        old = self.rev(self.dest)
        self.publish()
        real = os.replace

        def replace(src, dst):
            if Path(dst) == self.dest and ".update-" in Path(src).name:
                raise PermissionError("in use")
            return real(src, dst)
        os.replace = replace
        try:
            self.assertIn("could not swap", self.line(self.wf("library", "update")))
        finally:
            os.replace = real
        self.assertEqual(self.rev(self.dest), old)
        self.assertIn("updated", self.line(self.wf("library", "update")))

    def test_v10_entry_gets_branch_and_commit(self):
        home = Path(os.environ["DURWEG_HOME"])
        lib = json.loads((home / "library.json").read_text())
        for k in ("branch", "commit", "catalog"):
            lib["workflows"]["mini"].pop(k)
        (home / "library.json").write_text(json.dumps(lib))
        self.assertIn("unchanged", self.line(self.wf("library", "update")))
        self.assertEqual(self.lib()["mini"]["branch"], "main")
        self.assertEqual(self.lib()["mini"]["commit"], self.rev(self.dest))

    def test_unknown_name_and_no_git(self):
        self.assertIn("no workflow named nosuch", self.wf("library", "update", "nosuch", expect=1))
        old = os.environ["PATH"]
        empty = self.tmp / "empty-bin"
        empty.mkdir()
        os.environ["PATH"] = str(empty)
        try:
            out = self.wf("library", "update")
        finally:
            os.environ["PATH"] = old
        self.assertIn("needs git", self.line(out))


class UpdateAndStart(UpdateCase):
    """C4: a start that comes while an update swaps the folder gets the whole new version,
    whichever way it names the folder."""

    def test_start_waits_for_the_swap_by_every_name(self):
        self.wf("library", "add", str(self.dest), "--name", "alias")        # a second name, same folder
        ways = ["mini", "alias", str(self.dest), os.path.relpath(self.dest, self.here)]
        for i, way in enumerate(ways):
            new = self.publish(msg=f"v{i}")
            real = os.replace
            mid, go = threading.Event(), threading.Event()

            def replace(src, dst, real=real, mid=mid, go=go):
                r = real(src, dst)
                if Path(src) == self.dest:                  # the old one has just been moved aside
                    mid.set()
                    go.wait(10)
                return r
            os.replace = replace
            res = {}
            sink = io.StringIO()
            try:
                with contextlib.redirect_stdout(sink), contextlib.redirect_stderr(sink):
                    up = threading.Thread(target=lambda: res.setdefault("up", main(["library", "update", "mini"])))
                    up.start()
                    self.assertTrue(mid.wait(10))
                    st = threading.Thread(target=lambda: res.setdefault(
                        "st", main(["start", way, f"w{i}", "--runs", str(self.runs)])))
                    st.start()
                    time.sleep(0.4)
                    self.assertTrue(st.is_alive(), f"{way}: start did not wait for the swap")
                    go.set()
                    up.join(20)
                    st.join(20)
            finally:
                os.replace = real
            self.assertEqual((res.get("up"), res.get("st")), (0, 0), sink.getvalue())
            self.run = next(self.runs.glob(f"*_w{i}"))
            self.assertEqual(self.events()[0]["workflow"]["commit"], new, way)
            self.full()
            self.assertEqual(self.check()[0], 0, way)


class ReviewRegressions2a(UpdateCase):
    """agy V11-C-007, 008."""

    def hooked_copytree(self, after):
        import shutil
        real = shutil.copytree

        def copytree(src, dst, *a, **kw):
            r = real(src, dst, *a, **kw)
            if Path(src) == self.dest:
                after()
            return r
        shutil.copytree = copytree
        return lambda: setattr(shutil, "copytree", real)

    def test_c007_file_written_after_the_copy_is_kept_and_nothing_swapped(self):
        old = self.rev(self.dest)
        self.publish()
        undo = self.hooked_copytree(lambda: (self.dest / "note.txt").write_text("my edit"))
        try:
            line = self.line(self.wf("library", "update"))
        finally:
            undo()
        self.assertIn("was changed while it was being updated", line)
        self.assertEqual((self.dest / "note.txt").read_text(), "my edit")
        self.assertEqual(self.rev(self.dest), old)

    def test_c007_branch_switched_on_the_same_commit(self):
        old = self.rev(self.dest)
        self.publish()
        undo = self.hooked_copytree(lambda: git(self.dest, "checkout", "-q", "-b", "other"))
        try:
            line = self.line(self.wf("library", "update"))
        finally:
            undo()
        self.assertIn("was changed while it was being updated", line)
        self.assertEqual(self.rev(self.dest), old)

    def test_c007_file_written_during_fetch_is_not_swapped_in(self):
        from durweg import gitops
        old = self.rev(self.dest)
        self.publish()
        real = gitops.run

        def run(args, *a, **kw):
            r = real(args, *a, **kw)
            if args[:2] == ["fetch", "-q"] and Path(kw.get("cwd") or ".") == self.dest:   # the workflow's own fetch
                (self.dest / "skills" / "mini" / "extra.md").write_text("dirty")
            return r
        gitops.run = run
        try:
            line = self.line(self.wf("library", "update"))
        finally:
            gitops.run = real
        self.assertIn("was changed while it was being updated", line)
        self.assertTrue((self.dest / "skills" / "mini" / "extra.md").is_file())
        self.assertEqual(self.rev(self.dest), old)

    def v10(self):
        home = Path(os.environ["DURWEG_HOME"])
        lib = json.loads((home / "library.json").read_text())
        for k in ("branch", "commit", "catalog"):
            lib["workflows"]["mini"].pop(k, None)
        (home / "library.json").write_text(json.dumps(lib))

    def test_c008_detached_v10_entry_gets_no_branch_then_recovers(self):
        self.v10()
        git(self.dest, "checkout", "-q", "--detach", "HEAD")
        self.assertIn("detached", self.line(self.wf("library", "update")))
        self.assertNotIn("branch", self.lib()["mini"])
        git(self.dest, "checkout", "-q", "main")
        self.publish()
        self.assertIn("updated", self.line(self.wf("library", "update")))
        self.assertEqual(self.lib()["mini"]["branch"], "main")

    def test_c008_local_branch_is_not_written_down(self):
        self.v10()
        git(self.dest, "checkout", "-q", "-b", "mine")
        self.assertIn("on branch mine, not main", self.line(self.wf("library", "update")))
        self.assertNotIn("branch", self.lib()["mini"])
        git(self.dest, "checkout", "-q", "main")
        self.publish()
        self.assertIn("updated", self.line(self.wf("library", "update")))
        self.assertEqual(self.lib()["mini"]["branch"], "main")

    def test_c008_null_branch_from_df47c8a_is_repaired(self):
        home = Path(os.environ["DURWEG_HOME"])
        lib = json.loads((home / "library.json").read_text())
        lib["workflows"]["mini"]["branch"] = None
        (home / "library.json").write_text(json.dumps(lib))
        self.assertIn("unchanged", self.line(self.wf("library", "update")))
        self.assertEqual(self.lib()["mini"]["branch"], "main")


class DurwegUpdateWithoutInstaller(UpdateCase):
    def test_source_checkout_skips_the_platform_and_updates_the_library(self):
        new = self.publish()
        out = self.wf("update")
        self.assertRegex(out, r"Durweg +skipped +this Durweg was not installed by the installer")
        self.assertIn("updated", self.line(out))
        self.assertEqual(self.rev(self.dest), new)


class CatalogLinesInUpdate(UpdateCase):
    """agy V11-C-010: say "the last copy is kept" only when there is one; quiet says nothing new."""

    def test_never_downloaded_vs_kept_copy(self):
        os.environ["DURWEG_PUBLIC_CATALOG"] = str(self.tmp / "nothing.git")
        from durweg import catalog
        from durweg.util import rmtree
        rmtree(catalog.cache_dir("public"))
        out = self.wf("library", "update")
        self.assertIn("catalog public: not downloaded yet", out)
        self.assertNotIn("the last copy is kept", out)
        self.assertNotIn("catalog public", self.wf("library", "update", "--quiet"))
        os.environ["DURWEG_PUBLIC_CATALOG"] = self.pub_url
        self.assertIn("catalog public: refreshed", self.wf("library", "update"))
        os.environ["DURWEG_PUBLIC_CATALOG"] = str(self.tmp / "nothing.git")
        self.assertIn("the last copy is kept", self.wf("library", "update", "--quiet"))
