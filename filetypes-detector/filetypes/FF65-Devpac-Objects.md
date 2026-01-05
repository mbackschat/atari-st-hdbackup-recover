# HiSoft Devpac `.O` Object Files (`FF 65`)

This document describes a **practical, integrity-oriented spec** for Atari ST
**HiSoft Devpac** assembler object files (`.O`) that begin with the byte
signature `FF 65`.

These files are **not GEMDOS executables** (unlike `0x601A` PRG-container files)
and they are **not Turbo-C/Pure-C objects** (unlike `0x4EFA` containers).
They are **record / hunk based** object modules intended for the Devpac linker
ecosystem.

---

## 1. Magic / Signature

A Devpac object file begins with:

```
FF 65
```


This is treated as a **format signature** (not a “jump over header” opcode trick).

---

## 2. Embedded Module Filename (immediately after `FF 65`)

### 2.1 Structure

Immediately following the two magic bytes is a **NUL-terminated ASCII string**:

```
FF 65 <ASCII bytes...> 00
```


### 2.2 Example

Hex:

```
FF 65 6D 6F 64 66 2E 6F 00
```


Decodes to:
- magic: `FF 65`
- filename: `"modf.o"`
- terminator: `00`

### 2.3 Filename extraction rule (conceptual)

- Start reading bytes immediately after `FF 65`
- Continue until the first `00` byte
- Interpret the preceding bytes as the module filename (ASCII)
- This name is often used by linkers/debuggers for diagnostics (module identity)

### 2.4 Filename sanity constraints (for integrity checking)

To reduce false positives when carving:
- terminator (`00`) must appear within a reasonable maximum length
  (e.g., ≤ 64 bytes)
- bytes should be mostly printable ASCII
- commonly includes a `.o`/`.O` suffix (but do not hard-require it)

---

## 3. Object Payload: Record / “Hunk”-Based Structure

After the NUL-terminated filename, the remainder of the file is a sequence of
**self-delimiting records** (often referred to as “hunks” in Devpac/HiSoft docs).

Characteristics:
- Each record has a **type**
- Each record has an explicit **length** (or a length implied by the type)
- Parsing proceeds record-by-record
- A valid object module must end with an explicit **end marker** / “hunk end”

This is strongly supported by Devpac linker diagnostics that expect:
- an **end marker** to terminate a hunk, and
- a valid internal record grammar (otherwise the linker reports the module as
  invalid or damaged). :contentReference[oaicite:0]{index=0}

---

## 4. Exact File Length Determination (Integrity / Carving)

### 4.1 Why there is no direct “header size = file size” formula

Unlike:
- Turbo-C `0x4EFA` objects (exact size from header fields), or
- GEM `.RSC` files (exact size field in the header),

Devpac `FF 65` objects typically **do not store a total file size** as a single
header field. Therefore:

> The only reliable way to determine the exact module size is to
> **parse the record stream until the end marker is reached**.

### 4.2 Exact end-of-file rule

A Devpac object file’s **exact size** is:

> the byte position immediately after the final **end marker record**.

If the input ends before the end marker is encountered, the file is **truncated**
(or the carving window is incomplete). Devpac tooling explicitly complains when
no end marker is seen. :contentReference[oaicite:1]{index=1}

---

## 5. Recommended Integrity Checks (Format Validation)

A recovered candidate is a valid Devpac `.O` object module if all checks pass:

### 5.1 Header + filename checks
1. Starts with `FF 65`
2. Contains a NUL-terminated filename string
3. Filename bytes are plausible ASCII
4. Filename terminator occurs within an expected bound

### 5.2 Record-stream checks
5. The first record begins immediately after the filename terminator
6. Each record’s declared length:
   - is non-negative / plausible
   - does not exceed remaining bytes
7. Record types are all recognized for this format
8. The parser reaches a valid end marker (“hunk end”) before EOF

If any record is malformed or the end marker is missing, Devpac linkers treat
the file as “not a valid object file” / “damaged”, and specifically note missing
end markers (“No hunk end seen”). :contentReference[oaicite:2]{index=2}

---

## 6. Relationship to Other Atari ST Object/Executable Families

### 6.1 Not the same as `0x601A` PRG-container objects
- `0x601A` files are GEMDOS load modules with TEXT/DATA/BSS sizes and (optional)
  relocation streams
- Devpac `FF 65` files are **record-based object modules**, not directly runnable

### 6.2 Not the same as Turbo-C/Pure-C `0x4EFA` objects
- `0x4EFA` files jump to TEXT and provide exact sizes (TEXT/DATA/“blen” metadata)
- `FF 65` files embed a module name and then rely on record parsing to find end

---

## 7. Practical Notes for Recovery Workflows

- The embedded filename gives you a rare advantage in raw recovery: you can
  recover the module name even without filesystem metadata.
- Use strict parsing to avoid false positives:
  - `FF 65` + plausible NUL-terminated filename + well-formed record grammar
  is a very strong signature set.

---

## 8. Summary

- **Signature:** `FF 65`
- **Immediately followed by:** NUL-terminated ASCII filename (module name)
- **Then:** a record/hunk-based stream with explicit lengths and a required end marker
- **Exact size:** determined by parsing to the final end marker (no closed-form header formula)
- **Integrity verification:** validate header + filename + record grammar + end marker

---

## FILE NAME and EXTENSION

IMPORTANT: Since we can derive the filename from the file content, we can rename the file like this:

<original filename without extension>-<derived filename without extension>.<derived extension>


