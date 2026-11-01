#!/usr/bin/env python3
"""Make a test package of this working tree (Linux, macOS, Windows), for CI and local tests:
  python tools/package.py <version> <out folder>
writes durweg-<version>.tar.gz and .zip (top folder durweg-<version>/) with .sha256 files and
prints `tar <path> <sha>` and `zip <path> <sha>`. Releases use tools/build-release.sh (git archive)."""
import hashlib
import sys
import tarfile
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SKIP = {".git", "dist", "__pycache__", "runs", ".github", ".claude-plugin", ".gitattributes"}   # as git archive (.gitattributes)


def files():
    for p in sorted(ROOT.rglob("*")):
        rel = p.relative_to(ROOT)
        if p.is_file() and not any(part in SKIP for part in rel.parts) and p.suffix != ".pyc":
            yield p, rel.as_posix()


def main(version, out):
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    top = f"durweg-{version}"
    tgz, zp = out / f"{top}.tar.gz", out / f"{top}.zip"
    with tarfile.open(tgz, "w:gz") as t:
        for p, rel in files():
            info = t.gettarinfo(str(p), arcname=f"{top}/{rel}")
            info.mode = 0o755 if rel.startswith("bin/") or rel.endswith(".sh") else 0o644
            with open(p, "rb") as f:
                t.addfile(info, f)
    with zipfile.ZipFile(zp, "w", zipfile.ZIP_DEFLATED) as z:
        for p, rel in files():
            z.write(p, f"{top}/{rel}")
    for kind, f in (("tar", tgz), ("zip", zp)):
        sha = hashlib.sha256(f.read_bytes()).hexdigest()
        (out / (f.name + ".sha256")).write_text(f"{sha}  {f.name}\n")
        print(kind, f, sha)


if __name__ == "__main__":
    main(*sys.argv[1:3])
