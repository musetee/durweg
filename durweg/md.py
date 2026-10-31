"""Strict, small Markdown reading for the sections and table gates (design 4)."""

import re

PLACEHOLDERS = {"todo", "tbd", "…", "...", "-", "?", "xxx", "fixme"}
HEADING = re.compile(r"^(#{1,6})\s+(.*?)\s*#*\s*$")
FENCE = re.compile(r"^\s*(```|~~~)")
ITEM = re.compile(r"^\s*(?:[-*+]|\d+[.)])\s+(.*)$")


def empty(text):
    t = (text or "").strip()
    return not t or t.lower() in PLACEHOLDERS


def lines_outside_code(text):
    """(line, in_code) pairs; fenced code blocks are skipped by the gates."""
    out, fence = [], None
    for line in text.splitlines():
        m = FENCE.match(line)
        if m:
            if fence is None:
                fence = m.group(1)
            elif m.group(1) == fence:
                fence = None
            out.append((line, True))
            continue
        out.append((line, fence is not None))
    return out


def sections(text):
    """List of (level, title, body_lines) for ATX headings outside code blocks."""
    result, cur = [], None
    for line, code in lines_outside_code(text):
        m = None if code else HEADING.match(line)
        if m:
            cur = (len(m.group(1)), m.group(2).strip(), [])
            result.append(cur)
        elif cur is not None and not code:
            cur[2].append(line)
    return result


def section_body(secs, idx):
    """Body of section idx including its subsections (until a heading of the same or higher level)."""
    level = secs[idx][0]
    body = list(secs[idx][2])
    for lv, title, lines in secs[idx + 1:]:
        if lv <= level:
            break
        body.append("#" * lv + " " + title)
        body.extend(lines)
    return body


def find(text, title):
    """Indices of headings exactly equal to title."""
    secs = sections(text)
    return secs, [i for i, s in enumerate(secs) if s[1] == title]


def items(body):
    return [m.group(1) for m in (ITEM.match(line) for line in body) if m]


def first_table(body):
    """(columns, rows) of the first GFM table in body, or None."""
    rows = [line for line in body]
    for i in range(len(rows) - 1):
        if "|" in rows[i] and re.match(r"^\s*\|?\s*:?-{3,}:?\s*(\|\s*:?-{3,}:?\s*)*\|?\s*$", rows[i + 1]):
            cols = _cells(rows[i])
            data = []
            for line in rows[i + 2:]:
                if "|" not in line or not line.strip():
                    break
                data.append(_cells(line))
            return cols, data
    return None


def _cells(line):
    s = line.strip()
    if s.startswith("|"):
        s = s[1:]
    if s.endswith("|"):
        s = s[:-1]
    return [c.strip() for c in re.split(r"(?<!\\)\|", s)]
