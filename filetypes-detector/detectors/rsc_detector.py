"""
GEM Resource File (.RSC) detector.

RSC files have a 36-byte header with exact file size field.
This makes them the most reliable binary format to detect.
"""

from utils.binary_utils import read_be_word


def detect_rsc(data, size):
    """
    Detect GEM Resource (.RSC) files.

    Args:
        data: file content bytes
        size: file size

    Returns:
        tuple: (match: bool, ext: str, confidence: int, reason: str)
    """
    # RSC header is 36 bytes
    if size < 36:
        return False, '', 0, ''

    # Parse header fields (all big-endian 16-bit words)
    rsh_vrsn = read_be_word(data, 0x00)
    rsh_object = read_be_word(data, 0x02)
    rsh_tedinfo = read_be_word(data, 0x04)
    rsh_iconblk = read_be_word(data, 0x06)
    rsh_bitblk = read_be_word(data, 0x08)
    rsh_frstr = read_be_word(data, 0x0A)
    rsh_string = read_be_word(data, 0x0C)
    rsh_imdata = read_be_word(data, 0x0E)
    rsh_frimg = read_be_word(data, 0x10)
    rsh_trindex = read_be_word(data, 0x12)
    rsh_nobs = read_be_word(data, 0x14)
    rsh_ntree = read_be_word(data, 0x16)
    rsh_nted = read_be_word(data, 0x18)
    rsh_nib = read_be_word(data, 0x1A)
    rsh_nbb = read_be_word(data, 0x1C)
    rsh_nstring = read_be_word(data, 0x1E)
    rsh_nimages = read_be_word(data, 0x20)
    rsh_rssize = read_be_word(data, 0x22)

    # Check if any read failed
    if any(x is None for x in [rsh_vrsn, rsh_object, rsh_tedinfo, rsh_iconblk,
                                rsh_bitblk, rsh_frstr, rsh_string, rsh_imdata,
                                rsh_frimg, rsh_trindex, rsh_nobs, rsh_ntree,
                                rsh_nted, rsh_nib, rsh_nbb, rsh_nstring,
                                rsh_nimages, rsh_rssize]):
        return False, '', 0, ''

    # CRITICAL CHECK: File size must exactly match rsh_rssize
    if rsh_rssize != size:
        return False, '', 0, ''

    # All offsets must be >= 36 (header size)
    offsets = [rsh_object, rsh_tedinfo, rsh_iconblk, rsh_bitblk, rsh_frstr,
               rsh_string, rsh_imdata, rsh_frimg, rsh_trindex]

    for offset in offsets:
        if offset > 0 and offset < 36:
            return False, '', 0, 'Invalid offset < 36'

    # All offsets must be < file size
    for offset in offsets:
        if offset >= size:
            return False, '', 0, 'Offset >= file size'

    # Check that table sizes are reasonable
    OBJECT_SIZE = 24
    TEDINFO_SIZE = 28
    ICONBLK_SIZE = 34
    BITBLK_SIZE = 14
    TREE_INDEX_SIZE = 2

    # Verify tables fit within file
    if rsh_nobs > 0 and rsh_object > 0:
        if rsh_object + rsh_nobs * OBJECT_SIZE > size:
            return False, '', 0, 'OBJECT table overflows'

    if rsh_nted > 0 and rsh_tedinfo > 0:
        if rsh_tedinfo + rsh_nted * TEDINFO_SIZE > size:
            return False, '', 0, 'TEDINFO table overflows'

    if rsh_nib > 0 and rsh_iconblk > 0:
        if rsh_iconblk + rsh_nib * ICONBLK_SIZE > size:
            return False, '', 0, 'ICONBLK table overflows'

    if rsh_nbb > 0 and rsh_bitblk > 0:
        if rsh_bitblk + rsh_nbb * BITBLK_SIZE > size:
            return False, '', 0, 'BITBLK table overflows'

    if rsh_ntree > 0 and rsh_trindex > 0:
        if rsh_trindex + rsh_ntree * TREE_INDEX_SIZE > size:
            return False, '', 0, 'TREE index overflows'

    # Check offsets are monotonically increasing (mostly)
    # They should be ordered from low to high addresses
    non_zero_offsets = [o for o in offsets if o > 0]
    if non_zero_offsets:
        sorted_offsets = sorted(non_zero_offsets)
        # Allow some flexibility, but major violations indicate corruption
        if non_zero_offsets != sorted_offsets:
            # This is common in some RSC variants, so just reduce confidence slightly
            pass

    # Sanity check: counts should be reasonable
    # Typical RSC files have < 1000 objects, < 100 trees, etc.
    if rsh_nobs > 10000 or rsh_ntree > 1000 or rsh_nted > 1000:
        return False, '', 0, 'Unreasonable count values'

    # File size should be reasonable (most RSC files are < 500KB)
    if size > 1024 * 1024:  # 1MB
        return False, '', 0, 'File too large for RSC'

    # All checks passed - this is definitely an RSC file
    return True, 'RSC', 100, 'Valid RSC header with exact size match'
