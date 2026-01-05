"""
Atari ST image format detectors.

Formats:
- DEGAS uncompressed: PI1, PI2, PI3 (fixed 32034 bytes)
- DEGAS Elite compressed: PC1, PC2, PC3 (compressed, <32066 bytes)
- NEOchrome: NEO (fixed 32128 bytes)
- STAD: PAC (compressed with pM85/pM86 signature)
- GEM IMG: IMG (header-based)
"""

from utils.binary_utils import read_be_word
from utils.palette_validation import palette_looks_valid
from utils.decompression import decompress_degas_elite, decompress_stad


def detect_stad_pac(data, size):
    """
    Detect STAD PAC compressed images.
    Signature: pM85 or pM86 + compression params + compressed data

    Args:
        data: file content bytes
        size: file size

    Returns:
        tuple: (match: bool, ext: str, confidence: int, reason: str)
    """
    # Minimum size: signature (4) + params (3) + data
    if size < 20:
        return False, '', 0, ''

    # Check signature: "pM85" or "pM86"
    if data[0:4] not in [b'pM85', b'pM86']:
        return False, '', 0, ''

    # Extract compression parameters
    id_byte = data[4]
    pack_byte = data[5]
    special_byte = data[6]

    # Sanity: IdByte and SpecialByte should differ
    if id_byte == special_byte:
        return False, '', 0, 'Invalid compression params'

    # Try to decompress - PROOF STEP
    compressed_data_start = 7
    decompressed = decompress_stad(data, compressed_data_start, id_byte,
                                   pack_byte, special_byte, expected_size=32000)

    if decompressed is None:
        return False, '', 0, 'Decompression failed'

    if len(decompressed) != 32000:
        return False, '', 0, f'Wrong decompressed size: {len(decompressed)}'

    # Decompression proof succeeded
    return True, 'PAC', 100, 'Valid STAD PAC with successful decompression'


def detect_degas_pi(data, size):
    """
    Detect DEGAS uncompressed images (PI1/PI2/PI3).
    Fixed size: 32034 bytes (2 + 32 + 32000)

    Args:
        data: file content bytes
        size: file size

    Returns:
        tuple: (match: bool, ext: str, confidence: int, reason: str)
    """
    # EXACT SIZE CHECK
    if size != 32034:
        return False, '', 0, ''

    # Read resolution word
    res_word = read_be_word(data, 0)
    if res_word is None:
        return False, '', 0, ''

    # Resolution must be 0, 1, or 2
    if res_word not in [0, 1, 2]:
        return False, '', 0, f'Invalid resolution: {res_word}'

    # Validate palette (16 words starting at offset 2)
    if not palette_looks_valid(data, 2, 16):
        return False, '', 0, 'Invalid palette'

    # Map resolution to extension
    ext_map = {0: 'PI1', 1: 'PI2', 2: 'PI3'}
    ext = ext_map[res_word]

    return True, ext, 100, f'Valid DEGAS {ext} (resolution {res_word})'


def detect_degas_elite_uncompressed(data, size):
    """
    Detect DEGAS Elite uncompressed images (PI1/PI2/PI3).
    Fixed size: 32066 bytes (2 + 32 + 32000 + 32)

    This is different from DEGAS Elite compressed (which has high bit set).

    Args:
        data: file content bytes
        size: file size

    Returns:
        tuple: (match: bool, ext: str, confidence: int, reason: str)
    """
    # EXACT SIZE CHECK
    if size != 32066:
        return False, '', 0, ''

    # Read resolution word
    res_word = read_be_word(data, 0)
    if res_word is None:
        return False, '', 0, ''

    # Resolution must be 0, 1, or 2 (NO high bit set - that's compressed format)
    if res_word not in [0, 1, 2]:
        return False, '', 0, f'Invalid resolution: {res_word}'

    # Validate palette (16 words starting at offset 2)
    if not palette_looks_valid(data, 2, 16):
        return False, '', 0, 'Invalid palette'

    # Last 32 bytes are animation tables (by size check, they exist)
    # No need to validate their content - presence is enough

    # Map resolution to extension
    ext_map = {0: 'PI1', 1: 'PI2', 2: 'PI3'}
    ext = ext_map[res_word]

    return True, ext, 100, f'Valid DEGAS Elite {ext} uncompressed (resolution {res_word})'


def detect_neochrome(data, size):
    """
    Detect NEOchrome images (NEO).
    Fixed size: 32128 bytes (128-byte header + 32000 data)

    Args:
        data: file content bytes
        size: file size

    Returns:
        tuple: (match: bool, ext: str, confidence: int, reason: str)
    """
    # EXACT SIZE CHECK
    if size != 32128:
        return False, '', 0, ''

    # Parse header fields
    flag = read_be_word(data, 0)
    resolution = read_be_word(data, 2)
    # Palette at offset 4-35 (16 words)
    xoffset = read_be_word(data, 36)
    yoffset = read_be_word(data, 38)
    width = read_be_word(data, 40)
    height = read_be_word(data, 42)
    # Reserved area at 44-127

    if any(x is None for x in [flag, resolution, xoffset, yoffset, width, height]):
        return False, '', 0, ''

    # Strict header checks
    if flag != 0:
        return False, '', 0, 'flag != 0'

    if resolution not in [0, 1, 2]:
        return False, '', 0, f'Invalid resolution: {resolution}'

    if xoffset != 0 or yoffset != 0:
        return False, '', 0, 'Non-zero offset'

    if width != 320 or height != 200:
        return False, '', 0, f'Invalid dimensions: {width}x{height}'

    # Validate palette
    if not palette_looks_valid(data, 4, 16):
        return False, '', 0, 'Invalid palette'

    # Check reserved area is mostly zero (allow some tolerance)
    reserved = data[44:128]
    zero_count = sum(1 for b in reserved if b == 0)
    if zero_count < len(reserved) * 0.9:  # At least 90% zeros
        return False, '', 0, 'Reserved area not mostly zero'

    return True, 'NEO', 100, 'Valid NEOchrome image'


