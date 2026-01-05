# Atari ST GEM Resource Files (`.RSC`)

This document specifies the **on-disk structure**, **internal layout**, and
**integrity verification rules** for Atari ST **GEM resource files** (`.RSC`),
as produced by tools such as **RCS**, **ORCS**, **Interface**, or compiler
toolchains (DRI, Turbo-C, Pure-C).

Unlike PRG or object files, **RSC files are pure data containers** and are never
executed.

---

## 1. General Characteristics

- Binary, big-endian
- No executable header
- No relocation at load time (relocations are resolved at *resource-load time*)
- Entire file structure is defined by a **single header + offset tables**
- **Exact file length can be derived from the header**

---

## 2. RSC File Header (36 bytes)

All multi-byte values are **big-endian 16-bit words** unless noted.

| Offset | Size | Field | Meaning |
|------:|----:|------|--------|
| `0x00` | 2 | `rsh_vrsn` | Resource format version |
| `0x02` | 2 | `rsh_object` | Offset to OBJECT array |
| `0x04` | 2 | `rsh_tedinfo` | Offset to TEDINFO array |
| `0x06` | 2 | `rsh_iconblk` | Offset to ICONBLK array |
| `0x08` | 2 | `rsh_bitblk` | Offset to BITBLK array |
| `0x0A` | 2 | `rsh_frstr` | Offset to free string index |
| `0x0C` | 2 | `rsh_string` | Offset to string data |
| `0x0E` | 2 | `rsh_imdata` | Offset to image data |
| `0x10` | 2 | `rsh_frimg` | Offset to free image index |
| `0x12` | 2 | `rsh_trindex` | Offset to tree index |
| `0x14` | 2 | `rsh_nobs` | Number of OBJECTs |
| `0x16` | 2 | `rsh_ntree` | Number of trees |
| `0x18` | 2 | `rsh_nted` | Number of TEDINFO entries |
| `0x1A` | 2 | `rsh_nib` | Number of ICONBLK entries |
| `0x1C` | 2 | `rsh_nbb` | Number of BITBLK entries |
| `0x1E` | 2 | `rsh_nstring` | Number of free strings |
| `0x20` | 2 | `rsh_nimages` | Number of free images |
| `0x22` | 2 | `rsh_rssize` | **Total file size in bytes** |

**Header size:** `36 bytes`

---

## 3. Core Design Principle

All offsets in the header are:

- Relative to **start of file**
- Point to contiguous tables
- Ordered from low to high addresses

The **entire file size is explicitly stored** in `rsh_rssize`.

This makes RSC files **fully self-describing**.

---

## 4. Major Data Areas

### 4.1 OBJECT Array
- Offset: `rsh_object`
- Count: `rsh_nobs`
- Entry size: **24 bytes**
- Contains all UI object definitions

### 4.2 TEDINFO Array
- Offset: `rsh_tedinfo`
- Count: `rsh_nted`
- Entry size: **28 bytes**
- Text-edit field descriptors

### 4.3 ICONBLK Array
- Offset: `rsh_iconblk`
- Count: `rsh_nib`
- Entry size: **34 bytes**
- Icon definitions

### 4.4 BITBLK Array
- Offset: `rsh_bitblk`
- Count: `rsh_nbb`
- Entry size: **14 bytes**
- Bitmap descriptors

### 4.5 Tree Index
- Offset: `rsh_trindex`
- Count: `rsh_ntree`
- Entry size: **2 bytes**
- Index into OBJECT array for each resource tree

---

## 5. String and Image Storage

### 5.1 Free String Index
- Offset: `rsh_frstr`
- Count: `rsh_nstring`
- Each entry is a **16-bit offset** into the string data area

### 5.2 String Data
- Offset: `rsh_string`
- Variable length
- Null-terminated strings
- Referenced by OBJECTs, TEDINFO, ICONBLK

### 5.3 Free Image Index
- Offset: `rsh_frimg`
- Count: `rsh_nimages`
- Each entry is a **16-bit offset** into image data

### 5.4 Image Data
- Offset: `rsh_imdata`
- Variable length
- Raw bitmap data

---

## 6. File Layout Overview

```
+----------------------+ 0x00
| RSC Header | 36 bytes
+----------------------+
| OBJECT array |
+----------------------+
| TEDINFO array |
+----------------------+
| ICONBLK array |
+----------------------+
| BITBLK array |
+----------------------+
| Tree index |
+----------------------+
| Free string index |
+----------------------+
| String data |
+----------------------+
| Free image index |
+----------------------+
| Image data |
+----------------------+
```


Exact ordering is defined by the offsets in the header.

---

## 7. Exact File Length Calculation

### Authoritative size field

```
EXPECTED_FILE_SIZE = rsh_rssize
```


This value:
- Includes the header
- Includes all tables and data
- Is **mandatory and exact**

---

## 8. Integrity Verification Rules

An RSC file is **structurally valid** if all conditions hold:

1. File size equals `rsh_rssize`
2. All offsets are:
   - ≥ 36
   - < `rsh_rssize`
3. All tables fit completely inside file bounds:
   - `offset + count × entry_size ≤ rsh_rssize`
4. Offsets are monotonically increasing
5. Tree indices refer to valid OBJECT indices
6. String and image offsets point inside their data regions
7. No overlapping regions unless explicitly allowed

If any rule fails, the file is:
- truncated
- corrupted
- or not a valid GEM resource file

---

## 9. Comparison with Other Atari ST Formats

| Format | Exact size known from header |
|------|------------------------------|
| RSC | ✔ Yes (`rsh_rssize`) |
| Turbo-C `.O` (`0x4EFA`) | ✔ Yes (`32 + tlen + dlen + blen`) |
| GEMDOS PRG (`0x601A`) | ✘ No (requires relocation parsing) |

RSC files are therefore **the safest and easiest Atari ST binary format to carve and validate**.

---

## 10. Summary

- `.RSC` files are pure data containers
- Fixed-size header (36 bytes)
- All internal structures referenced by offsets
- Header contains **exact total file size**
- Full integrity validation is possible without heuristics

This makes RSC files ideal candidates for **reliable recovery from raw binary streams**.

