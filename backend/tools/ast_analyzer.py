"""AST Analyzer — analyzes code structure to find undefined names,
unused variables, function calls, and imports.

Uses Python's built-in ast module. Always wraps ast.parse() in
try/except SyntaxError — never lets it propagate.
"""

import ast
import builtins
from typing import Dict, List, Optional, Set


# Python builtins to exclude from "undefined" checks
BUILTINS = set(dir(builtins))


def analyze_ast(code_snippet: str) -> dict:
    """Analyze code's Abstract Syntax Tree for structural issues.

    Args:
        code_snippet: Python source code string.

    Returns:
        dict with keys: undefined_names, unused_variables,
        function_calls, import_list, parse_error
    """
    if not code_snippet or not code_snippet.strip():
        return {
            "undefined_names": [],
            "unused_variables": [],
            "function_calls": [],
            "import_list": [],
            "parse_error": None,
        }

    try:
        tree = ast.parse(code_snippet)
    except SyntaxError as e:
        return {
            "undefined_names": [],
            "unused_variables": [],
            "function_calls": [],
            "import_list": [],
            "parse_error": f"SyntaxError: {e.msg} (line {e.lineno})",
        }

    # Collect all names
    defined_names: Set[str] = set()
    used_names: Set[str] = set()
    assigned_names: Set[str] = set()  # Only Store context (for unused check)
    function_calls: List[str] = []
    import_list: List[str] = []
    has_star_import = False

    for node in ast.walk(tree):
        # Function/class definitions → defined names
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            defined_names.add(node.name)
            # Function arguments are also defined
            for arg in node.args.args + node.args.posonlyargs + node.args.kwonlyargs:
                defined_names.add(arg.arg)
            if node.args.vararg:
                defined_names.add(node.args.vararg.arg)
            if node.args.kwarg:
                defined_names.add(node.args.kwarg.arg)

        elif isinstance(node, ast.ClassDef):
            defined_names.add(node.name)

        # Imports → defined names + import list
        elif isinstance(node, ast.Import):
            for alias in node.names:
                name = alias.asname if alias.asname else alias.name
                defined_names.add(name)
                import_list.append(alias.name)

        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            for alias in node.names:
                if alias.name == "*":
                    has_star_import = True
                    import_list.append(f"{module}.*")
                else:
                    name = alias.asname if alias.asname else alias.name
                    defined_names.add(name)
                    import_list.append(f"{module}.{alias.name}")

        # Name nodes — track usage vs definition
        elif isinstance(node, ast.Name):
            if isinstance(node.ctx, ast.Store):
                defined_names.add(node.id)
                assigned_names.add(node.id)
            elif isinstance(node.ctx, (ast.Load, ast.Del)):
                used_names.add(node.id)

        # For loops define their target variable
        elif isinstance(node, ast.For):
            if isinstance(node.target, ast.Name):
                defined_names.add(node.target.id)
                assigned_names.add(node.target.id)
            elif isinstance(node.target, ast.Tuple):
                for elt in node.target.elts:
                    if isinstance(elt, ast.Name):
                        defined_names.add(elt.id)
                        assigned_names.add(elt.id)

        # With statements define their 'as' variable
        elif isinstance(node, ast.With):
            for item in node.items:
                if item.optional_vars and isinstance(item.optional_vars, ast.Name):
                    defined_names.add(item.optional_vars.id)
                    assigned_names.add(item.optional_vars.id)

        # Exception handlers define the 'as' variable
        elif isinstance(node, ast.ExceptHandler):
            if node.name:
                defined_names.add(node.name)
                assigned_names.add(node.name)

        # Global/nonlocal statements → treat as definitions
        elif isinstance(node, ast.Global):
            for name in node.names:
                defined_names.add(name)
        elif isinstance(node, ast.Nonlocal):
            for name in node.names:
                defined_names.add(name)

        # Function calls
        elif isinstance(node, ast.Call):
            call_name = _get_call_name(node)
            if call_name:
                function_calls.append(call_name)

    # Compute undefined: used but not defined, not a builtin
    undefined_names = sorted(used_names - defined_names - BUILTINS)

    # If there's a star import, we can't be sure what's defined
    if has_star_import:
        undefined_names = []

    # Compute unused: assigned (Store only) but never read
    # Exclude function/class names and _ prefixed variables
    unused_variables = sorted(
        name for name in assigned_names
        if name not in used_names
        and not name.startswith("_")
        and name not in {n.name for n in ast.walk(tree)
                         if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))}
    )

    return {
        "undefined_names": undefined_names,
        "unused_variables": unused_variables,
        "function_calls": function_calls,
        "import_list": import_list,
        "parse_error": None,
    }


def _get_call_name(node: ast.Call) -> Optional[str]:
    """Extract the function name from a Call node."""
    if isinstance(node.func, ast.Name):
        return node.func.id
    elif isinstance(node.func, ast.Attribute):
        # e.g., obj.method()
        if isinstance(node.func.value, ast.Name):
            return f"{node.func.value.id}.{node.func.attr}"
        return node.func.attr
    return None
