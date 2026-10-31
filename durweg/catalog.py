"""Catalogs: lists of workflows that can be installed by name (plan v1.1 D1, C1).

~/Durweg/catalogs.json   {"format": 1, "catalogs": {id: {"url", "added", "disabled"?, "fetched"?}}}
~/Durweg/catalogs/<id>/  a clone of the catalog repository, used as a cache

A catalog repository holds catalog.json:
    {"format": 1, "workflows": {name: {"title", "summary", "url"}}}

The public catalog (id `public`) is always known; it can be switched off but not removed. A catalog
only says where a workflow is: installing one clones the workflow's own repository into the library,
and `durweg start` never looks at catalogs.
"""

import os
import re
from pathlib import Path

from . import gitops
from .util import WfError, now, read_json, rmtree, write_json

PUBLIC = "public"
PUBLIC_URL = "https://github.com/musetee/durweg-workflows.git"
ID = re.compile(r"^[a-z0-9][a-z0-9-]+$")                                    # at least 2: never a drive C:
QUALIFIED = re.compile(r"^([a-z0-9][a-z0-9-]+):([a-z0-9][a-z0-9-]*)$")      # <id>:<name>
WF_NAME = re.compile(r"^[a-z0-9][a-z0-9-]*$")


def _home():
    from .library import home
    return home()


def public_url():
    return os.environ.get("DURWEG_PUBLIC_CATALOG") or PUBLIC_URL


def _lock():
    from .library import _IndexLock
    _home().mkdir(parents=True, exist_ok=True)
    return _IndexLock("catalogs")


def _load():
    p = _home() / "catalogs.json"
    data = {"format": 1, "catalogs": {}}
    if p.is_file():
        try:
            data = read_json(p)
        except (OSError, ValueError) as e:
            raise WfError(f"{p} cannot be read ({e}); fix or delete it")
        data.setdefault("catalogs", {})
    return data


def _save(data):
    write_json(_home() / "catalogs.json", data)


def configured():
    """{id: entry} with the public catalog always present (url from the environment in tests)."""
    cats = _load()["catalogs"]
    pub = dict(cats.get(PUBLIC, {}))
    pub["url"] = public_url()
    cats[PUBLIC] = pub
    return cats


def enabled():
    return {k: v for k, v in configured().items() if not v.get("disabled")}


def cache_dir(cid):
    return _home() / "catalogs" / cid


def _norm(url):
    u = (url or "").strip().rstrip("/")
    return u[:-4] if u.endswith(".git") else u


def same_url(a, b):
    return _norm(a).lower() == _norm(b).lower()


# -- reading a catalog -----------------------------------------------------------------
def _parse(cid, folder):
    p = Path(folder) / "catalog.json"
    try:
        data = read_json(p)
    except (OSError, ValueError) as e:
        raise WfError(f"catalog {cid}: catalog.json cannot be read ({e})")
    if not isinstance(data, dict) or data.get("format") != 1 or not isinstance(data.get("workflows"), dict):
        raise WfError(f"catalog {cid}: catalog.json is not format 1 with a \"workflows\" object")
    out, bad = {}, []
    for name, e in data["workflows"].items():
        if WF_NAME.match(name) and isinstance(e, dict) and isinstance(e.get("url"), str) and e["url"]:
            out[name] = {"title": str(e.get("title", "")), "summary": str(e.get("summary", "")), "url": e["url"]}
        else:
            bad.append(name)
    return out, bad


