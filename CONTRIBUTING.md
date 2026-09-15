# Contributing

This repository is a field guide, not a wiki. Everything in it was hit on
real hardware, diagnosed, and verified before it was written down. That is
the whole value of the thing, and it is the bar for anything added to it.

## The one rule

**Do not document a fix you have not run.** If you have not applied it on the
machine and watched the symptom go away, it is not a guide — it is a
hypothesis, and hypotheses go in `notes/` with `**Status:** open`.

Corollary: never write a command you have not executed, a version number you
have not read off the system, or a measurement you have not taken. If a
number in this repo cannot be reproduced by running the command next to it,
the repo is worse than empty.

## Before you write anything

Decide which of the four document types you are writing. This is the first
decision, and everything else follows from it:

| You have… | Write a… | It goes in |
|---|---|---|
| a fix that works | how-to | `docs/how-to/` |
| an understanding of why it broke | explanation | `docs/explanation/` |
| a table of values, registers, drivers | reference | `docs/reference/` |
| an unfinished investigation | note | `notes/` |

Most debugging sessions produce **two** documents: the fix and the story
behind it. Split them. The reader with a frozen laptop wants the first; the
reader who wants to fix the next machine wants the second. Serving both from
one file serves neither — see [the style guide](docs/STYLE.md) for why this
repository was restructured around that split.

Start from a template:

```bash
cp docs/templates/how-to.md docs/how-to/stop-the-thing-breaking.md
```

## Writing it

Read [docs/STYLE.md](docs/STYLE.md). It is short and it is enforced.

The parts people get wrong most often:

- **The rollback section is mandatory** on every how-to. Every guide here
  edits a bootloader, a kernel module or a system daemon. Writing the
  rollback is how you discover that your fix left something behind.
- **Keep the negative results.** "APST is not ASPM and changing it does
  nothing" is worth more than another paragraph about the fix that worked.
- **Date everything.** `**Verified on:**` ends with an ISO date. A claim
  about kernel behaviour with no date attached is not checkable a year later.
- **Sentence case headings, 80-column prose, no horizontal rules.**

## Before you open a pull request

```bash
tools/check-docs.py
```

It must exit clean. It checks the mechanical rules — metadata block, section
order, heading case, line width, fence language tags, link resolution, shell
prompts in code blocks, ISO dates — and that every document under `docs/` can
be reached by following links from the README. Add `--warnings` to see the
softer checks, such as a destructive command with no backup beside it.

**Everything must be reachable from the README.** If you add a guide, add its
row to the symptom table. A guide that only a directory listing will reveal
is a guide nobody will find at the moment they need it.

If you moved or split a document, also confirm no technical content was lost:

```bash
git worktree add ../base main
tools/extract-facts.py ../base --missing-from .
```

Every code block, inline command and identifier in the repository appears in
that inventory. A restructure should move facts between files, never drop one.
The check allows for rewrapped prose and rewritten comments — a fact only
counts as lost when its text appears nowhere in the tree at all.

Both checks also run in GitHub Actions on every pull request. The style check
must pass. The fact check is advisory: retiring a guide on purpose is a normal
change here, so it reports what was dropped into the job summary for a
reviewer to look at rather than blocking the merge.

## What a good pull request looks like

- One fix, or one guide, per pull request.
- The hardware it was verified on, in the metadata block, with a date.
- Kernel and package versions, exactly as the system reports them.
- If it applies beyond Monster — to the wider Clevo, TUXEDO, XMG or
  Schenker family on the same barebones — say so, and say whether that is
  tested or expected.

Changes are reviewed by the maintainers listed in
[.github/CODEOWNERS](.github/CODEOWNERS).

## Reporting something that stopped working

Kernel and driver updates break these guides regularly. If a guide no longer
works, that is a valuable report: open an issue with the guide's file name,
your kernel and package versions, and what you observed instead. Fixes that
have been overtaken get `**Status:** superseded` and a link forward, rather
than being deleted — the history of what used to be necessary is part of the
record.

## Language

English throughout: documents, code comments, commit messages and repository
metadata. The hardware is sold in Turkey; the people stuck on it are not all
Turkish speakers.
