#!/usr/bin/env python3
"""Step 4 of write-your-method (action): copy the frozen generated workflow into the library folder.

  register.py RUN

Copies RUN/generated/<name>/ to ~/Durweg/workflows/<name>/ ($DURWEG_HOME if set) and writes
RUN/steps/4-register.json (name, library_path, digest). Then register it: durweg library add.
A folder of that name that holds something else is left alone. Standard library only.
"""
import hashlib
import json
import os
import shutil
import sys
from pathlib import Path


def tree_digest(folder):
    h = hashlib.sha256()
    for p in sorted(Path(folder).rglob("*")):
        if p.is_file():
            h.update(p.relative_to(folder).as_posix().encode() + b"\0" + p.read_bytes())
    return h.hexdigest()


def main(argv):
    if len(argv) != 1:
        sys.exit(__doc__)
    run = Path(argv[0]).resolve()
    name = json.loads((run / "steps/2-steps.json").read_text(encoding="utf-8"))["name"]
    src = run / "generated" / name
    home = Path(os.environ.get("DURWEG_HOME") or Path.home() / "Durweg")
    dest = home / "workflows" / name
    digest = tree_digest(src)
    if dest.exists() and tree_digest(dest) != digest:
        sys.exit(f"{dest} exists and holds something else; it is left alone. Choose another name "
                 f"(durweg reopen the design step) or move that folder away.")
    if not dest.exists():
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(src, dest)
    rec = {"name": name, "library_path": str(dest), "digest": digest}
    (run / "steps/4-register.json").write_text(json.dumps(rec, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"copied to {dest}\nnow run: durweg library add \"{dest}\" --name {name}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
