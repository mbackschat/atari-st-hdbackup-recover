## Project Goal

I want to reverse engineer atari st files. My situation: I have a HD backup file that is only binary and contain many ST files. I want extract all kind of valid files from the byte stream.

Your task: write such files extractor in Python.

**Command Line Interface:**
```
python atari_extractor.py <input_file> [output_dir]

Arguments:
  input_file     : Binary file to extract from (required)
  output_dir     : Output directory (optional, default: "extracted")
```

Examples:
```
python atari_extractor.py test.st
python atari_extractor.py backup.hd extracted
```

### Requirements

- Ensure that output filenames are ATARI ST compatible
- When outputing the files, use a counter in the filename, like 00001.TXT, 00002.TXT etc.
- The filename extension is .TXT (we don't care whether its text)
- If the output folder does not exist, then create it. If it exists, then move the existing files into a randomly named subfolder


### Structure of the Binary Stream

The byte stream is a sequence of file fragments. The fragments have a header.

FRAGMENT
- HEADER (see below)
- CONTENT (bytes)
- ALIGNMENT (filler bytes to next 2-byte boundary)


FILE FRAGMENT HEADER structure (big endian; for Motorola 68000):
- Length: 4-Byte UNSIGNED LONG 
- Compression-Flag: 2-Byte WORD (treated as boolean)
- Last-Fragment-of-File-Flag: 2-Byte WORD (treated as boolean)

Flags:
- Compression-Flag: 0 = not compressed, 1 = compressed with a runlength encoding (RLE), see below
- Last-Fragment-of-File: 1 = true (It's the last fragment, next one will be a new file)

How to use the fragments:
A fragment content is first uncompressed (only if it was compressed), and then appended to the file content
The idea is to recreate file contents by combining its fragments.


#### Example

Here are hex byte sequence of sample headers:

1. Fragment-Header #1
00 00 8B 48 00 01 00 00
- Length 0x00008B48 = 35656 bytes
- Compression-Flag = 0x0001 (true) ==> RLE compressed (see below)
- Last-Fragment-of-File-Flag = 0x0000 ==> not last, so (at least) another fragment in the current file

Note: Length 0x00008B48 is even, so no filler bytes are needed to get to next 2-byte boundary

2. Fragment-Header #2
00 00 78 2C 00 00 00 00
- Length 0x0000782C = 30764 bytes
- Compression-Flag = 0x0000 (false) ==> not RLE compressed
- Last-Fragment-of-File-Flag = 0x0000 ==> not last, so (at least) another fragment in the current file

Note: Length 0x0000782C is even, so no filler bytes are needed to get to next 2-byte boundary

3. Fragment-Header #3
00 00 1A BC 00 01 00 01
- Length 0x00001ABC = 6844 bytes
- Compression-Flag = 0x0001 (true) ==> RLE compressed (see below)
- Last-Fragment-of-File-Flag = 0x0001 (true) ==> last fragment, so next fragment will be for new file!!!

Note: Length 0x00001ABC is even, so no filler bytes are needed to get to next 2-byte boundary

4. Fragment-Header #4
00 00 52 DF 00 01 00 01
(21215)
- Length 0x000052DF = 21215 bytes
- Compression-Flag = 0x0001 (true) ==> RLE compressed (see below)
- Last-Fragment-of-File-Flag = 0x0001 (true) ==> last fragment, so next fragment will be for new file!!!

Note: Length 0x000052DF is odd, so one filler byte is needed to get to next 2-byte boundary!!!!

The filler byte is 54, we just ignore it and get to the next Fragment-Header

5. Fragment-Header #5
00 00 43 C0  00 01 00 01
- Length 0x000043C0 = 17344 bytes
- Compression-Flag = 0x0001 (true) ==> RLE compressed (see below)
- Last-Fragment-of-File-Flag = 0x0001 (true) ==> last fragment, so next fragment will be for new file!!!

The binary stream ends.

The result is:

- File 1 is the combination of Fragment #1 (uncompressed), #2 (was not compressed), #3 (uncompressed)
- File 2 is Fragment #4 (uncompressed)
- File 3 is Fragment #5 (uncompressed)


#### How to uncompress the runlength encoding (RLE)

The RLE works like this. It uses 3 bytes

- 0xC7 is a marker
- 1-byte parameter for repetition
- 1-byte value to repeat: example 0xFE

Example: 0xC7 0x13 0xFE
==> The 3-byte seq with the byte 0xFE, repeated 0x13 times (19 times in decimal)



-----


### Analysis and Implementation Plan

The analysis and implementation is in this file: @PLAN.md

