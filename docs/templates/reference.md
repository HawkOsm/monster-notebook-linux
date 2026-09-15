# The thing, as a lookup table

**Status:** verified
**Applies to:** Monster TULPAR T6 V2.1 (AI Creator)
**Verified on:** Ubuntu 26.04 · kernel 7.0.0-15 · 2026-09-15
**See also:** [the style guide](../STYLE.md)

One sentence saying what this table is for and where the values came from
(a DSDT dump, `lspci`, the vendor's driver page).

## Table name

| Field | Offset | Meaning | Status |
|---|---|---|---|
| `CPUT` | `0xE0D` | CPU temperature | dead — always 0 |

No narrative. Order the rows for lookup, not for reading.
