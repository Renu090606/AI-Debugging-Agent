"""Phase 5 verification tests — enhanced self-critique, confidence, conclusion generator."""

import asyncio
from parsers.models import ErrorContext, Hypothesis
from agent.self_critique import calculate_confidence, _heuristic_critique
from agent.conclusion_generator import (
    generate_conclusion,
    _template_conclusion,
    _parse_conclusion_response,
    _build_evidence_summary,
)


# === Test 1: Imports work ===
print("=== Test 1: All imports successful ===")
print("  PASSED")
print()

# === Test 2: Enhanced confidence — base case (backward compat) ===
print("=== Test 2: Confidence — base case ===")
hyps = [Hypothesis(id="h1", description="A", probability=0.8, evidence_needed=[])]
c = calculate_confidence(hyps)
assert abs(c - 0.8) < 0.01
print(f"  Base 0.8 → {c}")
print("  PASSED")
print()

# === Test 3: Enhanced confidence — multiple tools confirmed ===
print("=== Test 3: Confidence — multiple tools bonus ===")
c = calculate_confidence(hyps, tool_confirmed=True, tools_confirmed_count=3)
# 0.8 + 0.10 (tool) + 0.10 (2 additional × 0.05 = 0.10) = 1.0 → capped at 0.95
assert abs(c - 0.95) < 0.01
print(f"  Base 0.8 + tool + 3 tools → {c} (capped at 0.95)")
print("  PASSED")
print()

# === Test 4: Enhanced confidence — no evidence penalty ===
print("=== Test 4: Confidence — no evidence penalty ===")
c = calculate_confidence(hyps, evidence_collected=False)
assert abs(c - 0.7) < 0.01
print(f"  Base 0.8 - 0.10 (no evidence) → {c}")
print("  PASSED")
print()

# === Test 5: Enhanced confidence — minimal iteration penalty ===
print("=== Test 5: Confidence — minimal iteration penalty ===")
c = calculate_confidence(hyps, iteration_count=1)
assert abs(c - 0.7) < 0.01
print(f"  Base 0.8 - 0.10 (only 1 iteration) → {c}")
print("  PASSED")
print()

# === Test 6: Enhanced confidence — user answer bonus ===
print("=== Test 6: Confidence — user answer bonus ===")
c = calculate_confidence(hyps, user_answer_helped=True)
assert abs(c - 0.85) < 0.01
print(f"  Base 0.8 + 0.05 (user helped) → {c}")
print("  PASSED")
print()

# === Test 7: Enhanced confidence — combined adjustments ===
print("=== Test 7: Confidence — combined adjustments ===")
c = calculate_confidence(
    hyps,
    tool_confirmed=True,
    tools_confirmed_count=2,
    stale_counter=1,
    evidence_collected=True,
    iteration_count=5,
    user_answer_helped=True,
)
# 0.8 + 0.10 (tool) + 0.05 (1 extra tool) - 0.10 (stale) + 0.05 (user) = 0.90
assert abs(c - 0.90) < 0.01
print(f"  Complex scenario → {c}")
print("  PASSED")
print()

# === Test 8: Enhanced confidence — floor at 0.0 ===
print("=== Test 8: Confidence — floor at 0.0 ===")
low_hyps = [Hypothesis(id="h1", description="A", probability=0.1, evidence_needed=[])]
c = calculate_confidence(
    low_hyps,
    stale_counter=3,
    evidence_collected=False,
    iteration_count=1,
)
# 0.1 - 0.30 (stale×3) - 0.10 (no evidence) - 0.10 (1 iter) = -0.40 → 0.0
assert c == 0.0
print(f"  Heavy penalties → {c} (floored at 0.0)")
print("  PASSED")
print()

# === Test 9: Parse conclusion response — valid ===
print("=== Test 9: Parse conclusion response — valid JSON ===")
valid_json = '{"conclusion": "The error is a NameError", "suggested_fix": "Add x = 0", "summary": "Found undefined var"}'
parsed = _parse_conclusion_response(valid_json)
assert parsed is not None
assert parsed["conclusion"] == "The error is a NameError"
assert parsed["suggested_fix"] == "Add x = 0"
print(f"  conclusion: {parsed['conclusion']}")
print("  PASSED")
print()

