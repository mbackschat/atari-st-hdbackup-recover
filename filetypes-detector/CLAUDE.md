## Project Goal

I want to reverse engineer atari st files. My situation: I have a folder full of  files where I don't know the file type. I want to detect all kind of valid filetypes that were common on the Atari ST, esp. regarding source code development.

Go through the folder, and for each file
analyse its content and/or file size to detect its filetype.
Change the file extension based on the derive filetype (using 3 letters, Atari ST compatible)

Binary files:

- Images, many formats like Degas, Neochrome, GEM images, might have fixed file size!  – see @filetypes/Images.md
- RSC (GEM Resource Files) – see @filetypes/RSC.md
- Exectuables (PRG/TOS/TTP/ACC/APP, GEMDOS .O) – see @filetypes/601A.md
- .O / .LIB (Turbo-C) - see @filetypes/4EFA-Turbo-C-Objects.md
- Devpac .O – see @filetypes/FF65-Devpac-Objects.md
- .ART (monochrome bitmap 640x400, size-based detection) - exactly 32000 bytes, no header


Text Files:

Also come up with some great logic to analyse text files, maybe using keywords that are common in these files.

- .C, .H,
- .S
- RSD (GEM Resource Definition files, )
- .INF
- Makefiles, .BAT
- Project File .PRJ
- .TXT (as fallback)

See @filetypes/Textfiles.md

Try to check first for filetypes that have a reliable and robust detection mechanism!!

If unsure, then skip the file, just output a message.

### Tests

Use the files in the folder "testfiles".
The folder structure is organized by file extension - each subfolder is named after the extension that the files inside should be detected as.

Structure:
```
testfiles/
  ├── H/          # Files that should be detected as .H (header files)
  ├── C/          # Files that should be detected as .C (C source)
  ├── S/          # Files that should be detected as .S (assembly)
  ├── GEMDOS-PRG/   # Files that should be detected as .PRG (programs) or .ACC
  ├── GEMDOS-O/   # Files that should be detected as .O (GEMDOS object files)
  ├── RSC/        # Files that should be detected as .RSC
  ├── PI1/        # Files that should be detected as .PI1
  └── ...         # Other extensions
```

Example:
- testfiles/S/randomname.xyz → should be detected as .S and renamed to randomname.S
- testfiles/H/foo.TXT → should be detected as .H and renamed using embedded filename extraction method (only if possible)

Run the tests on a copy of the folder!



### Command Line Interface

```
python filetype-detector.py [folder] [--dry-run | --no-dry-run]

Arguments:
  folder        : Directory containing files to analyze (required)
  --dry-run     : Show what would be renamed without actually renaming (default, safe mode)
  --no-dry-run  : Actually rename files (use with caution)
```

Examples:
```
# Preview what would happen (safe, default mode)
python filetype-detector.py extracted

# Same as above (explicit dry-run)
python filetype-detector.py extracted --dry-run

# Actually rename files (CAUTION!)
python filetype-detector.py extracted --no-dry-run
```

### Output and Reporting

The tool provides detailed output showing:
- Each file being processed with action (RENAME, SKIP, or OK)
- File type detected and confidence level
- Summary statistics at the end including:
  - Total files processed
  - Files renamed (or to be renamed in dry-run mode)
  - Files skipped (undetectable or already correct)
  - **Breakdown by detected file extension** (sorted alphabetically with counts)

Example output:
```
============================================================
Summary:
  Total files processed: 15
  Files to be renamed: 12
  Files skipped: 3

  Files by detected extension:
    .C      :   4 files
    .H      :   3 files
    .PI1    :   2 files
    .PRG    :   2 files
    .S      :   1 file
============================================================
```
