"""
Text and source code file type detector for Atari ST files.

Uses weighted evidence scoring to detect:
.C, .H, .S, .INF, Makefile, .BAT, .PRJ, .RSD, .TXT
"""

import re
import os


# Thresholds
STRONG_MIN = 8  # Minimum score to confidently classify
MARGIN = 3      # Minimum margin over second-best to avoid ambiguity


def extract_embedded_filename(text):
    """
    Extract embedded filename from comment headers in source files.

    Many Atari ST header files contain the filename in the first few lines
    of comments, using various patterns.

    Args:
        text: decoded file content

    Returns:
        str: embedded filename (without extension) or None if not found

    Examples:
        /* GEMBIND.H Do-It-Yourself... */ → "GEMBIND"
        * SETJMP.H → "SETJMP"
        * access.h -- modes for... → "access"
        @(#)math.h 3.1 12/30/85 → "math"
    """
    lines = text.split('\n')

    # Search first 20 lines for embedded filename
    search_lines = lines[:min(20, len(lines))]

    for line in search_lines:
        # Pattern 1: SCCS/RCS style: @(#)filename.ext
        # Example: " *  @(#)math.h	3.1	12/30/85"
        sccs_match = re.search(r'@\(#\)\s*([a-zA-Z_][a-zA-Z0-9_\-]*\.[a-zA-Z]{1,3})', line, re.IGNORECASE)
        if sccs_match:
            full_name = sccs_match.group(1)
            return os.path.splitext(full_name)[0]

        # Pattern 2: Asterisk continuation line with filename
        # Examples:
        #   " * SETJMP.H"
        #   " * access.h -- modes for the access system call."
        #   " * aesbind.h -- give bindings and structures"
        #   " * ASCII.H   -   Definition der ASCII..."
        # Match: <whitespace> * <whitespace> FILENAME.EXT [whitespace or -- or - or end]
        asterisk_match = re.search(r'^\s*\*\s+([a-zA-Z_][a-zA-Z0-9_\-]*\.[a-zA-Z]{1,3})(?:\s*$|\s+--|\s+-{1,2}\s)', line, re.IGNORECASE)
        if asterisk_match:
            full_name = asterisk_match.group(1)
            return os.path.splitext(full_name)[0]

        # Pattern 3: C-style comment with filename on same line
        # Examples:
        #   "/*	GEMBIND.H Do-It-Yourself GEM binding kit.			*/"
        #   "/*      EXT.H"
        # Match: /* <whitespace> FILENAME.EXT [end or whitespace or -- or description]
        c_comment_match = re.search(r'/\*\s+([a-zA-Z_][a-zA-Z0-9_\-]*\.[a-zA-Z]{1,3})(?:\s*$|\s+--|\s+-{1,2}\s|\s+\w)', line, re.IGNORECASE)
        if c_comment_match:
            full_name = c_comment_match.group(1)
            return os.path.splitext(full_name)[0]

        # Pattern 4: Standalone filename on line (after /* on previous line)
        # Example: "/*      EXT.H" or just "        EXT.H" as a standalone line
        # Match: <whitespace> FILENAME.EXT <whitespace or end>
        # Must be early in file and not have other text on same line
        standalone_match = re.search(r'^\s*([a-zA-Z_][a-zA-Z0-9_\-]*\.[a-zA-Z]{1,3})\s*$', line, re.IGNORECASE)
        if standalone_match:
            full_name = standalone_match.group(1)
            # Only accept if it looks like a reasonable header filename (not a random word)
            # Check that extension is plausible for header/source
            ext = os.path.splitext(full_name)[1].upper()
            if ext in ['.H', '.C', '.S', '.INC', '.HPP', '.CPP']:
                return os.path.splitext(full_name)[0]

        # Pattern 5: C++-style comment with filename
        # Example: "// FILENAME.H - description"
        cpp_comment_match = re.search(r'//\s+([a-zA-Z_][a-zA-Z0-9_\-]*\.[a-zA-Z]{1,3})\s+[-:]', line, re.IGNORECASE)
        if cpp_comment_match:
            full_name = cpp_comment_match.group(1)
            return os.path.splitext(full_name)[0]

    return None


