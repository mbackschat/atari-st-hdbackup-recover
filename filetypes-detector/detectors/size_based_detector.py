"""
Size-based binary file detector for Atari ST files.

This detector runs AFTER all other binary detectors but BEFORE text detection.
It catches binary files that couldn't be identified by header/magic bytes,
using only file size as the detection criterion.

Detection criteria:
1. File must NOT be text
2. Detection is purely size-based
"""


def is_text_file(data, max_binary_ratio=0.05):
    """
    Check if file appears to be text (ASCII/Latin-1).

    Args:
        data: file content bytes
        max_binary_ratio: maximum ratio of non-text bytes allowed

    Returns:
        bool: True if file appears to be text
    """
    if len(data) == 0:
        return False

    # Try to decode as text
    try:
        text = data.decode('ascii', errors='ignore')
    except:
        try:
            text = data.decode('latin-1', errors='ignore')
        except:
            return False

    # Count printable characters
    printable_count = 0
    for char in text:
        if char.isprintable() or char in '\n\r\t':
            printable_count += 1

    if len(text) == 0:
        return False

    printable_ratio = printable_count / len(text)
    return printable_ratio >= (1.0 - max_binary_ratio)


def detect_size_based_binary(data, size):
    """
    Detect binary files by size when no other detector matched.

    This is a fallback detector for binary files that have no magic bytes
    or headers, but have well-known fixed sizes.

    Args:
        data: file content bytes
        size: file size

    Returns:
        tuple: (match: bool, ext: str, confidence: int, reason: str)
    """
    # First check: must NOT be a text file
    if is_text_file(data):
        return False, '', 0, ''

    # Size-based detection rules
    # Rule 1: 32000 bytes = .ART (monochrome 640x400 bitmap, no header)
    if size == 32000:
        return True, 'ART', 60, 'Binary file, 32000 bytes (640x400 monochrome bitmap)'

    # Future size-based rules can be added here
    # Example patterns:
    # if size == XXXXX:
    #     return True, 'EXT', confidence, 'reason'

    # No size-based match
    return False, '', 0, ''
