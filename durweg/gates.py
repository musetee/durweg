"""Artifact digests and the six gate types (design 3.2, 4)."""

import glob
import json
import os
import subprocess
import sys
from pathlib import Path

from . import md
from .util import read_json, sha256_file, sha256_json, write_atomic


# -- digests ---------------------------------------------------------------------------
def artifact_files(run_dir, wf, sid):
    run_dir = Path(run_dir)
    found = set()
    for pattern in wf.step(sid)["artifacts"]:
        for p in glob.glob(str(run_dir / pattern), recursive=True):
            rel = os.path.relpath(p, run_dir)
            if os.path.isfile(p) and not rel.startswith(".wf" + os.sep):
                found.add(rel)
    return sorted(found)


def _digest(run_dir, rels):
    return sha256_json([[r, sha256_file(Path(run_dir) / r)] for r in rels])


def proposal_digest(run_dir, wf, sid):
    dec = wf.decision_path(sid)
    return _digest(run_dir, [r for r in artifact_files(run_dir, wf, sid) if r != dec])


def artifacts_digest(run_dir, wf, sid):
    rels = set(artifact_files(run_dir, wf, sid))
    if wf.has_user(sid) and (Path(run_dir) / wf.decision_path(sid)).is_file():
        rels.add(wf.decision_path(sid))
    return _digest(run_dir, sorted(rels))


# -- json schema subset ----------------------------------------------------------------
TYPES = {"object": dict, "array": list, "string": str, "boolean": bool,
         "integer": int, "number": (int, float)}


def check_schema(value, schema, where="$"):
    errs = []
    t = schema.get("type")
    if t:
        ok = isinstance(value, TYPES[t]) and not (t in ("integer", "number") and isinstance(value, bool))
        if not ok:
            return [f"{where}: expected {t}"]
    if "enum" in schema and value not in schema["enum"]:
        errs.append(f"{where}: must be one of {schema['enum']}")
    if isinstance(value, str):
        if md.empty(value):
            errs.append(f"{where}: empty or placeholder")
        if len(value.strip()) < schema.get("minLength", 0):
            errs.append(f"{where}: shorter than {schema['minLength']}")
    if isinstance(value, dict):
        for k in schema.get("required", []):
            if k not in value:
                errs.append(f"{where}: missing '{k}'")
        for k, sub in schema.get("properties", {}).items():
            if k in value:
                errs += check_schema(value[k], sub, f"{where}.{k}")
    if isinstance(value, list):
        if len(value) < schema.get("minItems", 0):
            errs.append(f"{where}: fewer than {schema['minItems']} items")
        if "maxItems" in schema and len(value) > schema["maxItems"]:
            errs.append(f"{where}: more than {schema['maxItems']} items")
        if schema.get("uniqueItems"):
            seen = [json.dumps(v, sort_keys=True) for v in value]
            if len(set(seen)) != len(seen):
                errs.append(f"{where}: items are not unique")
        if "items" in schema:
            for i, v in enumerate(value):
                errs += check_schema(v, schema["items"], f"{where}[{i}]")
    if not schema.get("type") and isinstance(value, (dict, list)) is False and value is None:
        errs.append(f"{where}: null")
    return errs


def _strings(value, where="$"):
    """Every string in a JSON document must be non-empty and not a placeholder."""
    if isinstance(value, str):
        return [f"{where}: empty or placeholder"] if md.empty(value) else []
    if isinstance(value, dict):
        return [e for k, v in value.items() for e in _strings(v, f"{where}.{k}")]
    if isinstance(value, list):
        return [e for i, v in enumerate(value) for e in _strings(v, f"{where}[{i}]")]
    return []


# -- gates -----------------------------------------------------------------------------
def gate_json(run_dir, g, ctx):
    p = Path(run_dir) / g["file"]
    if not p.is_file():
        return [f"{g['file']}: missing"]
    try:
        doc = read_json(p)
    except ValueError as e:
        return [f"{g['file']}: not valid JSON ({e})"]
    errs = check_schema(doc, g.get("schema", {}))
    errs += [e for e in _strings(doc) if e not in errs]
    return [f"{g['file']}: {e}" for e in errs]


def gate_sections(run_dir, g, ctx):
    p = Path(run_dir) / g["file"]
    if not p.is_file():
        return [f"{g['file']}: missing"]
    text = p.read_text(encoding="utf-8")
    errs = []
    for h in g["headings"]:
        secs, idx = md.find(text, h["title"])
        if not idx:
            errs.append(f"{g['file']}: no heading '{h['title']}'")
            continue
        if len(idx) > 1:
            errs.append(f"{g['file']}: heading '{h['title']}' appears {len(idx)} times")
            continue
        body = md.section_body(secs, idx[0])
        its = [i for i in md.items(body) if not md.empty(i)]
        bad = [i for i in md.items(body) if md.empty(i)]
        if bad:
            errs.append(f"{g['file']} '{h['title']}': {len(bad)} empty or placeholder item(s)")
        if len(its) < h.get("min_items", 0):
            errs.append(f"{g['file']} '{h['title']}': {len(its)} items, need at least {h['min_items']}")
        if "max_items" in h and len(its) > h["max_items"]:
            errs.append(f"{g['file']} '{h['title']}': {len(its)} items, at most {h['max_items']}")
        chars = len("".join("".join(body).split()))
        if chars < h.get("min_chars", 0):
            errs.append(f"{g['file']} '{h['title']}': {chars} characters, need {h['min_chars']}")
    return errs


