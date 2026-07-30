"""Quick verification tests for the error parser (Phase 1)."""

from parsers import parse_error

# Test 1: Standard TypeError with multi-frame traceback
tb1 = """Traceback (most recent call last):
  File "main.py", line 12, in <module>
    result = add(x, y)
  File "main.py", line 5, in add
    return a + b
TypeError: unsupported operand type(s) for +: 'int' and 'str'"""

code1 = """def add(a, b):
    return a + b

x = 5
y = "hello"
result = add(x, y)
print(result)"""

result = parse_error(tb1, code1)
print("=== Test 1: Standard TypeError ===")
assert result.error_type == "TypeError", f"Expected TypeError, got {result.error_type}"
assert "unsupported operand" in result.error_message
assert result.line_number == 5, f"Expected line 5 (innermost), got {result.line_number}"
assert result.file_name == "main.py"
assert len(result.code_lines) > 0
print(f"  error_type: {result.error_type}")
print(f"  error_message: {result.error_message}")
print(f"  line_number: {result.line_number}")
print(f"  file_name: {result.file_name}")
print(f"  code_lines count: {len(result.code_lines)}")
print("  PASSED")
print()

# Test 2: Empty traceback
result2 = parse_error("", "")
print("=== Test 2: Empty input ===")
assert result2.error_type == "UnknownError"
assert result2.error_message == "No traceback provided"
assert result2.line_number == 0
assert result2.code_lines == []
print(f"  error_type: {result2.error_type}")
print(f"  error_message: {result2.error_message}")
print("  PASSED")
print()

# Test 3: SyntaxError
tb3 = """  File "example.py", line 5
    x = (1 +
        ^
SyntaxError: invalid syntax"""

result3 = parse_error(tb3, "line1\nline2\nline3\nline4\nx = (1 +\nline6")
print("=== Test 3: SyntaxError ===")
assert result3.error_type == "SyntaxError"
assert result3.error_message == "invalid syntax"
assert result3.line_number == 5
assert result3.file_name == "example.py"
print(f"  error_type: {result3.error_type}")
print(f"  line_number: {result3.line_number}")
print(f"  file_name: {result3.file_name}")
print("  PASSED")
print()

# Test 4: NameError with no code snippet
tb4 = """Traceback (most recent call last):
  File "app.py", line 3, in <module>
    print(undefined_var)
NameError: name 'undefined_var' is not defined"""

result4 = parse_error(tb4, "")
print("=== Test 4: NameError (no code snippet) ===")
assert result4.error_type == "NameError"
assert result4.line_number == 3
assert result4.code_lines == []
print(f"  error_type: {result4.error_type}")
print(f"  line_number: {result4.line_number}")
print(f"  code_lines: {result4.code_lines}")
print("  PASSED")
print()

# Test 5: Non-Python text
result5 = parse_error("some random garbage text", "")
print("=== Test 5: Non-Python text ===")
assert result5.error_type == "NotPythonError"
assert result5.line_number == 0
print(f"  error_type: {result5.error_type}")
print(f"  error_message: {result5.error_message}")
print("  PASSED")
print()

# Test 6: ModuleNotFoundError
tb6 = """Traceback (most recent call last):
  File "main.py", line 1, in <module>
    import nonexistent_module
ModuleNotFoundError: No module named 'nonexistent_module'"""

result6 = parse_error(tb6, "import nonexistent_module\nprint('hello')")
print("=== Test 6: ModuleNotFoundError ===")
assert result6.error_type == "ModuleNotFoundError"
assert result6.line_number == 1
print(f"  error_type: {result6.error_type}")
print(f"  error_message: {result6.error_message}")
print(f"  line_number: {result6.line_number}")
print("  PASSED")
print()

# Test 7: IndexError with short code (bounds check)
tb7 = """Traceback (most recent call last):
  File "short.py", line 2, in <module>
    x = arr[5]
IndexError: list index out of range"""

result7 = parse_error(tb7, "arr = [1, 2, 3]\nx = arr[5]")
print("=== Test 7: IndexError (short file, bounds check) ===")
assert result7.error_type == "IndexError"
assert result7.line_number == 2
assert len(result7.code_lines) == 2  # only 2 lines exist
print(f"  error_type: {result7.error_type}")
print(f"  code_lines: {result7.code_lines}")
print("  PASSED")
print()

# Test 8: None input
result8 = parse_error(None, None)
print("=== Test 8: None input ===")
assert result8.error_type == "UnknownError"
assert result8.line_number == 0
print(f"  error_type: {result8.error_type}")
print("  PASSED")
print()

print("=" * 40)
print("ALL 8 TESTS PASSED")
