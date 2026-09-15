#!/usr/bin/env python3
"""Check every Markdown file against docs/STYLE.md.

Only the mechanical rules live here — the ones marked [checked] in the style
guide. Judgement calls (is this really a how-to? does the rollback actually
undo the fix?) stay with the reviewer.

Usage:
    tools/check-docs.py [path ...]     # default: whole repo
    tools/check-docs.py --warnings     # show warnings too

Exit status is 1 if any error was reported.
"""
from __future__ import annotations

import argparse
import pathlib
import re
import sys

MAX_WIDTH = 80
STATUSES = {"verified", "mitigated", "open", "abandoned", "superseded"}
META_ORDER = ["Status", "Applies to", "Verified on", "Symptom", "See also"]
HOWTO_ORDER = [
    "Before you start",
    "Confirm the diagnosis",
    "Fix",
    "Verify",
    "Roll back",
    "Trade-offs",
    "Troubleshooting",
]
HOWTO_REQUIRED = {"Fix", "Verify", "Roll back"}

ISO_DATE = re.compile(r"\b\d{4}-\d{2}-\d{2}\b")
BAD_DATE = re.compile(
    r"\b(\d{1,2}/\d{1,2}/\d{2,4}"
    r"|(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s+\d{1,2},?\s+\d{4})\b"
)
FENCE = re.compile(r"^\s*(```|~~~)\s*(\S*)")
HEADING = re.compile(r"^(#{1,6})\s+(.*)$")
META = re.compile(r"^\*\*([A-Z][A-Za-z ]*):\*\*\s*(.*)$")
LINK = re.compile(r"\[([^\]]*)\]\(([^)]+)\)")
PROMPT = re.compile(r"^\s*\$\s+\S|^\s*#\s+(sudo|apt|apt-get|pacman|systemctl|modprobe|dkms)\b")
OLD_EXPECT = re.compile(r"^\s*#\s*(Expected|Should (show|read|display|be))\b")
DESTRUCTIVE = re.compile(r"\b(sed -i|rm -[rf]|truncate|mkfs|dd if=)\b|\btee\s+/etc/")
BACKUP = re.compile(r"\bcp\b.*\.(bak|backup|orig)\b|\bcp\b.*\.bak")
VAGUE_LINK = {"here", "this", "link", "this link", "read more", "click here", "doc", "docs"}

# Multi-word proper nouns whose internal capitals are correct. Stripped from a
# heading before the sentence-case check so the product name does not trip it.
PROPER_PHRASES = [
    "TUXEDO Control Center",
    "Control Center",
    "Windows Setup",
    "Color Assistant",
    "Intel AI Boost",
]

# Words that must not be capitalised mid-heading. Anything not on this list is
# assumed to be a proper noun or an identifier and is left alone, which keeps
# the check quiet on TUXEDO, PCIe, D-Bus, Hyprland and friends.
COMMON = set(
    """a about add after all always an and any are as at back bad be because
    been before behind best between boot both broken build but by can change
    check come comes control could dead detect did do does doing done down
    during each early else enable enabled every everything fail fails find
    first fix fixed for found free from full get gets give go goes had half
    happen happens hard has have help her here how if in into is it its just
    keep kernel know last late later left less let like live load loads look
    lose made make makes many may mean means might missing more most much must
    my need needs never new no not nothing now of off on once one only open
    or other our out over own part pick power put ran read real really restart
    right run runs same save say see set sets should show shows side since so
    some something start starts state stay still stop stops such take takes
    tell than that the their them then there these they thing think this those
    three time to too try turn two under until up use used uses using very
    wait want was way we well what when where which while who why will with
    work works would write wrong you your""".split()
)


class Report:
    def __init__(self) -> None:
        self.errors = 0
        self.warnings = 0

    def error(self, path, line, rule, msg) -> None:
        self.errors += 1
        print(f"{path}:{line}: error [{rule}] {msg}")

    def warn(self, path, line, rule, msg, show) -> None:
        self.warnings += 1
        if show:
            print(f"{path}:{line}: warning [{rule}] {msg}")


def split_fences(lines):
    """Yield (index, line, in_fence, fence_lang) for each line."""
    in_fence, lang = False, ""
    for i, line in enumerate(lines, 1):
        m = FENCE.match(line)
        if m:
            if in_fence:
                in_fence, lang = False, ""
                yield i, line, "close", ""
            else:
                in_fence, lang = True, m.group(2)
                yield i, line, "open", lang
            continue
        yield i, line, in_fence, lang


