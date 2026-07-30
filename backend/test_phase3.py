"""Phase 3 verification tests — orchestrator logic and self-critique.

Tests the non-LLM logic: session state, stale detection, termination
conditions, confidence calculation, action parsing, and helper functions.
"""

from parsers.models import ErrorContext, Hypothesis, ToolResult
from agent.orchestrator import (
    SessionState,
    _all_hypotheses_low,
    _check_stale,
    _force_conclude,
    _conclude,
    _get_top_hypothesis,
    _parse_action_response,
    _pause_for_question,
    _summarize_observation,
    LOW_CONFIDENCE_THRESHOLD,
    MAX_QUESTIONS,
)
from agent.self_critique import (
    calculate_confidence,
    _heuristic_critique,
    _parse_critique_response,
)


# Helper to create a test session state
def _make_state(probs=None):
    ctx = ErrorContext(
        error_type="TypeError",
        error_message="test error",
        line_number=5,
        file_name="test.py",
        code_lines=["x = 1", "y = 'a'", "z = x + y"],
        full_traceback="...",
    )
    if probs is None:
        probs = [0.5, 0.3, 0.2]
    hypotheses = [
        Hypothesis(id=f"h{i+1}", description=f"Hypothesis {i+1}", probability=p, evidence_needed=["test"])
        for i, p in enumerate(probs)
    ]
    state = SessionState("test-session", ctx, "x=1\ny='a'\nz=x+y", hypotheses)
    return state


# === Test 1: Imports ===
print("=== Test 1: All imports successful ===")
print("  PASSED")
print()

# === Test 2: SessionState initialization ===
print("=== Test 2: SessionState initialization ===")
state = _make_state()
assert state.session_id == "test-session"
assert state.iteration == 0
assert state.stale_counter == 0
assert state.questions_asked == 0
assert len(state.hypotheses) == 3
assert state.pending_question is None
print(f"  session_id: {state.session_id}")
print(f"  hypotheses: {len(state.hypotheses)}")
print("  PASSED")
print()

# === Test 3: _get_top_hypothesis ===
print("=== Test 3: Get top hypothesis ===")
top = _get_top_hypothesis(state.hypotheses)
assert top.id == "h1"
assert top.probability == 0.5
print(f"  Top: {top.id} (p={top.probability})")
print("  PASSED")
print()

# === Test 4: _get_top_hypothesis with eliminated ===
print("=== Test 4: Get top hypothesis (with eliminated) ===")
state2 = _make_state([0.6, 0.3, 0.1])
state2.hypotheses[0].status = "eliminated"
top = _get_top_hypothesis(state2.hypotheses)
assert top.id == "h2", f"Expected h2, got {top.id}"
print(f"  h1 eliminated → top is now: {top.id} (p={top.probability})")
print("  PASSED")
print()

# === Test 5: _all_hypotheses_low ===
print("=== Test 5: All hypotheses low check ===")
low_state = _make_state([0.10, 0.05, 0.03])
assert _all_hypotheses_low(low_state.hypotheses) is True
high_state = _make_state([0.5, 0.3, 0.2])
assert _all_hypotheses_low(high_state.hypotheses) is False
edge_state = _make_state([0.15, 0.10, 0.05])  # 0.15 is NOT < 0.15
assert _all_hypotheses_low(edge_state.hypotheses) is False
print(f"  [0.10, 0.05, 0.03] → all low: True")
print(f"  [0.50, 0.30, 0.20] → all low: False")
print(f"  [0.15, 0.10, 0.05] → all low: False (0.15 is boundary)")
print("  PASSED")
print()

# === Test 6: Stale detection ===
print("=== Test 6: Stale counter logic ===")
state3 = _make_state()
# No change — should increment stale
_check_stale(state3, [0.5, 0.3, 0.2], [0.5, 0.3, 0.2])
assert state3.stale_counter == 1
# Small change (< 0.05) — should still increment
_check_stale(state3, [0.5, 0.3, 0.2], [0.52, 0.29, 0.19])
assert state3.stale_counter == 2
# Meaningful change (>= 0.05) — should reset
_check_stale(state3, [0.5, 0.3, 0.2], [0.6, 0.25, 0.15])
assert state3.stale_counter == 0
print(f"  No change → stale_counter: 1")
print(f"  Small change (0.02) → stale_counter: 2")
print(f"  Big change (0.10) → stale_counter: 0 (reset)")
print("  PASSED")
print()

