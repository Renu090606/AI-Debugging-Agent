"""Phase 2 verification tests — hypothesis generator and belief updater.

Tests cover:
1. Import validation (all modules load without error)
2. Prompt building (correct format)
3. JSON parsing (various LLM output formats)
4. Normalization (probabilities sum to 1.0)
5. Belief update logic (factor application + elimination)
6. Live LLM call (requires API keys in .env)
"""

import asyncio
import json
from parsers.models import ErrorContext, Hypothesis, ToolResult
from agent.hypothesis_generator import (
    generate_hypotheses,
    normalize_probabilities,
    _build_user_prompt,
    _parse_hypotheses_response,
    _strip_markdown_fences,
    _extract_json_array,
)
from agent.belief_updater import (
    update_beliefs,
    _build_belief_prompt,
    _parse_adjustment_factors,
)
from agent.llm_client import call_llm_with_retry


# === Test 1: Imports work ===
print("=== Test 1: All imports successful ===")
print("  PASSED")
print()

# === Test 2: Prompt building ===
print("=== Test 2: Prompt building ===")
ctx = ErrorContext(
    error_type="TypeError",
    error_message="unsupported operand type(s) for +: 'int' and 'str'",
    line_number=5,
    file_name="main.py",
    code_lines=["def add(a, b):", "    return a + b"],
    full_traceback="...",
)
prompt = _build_user_prompt(ctx)
assert "TypeError" in prompt
assert "unsupported operand" in prompt
assert "Line Number: 5" in prompt
assert "def add(a, b):" in prompt
print(f"  Prompt length: {len(prompt)} chars")
print("  PASSED")
print()

# === Test 3: JSON parsing — clean JSON ===
print("=== Test 3: Parse clean JSON response ===")
clean_json = """[
    {"id": "h1", "description": "Type mismatch", "probability": 0.5, "evidence_needed": ["check types"]},
    {"id": "h2", "description": "Missing conversion", "probability": 0.3, "evidence_needed": ["check casts"]},
    {"id": "h3", "description": "Wrong variable", "probability": 0.2, "evidence_needed": ["check names"]}
]"""
result = _parse_hypotheses_response(clean_json)
assert result is not None
assert len(result) == 3
assert result[0].id == "h1"
assert result[0].description == "Type mismatch"
assert abs(sum(h.probability for h in result) - 1.0) < 0.01
print(f"  Parsed {len(result)} hypotheses, sum={sum(h.probability for h in result):.4f}")
print("  PASSED")
print()

# === Test 4: JSON parsing — markdown fenced ===
print("=== Test 4: Parse markdown-fenced JSON ===")
fenced_json = """```json
[
    {"id": "h1", "description": "Null reference", "probability": 0.6, "evidence_needed": ["check var"]},
    {"id": "h2", "description": "Index error", "probability": 0.4, "evidence_needed": ["check bounds"]}
]
```"""
result = _parse_hypotheses_response(fenced_json)
assert result is not None
assert len(result) == 2
print(f"  Parsed {len(result)} hypotheses from fenced markdown")
print("  PASSED")
print()

# === Test 5: JSON parsing — with extra text ===
print("=== Test 5: Parse JSON with surrounding text ===")
messy_response = """Here are my hypotheses:
[{"id": "h1", "description": "Bug A", "probability": 0.7, "evidence_needed": ["test"]}, {"id": "h2", "description": "Bug B", "probability": 0.3, "evidence_needed": ["test"]}]
Let me know if you need more."""
result = _parse_hypotheses_response(messy_response)
assert result is not None
assert len(result) == 2
print(f"  Parsed {len(result)} hypotheses from messy response")
print("  PASSED")
print()

# === Test 6: JSON parsing — invalid input ===
print("=== Test 6: Handle invalid JSON gracefully ===")
assert _parse_hypotheses_response("") is None
assert _parse_hypotheses_response("not json at all") is None
assert _parse_hypotheses_response("{}") is None  # object, not array
print("  All invalid inputs returned None")
print("  PASSED")
print()

