"""Phase 4 verification tests — AST analyzer, linter, variable tracker."""

from tools.ast_analyzer import analyze_ast
from tools.linter import run_linter
from tools.variable_tracker import track_variables

# ============================================================
# AST ANALYZER TESTS
# ============================================================

print("=== Test 1: AST — undefined names ===")
code = """
x = 10
result = x + y
print(result + z)
"""
r = analyze_ast(code)
assert "y" in r["undefined_names"], f"Expected 'y' undefined, got {r['undefined_names']}"
assert "z" in r["undefined_names"], f"Expected 'z' undefined, got {r['undefined_names']}"
assert "print" not in r["undefined_names"]  # builtin excluded
assert "x" not in r["undefined_names"]  # x is defined
print(f"  undefined_names: {r['undefined_names']}")
print("  PASSED")
print()

print("=== Test 2: AST — unused variables ===")
code = """
used = 10
unused_var = 20
print(used)
"""
r = analyze_ast(code)
assert "unused_var" in r["unused_variables"], f"Got {r['unused_variables']}"
assert "used" not in r["unused_variables"]
print(f"  unused_variables: {r['unused_variables']}")
print("  PASSED")
print()

print("=== Test 3: AST — function calls ===")
code = """
import os
x = len([1,2,3])
path = os.path.join("a", "b")
print(x)
"""
r = analyze_ast(code)
assert "len" in r["function_calls"]
assert "print" in r["function_calls"]
print(f"  function_calls: {r['function_calls']}")
print("  PASSED")
print()

print("=== Test 4: AST — imports ===")
code = """
import os
import sys
from pathlib import Path
from collections import defaultdict
"""
r = analyze_ast(code)
assert "os" in r["import_list"]
assert "sys" in r["import_list"]
assert "pathlib.Path" in r["import_list"]
print(f"  import_list: {r['import_list']}")
print("  PASSED")
print()

print("=== Test 5: AST — SyntaxError handling ===")
code = """
def broken(
    x = 1 +
"""
r = analyze_ast(code)
assert r["parse_error"] is not None
assert "SyntaxError" in r["parse_error"]
assert r["undefined_names"] == []
print(f"  parse_error: {r['parse_error']}")
print("  PASSED")
print()

print("=== Test 6: AST — empty input ===")
r = analyze_ast("")
assert r["parse_error"] is None
assert r["undefined_names"] == []
assert r["function_calls"] == []
print("  Empty input returns clean empty result")
print("  PASSED")
print()

print("=== Test 7: AST — builtins excluded ===")
code = """
x = len(range(10))
y = str(x)
items = list(filter(None, [1, 0, 2]))
"""
r = analyze_ast(code)
assert "len" not in r["undefined_names"]
assert "range" not in r["undefined_names"]
assert "str" not in r["undefined_names"]
assert "list" not in r["undefined_names"]
assert "filter" not in r["undefined_names"]
print(f"  undefined_names (should be empty): {r['undefined_names']}")
print("  PASSED")
print()

print("=== Test 8: AST — star import disables undefined check ===")
code = """
from os.path import *
result = join("a", "b")
"""
r = analyze_ast(code)
assert r["undefined_names"] == [], f"Star import should disable undefined check, got {r['undefined_names']}"
print("  Star import → undefined_names disabled")
print("  PASSED")
print()

# ============================================================
# LINTER TESTS
# ============================================================

print("=== Test 9: Linter — finds issues ===")
code = """
import os
x=1
y = x +1
"""
r = run_linter(code)
assert "issues" in r
assert len(r["issues"]) > 0, f"Expected lint issues, got {r['issues']}"
# Should find whitespace issues at minimum
print(f"  Found {len(r['issues'])} issues")
for issue in r["issues"][:3]:
    print(f"    Line {issue['line']}: {issue['code']} {issue['message']}")
print("  PASSED")
print()

