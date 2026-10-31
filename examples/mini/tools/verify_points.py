#!/usr/bin/env python3
"""Gate for step 3 of the mini example: the verify record covers the chosen topic and every point."""
import json
import re
import sys
from pathlib import Path

run = Path(sys.argv[1])
errs = []
try:
    chosen = json.loads((run / "steps/1-topic.decision.json").read_text())["values"].get("chosen")
    rec = json.loads((run / "steps/3-verify.json").read_text())
except (OSError, ValueError, KeyError) as e:
    print(f"cannot read the record: {e}")
    sys.exit(1)
text = (run / "steps/2-points.md").read_text()
body = text.split("## Points", 1)[1].split("\n## ", 1)[0]
points = [m.group(1).strip() for m in re.finditer(r"^\s*[-*]\s+(.*)$", body, re.M)]
if rec.get("topic") != chosen:
    errs.append(f"topic is {rec.get('topic')!r}, the user chose {chosen!r}")
missing = [p for p in points if p not in rec.get("checked", [])]
if missing:
    errs.append(f"points not checked: {missing}")
for e in errs:
    print(e)
sys.exit(1 if errs else 0)
