#!/usr/bin/env python3
"""
Atari ST File Type Detector

Analyzes files and renames them with correct extensions based on content detection.

Usage:
    python filetype-detector.py [folder] [--dry-run]

Arguments:
    folder     : Directory containing files to analyze (required)
    --dry-run  : Show what would be renamed without actually renaming (default)
"""

import sys
import os
import argparse
from pathlib import Path

# Import detectors
from detectors.rsc_detector import detect_rsc
from detectors.binary_executables import detect_binary_executable
from detectors.image_detector import detect_image
from detectors.text_detector import detect_text_type


def detect_file_type(file_path):
    """
    Detect the file type of a given file.

    Args:
        file_path: path to file to analyze

    Returns:
        tuple: (match: bool, new_ext: str, confidence: int, reason: str, extra_info: dict)
    """
    try:
        with open(file_path, 'rb') as f:
            data = f.read()

        size = len(data)

        # Empty files - skip
        if size == 0:
            return False, '', 0, 'Empty file', {}

        # Detection order: most reliable first
        # Phase 1: RSC (most reliable - exact size field)
        match, ext, conf, reason = detect_rsc(data, size)
        if match:
            return match, ext, conf, reason, {}

        # Phase 2: Binary executables (Turbo-C, Devpac, GEMDOS)
        result = detect_binary_executable(data, size)
        if len(result) == 5:
            match, ext, conf, reason, extra = result
            if match:
                return match, ext, conf, reason, extra

        # Phase 3: Images (magic-based and fixed-size)
        match, ext, conf, reason = detect_image(data, size)
        if match:
            return match, ext, conf, reason, {}

        # Phase 4: Text files (last resort, scoring-based)
        match, ext, conf, reason, extra_info = detect_text_type(data, size)
        if match:
            return match, ext, conf, reason, extra_info

        # No match found
        return False, '', 0, 'No matching file type detected', {}

    except PermissionError:
        return False, '', 0, 'Permission denied', {}
    except Exception as e:
        return False, '', 0, f'Error reading file: {e}', {}


def get_new_filename(original_path, new_ext, extra_info=None):
    """
    Generate new filename with detected extension.

    Args:
        original_path: original file path
        new_ext: new extension (without dot)
        extra_info: optional dict with extra info (e.g., embedded_name for Devpac)

    Returns:
        str: new filename
    """
    path = Path(original_path)
    base_name = path.stem

    # Special handling for Devpac objects with embedded names
    if extra_info and 'embedded_name' in extra_info:
        embedded = extra_info['embedded_name']
        # Format: <original_name>-<embedded_stem>.<ext>
        # Example: "00123.TXT" with embedded "modf" -> "00123-modf.O"
        new_name = f"{base_name}-{embedded}.{new_ext}"
    else:
        new_name = f"{base_name}.{new_ext}"

    return path.parent / new_name


def process_folder(folder_path, dry_run=True):
    """
    Process all files in a folder.

    Args:
        folder_path: path to folder
        dry_run: if True, only show what would be done

    Returns:
        tuple: (total_files, renamed_files, skipped_files, extension_stats)
        extension_stats: dict mapping extension to count
    """
    folder = Path(folder_path)

    if not folder.exists():
        print(f"Error: Folder '{folder_path}' does not exist")
        return 0, 0, 0, {}

    if not folder.is_dir():
        print(f"Error: '{folder_path}' is not a directory")
        return 0, 0, 0, {}

    # Get all files (not directories, not hidden)
    files = [f for f in folder.iterdir() if f.is_file() and not f.name.startswith('.')]

    if len(files) == 0:
        print(f"No files found in '{folder_path}'")
        return 0, 0, 0, {}

    total_files = 0
    renamed_files = 0
    skipped_files = 0
    extension_stats = {}  # Track counts per extension

    mode_str = "[DRY-RUN]" if dry_run else "[LIVE]"

    for file_path in sorted(files):
        total_files += 1

        # Detect file type
        match, new_ext, confidence, reason, extra_info = detect_file_type(file_path)

        if not match:
            # Skip - no confident detection
            print(f"{mode_str} SKIP: {file_path.name} - {reason}")
            skipped_files += 1
            continue

        # Track extension statistics
        new_ext_upper = new_ext.upper()
        extension_stats[new_ext_upper] = extension_stats.get(new_ext_upper, 0) + 1

        # Check if extension change is needed
        current_ext = file_path.suffix[1:].upper() if file_path.suffix else ''

        if current_ext == new_ext_upper:
            # Already has correct extension
            print(f"{mode_str} OK: {file_path.name} - Already .{new_ext}")
            skipped_files += 1
            continue

        # Generate new filename
        new_path = get_new_filename(file_path, new_ext, extra_info)

        # Check if target already exists
        if new_path.exists() and new_path != file_path:
            print(f"{mode_str} SKIP: {file_path.name} - Target exists: {new_path.name}")
            skipped_files += 1
            continue

        # Show what we're doing
        print(f"{mode_str} RENAME: {file_path.name} → {new_path.name} ({new_ext}, confidence: {confidence}%)")

        # Actually rename if not dry-run
        if not dry_run:
            try:
                file_path.rename(new_path)
                renamed_files += 1
            except Exception as e:
                print(f"  ERROR: Failed to rename: {e}")
                skipped_files += 1
        else:
            renamed_files += 1

    return total_files, renamed_files, skipped_files, extension_stats


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Atari ST File Type Detector - Analyze and rename files based on content',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python filetype-detector.py extracted
  python filetype-detector.py testfiles --dry-run

Note: Uses dry-run mode by default for safety. Use --no-dry-run to actually rename files.
        """
    )

    parser.add_argument('folder', help='Directory containing files to analyze')
    parser.add_argument('--dry-run', dest='dry_run', action='store_true', default=True,
                       help='Show what would be done without renaming (default)')
    parser.add_argument('--no-dry-run', dest='dry_run', action='store_false',
                       help='Actually rename files (use with caution)')

    args = parser.parse_args()

    # Display mode
    mode = "DRY-RUN MODE (no files will be renamed)" if args.dry_run else "LIVE MODE (files will be renamed!)"
    print(f"Atari ST File Type Detector")
    print(f"{'=' * 60}")
    print(f"Mode: {mode}")
    print(f"Folder: {args.folder}")
    print(f"{'=' * 60}\n")

    # Process folder
    total, renamed, skipped, extension_stats = process_folder(args.folder, args.dry_run)

    # Summary
    print(f"\n{'=' * 60}")
    print(f"Summary:")
    print(f"  Total files processed: {total}")
    print(f"  Files {'to be renamed' if args.dry_run else 'renamed'}: {renamed}")
    print(f"  Files skipped: {skipped}")

    # Extension breakdown
    if extension_stats:
        print(f"\n  Files by detected extension:")
        # Sort by extension name
        for ext in sorted(extension_stats.keys()):
            count = extension_stats[ext]
            print(f"    .{ext:<6} : {count:>3} file{'s' if count != 1 else ''}")

    print(f"{'=' * 60}")

    if args.dry_run and renamed > 0:
        print(f"\nTo actually rename files, run with --no-dry-run")


if __name__ == '__main__':
    main()