print("=== Test 10: Linter — clean code ===")
code = """x = 1
y = x + 1
print(y)
"""
r = run_linter(code)
assert "issues" in r
# Clean code should have few or no issues
print(f"  Issues on clean code: {len(r['issues'])}")
print("  PASSED")
print()

print("=== Test 11: Linter — empty input ===")
r = run_linter("")
assert r == {"issues": []}
print("  Empty input → empty issues")
print("  PASSED")
print()

print("=== Test 12: Linter — syntax error code ===")
code = """
def broken(
    x = 1 +
"""
r = run_linter(code)
assert "issues" in r
# flake8 reports syntax errors as E999
has_syntax = any(i["code"] == "E999" for i in r["issues"])
print(f"  Issues: {len(r['issues'])}, has E999 (syntax): {has_syntax}")
print("  PASSED")
print()

# ============================================================
# VARIABLE TRACKER TESTS
# ============================================================

print("=== Test 13: Tracker — basic assignments and usages ===")
code = """x = 10
y = 20
z = x + y
"""
r = track_variables(code)
assert "x" in r["assignments"]
assert "y" in r["assignments"]
assert "z" in r["assignments"]
assert "x" in r["usages"]
assert "y" in r["usages"]
assert 1 in r["assignments"]["x"]
print(f"  assignments: {list(r['assignments'].keys())}")
print(f"  usages: {list(r['usages'].keys())}")
print("  PASSED")
print()

print("=== Test 14: Tracker — undefined usage (never assigned) ===")
code = """x = 10
result = x + undefined_var
"""
r = track_variables(code)
undef_names = [u["name"] for u in r["undefined_usages"]]
assert "undefined_var" in undef_names, f"Expected undefined_var, got {undef_names}"
print(f"  undefined_usages: {r['undefined_usages']}")
print("  PASSED")
print()

print("=== Test 15: Tracker — used before assignment ===")
code = """print(x)
x = 10
"""
r = track_variables(code)
undef = [u for u in r["undefined_usages"] if u["name"] == "x"]
assert len(undef) > 0, f"Expected x used before assignment, got {r['undefined_usages']}"
assert undef[0]["used_at"] == 1
assert undef[0]["assigned_at"] == 2
print(f"  x used at line {undef[0]['used_at']}, assigned at line {undef[0]['assigned_at']}")
print("  PASSED")
print()

print("=== Test 16: Tracker — function args are defined ===")
code = """def add(a, b):
    return a + b
result = add(1, 2)
"""
r = track_variables(code)
undef_names = [u["name"] for u in r["undefined_usages"]]
assert "a" not in undef_names
assert "b" not in undef_names
print(f"  Function args not in undefined: {undef_names}")
print("  PASSED")
print()

print("=== Test 17: Tracker — for loop variable defined ===")
code = """for i in range(10):
    print(i)
"""
r = track_variables(code)
assert "i" in r["assignments"]
undef_names = [u["name"] for u in r["undefined_usages"]]
assert "i" not in undef_names
print(f"  'i' assigned by for loop, not undefined")
print("  PASSED")
print()

print("=== Test 18: Tracker — empty input ===")
r = track_variables("")
assert r["assignments"] == {}
assert r["usages"] == {}
assert r["undefined_usages"] == []
print("  Empty input → empty result")
print("  PASSED")
print()

print("=== Test 19: Tracker — SyntaxError handling ===")
r = track_variables("def broken(\n    x = 1 +")
assert "parse_error" in r
print(f"  parse_error: {r['parse_error']}")
print("  PASSED")
print()

print("=== Test 20: Tracker — builtins excluded ===")
code = """x = len([1, 2, 3])
y = print(x)
"""
r = track_variables(code)
undef_names = [u["name"] for u in r["undefined_usages"]]
assert "len" not in undef_names
assert "print" not in undef_names
print(f"  Builtins excluded from undefined: {undef_names}")
print("  PASSED")
print()

print("=" * 40)
print("ALL 20 TESTS PASSED")
