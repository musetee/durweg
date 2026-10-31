#!/usr/bin/env python3
"""Step 6 of write-your-method (action): write this run up as a case, one web page to keep or share.

  make_case.py RUN

Builds RUN/case/<name>.html from the run's own record, so nothing in it is made up: the method
(steps/1-method.md), the confirmed steps (steps/2-steps.json), the user's own words at every
confirmation (.wf/state.json), the first run of the new workflow and its check (steps/5-try.json
and that run's record, frozen into case/inputs.json), and the user's lessons (steps/6-lessons.md). Copies the page to
~/Durweg/cases/ ($DURWEG_HOME if set) and writes RUN/steps/6-case.json. The page holds no paths
of this computer. Standard library only.
"""
import hashlib
import html
import json
import os
import re
import shutil
import sys
from pathlib import Path

TEXT = {
    "en": {
        "case": "A Durweg case", "made": "Made with Durweg on {date}. Workflow: {name}.",
        "method": "The method", "steps": "The steps", "num": "#", "step": "Step", "do": "What it does",
        "deliver": "What it delivers", "decide": "You decide", "yes": "yes", "no": "",
        "words": "In the user's own words", "words_lead": "Every step that needed the user's decision "
        "went on only after they confirmed it. What they said:",
        "try": "The first run", "try_lead": "The new workflow was run once right away: run {run}, "
        "check result {check}.", "try_words": "Decisions in that run:",
        "lessons": "Lessons", "use": "Use it yourself",
        "use_text": "With Durweg installed, put the workflow folder {name} into your library "
        "(durweg library add <folder> --name {name}) and tell your agent: \"Run {name} with durweg.\"",
        "ids": {"describe": "Describe how you do it", "design": "Turn it into steps",
                "build": "Build the workflow", "register": "Put it in your library",
                "try": "Run your new workflow once"},
    },
    "zh": {
        "case": "Durweg 案例", "made": "用 Durweg 制作于 {date}。工作流：{name}。",
        "method": "方法", "steps": "步骤", "num": "#", "step": "步骤", "do": "做什么",
        "deliver": "交出什么", "decide": "由用户决定", "yes": "是", "no": "",
        "words": "用户的原话", "words_lead": "每个需要用户拍板的步骤，都是用户确认以后才往下走的。用户当时说：",
        "try": "第一次运行", "try_lead": "新工作流做好后马上运行了一次：运行 {run}，检查结果 {check}。",
        "try_words": "那次运行里用户的决定：",
        "lessons": "经验", "use": "自己用这个工作流",
        "use_text": "装好 Durweg 以后，把工作流文件夹 {name} 放进方法库"
        "（durweg library add <文件夹> --name {name}），然后对 agent 说：“用 durweg 运行 {name}”。",
        "ids": {"describe": "描述你的方法", "design": "拆成步骤", "build": "生成工作流",
                "register": "放进方法库", "try": "试跑一次"},
    },
}

CSS = """
body{font:16px/1.65 -apple-system,"Segoe UI","PingFang SC","Microsoft YaHei",sans-serif;color:#1f2328;
background:#f6f8fa;margin:0}
main{max-width:860px;margin:2.5rem auto;padding:2rem 2.5rem;background:#fff;border:1px solid #d0d7de;
border-radius:12px}
header p{color:#57606a;margin:.2rem 0 0}
.tag{display:inline-block;font-size:.8rem;letter-spacing:.04em;text-transform:uppercase;color:#0969da;
background:#ddf4ff;border-radius:999px;padding:.15rem .7rem}
h1{font-size:1.9rem;margin:.6rem 0 .2rem}
h2{font-size:1.3rem;margin:2.2rem 0 .8rem;padding-bottom:.3rem;border-bottom:1px solid #d8dee4}
h3{font-size:1.05rem;margin:1.2rem 0 .4rem}
table{border-collapse:collapse;width:100%;font-size:.95rem}
th,td{border:1px solid #d0d7de;padding:.45rem .6rem;text-align:left;vertical-align:top}
th{background:#f6f8fa}
blockquote{margin:.4rem 0 .9rem;padding:.5rem .9rem;border-left:4px solid #1f883d;background:#f0fff4}
.who{font-size:.85rem;color:#57606a;margin-top:.8rem}
.pass{color:#1a7f37;font-weight:600}
code{background:#eff1f3;border-radius:4px;padding:.1rem .3rem;font-size:.9em}
footer{margin-top:2.5rem;color:#57606a;font-size:.85rem}
"""


def load(p):
    return json.loads(Path(p).read_text(encoding="utf-8"))


def e(s):
    return html.escape(str(s), quote=True)


def md(text):
    """The few forms a method file uses: ## headings, - lists, paragraphs."""
    out, items = [], []

    def flush():
        if items:
            out.append("<ul>" + "".join(f"<li>{e(i)}</li>" for i in items) + "</ul>")
            items.clear()
    for line in text.splitlines():
        s = line.strip()
        m = re.match(r"^#{1,6}\s+(.*)$", s)
        if m:
            flush()
            out.append(f"<h3>{e(m.group(1))}</h3>")
        elif re.match(r"^[-*]\s+", s):
            items.append(re.sub(r"^[-*]\s+", "", s))
        elif s:
            flush()
            out.append(f"<p>{e(s)}</p>")
        else:
            flush()
    flush()
    return "\n".join(out)