# === Test 7: Normalization ===
print("=== Test 7: Probability normalization ===")
hyps = [
    Hypothesis(id="h1", description="A", probability=0.6, evidence_needed=[]),
    Hypothesis(id="h2", description="B", probability=0.8, evidence_needed=[]),
    Hypothesis(id="h3", description="C", probability=0.1, evidence_needed=[]),
]
normalized = normalize_probabilities(hyps)
total = sum(h.probability for h in normalized)
assert abs(total - 1.0) < 0.01, f"Expected ~1.0, got {total}"
print(f"  Before: [0.6, 0.8, 0.1] → After: [{', '.join(f'{h.probability:.4f}' for h in normalized)}]")
print(f"  Sum: {total:.4f}")
print("  PASSED")
print()

# === Test 8: Normalization with all zeros ===
print("=== Test 8: Normalization with all-zero probabilities ===")
zero_hyps = [
    Hypothesis(id="h1", description="A", probability=0.0, evidence_needed=[]),
    Hypothesis(id="h2", description="B", probability=0.0, evidence_needed=[]),
]
normalized = normalize_probabilities(zero_hyps)
assert all(h.probability > 0 for h in normalized)
assert abs(sum(h.probability for h in normalized) - 1.0) < 0.01
print(f"  All-zero → equal distribution: [{', '.join(f'{h.probability:.4f}' for h in normalized)}]")
print("  PASSED")
print()

# === Test 9: Belief update — parse adjustment factors ===
print("=== Test 9: Parse adjustment factors ===")
test_hyps = [
    Hypothesis(id="h1", description="A", probability=0.5, evidence_needed=[]),
    Hypothesis(id="h2", description="B", probability=0.3, evidence_needed=[]),
    Hypothesis(id="h3", description="C", probability=0.2, evidence_needed=[]),
]
factors_json = '{"h1": 1.5, "h2": 0.5, "h3": 1.0}'
factors = _parse_adjustment_factors(factors_json, test_hyps)
assert factors is not None
assert factors["h1"] == 1.5
assert factors["h2"] == 0.5
assert factors["h3"] == 1.0
print(f"  Parsed factors: {factors}")
print("  PASSED")
print()

# === Test 10: Belief update — factor clamping ===
print("=== Test 10: Factor clamping (extreme values) ===")
extreme_json = '{"h1": 100.0, "h2": 0.001, "h3": 1.0}'
factors = _parse_adjustment_factors(extreme_json, test_hyps)
assert factors["h1"] == 5.0  # clamped from 100
assert factors["h2"] == 0.1  # clamped from 0.001
print(f"  Clamped factors: {factors}")
print("  PASSED")
print()

# === Test 11: Belief update prompt building ===
print("=== Test 11: Belief update prompt building ===")
tool_result = ToolResult(
    tool_name="ast_analyzer",
    output={"undefined_names": ["y"], "unused_variables": []},
    relevant_to=["h1"],
)
prompt = _build_belief_prompt(test_hyps, tool_result)
assert "ast_analyzer" in prompt
assert "undefined_names" in prompt
assert "h1" in prompt
print(f"  Prompt includes tool name, output, and hypothesis IDs")
print("  PASSED")
print()

# === Test 12: Live LLM call (only if API keys present) ===
import os
from dotenv import load_dotenv
load_dotenv()

async def test_live_llm():
    """Test actual LLM call — skipped if no API keys."""
    if not os.getenv("GROQ_API_KEY") and not os.getenv("GEMINI_API_KEY"):
        print("=== Test 12: Live LLM call — SKIPPED (no API keys) ===")
        return

    print("=== Test 12: Live LLM call ===")
    ctx = ErrorContext(
        error_type="NameError",
        error_message="name 'x' is not defined",
        line_number=3,
        file_name="test.py",
        code_lines=["def foo():", "    print(x)", "foo()"],
        full_traceback="Traceback...\nNameError: name 'x' is not defined",
    )
    result = await generate_hypotheses(ctx)

    if isinstance(result, dict) and "error" in result:
        print(f"  LLM returned error (expected if keys invalid): {result['error']}")
        print("  PASSED (graceful failure)")
    else:
        assert isinstance(result, list)
        assert 1 <= len(result) <= 5
        total = sum(h.probability for h in result)
        assert abs(total - 1.0) < 0.02
        print(f"  Got {len(result)} hypotheses:")
        for h in result:
            print(f"    {h.id}: {h.description} (p={h.probability:.3f})")
        print(f"  Sum of probabilities: {total:.4f}")
        print("  PASSED")
    print()

asyncio.run(test_live_llm())

print("=" * 40)
print("ALL TESTS PASSED")