# === Test 10: Parse conclusion response — invalid ===
print("=== Test 10: Parse conclusion response — invalid ===")
assert _parse_conclusion_response("") is None
assert _parse_conclusion_response("not json") is None
assert _parse_conclusion_response("{}") is None  # no conclusion field
print("  All invalid inputs → None")
print("  PASSED")
print()

# === Test 11: Parse conclusion response — markdown fenced ===
print("=== Test 11: Parse conclusion response — markdown fenced ===")
fenced = '```json\n{"conclusion": "Bug found", "suggested_fix": "fix it", "summary": "done"}\n```'
parsed = _parse_conclusion_response(fenced)
assert parsed is not None
assert parsed["conclusion"] == "Bug found"
print(f"  Fenced JSON parsed: {parsed['conclusion']}")
print("  PASSED")
print()

# === Test 12: Template conclusion fallback ===
print("=== Test 12: Template conclusion fallback ===")
hyp = Hypothesis(
    id="h1", description="Variable x is undefined",
    probability=0.85, evidence_needed=["check var tracker"],
    evidence_collected=["variable_tracker found x undefined"]
)
ctx = ErrorContext(
    error_type="NameError",
    error_message="name 'x' is not defined",
    line_number=5,
    file_name="test.py",
    code_lines=["print(x)"],
    full_traceback="...",
)
result = _template_conclusion(hyp, ctx, ["ast_analyzer", "variable_tracker"], "high")
assert "NameError" in result["conclusion"]
assert "Variable x is undefined" in result["conclusion"]
assert "suggested_fix" in result
assert "evidence_summary" in result
print(f"  conclusion: {result['conclusion'][:60]}...")
print(f"  has suggested_fix: {bool(result['suggested_fix'])}")
print("  PASSED")
print()

# === Test 13: Template conclusion — low confidence disclaimer ===
print("=== Test 13: Template conclusion — low confidence disclaimer ===")
result = _template_conclusion(hyp, ctx, [], "low")
assert "low confidence" in result["suggested_fix"]
print(f"  Low confidence disclaimer present in suggested_fix")
print("  PASSED")
print()

# === Test 14: Evidence summary building ===
print("=== Test 14: Evidence summary building ===")
hyp_with_evidence = Hypothesis(
    id="h1", description="A", probability=0.8,
    evidence_needed=[], evidence_collected=["found undefined var", "linter confirmed"]
)
summary = _build_evidence_summary(
    hyp_with_evidence,
    ["ast_analyzer", "linter", "variable_tracker"],
    ["[Iter 1] Observation (ast): ...", "[Iter 2] Observation (linter): ..."],
)
assert "Tools used" in summary
assert "Supporting evidence" in summary
assert "Observations gathered: 2" in summary
print(f"  summary: {summary[:80]}...")
print("  PASSED")
print()

# === Test 15: Live conclusion generation (LLM — graceful failure) ===
async def test_live_conclusion():
    """Test generate_conclusion — expected to fallback to template without API keys."""
    print("=== Test 15: Live conclusion generation (fallback) ===")
    hyp = Hypothesis(
        id="h1", description="Type mismatch in addition",
        probability=0.85, evidence_needed=[],
        evidence_collected=["AST found string + int"]
    )
    ctx = ErrorContext(
        error_type="TypeError",
        error_message="unsupported operand type(s) for +",
        line_number=5, file_name="main.py",
        code_lines=["x = 1", "y = 'a'", "z = x + y"],
        full_traceback="...",
    )
    result = await generate_conclusion(
        hyp, ctx, ["[Iter 1] Thought: check types"], ["ast_analyzer"], "high"
    )
    assert "conclusion" in result
    assert "suggested_fix" in result
    assert "summary" in result
    assert "evidence_summary" in result
    assert len(result["conclusion"]) > 0
    print(f"  conclusion: {result['conclusion'][:60]}...")
    print(f"  Keys present: {list(result.keys())}")
    print("  PASSED")
    print()

asyncio.run(test_live_conclusion())

# === Test 16: Orchestrator imports still work ===
print("=== Test 16: Orchestrator imports with new async conclude ===")
from agent.orchestrator import _conclude, _force_conclude, run_debug_session
import inspect
assert inspect.iscoroutinefunction(_conclude)
assert inspect.iscoroutinefunction(_force_conclude)
print("  _conclude is async: True")
print("  _force_conclude is async: True")
print("  PASSED")
print()

print("=" * 40)
print("ALL 16 TESTS PASSED")