def is_text_file(data, max_binary_ratio=0.05):
    """
    Check if file appears to be text (ASCII/UTF-8).
    Allows some binary content but rejects heavily binary files.

    Args:
        data: file content bytes
        max_binary_ratio: maximum ratio of non-text bytes allowed

    Returns:
        bool: True if file appears to be text
    """
    if len(data) == 0:
        return False

    # Try to decode as text with common Atari ST encodings
    try:
        # Try ASCII first (most common)
        text = data.decode('ascii', errors='ignore')
    except:
        try:
            # Try latin-1 as fallback
            text = data.decode('latin-1', errors='ignore')
        except:
            return False

    # Count non-printable characters (excluding common whitespace)
    printable_count = 0
    for char in text:
        if char.isprintable() or char in '\n\r\t':
            printable_count += 1

    if len(text) == 0:
        return False

    printable_ratio = printable_count / len(text)

    return printable_ratio >= (1.0 - max_binary_ratio)


def decode_text(data):
    """
    Decode bytes to text, trying common Atari ST encodings.

    Args:
        data: file content bytes

    Returns:
        str: decoded text or empty string on failure
    """
    for encoding in ['ascii', 'latin-1', 'utf-8']:
        try:
            return data.decode(encoding, errors='ignore')
        except:
            continue
    return ''


def detect_c_source(text, size):
    """
    Detect C source files (.C).

    Args:
        text: decoded file content
        size: file size

    Returns:
        int: confidence score
    """
    score = 0

    # Strong evidence: C preprocessor and structure
    c_markers = [
        (r'#include\s+[<"]', 4),  # #include (increased from 3 - very strong C indicator)
        (r'\bint\s+main\s*\(', 3),  # int main(
        (r'\bvoid\s+main\s*\(', 3),  # void main(
        (r'\breturn\s+', 2),  # return statement
        (r'\bprintf\s*\(', 2),  # printf
        (r'\bmalloc\s*\(', 2),  # malloc
        (r'\bfree\s*\(', 2),  # free
        (r'\bsizeof\s*\(', 2),  # sizeof
    ]

    for pattern, points in c_markers:
        if re.search(pattern, text):
            score += points

    # Check for balanced braces
    open_braces = text.count('{')
    close_braces = text.count('}')
    if open_braces > 0 and close_braces > 0:
        if abs(open_braces - close_braces) <= 2:  # Allow small imbalance
            score += 3

    # Moderate evidence: C keywords
    c_keywords = ['typedef', 'struct', 'enum', 'static', 'extern',
                  'const', 'volatile', 'switch', 'case', 'break', 'continue']

    keyword_count = sum(1 for kw in c_keywords if re.search(r'\b' + kw + r'\b', text))
    score += min(keyword_count, 4)  # Cap at 4 points

    # C-style comments
    if re.search(r'/\*.*?\*/', text, re.DOTALL):
        score += 1
    if '//' in text:
        score += 1

    # Preprocessor directives
    if re.search(r'^\s*#define\b', text, re.MULTILINE):
        score += 2

    # Anti-signals
    lines = text.split('\n')
    # Assembly-like (semicolon comments at line start)
    asm_comment_lines = sum(1 for line in lines if line.lstrip().startswith(';'))
    if asm_comment_lines > len(lines) * 0.1:
        score -= 3

    # Makefile-like (target: rules)
    if re.search(r'^\w+\s*:', text, re.MULTILINE):
        makefile_rules = len(re.findall(r'^\w+\s*:', text, re.MULTILINE))
        if makefile_rules > 3:
            score -= 3

    # Size hint: very small files are less likely to be .C
    if size < 80:
        score -= 2

    # Anti-signal: lots of #define without function bodies suggests header, not .C
    define_count = len(re.findall(r'^\s*#define\b', text, re.MULTILINE))
    if define_count >= 10 and open_braces <= 1:
        score -= 4  # Likely a header file, not C source

    return max(0, score)


def detect_h_header(text, size):
    """
    Detect C header files (.H).

    Args:
        text: decoded file content
        size: file size

    Returns:
        int: confidence score
    """
    score = 0

    # Count #define statements (very common in headers)
    define_count = len(re.findall(r'^\s*#define\b', text, re.MULTILINE))
    if define_count >= 10:
        score += 5  # Lots of defines is very strong header evidence
    elif define_count >= 5:
        score += 4  # Many defines is strong header evidence
    elif define_count >= 2:
        score += 2

    # Strong evidence: header guards
    if re.search(r'#ifndef\s+\w+', text) and re.search(r'#define\s+\w+', text) and '#endif' in text:
        score += 3

    # Function prototypes (declarations without bodies)
    # Look for patterns like: type name(...);
    prototypes = re.findall(r'\b\w+\s+\w+\s*\([^)]*\)\s*;', text)
    if len(prototypes) >= 2:
        score += 3

    # typedef patterns
    if re.search(r'\btypedef\s+struct\b', text):
        score += 2

    # extern declarations
    if 'extern' in text:
        score += 2

    # #include but few braces (headers don't usually have function bodies)
    if '#include' in text:
        score += 2

    open_braces = text.count('{')
    if open_braces <= 2:  # Very few or no function bodies
        score += 2

    # C-style comments (common in headers)
    if re.search(r'/\*.*?\*/', text, re.DOTALL):
        score += 1

    # Mandatory anti-signals
    # Should NOT have main()
    if re.search(r'\bmain\s*\(', text):
        score -= 5

    # Should NOT have lots of function bodies
    if open_braces > 5:
        score -= 3

    return max(0, score)


