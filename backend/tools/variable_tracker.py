"""Variable Tracker — tracks variable assignments and usage to find
NameError/UnboundLocalError causes.

Maps where each variable is assigned vs. where it's used, and identifies
variables that are used before (or without) being assigned.
"""

import ast
import builtins
from typing import Dict, List, Optional, Set


# Python builtins to exclude from undefined checks
BUILTINS = set(dir(builtins))


def track_variables(code_snippet: str) -> dict:
    """Track all variable assignments and usages in code.

    Args:
        code_snippet: Python source code string.

    Returns:
        dict with keys:
        - assignments: {name: [line_numbers]} where each var is assigned
        - usages: {name: [line_numbers]} where each var is used (read)
        - undefined_usages: list of {name, used_at, assigned_at} for
          variables used before or without assignment
    """
    if not code_snippet or not code_snippet.strip():
        return {
            "assignments": {},
            "usages": {},
            "undefined_usages": [],
        }

    try:
        tree = ast.parse(code_snippet)
    except SyntaxError:
        return {
            "assignments": {},
            "usages": {},
            "undefined_usages": [],
            "parse_error": "Code has syntax errors — cannot track variables",
        }

    assignments: Dict[str, List[int]] = {}
    usages: Dict[str, List[int]] = {}
    defined_names: Set[str] = set()  # All names that get defined anywhere

    for node in ast.walk(tree):
        # Assignments (Store context)
        if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Store):
            _add_to_dict(assignments, node.id, node.lineno)
            defined_names.add(node.id)

        # Usages (Load context)
        elif isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load):
            _add_to_dict(usages, node.id, node.lineno)

        # Function definitions → their name is assigned, args are defined
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            _add_to_dict(assignments, node.name, node.lineno)
            defined_names.add(node.name)
            for arg in node.args.args + node.args.posonlyargs + node.args.kwonlyargs:
                _add_to_dict(assignments, arg.arg, node.lineno)
                defined_names.add(arg.arg)
            if node.args.vararg:
                _add_to_dict(assignments, node.args.vararg.arg, node.lineno)
                defined_names.add(node.args.vararg.arg)
            if node.args.kwarg:
                _add_to_dict(assignments, node.args.kwarg.arg, node.lineno)
                defined_names.add(node.args.kwarg.arg)

        # Class definitions
        elif isinstance(node, ast.ClassDef):
            _add_to_dict(assignments, node.name, node.lineno)
            defined_names.add(node.name)

        # Imports
        elif isinstance(node, ast.Import):
            for alias in node.names:
                name = alias.asname if alias.asname else alias.name
                _add_to_dict(assignments, name, node.lineno)
                defined_names.add(name)

        elif isinstance(node, ast.ImportFrom):
            for alias in node.names:
                if alias.name != "*":
                    name = alias.asname if alias.asname else alias.name
                    _add_to_dict(assignments, name, node.lineno)
                    defined_names.add(name)

        # For loop targets
        elif isinstance(node, ast.For):
            _extract_targets(node.target, assignments, defined_names, node.lineno)

        # With statement 'as' variables
        elif isinstance(node, ast.With):
            for item in node.items:
                if item.optional_vars:
                    _extract_targets(item.optional_vars, assignments, defined_names, node.lineno)

        # Exception handler 'as' variable
        elif isinstance(node, ast.ExceptHandler):
            if node.name:
                _add_to_dict(assignments, node.name, node.lineno)
                defined_names.add(node.name)

        # Global/nonlocal
        elif isinstance(node, ast.Global):
            for name in node.names:
                _add_to_dict(assignments, name, node.lineno)
                defined_names.add(name)
        elif isinstance(node, ast.Nonlocal):
            for name in node.names:
                _add_to_dict(assignments, name, node.lineno)
                defined_names.add(name)

    # Find undefined usages
    undefined_usages = _find_undefined_usages(assignments, usages, defined_names)

    return {
        "assignments": assignments,
        "usages": usages,
        "undefined_usages": undefined_usages,
    }


def _add_to_dict(d: Dict[str, List[int]], name: str, lineno: int):
    """Add a line number to a name's list in the dict."""
    if name not in d:
        d[name] = []
    if lineno not in d[name]:
        d[name].append(lineno)


def _extract_targets(
    target, assignments: Dict[str, List[int]], defined_names: Set[str], lineno: int
):
    """Extract assignment targets from potentially nested structures."""
    if isinstance(target, ast.Name):
        _add_to_dict(assignments, target.id, lineno)
        defined_names.add(target.id)
    elif isinstance(target, (ast.Tuple, ast.List)):
        for elt in target.elts:
            _extract_targets(elt, assignments, defined_names, lineno)


def _find_undefined_usages(
    assignments: Dict[str, List[int]],
    usages: Dict[str, List[int]],
    defined_names: Set[str],
) -> List[dict]:
    """Find variables that are used before or without assignment.

    A usage is 'undefined' if:
    1. The name is never assigned anywhere in the code AND not a builtin, OR
    2. The name is used at a line BEFORE its first assignment

    Note: This is a simplified flat-scope analysis — does not handle
    nested function scopes correctly (v1 limitation).
    """
    undefined = []

    for name, usage_lines in usages.items():
        # Skip builtins
        if name in BUILTINS:
            continue

        # Case 1: Never assigned anywhere
        if name not in assignments:
            for line in usage_lines:
                undefined.append({
                    "name": name,
                    "used_at": line,
                    "assigned_at": None,
                })
            continue

        # Case 2: Used before first assignment
        first_assignment = min(assignments[name])
        for usage_line in usage_lines:
            if usage_line < first_assignment:
                undefined.append({
                    "name": name,
                    "used_at": usage_line,
                    "assigned_at": first_assignment,
                })

    # Sort by line number for consistent output
    undefined.sort(key=lambda x: x["used_at"])
    return undefined