def gate_table(run_dir, g, ctx):
    p = Path(run_dir) / g["file"]
    if not p.is_file():
        return [f"{g['file']}: missing"]
    secs, idx = md.find(p.read_text(encoding="utf-8"), g["under"])
    if len(idx) != 1:
        return [f"{g['file']}: heading '{g['under']}' found {len(idx)} times, need exactly 1"]
    tab = md.first_table(md.section_body(secs, idx[0]))
    if not tab:
        return [f"{g['file']} '{g['under']}': no table"]
    cols, rows = tab
    errs = []
    if cols != g["columns"]:
        errs.append(f"{g['file']} '{g['under']}': columns {cols}, expected {g['columns']}")
        return errs
    if len(rows) < g.get("min_rows", 0):
        errs.append(f"{g['file']} '{g['under']}': {len(rows)} rows, need at least {g['min_rows']}")
    if "max_rows" in g and len(rows) > g["max_rows"]:
        errs.append(f"{g['file']} '{g['under']}': {len(rows)} rows, at most {g['max_rows']}")
    for i, r in enumerate(rows):
        if len(r) != len(cols):
            errs.append(f"{g['file']} '{g['under']}' row {i + 1}: {len(r)} cells, expected {len(cols)}")
        elif any(md.empty(c) for c in r):
            errs.append(f"{g['file']} '{g['under']}' row {i + 1}: empty or placeholder cell")
    for col in g.get("unique", []):
        if col in cols:
            vals = [r[cols.index(col)].lower() for r in rows if len(r) == len(cols)]
            if len(set(vals)) != len(vals):
                errs.append(f"{g['file']} '{g['under']}': column '{col}' has duplicates")
    return errs


def gate_files(run_dir, g, ctx):
    matches = [p for p in glob.glob(str(Path(run_dir) / g["glob"]), recursive=True) if os.path.isfile(p)]
    errs = []
    if len(matches) < g.get("min_count", 1):
        errs.append(f"{g['glob']}: {len(matches)} file(s), need at least {g.get('min_count', 1)}")
    for p in matches:
        if os.path.getsize(p) == 0:
            errs.append(f"{os.path.relpath(p, run_dir)}: empty")
    return errs


def gate_command(run_dir, g, ctx):
    snap = str(Path(run_dir) / ".wf" / "workflow")
    subst = {"{run}": str(run_dir), "{wf}": snap, "{step}": ctx["step"]}
    argv = []
    for a in g["argv"]:
        for k, v in subst.items():
            a = a.replace(k, v)
        argv.append(a)
    if argv[0] in ("python3", "python"):
        argv[0] = sys.executable
    env = dict(os.environ, WF_RUN=str(run_dir), WF_SNAPSHOT=snap, WF_STEP=ctx["step"],
               WF_STATE=str(Path(run_dir) / ".wf" / "state.json"))
    out = Path(run_dir) / ".wf" / "gates" / f"{ctx['step']}-{ctx['index']}.out"
    try:
        r = subprocess.run(argv, cwd=run_dir, capture_output=True, text=True, encoding="utf-8",
                           errors="replace", timeout=g.get("timeout", 60), env=dict(env, PYTHONIOENCODING="utf-8"))
    except subprocess.TimeoutExpired:
        write_atomic(out, "timeout\n")
        return [f"command {' '.join(g['argv'])}: timed out after {g.get('timeout', 60)} s"]
    except OSError as e:
        write_atomic(out, f"could not start: {e}\n")
        return [f"command {' '.join(g['argv'])}: could not start ({e})"]
    write_atomic(out, f"exit {r.returncode}\n--- stdout\n{r.stdout}--- stderr\n{r.stderr}")
    if r.returncode != 0:
        detail = (r.stdout + r.stderr).strip().splitlines()[-8:]
        return [f"command {' '.join(g['argv'])}: exit {r.returncode}"] + ["  " + d for d in detail]
    return []


def gate_user(run_dir, g, ctx):
    """The latest confirm of this round binds the current proposal; the decision file matches it."""
    wf, sid, rp = ctx["wf"], ctx["step"], ctx["replay"]
    c, p = rp.confirm.get(sid), rp.propose.get(sid)
    if not c or not p or c["proposal_event"] != p["n"]:
        return [f"step {sid}: no user confirmation bound to the latest proposal in this round"]
    errs = []
    if proposal_digest(run_dir, wf, sid) != p["proposal_digest"]:
        errs.append(f"step {sid}: the proposal changed after `durweg propose` (event {p['n']}); "
                    f"propose again, show it to the user and confirm")
    dec = Path(run_dir) / wf.decision_path(sid)
    want = {"confirm_event": c["n"], "values": c.get("set", {})}
    try:
        have = read_json(dec)
    except (OSError, ValueError):
        have = None
    if have != want:
        errs.append(f"{wf.decision_path(sid)}: does not match confirm event {c['n']} "
                    f"(the decision file is written only by `durweg confirm`)")
    return errs


GATES = {"json": gate_json, "sections": gate_sections, "table": gate_table,
         "files": gate_files, "command": gate_command, "user": gate_user}


def evaluate(run_dir, wf, sid, replay):
    problems = []
    for i, g in enumerate(wf.step(sid)["gates"]):
        ctx = {"wf": wf, "step": sid, "index": i + 1, "replay": replay}
        problems += GATES[g["type"]](run_dir, g, ctx)
    return problems