# === Test 7: Force conclude ===
print("=== Test 7: Force conclude ===")
import asyncio as _asyncio

async def _test7():
    s = _make_state([0.5, 0.3, 0.2])
    r = await _force_conclude(s, confidence_level="low")
    assert r.confidence_level == "low"
    assert r.session_id == "test-session"
    assert len(r.conclusion) > 0
    assert r.confidence <= 0.95
    print(f"  confidence_level: {r.confidence_level}")
    print(f"  confidence: {r.confidence:.3f}")
    print(f"  conclusion: {r.conclusion[:40]}...")
    print("  PASSED")

_asyncio.run(_test7())
print()

# === Test 8: Normal conclude ===
print("=== Test 8: Normal conclude ===")

async def _test8():
    s = _make_state([0.85, 0.10, 0.05])
    r = await _conclude(s, adjusted_confidence=0.82)
    assert r.confidence_level == "high"
    assert r.confidence == 0.82
    assert len(r.conclusion) > 0
    print(f"  confidence_level: {r.confidence_level}")
    print(f"  confidence: {r.confidence}")
    print("  PASSED")

_asyncio.run(_test8())
print()

# === Test 9: Confidence cap at 0.95 ===
print("=== Test 9: Confidence hard cap at 0.95 ===")

async def _test9():
    s = _make_state([0.99, 0.005, 0.005])
    r = await _conclude(s, adjusted_confidence=0.99)
    assert r.confidence == 0.95, f"Expected 0.95, got {r.confidence}"
    print(f"  Input 0.99 \u2192 capped to {r.confidence}")
    print("  PASSED")

_asyncio.run(_test9())
print()

# === Test 10: Pause for question ===
print("=== Test 10: Pause for question ===")
state7 = _make_state()
state7.questions_asked = 1
response = _pause_for_question(state7, "What type is variable x?")
assert response["status"] == "pending_question"
assert response["question"] == "What type is variable x?"
assert response["session_id"] == "test-session"
assert state7.pending_question == "What type is variable x?"
print(f"  status: {response['status']}")
print(f"  question: {response['question']}")
print("  PASSED")
print()

# === Test 11: Parse action response ===
print("=== Test 11: Parse action response — valid JSON ===")
action = _parse_action_response(
    '{"action_type": "RUN_TOOL", "tool_name": "linter", "question": null, "reasoning": "Need lint check"}',
    questions_remaining=2
)
assert action.action_type == "RUN_TOOL"
assert action.tool_name == "linter"
assert action.reasoning == "Need lint check"
print(f"  action: {action.action_type}, tool: {action.tool_name}")
print("  PASSED")
print()

# === Test 12: Parse action — ASK_USER with no questions left ===
print("=== Test 12: Parse action — ASK_USER blocked when no questions left ===")
action = _parse_action_response(
    '{"action_type": "ASK_USER", "tool_name": null, "question": "What?", "reasoning": "need info"}',
    questions_remaining=0
)
assert action.action_type == "RUN_TOOL"  # Should switch to tool
assert action.tool_name == "ast_analyzer"
print(f"  ASK_USER with 0 remaining → switched to: {action.action_type} ({action.tool_name})")
print("  PASSED")
print()

# === Test 13: Parse action — invalid response ===
print("=== Test 13: Parse action — invalid response fallback ===")
action = _parse_action_response("I think we should look at the code", questions_remaining=2)
assert action.action_type == "RUN_TOOL"
assert action.tool_name == "ast_analyzer"
print(f"  Garbage input → fallback: {action.action_type} ({action.tool_name})")
print("  PASSED")
print()