def refresh(cid, url):
    """Bring the cache of one catalog up to date. Returns None, or the reason it could not."""
    dest = cache_dir(cid)
    try:
        if dest.is_dir():
            try:
                origin = gitops.run(["remote", "get-url", "origin"], cwd=dest).strip()
            except gitops.GitFailed:
                origin = ""
            if not same_url(origin, url):
                rmtree(dest)
        if dest.is_dir():
            gitops.run(["fetch", "-q", "origin", "HEAD"], cwd=dest, url=url)
            gitops.run(["reset", "-q", "--hard", "FETCH_HEAD"], cwd=dest)
        else:
            tmp = dest.with_name(f".{cid}.new")
            rmtree(tmp)
            tmp.parent.mkdir(parents=True, exist_ok=True)
            gitops.clone(url, tmp)
            os.replace(tmp, dest)
        _parse(cid, dest)
    except WfError as e:
        return str(e)
    with _lock():
        data = _load()
        entry = data["catalogs"].setdefault(cid, {})
        if cid != PUBLIC:
            entry.setdefault("url", url)
        entry["fetched"] = now()
        _save(data)
    return None


def read(cid, entry, fetch=True):
    """(workflows or None, note or None) for one catalog: refreshed when possible, else the cache."""
    reason = refresh(cid, entry["url"]) if fetch else None
    dest = cache_dir(cid)
    if not (dest / "catalog.json").is_file():
        return None, f"catalog {cid} is not available ({reason or 'never downloaded'})"
    try:
        items, bad = _parse(cid, dest)
    except WfError as e:
        return None, str(e)
    notes = []
    if reason:
        when = (_load()["catalogs"].get(cid) or {}).get("fetched", "an earlier download")
        notes.append(f"catalog {cid} could not be refreshed ({reason}); showing the copy from {when}")
    if bad:
        notes.append(f"catalog {cid}: skipped invalid entries: {', '.join(sorted(bad))}")
    return items, "; ".join(notes) or None


def find(name, only=None):
    """Matches of a workflow name in the enabled catalogs (or in catalog `only`):
    ([(id, entry)], [notes])."""
    cats = enabled()
    if only is not None:
        if only not in configured():
            raise WfError(f"no catalog named {only} (catalogs: {', '.join(sorted(configured()))})")
        if only not in cats:
            raise WfError(f"catalog {only} is switched off; switch it on with `durweg catalog add {only}`")
        cats = {only: cats[only]}
    hits, notes = [], []
    for cid in sorted(cats):
        items, note = read(cid, cats[cid])
        if note:
            notes.append(note)
        if items and name in items:
            hits.append((cid, items[name]))
    return hits, notes


# -- managing the list of catalogs ------------------------------------------------------
def add(cid, url=None):
    if not ID.match(cid or ""):
        raise WfError(f"catalog names use lower-case letters, digits and -, at least 2 characters: {cid!r}")
    if cid == PUBLIC:
        if url and not same_url(url, public_url()):
            raise WfError("the name public is kept for the public catalog; choose another name")
        with _lock():
            data = _load()
            data["catalogs"].setdefault(PUBLIC, {}).pop("disabled", None)
            _save(data)
        return public_url(), refresh(PUBLIC, public_url())
    if not url:
        raise WfError("durweg catalog add <name> <git address>")
    if not gitops_url(url):
        raise WfError(f"{url} is not a git address (https://…, git@…, ssh://… or …/name.git)")
    if cid in configured():
        raise WfError(f"a catalog named {cid} exists already ({configured()[cid]['url']})")
    reason = refresh(cid, url)                   # also proves the address works and the format is right
    if reason:
        rmtree(cache_dir(cid))
        raise WfError(f"catalog {cid} was not added: {reason}")
    with _lock():
        data = _load()
        fetched = data["catalogs"].get(cid, {}).get("fetched") or now()
        data["catalogs"][cid] = {"url": url, "added": now(), "fetched": fetched}
        _save(data)
    return url, None


def remove(cid):
    if cid not in configured():
        raise WfError(f"no catalog named {cid}")
    with _lock():
        data = _load()
        if cid == PUBLIC:
            data["catalogs"].setdefault(PUBLIC, {})["disabled"] = True
        else:
            data["catalogs"].pop(cid, None)
        _save(data)
    if cid != PUBLIC:
        rmtree(cache_dir(cid))
    return cid == PUBLIC


def gitops_url(arg):
    from .library import GIT_URL
    return bool(GIT_URL.search(arg))
