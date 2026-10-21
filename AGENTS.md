# AGENTS.md

Operating instructions for coding agents working in this repository. Read
[docs/STYLE.md](docs/STYLE.md) before editing any Markdown; this file covers
only what an agent needs on top of it.

## What this repository is

Hardware debugging field notes for Monster (Clevo/TONGFANG-based) laptops
running Linux. It is a support repository for that hardware and nothing else —
personal dotfiles, desktop theming and abandoned non-Linux side quests do not
belong in it. Every claim in it was produced by running a command on real
hardware. There is no build, no test suite and no application code apart from
one out-of-tree kernel module in `drivers/abra-a5-fan/`.

The consequence: **you cannot verify anything here by reasoning about it.**
A kernel version, a register offset, a fan duty value or a D-Bus method name
is either something the maintainer measured, or it is wrong.

## Hard constraints

1. **Never invent a technical fact.** Do not add, adjust or "correct" a
   command, path, package name, version number, register offset, sysfs
   attribute, D-Bus interface or measurement. If something looks wrong, say
   so in your report — do not fix it.
2. **Preserve every fact when restructuring.** Moving content between files,
   splitting a document, or rewriting prose must leave every fenced code
   block and every inline `code` token present somewhere in the tree.
   Verify with `tools/extract-facts.py` (see below).
3. **Never run a command that changes this machine's hardware
   configuration.** The repository is full of commands that patch kernel
   modules, edit GRUB and restart system daemons. They are documentation.
   Do not execute them.
4. **Do not commit, push, tag, or amend.** Leave changes in the working tree
   for review.
5. **Do not create files outside the repository layout below.** Scratch work
   goes in a temporary directory, not in the repository root.

## Layout

```text
README.md              entry point and symptom index
CONTRIBUTING.md        how humans add to this
AGENTS.md              this file
docs/STYLE.md          the writing rules, enforced by tools/check-docs.py
docs/templates/        how-to.md, explanation.md, reference.md
docs/how-to/           action: one task per file
docs/explanation/      why it breaks, how it was diagnosed
docs/reference/        tables and lookups, no narrative
notes/                 open investigations, abandoned efforts, ideas
tools/                 check-docs.py, extract-facts.py
drivers/               out-of-tree kernel module (C, DKMS): ABRA A5 fan
bios-dumps/            UEFI Setup variable dumps
firmware-cache/        gitignored; binaries are not published
```

Picking the right directory is the main judgement call. A document that
tells the reader what to run is a how-to. A document that tells them why is
an explanation. A document that is looked up rather than read is a
reference. An unfinished investigation is a note, not documentation.

## Checks you must run

Both scripts are dependency-free Python 3 and safe to run.

```bash
tools/check-docs.py
# expect: "N files, 0 errors"
```

`check-docs.py` enforces the mechanical rules in the style guide: metadata
block contents and order, how-to section names and order, sentence-case
headings, 80-column prose, fence language tags, relative links that resolve,
ISO dates, and shell prompts in code blocks. Run with no arguments it also
checks that every document under `docs/` is reachable by following links from
`README.md` — a guide nobody can navigate to is a file, not documentation.
Pass `--warnings` for the softer checks. It must exit clean before you report
a task finished.

```bash
tools/extract-facts.py <baseline-dir> --missing-from .
# expect: "0 facts present in <baseline-dir> are absent from ."
```

`extract-facts.py` inventories every code block, inline code token and
identifier in the repository. Snapshot the tree **before** you start any
restructure, then run the comparison after. Facts may move between files; a
fact whose text appears nowhere in the tree is lost and must be restored. The
comparison tolerates rewrapped prose and rewritten code comments, so a
difference it reports is a real one — investigate every line before dismissing
it.

Both checks also run in CI, defined in `.github/workflows/docs.yml`. The
style job must pass; the fact job is advisory and writes its findings to the
job summary.

```bash
tools/prose-delta.py /path/to/pre-rewrite-snapshot .
# expect: no file above 40% verbatim after a rewrite task
```

`prose-delta.py` reports, per file, the share of prose sentences that survived
a rewrite word-for-word. Facts are supposed to survive unchanged; **prose is
not**. A file at 75% verbatim was moved into a new skeleton, not rewritten,
and does not satisfy a rewrite task. Code blocks, tables and metadata lines
are excluded from the measurement, so there is no tension between this check
and the constraint that facts stay byte-identical.

## Editing rules

- Hard-wrap prose at 80 columns. Never reflow a code block, a table, or a
  URL.
- Never reword the inside of a fenced code block, including its comments,
  unless the task explicitly says to.
- When you split a document, the how-to keeps the commands and the
  explanation keeps the reasoning. Link them with the `**See also:**`
  metadata field in both directions.
- When a fix has an Ubuntu path and an Arch path, put the two package
  commands side by side in the same step. Do not append a second
  distribution as a trailing section.
- Update `README.md`'s symptom table whenever a file is added, moved or
  renamed. Every guide must be reachable from it.

## Reporting

Report what you changed, per file. If you were asked to measure something,
paste the raw command output rather than describing it. If you could not
complete part of a task, say which part and why — do not silently narrow the
scope.
