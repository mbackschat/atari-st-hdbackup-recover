# Turbo-C / Pure-C Object & Library Files (`0x4EFA` Container)

This document describes the **exact on-disk structure** and **file length calculation**
for Atari ST **Turbo-C / Pure-C** object and library files that start with the
`0x4EFA` magic word.

The description is **complete and deterministic**: the header fully defines the
exact file size.


When extracting such files, use the file extension ".TCO"



---

## 1. Header Magic: `0x4EFA`

The first word of the file is:

```
0x4EFA
```


This is a valid Motorola 68000 opcode:

- `JMP (d16,PC)`

The instruction is followed by a **16-bit signed displacement**.
Execution jumps over the header to the start of the TEXT segment.

This is a deliberate design choice:
- prevents execution by GEMDOS
- keeps the file executable by the CPU
- allows Turbo-C/Pure-C tools to parse the header reliably

---

## 2. Header Layout (32 bytes total)

All multi-byte values are **big-endian**.

| Offset | Size | Field | Meaning |
|------:|----:|------|--------|
| `0x00` | 2 | Magic | `0x4EFA` |
| `0x02` | 2 | Displacement | PC-relative jump offset |
| `0x04` | 4 | `tlen` | TEXT segment size (stored) |
| `0x08` | 4 | `dlen` | DATA segment size (stored) |
| `0x0C` | 4 | `blen` | **Stored symbol / metadata size** |
| `0x10` | 4 | `slen` | Unused (always `0`) |
| `0x14` | 12 | Reserved | Zero-filled |

**Header size:** `32` bytes

---

## 3. Entry Point / TEXT Start

The entry point is computed as:

```
entry = 4 + displacement
```


In all observed Turbo-C files:

```
entry = 0x20
```


This is the start of the TEXT segment.

---

## 4. File Layout

All segments described by the header are **physically stored** in the file.


```
+----------------------+ 0x00
| JMP instruction | 4 bytes
+----------------------+
| Size fields + pad | 28 bytes
+----------------------+ 0x20 ← TEXT start
| TEXT segment | tlen bytes
+----------------------+
| DATA segment | dlen bytes
+----------------------+
| SYMBOL / METADATA | blen bytes
+----------------------+
```


### Important distinction

Unlike GEMDOS PRG files:

- `blen` **does not describe uninitialized memory**
- `blen` is a **stored region** containing:
  - symbols
  - relocation data
  - library indexes (for `.LIB`)

There is **no relocation stream terminator** and **no implicit padding**.

---

## 5. Exact File Size Formula

The file size is **fully defined by the header**.

### Exact length calculation

```
FILE_SIZE = 32 + tlen + dlen + blen
```


This is:
- **exact**, not a minimum
- valid for both `.O` and `.LIB`
- sufficient to detect truncation or corruption

## 6. Validation Rules

A Turbo-C `0x4EFA` file is **structurally valid** if:

1. Magic is `0x4EFA`
2. Entry jump lands at a sane offset (typically `0x20`)
3. `FILE_SIZE == 32 + tlen + dlen + blen`
4. No segment overlaps
5. File contains exactly `FILE_SIZE` bytes

Any mismatch means:
- truncation
- corruption
- or non-Turbo-C format

---

## 7. Summary

- `0x4EFA` identifies Turbo-C / Pure-C containers
- Uses executable jump-over-header technique
- Stores **TEXT, DATA, and SYMBOL/METADATA** explicitly
- Header defines **exact file length**
- Deterministic parsing and validation is possible

This format is **distinct from**:
- GEMDOS PRG (`0x601A`)
- DRI record-based `.O`
