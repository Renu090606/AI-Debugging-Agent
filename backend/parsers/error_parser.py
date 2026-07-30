"""Error parser — extracts structured ErrorContext from raw Python tracebacks."""

import re
from typing import List

from .models import ErrorContext


# Regex patterns for traceback parsing
# Matches: File "filename.py", line 12, in <module>
FRAME_PATTERN = re.compile(
    r'File "([^"]+)", line (\d+)(?:, in (.+))?'
)

# Matches the final error line: ErrorType: message
# Handles both "ErrorType: message" and bare "ErrorType"
ERROR_LINE_PATTERN = re.compile(
    r"^(\w+(?:Error|Exception|Warning|Exit))\s*(?::\s*(.+))?$"
)

# SyntaxError specific: matches the caret indicator line
SYNTAX_CARET_PATTERN = re.compile(r"^\s*\^~*\s*$")

# SyntaxError format: has filename and line before the error
SYNTAX_FILE_PATTERN = re.compile(
    r'File "([^"]+)", line (\d+)'
)


def parse_error(traceback_str: str, code_snippet: str = "") -> ErrorContext:
    """Parse a raw Python traceback into a structured ErrorContext.

    Args:
        traceback_str: Raw traceback text (as copied from terminal).
        code_snippet: The full source code of the Python file being debugged.

    Returns:
        ErrorContext with extracted error details. Never raises — returns
        defaults for unparseable inputs.
    """
    # Handle empty/null input
    if not traceback_str or not traceback_str.strip():
        return ErrorContext(
            error_type="UnknownError",
            error_message="No traceback provided",
            line_number=0,
            file_name="unknown",
            code_lines=[],
            full_traceback="",
        )

    traceback_str = traceback_str.strip()
    lines = traceback_str.splitlines()

    # Try to parse as a standard traceback
    error_type, error_message = _extract_error_type_and_message(lines)
    file_name, line_number = _extract_innermost_frame(lines)

    # Handle SyntaxError special format
    if error_type == "SyntaxError":
        file_name, line_number = _parse_syntax_error(lines, file_name, line_number)

    # Extract code context lines
    code_lines = _extract_code_lines(code_snippet, line_number)

    return ErrorContext(
        error_type=error_type,
        error_message=error_message,
        line_number=line_number,
        file_name=file_name,
        code_lines=code_lines,
        full_traceback=traceback_str,
    )


def _extract_error_type_and_message(lines: List[str]) -> tuple:
    """Extract error type and message from the last meaningful line.

    Standard format: 'TypeError: unsupported operand type(s)...'
    Bare format: 'KeyboardInterrupt'
    """
    # Search from the bottom up for the error line
    for line in reversed(lines):
        line = line.strip()
        if not line:
            continue

        match = ERROR_LINE_PATTERN.match(line)
        if match:
            error_type = match.group(1)
            error_message = match.group(2) or ""
            return error_type, error_message.strip()

    # Could not identify a Python error pattern
    # Return the last non-empty line as the message
    last_line = ""
    for line in reversed(lines):
        if line.strip():
            last_line = line.strip()
            break

    return "NotPythonError", last_line


def _extract_innermost_frame(lines: List[str]) -> tuple:
    """Extract file name and line number from the innermost (last) stack frame.

    In a multi-frame traceback, the last 'File ...' line is where the
    error actually occurred.
    """
    file_name = "unknown"
    line_number = 0

    for line in lines:
        match = FRAME_PATTERN.search(line)
        if match:
            file_name = match.group(1)
            line_number = int(match.group(2))

    return file_name, line_number


def _parse_syntax_error(
    lines: List[str], default_file: str, default_line: int
) -> tuple:
    """Handle SyntaxError's special traceback format.

    SyntaxError tracebacks look different:
        File "example.py", line 5
            x = (1 +
                ^
        SyntaxError: invalid syntax

    The file/line info may appear differently than runtime errors.
    """
    file_name = default_file
    line_number = default_line

    for line in lines:
        match = SYNTAX_FILE_PATTERN.search(line)
        if match:
            file_name = match.group(1)
            line_number = int(match.group(2))
            # Don't break — take the last match (innermost frame)

    return file_name, line_number


def _extract_code_lines(code_snippet: str, line_number: int) -> List[str]:
    """Extract +-5 lines around the error line from the code snippet.

    Returns an empty list if code_snippet is empty or line_number is 0.
    Clamps to available bounds — never raises IndexError.
    """
    if not code_snippet or not code_snippet.strip() or line_number <= 0:
        return []

    source_lines = code_snippet.splitlines()

    # Convert to 0-indexed
    idx = line_number - 1

    # Clamp range to valid bounds
    start = max(0, idx - 5)
    end = min(len(source_lines), idx + 6)  # +6 because slice is exclusive

    return source_lines[start:end]