def confirms(run_dir, skip=()):
    """The last confirmation of each step, in step order: (step, quote). Steps in skip are left out
    (the case step itself: its confirmation comes after the page is written)."""
    try:
        events = load(Path(run_dir) / ".wf/state.json")["events"]
    except (OSError, ValueError, KeyError):
        return []
    last = {}
    for ev in events:
        if ev.get("type") == "confirm" and ev.get("quote") and ev["step"] not in skip:
            last[ev["step"]] = ev["quote"]
    order = []
    for ev in events:
        if ev.get("type") == "confirm" and ev["step"] in last and ev["step"] not in order:
            order.append(ev["step"])
    return [(s, last[s]) for s in order]


def language():
    home = Path(os.environ.get("DURWEG_HOME") or Path.home() / "Durweg")
    try:
        return "zh" if load(home / "config.json").get("language") == "zh" else "en"
    except (OSError, ValueError):
        return "en"


def collect(run):
    """What the page needs from outside this run, frozen into case/inputs.json when the page is
    made, so later checks of this run do not depend on other runs or on the settings."""
    tr = load(run / "steps/5-try.json")
    try_run = Path(tr["run"])
    return {"language": language(), "try_run": try_run.name, "try_check": tr["check"],
            "try_confirms": confirms(try_run)}


def page(run, inputs):
    T = TEXT[inputs["language"]]
    lang = inputs["language"]
    d = load(run / "steps/2-steps.json")
    name, title = d["name"], d.get("title") or d["name"]
    date = load(run / ".wf/state.json")["events"][0]["t"][:10]
    method = (run / "steps/1-method.md").read_text(encoding="utf-8")
    lessons = (run / "steps/6-lessons.md").read_text(encoding="utf-8")
    lessons = re.sub(r"^\s*#{1,6}\s+Lessons\s*$", "", lessons, count=1, flags=re.M | re.I)
    rows = "".join(
        f"<tr><td>{i}</td><td><b>{e(s['title'])}</b></td><td>{e(s['do'])}</td><td>{e(s['deliver'])}</td>"
        f"<td>{T['yes'] if s.get('user') else T['no']}</td></tr>" for i, s in enumerate(d["steps"], 1))
    words = "".join(f"<p class='who'>{e(T['ids'].get(s, s))}</p><blockquote>{e(q)}</blockquote>"
                    for s, q in confirms(run, skip=("case",)))
    titles = {s["id"]: s["title"] for s in d["steps"]}
    try_words = "".join(f"<p class='who'>{e(titles.get(s, s))}</p><blockquote>{e(q)}</blockquote>"
                        for s, q in inputs["try_confirms"])
    check = f"<span class='pass'>{e(inputs['try_check'])}</span>"
    return f"""<!DOCTYPE html>
<html lang="{lang}"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{e(title)} · {e(T['case'])}</title><style>{CSS}</style></head>
<body><main>
<header><span class="tag">{e(T['case'])}</span><h1>{e(title)}</h1>
<p>{e(T['made'].format(date=date, name=name))}</p></header>
<h2>{e(T['method'])}</h2>
{md(method)}
<h2>{e(T['steps'])}</h2>
<table><tr><th>{T['num']}</th><th>{e(T['step'])}</th><th>{e(T['do'])}</th><th>{e(T['deliver'])}</th><th>{e(T['decide'])}</th></tr>
{rows}</table>
<h2>{e(T['words'])}</h2>
<p>{e(T['words_lead'])}</p>
{words}
<h2>{e(T['try'])}</h2>
<p>{T['try_lead'].format(run=f"<code>{e(inputs['try_run'])}</code>", check=check)}</p>
{f"<p>{e(T['try_words'])}</p>{try_words}" if try_words else ""}
<h2>{e(T['lessons'])}</h2>
{md(lessons)}
<h2>{e(T['use'])}</h2>
<p>{e(T['use_text'].format(name=name))}</p>
<footer>Durweg · <code>{e(name)}</code></footer>
</main></body></html>
"""


def main(argv):
    if len(argv) != 1:
        sys.exit(__doc__)
    run = Path(argv[0]).resolve()
    for need in ("steps/1-method.md", "steps/2-steps.json", "steps/5-try.json", "steps/6-lessons.md"):
        if not (run / need).is_file():
            sys.exit(f"{need} is missing; write it first")
    name = load(run / "steps/2-steps.json")["name"]
    inputs = collect(run)
    out = run / "case" / f"{name}.html"
    out.parent.mkdir(parents=True, exist_ok=True)
    (run / "case/inputs.json").write_text(json.dumps(inputs, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    text = page(run, inputs).encode("utf-8")
    out.write_bytes(text)
    home = Path(os.environ.get("DURWEG_HOME") or Path.home() / "Durweg")
    copy = home / "cases" / f"{name}_{run.name}.html"
    copy.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(out, copy)
    rec = {"made": True, "html": f"case/{name}.html", "copy": str(copy),
           "sha256": hashlib.sha256(text).hexdigest()}
    (run / "steps/6-case.json").write_text(json.dumps(rec, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"case written: {out}\nkept in your library folder: {copy}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