def detect_degas_elite(data, size):
    """
    Detect DEGAS Elite compressed images (PC1/PC2/PC3).
    Size: < 32066 bytes, resolution word has high bit set

    Args:
        data: file content bytes
        size: file size

    Returns:
        tuple: (match: bool, ext: str, confidence: int, reason: str)
    """
    # Size constraints
    MIN_SIZE = 2 + 32 + 32 + 100  # header + palette + tables + minimal compressed data
    MAX_SIZE = 32066

    if size < MIN_SIZE or size >= MAX_SIZE:
        return False, '', 0, ''

    # Read resolution word
    res_word = read_be_word(data, 0)
    if res_word is None:
        return False, '', 0, ''

    # High bit must be set for compressed format
    if (res_word & 0x8000) == 0:
        return False, '', 0, 'High bit not set'

    # Extract actual resolution (bits 0-1)
    resolution = res_word & 0x0003

    if resolution not in [0, 1, 2]:
        return False, '', 0, f'Invalid resolution: {resolution}'

    # Validate palette (16 words starting at offset 2)
    if not palette_looks_valid(data, 2, 16):
        return False, '', 0, 'Invalid palette'

    # Animation tables are in last 32 bytes
    # Compressed data is from offset 34 to (size - 32)
    compressed_start = 34
    compressed_end = size - 32

    if compressed_end <= compressed_start:
        return False, '', 0, 'No room for compressed data'

    # Try to decompress - PROOF STEP
    decompressed = decompress_degas_elite(data, compressed_start, 2)

    if decompressed is None:
        return False, '', 0, 'Decompression failed'

    if len(decompressed) != 32000:
        return False, '', 0, f'Wrong decompressed size: {len(decompressed)}'

    # Map resolution to extension
    ext_map = {0: 'PC1', 1: 'PC2', 2: 'PC3'}
    ext = ext_map[resolution]

    return True, ext, 100, f'Valid DEGAS Elite {ext} with successful decompression'


def detect_gem_img(data, size):
    """
    Detect GEM IMG raster images.
    Header-based detection (full decode not yet implemented).

    Args:
        data: file content bytes
        size: file size

    Returns:
        tuple: (match: bool, ext: str, confidence: int, reason: str)
    """
    # Minimum header size: 8 words = 16 bytes
    if size < 16:
        return False, '', 0, ''

    # Parse header (big-endian)
    version = read_be_word(data, 0)
    header_len_words = read_be_word(data, 2)
    planes = read_be_word(data, 4)
    pattern_len = read_be_word(data, 6)
    pixel_width = read_be_word(data, 8)
    pixel_height = read_be_word(data, 10)
    line_width = read_be_word(data, 12)
    num_lines = read_be_word(data, 14)

    if any(x is None for x in [version, header_len_words, planes, pattern_len,
                                pixel_width, pixel_height, line_width, num_lines]):
        return False, '', 0, ''

    # Version must be 1
    if version != 1:
        return False, '', 0, f'Version != 1: {version}'

    # Header length must be >= 8 words
    if header_len_words < 8:
        return False, '', 0, f'Header length too small: {header_len_words}'

    # Planes should be 1-8 (typically 1 for monochrome)
    if planes < 1 or planes > 8:
        return False, '', 0, f'Invalid planes: {planes}'

    # Dimensions should be reasonable
    if pixel_width == 0 or pixel_height == 0:
        return False, '', 0, 'Zero dimensions'

    if pixel_width > 4096 or pixel_height > 4096:
        return False, '', 0, 'Dimensions too large'

    if line_width == 0 or num_lines == 0:
        return False, '', 0, 'Zero line dimensions'

    # Data offset calculation
    data_offset = header_len_words * 2
    if data_offset >= size:
        return False, '', 0, 'Data offset >= file size'

    # Without full decoding, we can only give moderate confidence
    # With full IMG decoder implementation, this would be 100
    return True, 'IMG', 90, 'Valid GEM IMG header (decode not verified)'


def detect_image(data, size):
    """
    Master detector for all image formats.
    Tries formats in priority order (most specific first).

    Args:
        data: file content bytes
        size: file size

    Returns:
        tuple: (match: bool, ext: str, confidence: int, reason: str)
    """
    # Try magic-based formats first
    match, ext, conf, reason = detect_stad_pac(data, size)
    if match:
        return match, ext, conf, reason

    # Try fixed-size formats
    match, ext, conf, reason = detect_degas_pi(data, size)
    if match:
        return match, ext, conf, reason

    match, ext, conf, reason = detect_degas_elite_uncompressed(data, size)
    if match:
        return match, ext, conf, reason

    match, ext, conf, reason = detect_neochrome(data, size)
    if match:
        return match, ext, conf, reason

    # Try compressed format with decompression proof
    match, ext, conf, reason = detect_degas_elite(data, size)
    if match:
        return match, ext, conf, reason

    # Try GEM IMG last (header-only validation)
    match, ext, conf, reason = detect_gem_img(data, size)
    if match:
        return match, ext, conf, reason

    return False, '', 0, ''
