#!/usr/bin/env python3
"""Measure how much prose survived a rewrite verbatim.

A restructure that only moves paragraphs into new files passes both
check-docs.py and extract-facts.py while leaving the writing exactly as it
was. This script is the check for that: it reports, per file, the share of
substantial prose sentences that appear word-for-word in the pre-rewrite
snapshot.

Code blocks, tables and metadata lines are excluded — those are *supposed* to
survive unchanged. Only running prose is compared.

Usage:
    tools/prose-delta.py <baseline-dir> [current-dir]

A file reported at 70% verbatim was moved, not rewritten.
"""
from __future__ import annotations

import pathlib
import re
import sys

FENCE = re.compile(r"^\s*(?:```|~~~)")
MIN_WORDS = 8


def sentences(path: pathlib.Path) -> list[str]:
    """Return the substantial prose sentences of one Markdown file."""
    out, in_fence = [], False
    prose = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if FENCE.match(line):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        s = line.strip()
        if not s or s.startswith(("|", "#", ">", "**Status:", "**Applies to:",
                                  "**Verified on:", "**See also:")):
            continue
        prose.append(re.sub(r"^[-*]\s+|^\d+\.\s+", "", s))
    text = " ".join(prose)
    for raw in re.split(r"(?<=[.:!?])\s+(?=[A-Z`*\[(])", text):
        norm = " ".join(raw.split()).strip(" -—*")
        if len(norm.split()) >= MIN_WORDS:
            out.append(norm)
    return out


def main() -> int:
    if len(sys.argv) < 2:
        print(__doc__)
        return 2
    baseline = pathlib.Path(sys.argv[1])
    current = pathlib.Path(sys.argv[2] if len(sys.argv) > 2 else ".")

    old = set()
    for md in baseline.rglob("*.md"):
        old.update(sentences(md))

    rows = []
    for md in sorted(current.rglob("*.md")):
        if ".git" in md.parts or "templates" in md.parts:
            continue
        rel = md.relative_to(current)
        if rel.as_posix() in {"docs/STYLE.md", "CONTRIBUTING.md", "AGENTS.md"}:
            continue
        sents = sentences(md)
        if not sents:
            continue
        kept = [s for s in sents if s in old]
        rows.append((len(kept) / len(sents), len(kept), len(sents), rel))

    rows.sort(reverse=True)
    print(f"{'verbatim':>9}  {'kept':>5} {'total':>5}  file")
    for share, kept, total, rel in rows:
        flag = "  <-- moved, not rewritten" if share >= 0.70 else ""
        print(f"{share:>8.0%}  {kept:>5} {total:>5}  {rel}{flag}")

    if rows:
        tot_kept = sum(r[1] for r in rows)
        tot_all = sum(r[2] for r in rows)
        print(f"\noverall: {tot_kept}/{tot_all} sentences verbatim "
              f"({tot_kept / tot_all:.0%})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