def detect_assembly(text, size):
    """
    Detect assembly source files (.S) - Motorola 68000 syntax.

    Args:
        text: decoded file content
        size: file size

    Returns:
        int: confidence score
    """
    score = 0

    # Strong evidence: 68k directives
    asm_directives = [
        r'\bSECTION\b',
        r'\bTEXT\b',
        r'\bDATA\b',
        r'\bBSS\b',
        r'\bDC\.[BWL]\b',
        r'\bDS\.[BWL]\b',
        r'\bEQU\b',
        r'\bORG\b',
        r'\bEND\b',
        r'\bXDEF\b',
        r'\bXREF\b',
        r'\bGLOBL\b',
    ]

    directive_count = sum(1 for pattern in asm_directives
                         if re.search(pattern, text, re.IGNORECASE))

    score += directive_count * 3  # 3 points per directive

    # Semicolon comments (common in assembly)
    lines = text.split('\n')
    comment_lines = sum(1 for line in lines if line.lstrip().startswith(';'))
    if comment_lines > len(lines) * 0.1:  # > 10% are comments
        score += 3

    # Labels at line start (pattern: label:)
    labels = re.findall(r'^[A-Za-z_\.][\w\.]*:\s', text, re.MULTILINE)
    if len(labels) >= 3:
        score += 3

    # 68k mnemonics (expanded list to catch more assembly patterns)
    mnemonics = ['MOVE', 'MOVEA', 'MOVEM', 'MOVEQ', 'ADD', 'ADDA', 'ADDI', 'ADDQ',
                 'SUB', 'SUBA', 'SUBI', 'SUBQ', 'LEA', 'PEA', 'JSR', 'JMP',
                 'BRA', 'BSR', 'BEQ', 'BNE', 'BGT', 'BLT', 'BGE', 'BLE',
                 'RTS', 'RTE', 'CLR', 'CMP', 'CMPA', 'CMPI', 'TST',
                 'AND', 'OR', 'EOR', 'NOT', 'NEG', 'EXT', 'SWAP',
                 'TRAP', 'LINK', 'UNLK', 'BTST', 'BSET', 'BCLR']

    mnemonic_count = sum(1 for m in mnemonics
                        if re.search(r'\b' + m + r'\b', text, re.IGNORECASE))
    score += min(mnemonic_count, 5) * 2  # Up to 10 points

    # For very small files (< 200 bytes), if we find mnemonics and hex patterns,
    # give bonus points since they're likely code snippets
    if size < 200 and mnemonic_count >= 2:
        score += 4  # Bonus for small assembly snippets

    # Hex immediate patterns: #$[0-9A-F]+
    if re.search(r'#\$[0-9A-Fa-f]+', text):
        score += 2

    # Anti-signals: C-like syntax (strengthened to avoid C/S ambiguity)
    if re.search(r'#include\s+[<"]', text):
        score -= 8  # Very strong penalty - #include is uniquely C

    if text.count('{') > 5 or text.count('}') > 5:
        score -= 6  # Increased penalty for braces

    # C-style block comments /* */ are not assembly
    if re.search(r'/\*.*?\*/', text, re.DOTALL):
        score -= 4

    # Strong anti-signal: #define is C preprocessor, not assembly
    define_count = len(re.findall(r'^\s*#define\b', text, re.MULTILINE))
    if define_count >= 5:
        score -= 8  # Stronger penalty for lots of #define
    elif define_count >= 2:
        score -= 5  # Stronger penalty even for few #defines

    return max(0, score)