def check_file(path: pathlib.Path, root: pathlib.Path, rep: Report, show_warn: bool) -> None:
    rel = path.relative_to(root)
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()
    if not lines:
        rep.error(rel, 1, "empty", "file is empty")
        return

    # --- file name -------------------------------------------------------
    if not re.fullmatch(r"[a-z0-9]+(-[a-z0-9]+)*\.md", path.name) and path.name not in {
        "README.md",
        "CONTRIBUTING.md",
        "AGENTS.md",
        "STYLE.md",
        "MEMORY.md",
    }:
        rep.error(rel, 1, "filename", f"file name must be lowercase-hyphenated: {path.name}")

    # --- headings --------------------------------------------------------
    h1s, headings = [], []
    for i, line, in_fence, _lang in split_fences(lines):
        if in_fence in (True, "open", "close"):
            continue
        m = HEADING.match(line)
        if not m:
            continue
        level, title = len(m.group(1)), m.group(2).strip()
        headings.append((i, level, title))
        if level == 1:
            h1s.append(i)
        bare_title = re.sub(r"`[^`]*`", "", title)
        for phrase in PROPER_PHRASES:
            bare_title = bare_title.replace(phrase, "")
        words = bare_title.split()
        if words and re.fullmatch(r"\d+[.)]", words[0]):
            words = words[1:]
        for w in words[1:]:
            bare = w.strip("*_()[],.:;\"'—–-")
            if bare[:1].isupper() and bare.lower() in COMMON:
                rep.error(rel, i, "sentence-case", f"heading should be sentence case: {bare!r} in {title!r}")
                break

    if len(h1s) != 1:
        rep.error(rel, h1s[1] if len(h1s) > 1 else 1, "h1", f"expected exactly one H1, found {len(h1s)}")
    elif h1s[0] != 1:
        rep.error(rel, h1s[0], "h1", "H1 must be the first line of the file")

    # --- metadata block --------------------------------------------------
    is_doc = rel.parts[:1] == ("docs",) and rel.name not in {"STYLE.md"}
    is_note = rel.parts[:1] == ("notes",)
    is_howto = rel.parts[:2] == ("docs", "how-to") or rel.as_posix() == "docs/templates/how-to.md"
    meta = {}
    seen_order = []
    last_key = None
    for i, line in enumerate(lines[1:16], 2):
        m = META.match(line)
        if m:
            last_key = m.group(1)
            meta[last_key] = m.group(2)
            seen_order.append(last_key)
        elif last_key and line.strip() and not line.startswith("#"):
            # Continuation of the previous field's value.
            meta[last_key] += " " + line.strip()
        elif not line.strip():
            last_key = None
    if is_note:
        # Notes are working state, not documentation: they need a status so a
        # reader knows whether to trust them, but nothing else is required.
        if "Status" not in meta:
            rep.error(rel, 2, "metadata", "missing **Status:** field")
        elif meta["Status"].strip() not in STATUSES:
            rep.error(rel, 2, "metadata", f"Status must be one of {sorted(STATUSES)}, got {meta['Status']!r}")
        if "Symptom" in meta:
            rep.error(rel, 2, "metadata", "**Symptom:** belongs only on how-to documents")
    if is_doc:
        if "Status" not in meta:
            rep.error(rel, 2, "metadata", "missing **Status:** field")
        elif meta["Status"].strip() not in STATUSES:
            rep.error(rel, 2, "metadata", f"Status must be one of {sorted(STATUSES)}, got {meta['Status']!r}")
        if "Applies to" not in meta:
            rep.error(rel, 2, "metadata", "missing **Applies to:** field")
        if "Verified on" not in meta:
            rep.error(rel, 2, "metadata", "missing **Verified on:** field")
        elif not ISO_DATE.search(meta["Verified on"]):
            rep.error(rel, 2, "metadata", "**Verified on:** must end with an ISO date (YYYY-MM-DD)")
        ranks = [META_ORDER.index(k) for k in seen_order if k in META_ORDER]
        if ranks != sorted(ranks):
            rep.error(rel, 2, "metadata", f"metadata fields out of order: {seen_order}")
        if is_howto and "Symptom" not in meta:
            rep.error(rel, 2, "metadata", "how-to documents need a **Symptom:** field")
        if not is_howto and "Symptom" in meta:
            rep.error(rel, 2, "metadata", "**Symptom:** belongs only on how-to documents")

    # --- how-to section structure ---------------------------------------
    if is_howto:
        h2 = [(i, t) for i, lvl, t in headings if lvl == 2]
        names = [t for _i, t in h2]
        unknown = [t for t in names if t not in HOWTO_ORDER]
        for i, t in h2:
            if t in unknown:
                rep.error(rel, i, "sections", f"unknown H2 {t!r}; allowed: {HOWTO_ORDER}")
        known = [t for t in names if t in HOWTO_ORDER]
        ranks = [HOWTO_ORDER.index(t) for t in known]
        if ranks != sorted(ranks):
            rep.error(rel, h2[0][0] if h2 else 1, "sections", f"sections out of order: {known}")
        for req in HOWTO_ORDER:
            if req in HOWTO_REQUIRED and req not in names:
                rep.error(rel, 1, "sections", f"missing required section '## {req}'")

    # --- body ------------------------------------------------------------
    block_start, block_body = 0, []
    for i, line, in_fence, lang in split_fences(lines):
        if in_fence == "open":
            if not lang:
                rep.error(rel, i, "fence-lang", "fenced block has no language tag")
            block_start, block_body = i, []
            continue
        if in_fence == "close":
            joined = "\n".join(block_body)
            if DESTRUCTIVE.search(joined) and not BACKUP.search(joined):
                rep.warn(rel, block_start, "backup", "destructive command with no backup in the same block", show_warn)
            continue
        if in_fence:
            block_body.append(line)
            # A `text` block may be a terminal transcript, prompts and all.
            # Only blocks presented as runnable commands must be paste-ready.
            if lang in {"bash", "sh", "zsh", "shell"} and PROMPT.match(line):
                rep.error(rel, i, "prompt", "code block contains a shell prompt; commands must be paste-ready")
            if OLD_EXPECT.match(line):
                rep.error(rel, i, "expect", "expected output must be written as '# expect: ...'")
            continue

        if line.strip() == "---" and i > 1:
            rep.error(rel, i, "hrule", "horizontal rules are not used in this repo; use headings")
        if len(line) > MAX_WIDTH:
            stripped = line.strip()
            is_table = stripped.startswith("|")
            # A link target cannot be wrapped. Judge the line by what is left
            # once the targets are removed.
            without_targets = re.sub(r"\]\([^)]*\)", "]", line)
            only_link = len(without_targets) <= MAX_WIDTH
            # A single code span on its own line is usually a verbatim error
            # message. Wrapping it would stop it matching what the reader
            # pasted, so it is allowed to run long.
            lone_code = bool(re.fullmatch(r"\*{0,2}`[^`]+`\*{0,2}[.,]?", stripped))
            if not (is_table or only_link or lone_code):
                rep.error(rel, i, "width", f"line is {len(line)} columns, wrap prose at {MAX_WIDTH}")
        if BAD_DATE.search(line):
            rep.error(rel, i, "date", "dates must be ISO (YYYY-MM-DD)")
        # A link inside a code span is an example, not a link.
        for textpart, target in LINK.findall(re.sub(r"`[^`]*`", "", line)):
            if textpart.strip().lower().strip(".") in VAGUE_LINK:
                rep.error(rel, i, "link-text", f"link text {textpart!r} does not describe the destination")
            if target.startswith(("http://", "https://", "#", "mailto:")):
                continue
            dest = (path.parent / target.split("#")[0]).resolve()
            if not dest.exists():
                rep.error(rel, i, "link", f"relative link does not resolve: {target}")