# === Test 14: calculate_confidence ===
print("=== Test 14: Confidence calculation ===")
hyps = [Hypothesis(id="h1", description="A", probability=0.8, evidence_needed=[])]
# Base case
c = calculate_confidence(hyps)
assert abs(c - 0.8) < 0.01
# With tool confirmation
c = calculate_confidence(hyps, tool_confirmed=True)
assert abs(c - 0.9) < 0.01
# With stale penalty
c = calculate_confidence(hyps, stale_counter=2)
assert abs(c - 0.6) < 0.01
# With critique says continue
c = calculate_confidence(hyps, critique_says_continue=True)
assert abs(c - 0.65) < 0.01
# Cap at 0.95
hyps_high = [Hypothesis(id="h1", description="A", probability=0.95, evidence_needed=[])]
c = calculate_confidence(hyps_high, tool_confirmed=True)
assert abs(c - 0.95) < 0.01
print(f"  Base 0.8 → {calculate_confidence(hyps)}")
print(f"  + tool confirmed → {calculate_confidence(hyps, tool_confirmed=True)}")
print(f"  + stale×2 → {calculate_confidence(hyps, stale_counter=2)}")
print(f"  + critique CONTINUE → {calculate_confidence(hyps, critique_says_continue=True)}")
print(f"  Cap: 1.05 → {calculate_confidence(hyps_high, tool_confirmed=True)}")
print("  PASSED")
print()

# === Test 15: Heuristic critique ===
print("=== Test 15: Heuristic critique fallback ===")
# High confidence, few alternatives
hyps_clear = [
    Hypothesis(id="h1", description="A", probability=0.75, evidence_needed=[], status="untested"),
    Hypothesis(id="h2", description="B", probability=0.25, evidence_needed=[], status="eliminated"),
]
result = _heuristic_critique(hyps_clear)
assert result["recommendation"] == "CONCLUDE"
print(f"  Clear winner → {result['recommendation']} (conf={result['adjusted_confidence']:.2f})")

# Close probabilities
hyps_unclear = [
    Hypothesis(id="h1", description="A", probability=0.35, evidence_needed=[], status="untested"),
    Hypothesis(id="h2", description="B", probability=0.33, evidence_needed=[], status="untested"),
    Hypothesis(id="h3", description="C", probability=0.32, evidence_needed=[], status="untested"),
]
result = _heuristic_critique(hyps_unclear)
assert result["recommendation"] == "CONTINUE"
print(f"  Close race → {result['recommendation']} (conf={result['adjusted_confidence']:.2f})")
print("  PASSED")
print()

# === Test 16: Parse critique response ===
print("=== Test 16: Parse critique response ===")
valid = '{"critique": "Well supported", "adjusted_confidence": 0.82, "recommendation": "CONCLUDE"}'
parsed = _parse_critique_response(valid)
assert parsed is not None
assert parsed["recommendation"] == "CONCLUDE"
assert parsed["adjusted_confidence"] == 0.82

# Invalid
assert _parse_critique_response("not json") is None
assert _parse_critique_response("") is None
print(f"  Valid JSON → recommendation={parsed['recommendation']}, conf={parsed['adjusted_confidence']}")
print(f"  Invalid → None")
print("  PASSED")
print()

# === Test 17: Summarize observation ===
print("=== Test 17: Summarize tool observation ===")
obs1 = ToolResult(tool_name="ast_analyzer", output={"undefined_names": ["x", "y"], "unused_variables": []}, relevant_to=[])
summary = _summarize_observation(obs1)
assert "undefined" in summary
print(f"  AST with undefined names: '{summary}'")

obs2 = ToolResult(tool_name="linter", output={"issues": [{"line": 1, "code": "E101"}]}, relevant_to=[])
summary = _summarize_observation(obs2)
assert "lint issues" in summary
print(f"  Linter with issues: '{summary}'")

obs3 = ToolResult(tool_name="ast_analyzer", output={"error": "Tool failed"}, relevant_to=[])
summary = _summarize_observation(obs3)
assert "Error" in summary
print(f"  Error case: '{summary}'")
print("  PASSED")
print()

print("=" * 40)
print("ALL 17 TESTS PASSED")