def detect_inf(text, size):
    """
    Detect INF configuration files (.INF).

    Args:
        text: decoded file content
        size: file size

    Returns:
        int: confidence score
    """
    score = 0

    lines = text.split('\n')

    # KEY=VALUE patterns
    kv_lines = sum(1 for line in lines if '=' in line and not line.lstrip().startswith('#'))
    if kv_lines >= len(lines) * 0.1:  # At least 10% KEY=VALUE
        score += 3

    # Drive letter paths (A:\, C:\, etc.)
    drive_paths = re.findall(r'[A-Z]:\\', text)
    if len(drive_paths) >= 2:
        score += 3

    # INF-specific keywords
    inf_keywords = ['DESKTOP', 'NEWDESK', 'GEMDESK', 'PATH', 'FILE',
                    'DEVICE', 'PRINTER', 'PORT', 'WINDOW', 'AUTO']

    keyword_count = sum(1 for kw in inf_keywords
                       if re.search(r'\b' + kw + r'\b', text, re.IGNORECASE))
    score += min(keyword_count, 5)

    # Anti-signals: code-like syntax
    if text.count('{') > 2 or '#include' in text:
        score -= 4

    if re.search(r'\bDC\.[BWL]\b', text, re.IGNORECASE):
        score -= 4

    return max(0, score)


def detect_makefile(text, size):
    """
    Detect Makefiles.

    Args:
        text: decoded file content
        size: file size

    Returns:
        int: confidence score
    """
    score = 0

    # Rule lines: target: dependencies
    rules = re.findall(r'^[^\s:#=]+(\s+[^\s:]+)*\s*:\s+', text, re.MULTILINE)
    if len(rules) >= 1:
        score += 4

    # Tab-indented command lines (recipes)
    lines = text.split('\n')
    tab_lines = sum(1 for line in lines if line.startswith('\t') and len(line.strip()) > 0)
    if tab_lines >= 1:
        score += 4

    # Make variables
    if re.search(r'CC\s*=', text):
        score += 2
    if re.search(r'CFLAGS\s*=', text):
        score += 2
    if re.search(r'LDFLAGS\s*=', text):
        score += 2

    # Macro usage: $(VAR), $@, $<, $^
    if re.search(r'\$\([\w]+\)', text):
        score += 2
    if re.search(r'\$[@<^]', text):
        score += 2

    # Common targets
    common_targets = ['all:', 'clean:', 'install:']
    target_count = sum(1 for t in common_targets if t in text)
    score += target_count * 2

    # Anti-signals
    if text.count('{') > 10:
        score -= 5

    return max(0, score)


def detect_bat(text, size):
    """
    Detect batch files (.BAT).

    Args:
        text: decoded file content
        size: file size

    Returns:
        int: confidence score
    """
    score = 0

    # Batch commands
    bat_commands = ['echo', 'REM', 'cd', 'copy', 'del', 'ren',
                    'mkdir', 'rmdir', 'path', 'set']

    lines = text.split('\n')

    command_count = 0
    for cmd in bat_commands:
        pattern = r'^\s*' + cmd + r'\b'
        if re.search(pattern, text, re.IGNORECASE | re.MULTILINE):
            command_count += 1

    if command_count >= 2:
        score += 4

    # @echo (batch marker)
    if re.search(r'^\s*@?echo\b', text, re.IGNORECASE | re.MULTILINE):
        score += 2

    # SET VAR=
    if re.search(r'^\s*SET\s+\w+=', text, re.IGNORECASE | re.MULTILINE):
        score += 2

    # IF / GOTO / labels
    if re.search(r'\bIF\b', text, re.IGNORECASE):
        score += 2
    if re.search(r'\bGOTO\b', text, re.IGNORECASE):
        score += 2

    # Anti-signals
    # Makefile patterns
    if re.search(r'^\w+\s*:', text, re.MULTILINE) and '\t' in text:
        score -= 4

    return max(0, score)


def detect_prj(text, size):
    """
    Detect project files (.PRJ).

    Args:
        text: decoded file content
        size: file size

    Returns:
        int: confidence score
    """
    score = 0

    # Source file references
    source_extensions = [r'\.c\b', r'\.h\b', r'\.s\b', r'\.o\b',
                        r'\.prg\b', r'\.ttp\b', r'\.tos\b', r'\.rsc\b']

    ref_count = sum(len(re.findall(pattern, text, re.IGNORECASE))
                   for pattern in source_extensions)

    if ref_count >= 5:
        score += 3

    # Compiler/linker flags
    flag_patterns = [r'-I', r'-D', r'-L', r'-l', r'-O', r'-g']
    flag_count = sum(1 for pattern in flag_patterns if pattern in text)
    if flag_count >= 2:
        score += 2

    # INI-like sections
    if re.search(r'^\[[\w]+\]', text, re.MULTILINE):
        score += 2

    # Paths with backslashes
    if re.search(r'\\[\w\.]+', text):
        score += 1

    # Anti-signals: actual code
    if text.count('{') > 10:
        score -= 4

    # Not a makefile
    if re.search(r'^\w+\s*:', text, re.MULTILINE) and '\t' in text:
        score -= 3

    return max(0, score)


