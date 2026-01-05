### Task

Write a python script to read a binary file and cut it into multiple pieces.

The parameters are:
- binary file
- one or more offsets, either decimal, or hex (using "$" or "0x" prefix)

The output is:
- files numbered sequentially: the first uses the original binary filename and adds "-1" to filename, the second adds "-2", the third adds "-3", etc.
- with one offset, creates 2 files
- with two offsets, creates 3 files
- with N offsets, creates N+1 files



### Tests

Use the example/test.bin for testing.

#### Test 1: Single cut point
Make a cut at offset 96304
- Expected: 2 files created
- File 2 should start with byte sequence (hex codes): 23 64 65 66 69 6E 65 20 53 45 54 54 49

#### Test 2: Multiple cut points
Make cuts at offsets 5 and 96304
- Expected: 3 files created
- File 1 should contain bytes: 21 12 53 74 2F
- File 2 should start with bytes: 2A 2A 2A 2A
- File 3 should start with bytes: 23 64 65 66 69 6E 65 20 53 45 54 54 49
- File 3 should end with bytes: 2A 2F 0D 0A 0D 0A

