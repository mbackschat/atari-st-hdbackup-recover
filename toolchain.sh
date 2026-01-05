#!/usr/bin/env bash

# Before running this script, move
# the .st files (disk images created with Greaseweazle tool) to DATAFOLDER
# (Mine were called "E* (Harddisk Utility, 10 Sec)-2.st")
#
# After the script successfully ran, the extracted files are in EXTRACTED
#
# Optional parameters:
#   $1 = DATAFOLDER (default: example/disks)   [relative to the original working dir]
#   $2 = EXTRACTED  (default: sibling folder "extracted" next to DATAFOLDER)


set -euo pipefail

# ---- Python selector (macOS-safe) -------------------------------------------
if command -v python3 >/dev/null 2>&1; then
  PYTHON=python3
elif command -v python >/dev/null 2>&1; then
  PYTHON=python
else
  echo "Error: neither python3 nor python found in PATH" >&2
  exit 1
fi
# ------------------------------------------------------------------------------

DATAFOLDER="${1:-example/disks}"
EXTRACTED="${2:-"$(dirname "$DATAFOLDER")/extracted"}"

if [ ! -d "$DATAFOLDER" ]; then
  echo "Error: DATAFOLDER does not exist: $DATAFOLDER" >&2
  echo "Usage: $(basename "$0") [DATAFOLDER] [EXTRACTED]" >&2
  echo "Defaults:" >&2
  echo "  DATAFOLDER = example/disks" >&2
  echo "  EXTRACTED  = <parent-of-DATAFOLDER>/extracted" >&2
  exit 1
fi

# Remember original working dir and ensure we come back (also on error)
ORIG_PWD="$(pwd -P)"
trap 'cd "$ORIG_PWD"' EXIT

# Resolve paths relative to original working dir
DATAFOLDER_ABS="$(cd "$ORIG_PWD" && cd "$DATAFOLDER" && pwd -P)"
EXTRACTED_ABS="$(cd "$ORIG_PWD" && cd "$(dirname "$EXTRACTED")" 2>/dev/null && pwd -P)/$(basename "$EXTRACTED")"

# Run python tools relative to this script's directory (repo root assumed)
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
cd "$SCRIPT_DIR"

# Tool 1 Prep: Get list of .st files to work on

shopt -s nullglob
all_st_files=( "$DATAFOLDER_ABS"/*.st )

## Excludes files ending in "-<number>.st"
st_files=()
for f in "${all_st_files[@]}"; do
  [[ "$(basename "$f")" =~ -[0-9]+\.st$ ]] || st_files+=( "$f" )
done

## Fail fast if no .st files exist
if (( ${#st_files[@]} == 0 )); then
  echo "Error: No .st files found in: $DATAFOLDER_ABS" >&2
  exit 1
fi



# ----- Tool 1: carver
for i in "${st_files[@]}"; do
  "$PYTHON" carver/carver.py "$i" 10240 819200
done

# Fail fast if no *-2.st files exist
carved_files=( "$DATAFOLDER_ABS"/*-2.st )
if (( ${#carved_files[@]} == 0 )); then
  echo "Error: No '*-2.st' files found in: $DATAFOLDER_ABS (did carver produce them?)" >&2
  exit 1
fi

cat "${carved_files[@]}" >"$DATAFOLDER_ABS/carved.bin"

# ----- Tool 2: extract (create only when extraction runs)
mkdir -p "$EXTRACTED_ABS"
"$PYTHON" extract/atari_extractor.py "$DATAFOLDER_ABS/carved.bin" "$EXTRACTED_ABS"

## Clean up
tmp_files=( "$DATAFOLDER_ABS"/*-[0-9].st )
rm -f "${tmp_files[@]}" "$DATAFOLDER_ABS/carved.bin"

# ----- Tool 3: filetype detector
"$PYTHON" filetypes-detector/filetype-detector.py "$EXTRACTED_ABS" --no-dry-run

# ----- Tool 4: Degas Image to PNG converter
"$PYTHON" degas_to_png/degas_to_png.py "$EXTRACTED_ABS"
