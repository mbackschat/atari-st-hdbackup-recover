# Robust detection of Atari ST-era text file types (content + size)

Goal: Given a directory of unknown files from an Atari ST context, detect likely *text* file types and assign the corresponding extension:

## 1) Most important Text and sourcecode files and their extensions

- `.C`, `.H`
- `.S` (assembly)
- `.RSD` (GEM resource definition “source” text; not the compiled `.RSC`)
- `.INF`
- `Makefile`, `.BAT`
- `.PRJ` (project)
- `.TXT` (fallback)

## 2) Constraints
- Minimize false positives (prefer “unknown” / `.TXT` over a wrong specific type).
- Use file content *and* size.
- Be robust across mixed encodings / line endings typical for ST-era tools.

---

## 3) Classification approach: weighted evidence + balanced thresholds

Use a scoring model with **balanced thresholds** and an "unknown" fallback.

### 3.1 General decision rules
- Compute a **score per type** from independent evidence groups.
- A type can only be chosen if:
  1. `score(type) >= STRONG_MIN` (e.g., **6 points** - lowered from 8 to catch more valid headers)
  2. `score(type) - score(second_best) >= MARGIN` (e.g., 3 points)
  3. Any **type-specific mandatory checks** pass (see below)
- If not, choose `.TXT` (or "unknown-text") to minimize false positives.

### 3.2 Key Insight from Atari ST Headers

