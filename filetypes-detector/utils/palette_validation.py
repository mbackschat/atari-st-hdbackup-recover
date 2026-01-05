"""
Atari ST/STE palette validation utilities.

Atari ST classic palette: 3 bits per channel (values 0-7)
Atari STE palette: 4 bits per channel (values 0-15)
Both stored as 16-bit words: 0x0RGB (12-bit color)
"""

from .binary_utils import read_be_word


def validate_st_palette(data, offset, count=16, strict_st=False):
    """
    Validate an Atari ST/STE palette.

    Args:
        data: bytes object containing palette
        offset: starting position of palette
        count: number of palette entries to check (default 16)
        strict_st: if True, require classic ST format (3-bit per channel)
                   if False, allow STE format (4-bit per channel)

    Returns:
        bool: True if palette is valid
    """
    if offset + (count * 2) > len(data):
        return False

    valid_count = 0

    for i in range(count):
        word = read_be_word(data, offset + i * 2)
        if word is None:
            return False

        # High nibble must be 0 (0x0RGB format)
        if (word & 0xF000) != 0:
            return False

        # Value must be within 12-bit range
        if word > 0x0FFF:
            return False

        if strict_st:
            # Classic ST: each color component must be 0-7 (3-bit)
            # Check that bit 3 of each nibble is 0
            if (word & 0x0888) != 0:
                return False

        valid_count += 1

    # Require at least half the palette entries to be valid
    return valid_count >= count // 2


def palette_looks_valid(data, offset, count=16):
    """
    Lenient palette check - just verify basic structure.

    Args:
        data: bytes object
        offset: palette start position
        count: number of entries

    Returns:
        bool: True if palette structure looks reasonable
    """
    return validate_st_palette(data, offset, count, strict_st=False)


def palette_is_strict_st(data, offset, count=16):
    """
    Strict palette check for classic Atari ST (3-bit per channel).

    Args:
        data: bytes object
        offset: palette start position
        count: number of entries

    Returns:
        bool: True if palette matches classic ST format
    """
    return validate_st_palette(data, offset, count, strict_st=True)
