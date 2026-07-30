"""Linter — runs flake8 on code to find style and logic issues.

Focuses on E-codes (errors) and W-codes (warnings).
Ignores C-codes (convention) for cleaner agent output.
"""

import os
import subprocess
import tempfile
from typing import List


def run_linter(code_snippet: str) -> dict:
    """Run flake8 linting on a code snippet.

    Writes code to a temp file, runs flake8 as subprocess, parses output.
    Handles: missing flake8, timeout, empty input gracefully.

    Args:
        code_snippet: Python source code string.

    Returns:
        dict with key 'issues': list of {line, col, code, message} dicts.
        May include 'error' key if flake8 unavailable or times out.
    """
    if not code_snippet or not code_snippet.strip():
        return {"issues": []}

    # Write to temp file
    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".py", delete=False
        ) as tmp:
            tmp.write(code_snippet)
            tmp_path = tmp.name

        # Run flake8
        issues = _run_flake8(tmp_path)
        return issues

    except FileNotFoundError:
        # flake8 not installed
        return {"issues": [], "error": "flake8 not available"}
    except subprocess.TimeoutExpired:
        return {"issues": [], "error": "Linter timed out"}
    except Exception as e:
        return {"issues": [], "error": f"Linter error: {str(e)}"}
    finally:
        # Clean up temp file
        if tmp_path and os.path.exists(tmp_path):
            os.unlink(tmp_path)


def _run_flake8(file_path: str) -> dict:
    """Execute flake8 and parse its output.

    Args:
        file_path: Path to the temp file to lint.

    Returns:
        dict with 'issues' list.
    """
    result = subprocess.run(
        [
            "flake8",
            "--select=E,W",
            "--format=default",
            "--max-line-length=120",
            file_path,
        ],
        capture_output=True,
        text=True,
        timeout=10,
    )

    # flake8 exits with 0 if no issues, 1 if issues found
    # Both are valid — parse stdout regardless
    issues = _parse_flake8_output(result.stdout)
    return {"issues": issues}


def _parse_flake8_output(output: str) -> List[dict]:
    """Parse flake8 output lines into structured issue dicts.

    Format: filename:line:col: CODE message
    Example: /tmp/code.py:5:1: E302 expected 2 blank lines, got 1
    """
    issues = []

    if not output or not output.strip():
        return issues

    for line in output.strip().splitlines():
        parsed = _parse_flake8_line(line)
        if parsed:
            issues.append(parsed)

    return issues


def _parse_flake8_line(line: str) -> dict:
    """Parse a single flake8 output line.

    Returns dict with line, col, code, message — or None if unparseable.
    """
    try:
        # Format: path:line:col: CODE message
        # Split on ': ' to separate path:line:col from 'CODE message'
        parts = line.split(": ", 1)
        if len(parts) != 2:
            return None

        location = parts[0]  # path:line:col
        code_and_msg = parts[1]  # CODE message

        # Extract line and col from location
        loc_parts = location.rsplit(":", 2)
        if len(loc_parts) < 3:
            return None

        line_num = int(loc_parts[-2])
        col_num = int(loc_parts[-1])

        # Extract code and message
        code_msg_parts = code_and_msg.split(" ", 1)
        code = code_msg_parts[0]
        message = code_msg_parts[1] if len(code_msg_parts) > 1 else ""

        return {
            "line": line_num,
            "col": col_num,
            "code": code,
            "message": message,
        }
    except (ValueError, IndexError):
        return None