**Many ST-era header files lack "modern" features:**
- No header guards (#ifndef/#define/#endif)
- No function prototypes (just #define constants)
- No typedef or extern declarations

**Common ST header patterns:**
- **#define-heavy**: Just dozens/hundreds of #define constants (very common!)
- **#include-only**: Just 2-5 #include statements
- **Mixed minimal**: Few #defines + few #includes

Therefore, detection must not over-rely on header guards or prototypes.

### 3.3 File size as a prior (lightweight)
Size should bias, not decide:
- `.H` often smaller than `.C`, but not always.
- `Makefile` and `.BAT` often small-to-medium.
- `.INF` typically small.
- `.RSD` can be medium/large with lots of GUI definitions.
- `.S` can be large, but often has many short lines.

Use size only as **+1 / -1** support, never as sole evidence.

---

## 4) Type-specific detection heuristics (robust + conservative)

Below are conservative rules designed to minimize false positives.

### 4.1 Detect `.C` (C source)

**Strong evidence**:
- `int main(` or `void main(` → +3 points (strong C indicator)
- `#include` present → +4 points (very strong for .C when combined with code)
- **Function definition pattern**: `\w+\s+\w+\s*\([^)]*\)\s*\{` (NEW) → +3 points
- Multiple functions (>1 function body) → +2 points
- `return ` statement → +2 points
- C standard library calls: `printf(`, `malloc(`, `free(`, `sizeof(` → +2 points each

**Moderate evidence (+1-2 points each)**:
- Has **both** `{` and `}` with balanced counts → +3 points
- Braces present (>=1 pair) AND #include → +2 points (NEW - typical C combination)
- C keywords: `typedef`, `struct`, `enum`, `static`, `const`, `volatile`, `switch`, `case`, `break`, `continue` → +1 point per keyword (max +4)
- C-style comments: `/* ... */` or `//` → +1 point
- Preprocessor directives: `#define`, `#ifdef` → +2 points

**Mandatory checks** (must satisfy at least one):
- Either:
  - At least one `#include` **and** at least one `{`
  - OR at least one function body pattern
  - OR at least 3 distinct C keywords and braces present

**Anti-signals**:
- Very high ratio of `;` at start of line (assembly) → -3 points
- Many `target:` style rules (Makefile) → -3 points
- Lots of #define (>=10) without function bodies (braces <=1) → -4 points (likely header)

**Size hint**:
- If `size < 80 bytes`, reduce score by -2 (tiny files less likely to be full C source)

---

### 4.2 Detect `.H` (C header)
Headers often have preprocessor guards and declarations, BUT many ST-era headers are just #defines or #includes.

**Strong evidence**:
- **20+ #defines** → +6 points (extremely common on ST)
- **10-19 #defines** → +5 points
- **5-9 #defines** → +4 points
- **2-4 #defines** → +3 points
- **1 #define** → +1 point
- `#ifndef` + `#define` + `#endif` present (classic guard) → +3 points
- Many function prototypes (≥2): lines matching `type name(args);` with no `{` in file → +3 points

**#include-only pattern** (NEW):
- If **>=2 #include** AND **<3 #defines** AND **no braces** → +4 points
- (Catches headers that are just including other headers)

**Moderate evidence (+2 each)**:
- `typedef struct` patterns without implementations
- `extern` declarations
- `#include` present (general)
- Very few braces (<=2) → +2 points

**C-style comments** (+1):
- Presence of `/* */` or `//` comments

**Mandatory anti-signals**:
- Must have **no** `int main(` / `void main(` → -5 points if present
- If braces > 5 → -3 points (likely C source, not header)

**Anti-signals (-3 each)**:
- Lots of make rules or batch commands

**Size hint**:
- Very small headers (50–800 bytes) are common; don't penalize.
- Large headers (1000+ bytes) with many #defines are also common.

#### Embedded Filename Extraction (HEADER files)

Many Atari ST header files (and some C source files) include the filename in comment headers. This provides valuable metadata for file identification and recovery.

**Supported patterns** (searched in first 20 lines):

1. **Asterisk continuation line** (most common):
   ```c
   /*
    * SETJMP.H
    */

   /*
    * access.h -- modes for the access system call.
    */
   ```
   - Pattern: `* <whitespace> FILENAME.EXT [-- or - separator]`
   - Extremely common in Mark Williams C, Borland, and other ST compilers

2. **C-style comment with filename on same line**:
   ```c
   /*	GEMBIND.H Do-It-Yourself GEM binding kit.			*/
   /*      EXT.H
   ```
   - Pattern: `/* <whitespace> FILENAME.EXT [description]`
   - Common in Atari Corp headers and compact header files

3. **SCCS/RCS version control format**:
   ```c
   *  @(#)math.h	3.1	12/30/85
   ```
   - Pattern: `@(#)filename.ext <version> <date>`
   - Common in Alcyon C, DRI C, and commercial libraries

4. **Standalone filename line**:
   ```c
   /*
           EXT.H

           Extended library definitions
   ```
   - Pattern: Just filename on its own line (whitespace-padded)
   - Used in some Borland and commercial headers

5. **C++ style comment** (rare):
   ```c
   // FILENAME.H - description
   ```
   - Pattern: `// FILENAME.EXT - <description>`
   - Less common in ST era, but supported for completeness

**Usage in classification**:
- If embedded filename is found AND classification is ambiguous between H/C:
  - Use embedded name as tie-breaker
  - Boost confidence slightly (+5-10 points)
- Embedded name is stored in `extra_info['embedded_name']` (without extension)

**Filename format**:
- When renaming: `<original>-<embedded>.<ext>`
- Example: `00014.TXT` with embedded "GEMBIND.H" → `00014-GEMBIND.H`
- Example: `00018.TXT` with embedded "math.h" → `00018-math.H`

**Rationale**:
- Helps recover original filenames from numbered/corrupted file lists
- Provides additional evidence for H vs C classification
- Common practice in ST-era development (especially system headers)

---

### 4.3 Detect `.S` (assembly)
Atari ST assembly frequently uses Motorola 68000 syntax and tool directives.

**Strong evidence (+3 each)**:
- Contains ≥2 of these directives/keywords (case-insensitive, tokenized):
  - `SECTION`, `TEXT`, `DATA`, `BSS`
  - `DC.B`, `DC.W`, `DC.L`, `DS.B`, `DS.W`, `DS.L`
  - `EQU`, `ORG`, `END`
  - `XDEF`, `XREF`, `GLOBL`
  - `INCLUDE`
- Many comment lines starting with `;` (e.g., `; comment`)
- Label patterns at line start: `^[A-Za-z_\.][\w\.]*:\s`

**Moderate evidence (+2)**:
- Presence of common 68k mnemonics in column-ish format:
  - `MOVE`, `MOVEA`, `ADD`, `SUB`, `LEA`, `JSR`, `JMP`, `BRA`, `BSR`, `RTS`, `RTE`, `CLR`, `CMP`, `TST`
- Hex immediate patterns: `#$[0-9A-F]+` (common in 68k)

**Mandatory checks**:
- Must have at least one directive OR at least 3 mnemonic hits AND label/comment structure typical of asm.

**Anti-signals (-4)**:
- Many `#include` + C keywords + braces (more likely `.C`/`.H`)

**Size hint**:
- Assembly can be very small (startup stubs); rely on directives/mnemonics, not size.

---

### 4.4 Detect `.INF` (Atari ST desktop/app config)
`.INF` could be GEM Desktop (`DESKTOP.INF`) or app-specific configuration. Because “INF” is generic, keep rules strict.

**Strong evidence (+3 each)**:
- High proportion of `KEY=VALUE` lines (e.g., ≥10% of lines), with keys like:
  - `PATH`, `FILE`, `DEVICE`, `PRINTER`, `PORT`, `WINDOW`, `DESKTOP`, `GEM`, `AUTO`
- Multiple lines containing **drive-letter paths**: `A:\`, `B:\`, `C:\` or `A:` `C:` followed by `\`
- Contains desktop-ish tokens:
  - `DESKTOP`, `NEWDESK`, `GEMDESK`, `ACC`, `AUTO`, `TOS` (not all are guaranteed; treat as support)

**Moderate evidence (+2)**:
- Lines start with a small set of uppercase tokens and numeric parameters (common in config formats)
- Many semicolon/asterisk comment lines but *no* code braces

**Mandatory checks**:
- Must be strongly “config-shaped”:
  - `KEY=VALUE` density OR many `A:\`-style paths
- Must NOT look like source code (few/no braces, low C/asm keyword hits)

**Anti-signals (-4)**:
- `#include`, `typedef`, `SECTION`, `DC.W` etc.

**Size hint**:
- Often small (< 20 KiB). If huge, require stronger matching.

---

### 4.5 Detect `Makefile`
Makefiles have distinctive syntax: `target: deps` and *tab-indented recipes*.

**Strong evidence (+4 each)**:
- At least one rule line: `^[^\s:#=]+(\s+[^\s:]+)*\s*:\s+`
- At least one **tab-indented** command line following a rule (TAB at column 1)
- Variables like `CC=`, `CFLAGS=`, `LDFLAGS=`, `OBJS=`

**Moderate evidence (+2)**:
- Built-in macro usage: `$(CC)`, `$(CFLAGS)`, `$@`, `$<`, `$^`
- Targets like `all:`, `clean:`, `install:`

**Mandatory checks**:
- Must have a `target:` rule AND at least one recipe/tab line OR macro usage like `$@`.

**Anti-signals (-5)**:
- Heavy presence of C braces or asm directives

**Size hint**:
- Usually small to medium, but ignore size unless extremely tiny.

---

### 4.6 Detect `.BAT` (batch / script)
On Atari ST, “.BAT” could be used by some environments/shells. Batch syntax varies, so stay conservative and detect only when very clear.

**Strong evidence (+4)**:
- Starts with a known batch marker:
  - `@echo` / `echo` (DOS-like)
  - `REM ` comment lines
  - or repetitive command-only lines (`cd`, `copy`, `del`, `ren`, `mkdir`, `rmdir`, `path`, `set`) — *if* multiple hits

**Moderate evidence (+2)**:
- Environment style: `SET VAR=...`
- `IF ` / `GOTO ` / labels like `:label` (DOS-like)

**Mandatory checks**:
- Must contain ≥2 distinct batch commands from the list above, or `REM` + another command.

**Anti-signals (-4)**:
- Makefile tab+rule patterns
- C/asm directives

**Size hint**:
- Usually small.

---

### 4.7 Detect `.PRJ` (project file)
Project file formats differ by IDE/compiler (Pure C, Lattice, Devpac, etc.). Without pinning to a specific tool, treat `.PRJ` as “structured list of sources/options”.

**Strong evidence (+3)**:
- Many lines referencing source-like filenames:
  - `*.c`, `*.h`, `*.s`, `*.o`, `*.prg`, `*.ttp`, `*.tos`, `*.rsc`
- Option blocks with compiler/linker flags:
  - `-I`, `-D`, `-L`, `-l`, `-O`, `-g` (but beware false positives in docs)

**Moderate evidence (+2)**:
- INI-like sections: `[Project]`, `[Files]`, `[Options]` (if present)
- Relative paths with backslashes and source extensions

**Mandatory checks**:
- Must have **multiple** filename references (e.g., ≥5) with relevant extensions.
- Must not strongly match Makefile (no tab recipes/rules).

**Anti-signals (-4)**:
- High density of code keywords and braces (actual source file)

**Size hint**:
- Often small-to-medium.

---

### 4.8 Detect `.RSD` (GEM Resource Definition text)
Important: **compiled resources are `.RSC` and binary**; you want the *definition/source* text. Tools and formats vary, so detection must lean on “resource-shaped” tokens.

**Strong evidence (+3)**:
- Presence of multiple resource-object concepts (any 2+), case-insensitive:
  - `OBJECT`, `TREE`, `DIALOG`, `FORM`, `MENU`, `TEDINFO`, `ICON`, `BITBLK`, `CICON`, `STRING`, `ALERT`
- Lots of numeric attribute tables (many lines with comma-separated integers / hex) *without* C braces

**Moderate evidence (+2)**:
- Many identifiers in ALLCAPS (resource symbols) plus numeric definitions
- “Resource header” style comments or tool markers (if any appear consistently)

**Mandatory checks**:
- Must contain ≥2 distinct resource-object concept tokens AND
- Must not match C/asm strongly

**Anti-signals (-4)**:
- `#include` + braces + function-like syntax (C)
- `SECTION`, `DC.W` (asm)

**Size hint**:
- Often medium; if very small, require very strong token matches.

---

### 4.9 `.TXT` fallback
If a file passes the “text gate” but:
- no type meets `STRONG_MIN`, or
- the margin is too small (ambiguous), or
- it looks like prose/documentation (long sentences, few symbols/keywords)

→ label as `.TXT`.

A very effective “prose detector” (to avoid mislabeling as code):
- If average line length is high (e.g., > 60),
- low symbol density (`{}`, `;`, `#`, `:` at line start),
- and high ratio of dictionary-like words (optional),
then bias strongly toward `.TXT`.

---

## 5) Tie-breaking rules (minimize false positives)

When two types are close, pick the *less specific* label unless one has a “signature feature”:

Priority of signature features:
1. **Makefile**: `target:` + TAB recipe or `$@`
2. **Assembly**: multiple 68k directives (`DC.W`, `SECTION`, `XDEF`)
3. **Header**: guard trio `#ifndef/#define/#endif`
4. **C source**: `main(` or multiple function bodies
5. **INF / PRJ / RSD**: only if their mandatory checks pass clearly
6. Otherwise `.TXT`

If ambiguity remains, prefer `.TXT`.

---

## 6) Practical notes specific to Atari ST archives

- Line endings may be CR-only.
- Tabs matter for Makefiles: preserve raw bytes long enough to detect leading TAB.
- Some files may be “mostly ASCII” but contain a few