def detect_rsd(text, size):
    """
    Detect GEM Resource Definition files (.RSD).

    Args:
        text: decoded file content
        size: file size

    Returns:
        int: confidence score
    """
    score = 0

    # Resource object keywords
    resource_keywords = ['OBJECT', 'TREE', 'DIALOG', 'FORM', 'MENU',
                        'TEDINFO', 'ICON', 'BITBLK', 'CICON', 'STRING', 'ALERT']

    keyword_count = sum(1 for kw in resource_keywords
                       if re.search(r'\b' + kw + r'\b', text, re.IGNORECASE))

    if keyword_count >= 2:
        score += 3

    # Lots of numeric tables (comma-separated integers/hex)
    lines = text.split('\n')
    numeric_lines = sum(1 for line in lines if ',' in line and re.search(r'\d+', line))
    if numeric_lines > len(lines) * 0.2:  # > 20% numeric
        score += 2

    # ALLCAPS identifiers (common in resource files)
    allcaps_count = len(re.findall(r'\b[A-Z_][A-Z0-9_]{3,}\b', text))
    if allcaps_count > 10:
        score += 2

    # Anti-signals
    if '#include' in text and text.count('{') > 5:
        score -= 4

    if re.search(r'\bDC\.[BWL]\b', text, re.IGNORECASE):
        score -= 4

    return max(0, score)


def detect_text_type(data, size):
    """
    Master text file type detector using weighted scoring.

    Args:
        data: file content bytes
        size: file size

    Returns:
        tuple: (match: bool, ext: str, confidence: int, reason: str, extra_info: dict)
        extra_info may contain 'embedded_name' for files with embedded filenames
    """
    # First check if file is text
    if not is_text_file(data):
        return False, '', 0, 'Not a text file', {}

    # Decode to text
    text = decode_text(data)
    if not text:
        return False, '', 0, 'Cannot decode text', {}

    # Run all detectors
    scores = {
        'C': detect_c_source(text, size),
        'H': detect_h_header(text, size),
        'S': detect_assembly(text, size),
        'INF': detect_inf(text, size),
        'MAK': detect_makefile(text, size),
        'BAT': detect_bat(text, size),
        'PRJ': detect_prj(text, size),
        'RSD': detect_rsd(text, size),
    }

    # Find best and second-best
    sorted_scores = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    best_type, best_score = sorted_scores[0]
    second_score = sorted_scores[1][1] if len(sorted_scores) > 1 else 0

    # Try to extract embedded filename early (for .H/.C files)
    # This is done before classification decisions so we can use it even for ambiguous cases
    embedded_name = extract_embedded_filename(text)
    extra_info = {}
    if embedded_name:
        extra_info['embedded_name'] = embedded_name

    # Check thresholds
    if best_score < STRONG_MIN:
        # Not confident enough - use TXT fallback
        # But check if best_type was H or C and we have embedded name
        if best_type in ('H', 'C') and embedded_name:
            # Use the embedded filename to help classify
            return True, best_type, 60, f'{best_type} score: {best_score} (embedded name found)', extra_info
        return True, 'TXT', 50, 'No strong type match, defaulting to TXT', extra_info

    if best_score - second_score < MARGIN:
        # Too ambiguous - but check if H or C is in top 2 and we have embedded name
        second_type = sorted_scores[1][0] if len(sorted_scores) > 1 else None
        if embedded_name and ('H' in (best_type, second_type) or 'C' in (best_type, second_type)):
            # Prefer H/C when we have an embedded filename
            chosen_type = best_type if best_type in ('H', 'C') else second_type
            return True, chosen_type, 65, f'{chosen_type} (embedded name: {embedded_name})', extra_info
        return True, 'TXT', 50, f'Ambiguous between {best_type} ({best_score}) and {second_type} ({second_score})', extra_info

    # Confident match
    confidence = min(95, 70 + best_score)  # Scale score to confidence
    return True, best_type, confidence, f'{best_type} score: {best_score}', extra_info
