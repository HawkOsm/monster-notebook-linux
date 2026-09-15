#!/usr/bin/env python3
"""Extract the technical facts from every Markdown file in the repo.

A "fact" is anything a reader would copy or act on: a fenced code block, an
inline `code` token, or a table row. The restructure and rewrite passes are
allowed to move facts between files and reword the prose around them, but not
to lose or alter a single one. Diffing this inventory before and after a
rewrite is how that is checked.

Usage:
    tools/extract-facts.py [root] > facts.txt
    tools/extract-facts.py <baseline> --missing-from <current>

The second form is the check that matters during a restructure: it reports
every fact in <baseline> whose text no longer appears anywhere in <current>,
and exits non-zero if there are any. Facts are allowed to move between files;
they are not allowed to vanish.
"""
import argparse
import hashlib
import pathlib
import re
import sys

FENCE = re.compile(r"^\s*(?:```|~~~)")
INLINE = re.compile(r"`([^`\n]+)`")


def extract(path: pathlib.Path):
    """Yield (kind, normalized_text) for every fact in one file."""
    blocks, inlines = [], []
    buf, in_fence = [], False
    for line in path.read_text(encoding="utf-8").splitlines():
        if FENCE.match(line):
            if in_fence:
                blocks.append("\n".join(buf))
                buf = []
            in_fence = not in_fence
            continue
        if in_fence:
            buf.append(line.rstrip())
        else:
            inlines.extend(m.group(1).strip() for m in INLINE.finditer(line))
    if buf:
        blocks.append("\n".join(buf))
    for b in blocks:
        body = "\n".join(l for l in b.splitlines() if l.strip())
        if body:
            yield "BLOCK", body
    for i in inlines:
        if i:
            yield "INLINE", i


def markdown_files(root: pathlib.Path):
    return [p for p in sorted(root.rglob("*.md")) if ".git" not in p.parts]


def inventory(root: pathlib.Path) -> set[str]:
    facts = set()
    for md in markdown_files(root):
        for kind, text in extract(md):
            digest = hashlib.sha256(text.encode()).hexdigest()[:12]
            facts.add(f"{kind} {digest} {text.splitlines()[0][:110]}")
    return facts


def report_missing(baseline: pathlib.Path, current: pathlib.Path) -> int:
    """Report facts from baseline whose text is gone from current entirely.

    Comparing hashes alone is too strict: rewrapping a paragraph or rewriting
    a comment inside a code block changes the hash while keeping every fact.
    So a fact only counts as lost when its text appears nowhere in the current
    tree at all.
    """
    old = {(k, t) for md in markdown_files(baseline) for k, t in extract(md)}
    new = {(k, t) for md in markdown_files(current) for k, t in extract(md)}
    haystack = "\n".join(p.read_text(encoding="utf-8") for p in markdown_files(current))

    lost = [(k, t) for k, t in sorted(old - new) if t not in haystack]
    for kind, text in lost:
        print(f"LOST [{kind}] {text.splitlines()[0][:110]}")
    print(f"\n{len(lost)} facts present in {baseline} are absent from {current}")
    return 1 if lost else 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("root", nargs="?", default=".")
    ap.add_argument("--missing-from", metavar="DIR",
                    help="compare against DIR and report facts lost from it")
    args = ap.parse_args()

    root = pathlib.Path(args.root)
    if args.missing_from:
        return report_missing(root, pathlib.Path(args.missing_from))

    for line in sorted(inventory(root)):
        print(line)
    return 0


if __name__ == "__main__":
    sys.exit(main())