def check_reachable(root: pathlib.Path, rep: Report) -> None:
    """Every document must be findable by walking links from the README.

    A guide nobody can navigate to is not documentation, it is a file. This
    walks the relative-link graph outward from README.md and reports anything
    under docs/ or notes/ that it never reaches.
    """
    readme = root / "README.md"
    if not readme.exists():
        rep.error("README.md", 1, "reachable", "README.md is missing")
        return

    def links_from(path: pathlib.Path) -> set[pathlib.Path]:
        out = set()
        in_fence = False
        for line in path.read_text(encoding="utf-8").splitlines():
            if FENCE.match(line):
                in_fence = not in_fence
                continue
            if in_fence:
                continue
            for _text, target in LINK.findall(re.sub(r"`[^`]*`", "", line)):
                if target.startswith(("http://", "https://", "#", "mailto:")):
                    continue
                dest = (path.parent / target.split("#")[0]).resolve()
                # A link to a directory does not count: browsing a folder
                # listing is not finding the guide you needed.
                if dest.suffix == ".md" and dest.is_file():
                    out.add(dest)
        return out

    seen, queue = {readme.resolve()}, [readme]
    while queue:
        for nxt in links_from(queue.pop()):
            if nxt not in seen:
                seen.add(nxt)
                queue.append(nxt)

    for doc in sorted(root.rglob("*.md")):
        if ".git" in doc.parts or "templates" in doc.parts:
            continue
        rel = doc.relative_to(root)
        # notes/ is working state, not documentation — browsing it is fine.
        if rel.parts[0] != "docs" or rel.name == "STYLE.md":
            continue
        if doc.resolve() not in seen:
            rep.error(rel, 1, "reachable",
                      "not reachable by following links from README.md")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("paths", nargs="*", default=None)
    ap.add_argument("--warnings", action="store_true", help="also print warnings")
    args = ap.parse_args()

    root = pathlib.Path(__file__).resolve().parent.parent
    if args.paths:
        targets = []
        for arg in args.paths:
            path = pathlib.Path(arg).resolve()
            if path.is_dir():
                targets += [q for q in path.rglob("*.md") if ".git" not in q.parts]
            elif path.suffix == ".md":
                targets.append(path)
    else:
        targets = [p for p in root.rglob("*.md") if ".git" not in p.parts]

    rep = Report()
    for path in sorted(targets):
        check_file(path, root, rep, args.warnings)
    if not args.paths:
        check_reachable(root, rep)

    print(f"\n{len(targets)} files, {rep.errors} errors, {rep.warnings} warnings")
    return 1 if rep.errors else 0


if __name__ == "__main__":
    sys.exit(main())
