"""Belief updater — adjusts hypothesis probabilities based on new evidence."""

import json
import re
from typing import List, Union

from parsers.models import Hypothesis, ToolResult
from agent.llm_client import call_llm_with_retry
from agent.hypothesis_generator import normalize_probabilities

# System prompt for belief updates
BELIEF_UPDATE_PROMPT = """You are an expert Python debugger updating your beliefs based on new evidence.

Given a list of hypotheses and new evidence (from a tool or user answer), determine how each hypothesis should be adjusted.

For each hypothesis, return an adjustment factor:
- > 1.0 means the evidence SUPPORTS this hypothesis (e.g., 1.5 = moderately supported)
- < 1.0 means the evidence WEAKENS this hypothesis (e.g., 0.5 = moderately weakened)
- 1.0 means the evidence is NEUTRAL for this hypothesis

Return ONLY a valid JSON object with hypothesis IDs as keys and adjustment factors as values.
Example: {"h1": 1.5, "h2": 0.3, "h3": 1.0}

No explanation text outside the JSON. No markdown fences."""


async def update_beliefs(
    hypotheses: List[Hypothesis],
    observation: Union[ToolResult, str],
) -> List[Hypothesis]:
    """Update hypothesis probabilities based on new evidence.

    Uses the same LLM retry/fallback logic as generate_hypotheses().
    If LLM call fails, returns hypotheses unchanged (safe fallback).

    Args:
        hypotheses: Current list of hypotheses with probabilities.
        observation: New evidence — either a ToolResult or a user answer string.

    Returns:
        Updated list of hypotheses with adjusted probabilities.
    """
    if not hypotheses:
        return hypotheses

    user_prompt = _build_belief_prompt(hypotheses, observation)
    response_text = await call_llm_with_retry(BELIEF_UPDATE_PROMPT, user_prompt)

    # If LLM failed, return hypotheses unchanged (safe degradation)
    if isinstance(response_text, dict):
        return hypotheses

    # Parse adjustment factors
    factors = _parse_adjustment_factors(response_text, hypotheses)
    if factors is None:
        # Try once more with stricter prompt
        strict_prompt = user_prompt + "\n\nRETURN ONLY RAW JSON OBJECT. NO OTHER TEXT."
        response_text = await call_llm_with_retry(BELIEF_UPDATE_PROMPT, strict_prompt)
        if isinstance(response_text, dict):
            return hypotheses
        factors = _parse_adjustment_factors(response_text, hypotheses)
        if factors is None:
            return hypotheses

    # Apply adjustment factors
    for h in hypotheses:
        factor = factors.get(h.id, 1.0)
        h.probability = h.probability * factor

    # Normalize so probabilities sum to 1.0
    hypotheses = normalize_probabilities(hypotheses)

    # Mark hypotheses with very low probability as eliminated
    for h in hypotheses:
        if h.probability < 0.05 and h.status != "confirmed":
            h.status = "eliminated"

    return hypotheses


def _build_belief_prompt(
    hypotheses: List[Hypothesis], observation: Union[ToolResult, str]
) -> str:
    """Build the user prompt for belief updating."""
    # Format hypotheses
    hyp_text = "\n".join(
        f"- {h.id}: {h.description} (probability: {h.probability:.2f}, status: {h.status})"
        for h in hypotheses
        if h.status != "eliminated"
    )

    # Format observation
    if isinstance(observation, ToolResult):
        obs_text = f"Tool: {observation.tool_name}\nOutput: {json.dumps(observation.output, indent=2)}"
    else:
        obs_text = f"User answer: {observation}"

    return f"""Current Hypotheses:
{hyp_text}

New Evidence:
{obs_text}

Based on this evidence, provide adjustment factors for each hypothesis."""


def _parse_adjustment_factors(
    response_text: str, hypotheses: List[Hypothesis]
) -> Union[dict, None]:
    """Parse LLM response into a dict of hypothesis_id -> adjustment_factor.

    Returns None if parsing fails.
    """
    if not response_text:
        return None

    # Strip markdown fences
    cleaned = re.sub(r"^```(?:json)?\s*\n?", "", response_text.strip())
    cleaned = re.sub(r"\n?```\s*$", "", cleaned.strip())

    # Try to find JSON object in the response
    json_str = _extract_json_object(cleaned)
    if json_str is None:
        return None

    try:
        raw_dict = json.loads(json_str)
    except json.JSONDecodeError:
        return None

    if not isinstance(raw_dict, dict):
        return None

    # Validate and sanitize factors
    factors = {}
    valid_ids = {h.id for h in hypotheses}
    for key, value in raw_dict.items():
        if key in valid_ids:
            try:
                factor = float(value)
                # Clamp to reasonable range to prevent extreme swings
                factor = max(0.1, min(factor, 5.0))
                factors[key] = factor
            except (ValueError, TypeError):
                factors[key] = 1.0

    return factors if factors else None


def _extract_json_object(text: str) -> Union[str, None]:
    """Find and extract a JSON object from text."""
    text = text.strip()
    if text.startswith("{"):
        # Find matching closing brace
        depth = 0
        for i in range(len(text)):
            if text[i] == "{":
                depth += 1
            elif text[i] == "}":
                depth -= 1
                if depth == 0:
                    return text[: i + 1]
        return text

    # Look for a JSON object within the text
    start = text.find("{")
    if start == -1:
        return None

    depth = 0
    for i in range(start, len(text)):
        if text[i] == "{":
            depth += 1
        elif text[i] == "}":
            depth -= 1
            if depth == 0:
                return text[start : i + 1]

    return None
