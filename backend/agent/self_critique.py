"""Self-critique module — the agent critiques its own reasoning before concluding.

Reduces hallucination and improves answer quality by checking whether the
conclusion is well-supported by the evidence gathered.
"""

import json
import re
from typing import List

from parsers.models import Hypothesis
from agent.llm_client import call_llm_with_retry

CRITIQUE_PROMPT = """You are reviewing a debugging agent's reasoning. The agent is about to conclude with a root cause diagnosis.

Critique this reasoning:
1. Is the conclusion well-supported by the evidence?
2. Are there alternative hypotheses not yet eliminated?
3. Is the confidence score justified?

Return ONLY a JSON object:
{"critique": "your critique text", "adjusted_confidence": 0.XX, "recommendation": "CONCLUDE|CONTINUE"}

Rules:
- If evidence strongly supports the top hypothesis, recommend CONCLUDE with high confidence
- If alternative hypotheses still viable, recommend CONTINUE with lower confidence
- adjusted_confidence should be between 0.0 and 0.95 (never 1.0)
- No markdown fences. No extra text."""


async def self_critique(
    hypotheses: List[Hypothesis], reasoning_chain: List[str]
) -> dict:
    """Critique the agent's reasoning and adjust confidence.

    Args:
        hypotheses: Current hypothesis list with probabilities.
        reasoning_chain: Full reasoning trace so far.

    Returns:
        dict with keys: critique, adjusted_confidence, recommendation
    """
    user_prompt = _build_critique_prompt(hypotheses, reasoning_chain)
    result = await call_llm_with_retry(CRITIQUE_PROMPT, user_prompt)

    if isinstance(result, dict):
        # LLM failed — use heuristic confidence
        return _heuristic_critique(hypotheses)

    parsed = _parse_critique_response(result)
    if parsed is None:
        return _heuristic_critique(hypotheses)

    return parsed


def calculate_confidence(
    hypotheses: List[Hypothesis],
    stale_counter: int = 0,
    tool_confirmed: bool = False,
    critique_says_continue: bool = False,
    tools_confirmed_count: int = 0,
    evidence_collected: bool = True,
    iteration_count: int = 2,
    user_answer_helped: bool = False,
) -> float:
    """Calculate final confidence score with evidence-aware adjustments.

    Rules:
    - Base = highest hypothesis probability
    - Tool confirms hypothesis → +0.10
    - Multiple tools confirmed → +0.05 per additional (max +0.15)
    - Self-critique says CONTINUE → -0.15
    - stale_counter > 0 → -0.10 per stale cycle
    - No evidence collected → -0.10
    - Only 1 iteration (minimal investigation) → -0.10
    - User answer helped → +0.05
    - Hard cap at 0.95
    """
    if not hypotheses:
        return 0.0

    base = max(h.probability for h in hypotheses)

    # Tool confirmation bonuses
    if tool_confirmed:
        base += 0.10
    if tools_confirmed_count > 1:
        additional_bonus = min((tools_confirmed_count - 1) * 0.05, 0.15)
        base += additional_bonus

    # Penalties
    if critique_says_continue:
        base -= 0.15
    if stale_counter > 0:
        base -= 0.10 * stale_counter
    if not evidence_collected:
        base -= 0.10
    if iteration_count <= 1:
        base -= 0.10

    # User answer bonus
    if user_answer_helped:
        base += 0.05

    # Clamp to [0.0, 0.95]
    return max(0.0, min(base, 0.95))


def _build_critique_prompt(
    hypotheses: List[Hypothesis], reasoning_chain: List[str]
) -> str:
    """Build the user prompt for self-critique."""
    top = max(hypotheses, key=lambda h: h.probability)

    hyp_summary = "\n".join(
        f"- {h.id}: {h.description} (p={h.probability:.2f}, status={h.status})"
        for h in hypotheses
    )

    # Last 5 reasoning steps for context
    recent = "\n".join(reasoning_chain[-5:]) if reasoning_chain else "(no reasoning yet)"

    return f"""Proposed conclusion: {top.description}
Top hypothesis probability: {top.probability:.2f}

All hypotheses:
{hyp_summary}

Recent reasoning steps:
{recent}

Evidence collected for top hypothesis: {top.evidence_collected}

Critique this diagnosis."""


def _parse_critique_response(response_text: str) -> dict:
    """Parse the LLM critique response into a structured dict."""
    if not response_text:
        return None

    # Strip markdown fences
    cleaned = re.sub(r"^```(?:json)?\s*\n?", "", response_text.strip())
    cleaned = re.sub(r"\n?```\s*$", "", cleaned.strip())

    try:
        start = cleaned.find("{")
        end = cleaned.rfind("}") + 1
        if start >= 0 and end > start:
            data = json.loads(cleaned[start:end])
        else:
            return None

        critique = data.get("critique", "No critique provided")
        adjusted_confidence = float(data.get("adjusted_confidence", 0.5))
        recommendation = data.get("recommendation", "CONCLUDE")

        # Validate
        adjusted_confidence = max(0.0, min(adjusted_confidence, 0.95))
        if recommendation not in ("CONCLUDE", "CONTINUE"):
            recommendation = "CONCLUDE"

        return {
            "critique": critique,
            "adjusted_confidence": adjusted_confidence,
            "recommendation": recommendation,
        }
    except (json.JSONDecodeError, ValueError, TypeError):
        return None


def _heuristic_critique(hypotheses: List[Hypothesis]) -> dict:
    """Fallback critique when LLM is unavailable — uses heuristic rules."""
    if not hypotheses:
        return {
            "critique": "No hypotheses available.",
            "adjusted_confidence": 0.0,
            "recommendation": "CONCLUDE",
        }

    top = max(hypotheses, key=lambda h: h.probability)
    active = [h for h in hypotheses if h.status != "eliminated"]

    # If top probability is very high and few alternatives, conclude
    if top.probability >= 0.70 and len(active) <= 2:
        return {
            "critique": "High confidence in top hypothesis with few alternatives.",
            "adjusted_confidence": min(top.probability, 0.95),
            "recommendation": "CONCLUDE",
        }

    # If multiple active hypotheses with similar probabilities, continue
    if len(active) >= 3:
        probs = sorted([h.probability for h in active], reverse=True)
        if probs[0] - probs[1] < 0.15:
            return {
                "critique": "Top hypotheses are too close in probability — more evidence needed.",
                "adjusted_confidence": top.probability * 0.7,
                "recommendation": "CONTINUE",
            }

    # Default: conclude with moderate confidence
    return {
        "critique": "Heuristic assessment — LLM unavailable for detailed critique.",
        "adjusted_confidence": min(top.probability * 0.9, 0.95),
        "recommendation": "CONCLUDE",
    }
