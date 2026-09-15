# Stop the thing from doing the broken thing

**Status:** verified
**Applies to:** Monster TULPAR T6 V2.1 (AI Creator)
**Verified on:** Ubuntu 26.04 · kernel 7.0.0-15 · 2026-09-15
**Symptom:** what the reader sees, in their words, specific enough that they
can recognise their own problem in one line.
**See also:** [the style guide](../STYLE.md)

One paragraph, at most three sentences: what this guide changes and what the
reader gets. No history, no diagnosis — link to the explanation document for
that.

## Before you start

- Packages, hardware or prior guides this depends on.
- Anything to back up before the first destructive command.

## Confirm the diagnosis

Commands that prove the reader has this exact problem and not a lookalike.

```bash
journalctl -k | grep -E "the smoking gun"
# expect: the line that confirms it
```

## Fix

### 1. First step, named by what it achieves

```bash
sudo cp /etc/example.conf /etc/example.conf.bak
sudo tee /etc/example.conf <<'CONF'
setting = value
CONF
```

### 2. Second step

State any machine-specific value on the spot, with the command that finds the
reader's own.

## Verify

```bash
some-command --check
# expect: the output that means it worked
```

## Roll back

Undo every change made above, in reverse order.

```bash
sudo mv /etc/example.conf.bak /etc/example.conf
```

## Trade-offs

What this costs. Battery, boot time, a feature that stops working.

## Troubleshooting

**The exact error the reader will see**

What it means and what to do about it.
