# Style guide

Every document in this repository follows these rules. They exist so that a
guide written at 2 a.m. in the middle of a debugging session still reads like
the rest of the repo a year later, and so that a reader in the same hole can
find the command they need without reading a story first.

`tools/check-docs.py` enforces the mechanical half of this guide. Run it
before you commit. Rules it can check are marked **[checked]**.

## 1. Pick the document type first

This repository uses [Diátaxis](https://diataxis.fr/). Before writing
anything, decide which of these you are writing, because the whole shape of
the document follows from it. If a draft wants to be two of them, it is two
documents.

| Type | Directory | Serves | Answers |
|---|---|---|---|
| How-to | `docs/how-to/` | someone with a broken machine, now | "How do I fix this?" |
| Explanation | `docs/explanation/` | someone who wants to understand | "Why does this happen?" |
| Reference | `docs/reference/` | someone looking a value up | "What is the register at 0xE1C?" |
| Note | `notes/` | future you | "Where did I leave this?" |

`notes/` is deliberately outside Diátaxis. Investigation logs, abandoned
efforts and open questions are not documentation for a reader — they are
working state, and pretending otherwise is what turned several guides in this
repo into half-guide, half-diary. Keep them, but keep them separate.

**The test for a how-to:** a competent Linux user who has your symptom should
be able to act on every line. The moment a paragraph is there to teach rather
than to be executed, it belongs in an explanation document, linked from the
top of the how-to. Diátaxis: "no digression, explanation, teaching."

## 2. Title and file name

- **[checked]** One `# ` heading per file, on line 1.
- **[checked]** Sentence case for every heading, at every level. "Why the
  greeter loses the race", not "Why The Greeter Loses The Race". Keep the
  case of proper nouns and identifiers: `tccd`, NVIDIA, PCIe, Hyprland.
- How-to titles name the **outcome**, in the imperative: "Stop random hard
  freezes on a DRAM-less NVMe". Not "Fix:", not "NVMe issues".
- Explanation titles name the **subject**: "Why a DRAM-less NVMe freezes the
  whole machine".
- Reference titles name the **thing**: "ABRA A5 EC field map".
- **[checked]** File names are lowercase, hyphenated, and match the title:
  `stop-random-hard-freezes-nvme.md`. No `fix-` prefix — the directory
  already says what kind of document it is.

## 3. The metadata block

- **[checked]** Every document under `docs/` opens with a metadata block
  directly after the title: bold key, colon, value, one field per line, in
  this order. Omit a field entirely rather than writing "n/a".

```markdown
**Status:** verified
**Applies to:** Monster TULPAR T6 V2.1 (AI Creator); any Clevo NH5x/NH7x shell
**Verified on:** Ubuntu 26.04 · kernel 7.0.0-15 · nvidia-driver-580-open · 2026-07-05
**Symptom:** the whole machine hard-freezes at random — no cursor, no VT
switch, no SysRq, nothing in the journal.
**See also:** [why this happens](../explanation/nvme-aspm-freezes.md)
```

- **[checked]** `Status:` is exactly one of `verified`, `mitigated`, `open`,
  `abandoned`, `superseded`. It is the first thing a reader needs and the
  first thing that goes stale.
  - `verified` — applied on real hardware and confirmed working.
  - `mitigated` — the symptom is gone but the cause is not fixed.
  - `open` — diagnosed, no working fix. Say so in the title too.
  - `abandoned` — no longer pursued. Say why in the first paragraph.
  - `superseded` — link the replacement in `See also:`.
- `Symptom:` is required on how-to documents and forbidden elsewhere.
- **[checked]** `Verified on:` ends with an ISO date. Everything in this repo
  is a claim about a moving target; an undated claim is worthless. Fields are
  separated by ` · `.
- **[checked]** Dates anywhere in the repo are ISO: `2026-07-05`.

## 4. Section structure

**[checked]** A how-to uses these H2 sections, in this order. `Fix`,
`Verify` and `Roll back` are mandatory; the rest are optional.

| Section | Contents |
|---|---|
| `## Before you start` | prerequisites, packages, backups to take |
| `## Confirm the diagnosis` | commands that prove the reader has *this* problem |
| `## Fix` | the steps, as `### 1. …`, `### 2. …` |
| `## Verify` | commands that prove it worked, with expected output |
| `## Roll back` | how to undo every change made above |
| `## Trade-offs` | what this costs — battery, boot time, warranty |
| `## Troubleshooting` | `**symptom in bold**` then the remedy |

**Roll back is mandatory and is not a formality.** Every guide here tells
someone to modify a bootloader, a kernel module or a system daemon. A guide
that cannot be undone is a trap, and writing the rollback section is how you
find out that your fix left something behind.

An explanation opens with `## In short` — three sentences that a reader can
stop after — and is free-form below that. A reference is tables and lists,
ordered for lookup, with no narrative.

## 5. Commands and output

- **[checked]** Every fenced block carries a language tag: `bash`, `ini`,
  `json`, `c`, `python`, `text`. Use `text` for output and diagrams.
- **[checked]** No shell prompts. Write `sudo nvme smart-log /dev/nvme1`, not
  `$ sudo nvme ...` or `# nvme ...`. A reader should be able to select the
  whole block and paste it.
- Root is explicit `sudo` on the line that needs it, never an instruction to
  "become root first".
- **[checked]** Expected output goes in the same block as a comment starting
  `# expect:`, not in a second block and not in prose:

```bash
cat /proc/cmdline | tr ' ' '\n' | grep aspm
# expect: pcie_aspm=off
```

- **[checked]** Any command that overwrites or deletes a file is immediately
  preceded, in the same block, by the command that backs it up:

```bash
sudo cp /etc/default/grub /etc/default/grub.bak
sudo sed -i 's/.../.../' /etc/default/grub
```

- Prefer one command per idea. A ten-line block that does five things cannot
  be partially recovered when step three fails.
- Real values from real hardware, always. If a path is machine-specific
  (`/dev/nvme1`, `card1-eDP-1`, PCI addresses), say so on the spot and give
  the command that finds the reader's own.

## 6. Prose

The audience is a competent Linux user who is annoyed and in a hurry. Write
for them.

- Second person, active voice, present tense. "Mask the service", not "the
  service should be masked" or "we will now mask the service".
- Put the condition before the instruction: "If VMD is enabled
  in your BIOS, verify with `lspci -vv`", not the reverse. A reader who acts
  on the first half of the sentence has already acted.
- Lead with what to do; explain after, or link away. A how-to step that opens
  with two sentences of background has buried its own instruction.
- Cut hedges — "it seems that", "you may want to", "basically". If it is
  uncertain, say what is uncertain and what would settle it.
- Keep the findings that cost you a weekend. "If your freeze logs look like
  memory corruption but memtest is clean, check the disk's link power
  management before buying new DIMMs" is the single most valuable sentence in
  that guide. Findings like that belong in the explanation document, stated
  once, and linked from the how-to.
- Never delete a negative result. "`nvme_core.default_ps_max_latency_us=0`
  does not fix this" saves the next reader an evening.
- English throughout, including comments, commit messages and repository
  metadata.

## 7. Markdown mechanics

- **[checked]** Hard-wrap prose at 80 columns. Do not wrap code blocks,
  tables, or long URLs.
- **[checked]** No `---` horizontal rules. Headings already separate sections;
  the rules in this repo were placed by feel and no two files agreed.
- **[checked]** Links are relative and must resolve — a link written as
  `[the driver map](../reference/driver-map.md)` is checked against the
  filesystem.
- **[checked]** Link text describes the destination. Never `see [here](x.md)`.
- Tables for anything with more than two parallel attributes. Prose that
  lists four registers and their states is a table that has not been written
  yet.
- Blockquotes (`>`) are for warnings and asides only, not for emphasis.
- Use `**bold**` for UI elements, `` `code` `` for anything typed or read by
  a machine: paths, commands, package names, kernel modules, sysfs
  attributes, D-Bus names, register names.

## 8. Multiple distributions and machines

Several fixes now exist for both Ubuntu and Arch, and for more than one SKU.
Do not bolt a second distribution onto the end of a guide as an "Arch port"
section — that is how `fix-keyboard-touchpad.md` grew to 500 lines with its
Ubuntu steps and its Arch steps four screens apart.

- If the *procedure* is the same and only package names differ, keep one
  document and give the per-distribution commands side by side inside the
  relevant step.
- If the procedure genuinely differs, write two documents and link them from
  each other's `See also:` field.
- State the machine in `Applies to:`, and say plainly when a fix is expected
  to work on the wider Clevo/TUXEDO/XMG family rather than only on Monster.
