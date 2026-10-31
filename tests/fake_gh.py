"""A stand-in for the GitHub command gh, for the publish tests. State in $DURWEG_FAKE_GH (json):
{"login": str|None, "repos": {owner/name: {visibility, viewerPermission, url}}, "prs": [], "calls": []}.
Repositories are bare git repositories in $DURWEG_FAKE_GH_DIR."""

import json
import os
import shutil
import subprocess
import sys

state_path = os.environ["DURWEG_FAKE_GH"]
with open(state_path, encoding="utf-8") as f:
    st = json.load(f)
args = sys.argv[1:]
st.setdefault("calls", []).append(args)


def save():
    with open(state_path, "w", encoding="utf-8") as f:
        json.dump(st, f, indent=1)


def bare(name):
    return os.path.join(os.environ["DURWEG_FAKE_GH_DIR"], name.replace("/", "__") + ".git")


def opt(name):
    return args[args.index(name) + 1] if name in args else None


rc = 0
if args[:2] == ["api", "user"]:
    if st.get("login"):
        print(st["login"])
    else:
        print("not logged in", file=sys.stderr)
        rc = 1
elif args[0] == "api" and args[1].startswith("licenses/"):
    key = args[1].split("/", 1)[1]
    print(json.dumps({"body": f"{key.upper()} LICENSE\nCopyright (c) [year] [fullname]\n"}))
elif args[:2] == ["repo", "view"]:
    r = st["repos"].get(args[2])
    if r:
        print(json.dumps({k: r[k] for k in ("visibility", "viewerPermission", "url")}))
    else:
        print(f"Could not resolve to a Repository with the name '{args[2]}'.", file=sys.stderr)
        rc = 1
elif args[:2] == ["repo", "create"]:
    name = args[2]
    if name in st["repos"] or st.get("fail_create"):
        print("Name already exists on this account", file=sys.stderr)
        rc = 1
    else:
        subprocess.run(["git", "init", "-q", "--bare", "-b", "main", bare(name)], check=True)
        st["repos"][name] = {"visibility": "PRIVATE" if "--private" in args else "PUBLIC",
                             "viewerPermission": "ADMIN", "url": bare(name)}
        print(f"https://github.com/{name}")
elif args[:2] == ["repo", "fork"]:
    up = args[2]
    mine = f"{st['login']}/{up.split('/')[1]}"
    if mine not in st["repos"]:
        shutil.copytree(st["repos"][up]["url"], bare(mine))
        st["repos"][mine] = {"visibility": "PUBLIC", "viewerPermission": "ADMIN", "url": bare(mine)}
elif args[:2] == ["pr", "create"]:
    st.setdefault("prs", []).append({"repo": opt("--repo"), "head": opt("--head"), "title": opt("--title")})
    print(f"https://github.com/{opt('--repo')}/pull/{len(st['prs'])}")
else:
    print(f"fake gh: not supported: {args}", file=sys.stderr)
    rc = 2
save()
sys.exit(rc)
