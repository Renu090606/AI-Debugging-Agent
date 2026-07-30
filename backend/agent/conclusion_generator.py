"""Conclusion generator — produces human-readable diagnosis and fix suggestions.

Called at the end of the ReAct loop to generate a polished conclusion
with a concrete suggested fix via LLM, with template-based fallback.
"""

import json
import re
from typing import List

from parsers.models import ErrorContext, Hypothesis
from agent.llm_client import call_llm_with_retry


CONCLUSION_PROMPT = """You are an expert Python debugger writing a final diagnosis for a user.

Given the root cause hypothesis, error context, and evidence gathered,
produce:
1. conclusion: A clear 1-2 sentence explanation of WHY the error occurred
2. suggested_fix: A concrete code change the user should make (show the actual fix as a Python code snippet)
3. summary: A 2-3 sentence summary of the debugging process and what was found

Return ONLY valid JSON with keys: conclusion, suggested_fix, summary
No markdown fences. No extra text."""


async def generate_conclusion(
    top_hypothesis: Hypothesis,
    error_context: ErrorContext,
    reasoning_chain: List[str],
    tools_used: List[str],
    confidence_level: str,
) -> dict:
    """Generate a human-readable conclusion with suggested fix.

    Uses LLM for rich output, falls back to template if LLM fails.
    Never crashes — always returns a valid dict.

    Args:
        top_hypothesis: Highest-probability hypothesis at conclusion time.
        error_context: Original parsed error.
        reasoning_chain: Full trace of agent reasoning.
        tools_used: Which tools were run during the session.
        confidence_level: "high", "medium", or "low".

    Returns:
        dict with keys: conclusion, suggested_fix, summary, evidence_summary
    """
    user_prompt = _build_conclusion_prompt(
        top_hypothesis, error_context, reasoning_chain, tools_used
    )

    result = await call_llm_with_retry(CONCLUSION_PROMPT, user_prompt)

    if isinstance(result, dict):
        # LLM failed — use template fallback
        return _template_conclusion(
            top_hypothesis, error_context, tools_used, confidence_level
        )

    parsed = _parse_conclusion_response(result)
    if parsed is None:
        return _template_conclusion(
            top_hypothesis, error_context, tools_used, confidence_level
        )

    # Add evidence summary and confidence disclaimer
    parsed["evidence_summary"] = _build_evidence_summary(
        top_hypothesis, tools_used, reasoning_chain
    )

    if confidence_level == "low":
        parsed["suggested_fix"] += (
            "\n\n# Note: This diagnosis has low confidence — "
            "manual verification recommended."
        )

    return parsed


def _build_conclusion_prompt(
    top_hypothesis: Hypothesis,
    error_context: ErrorContext,
    reasoning_chain: List[str],
    tools_used: List[str],
) -> str:
    """Build the user prompt for conclusion generation."""
    code_context = (
        "\n".join(error_context.code_lines)
        if error_context.code_lines
        else "(no code available)"
    )

    recent_reasoning = "\n".join(reasoning_chain[-5:]) if reasoning_chain else "(none)"

    evidence = (
        "\n".join(f"- {e}" for e in top_hypothesis.evidence_collected)
        if top_hypothesis.evidence_collected
        else "(no evidence collected)"
    )

    return f"""Root cause hypothesis: {top_hypothesis.description}
Hypothesis probability: {top_hypothesis.probability:.2f}

Error: {error_context.error_type}: {error_context.error_message}
File: {error_context.file_name}, Line: {error_context.line_number}

Code around error:
{code_context}

Tools used: {', '.join(tools_used) if tools_used else 'none'}
Evidence collected: {evidence}

Recent reasoning:
{recent_reasoning}

Generate a clear conclusion and concrete fix."""


def _parse_conclusion_response(response_text: str) -> dict:
    """Parse LLM conclusion response into structured dict."""
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

        conclusion = data.get("conclusion", "")
        suggested_fix = data.get("suggested_fix", "")
        summary = data.get("summary", "")

        if not conclusion:
            return None

        return {
            "conclusion": conclusion,
            "suggested_fix": suggested_fix,
            "summary": summary,
        }
    except (json.JSONDecodeError, ValueError, TypeError):
        return None


def _template_conclusion(
    top_hypothesis: Hypothesis,
    error_context: ErrorContext,
    tools_used: List[str],
    confidence_level: str,
) -> dict:
    """Template-based fallback when LLM is unavailable."""
    conclusion = (
        f"The error `{error_context.error_type}: {error_context.error_message}` "
        f"at line {error_context.line_number} in `{error_context.file_name}` "
        f"is most likely caused by: {top_hypothesis.description}."
    )

    suggested_fix = (
        f"# Fix for {error_context.error_type} at line {error_context.line_number}\n"
        f"# Root cause: {top_hypothesis.description}\n"
        f"# Check line {error_context.line_number} in {error_context.file_name} "
        f"and verify the fix addresses the root cause."
    )

    if confidence_level == "low":
        suggested_fix += (
            "\n\n# Note: This diagnosis has low confidence — "
            "manual verification recommended."
        )

    tools_str = ", ".join(tools_used) if tools_used else "none"
    summary = (
        f"The debugging agent analyzed the error using {tools_str}. "
        f"The most likely root cause (confidence: {confidence_level}) is: "
        f"{top_hypothesis.description}."
    )

    evidence_summary = _build_evidence_summary(top_hypothesis, tools_used, [])

    return {
        "conclusion": conclusion,
        "suggested_fix": suggested_fix,
        "summary": summary,
        "evidence_summary": evidence_summary,
    }


def _build_evidence_summary(
    top_hypothesis: Hypothesis,
    tools_used: List[str],
    reasoning_chain: List[str],
) -> str:
    """Build a summary of what evidence supported the conclusion."""
    parts = []

    if tools_used:
        parts.append(f"Tools used: {', '.join(set(tools_used))}")

    if top_hypothesis.evidence_collected:
        parts.append(
            f"Supporting evidence: {'; '.join(top_hypothesis.evidence_collected)}"
        )
    else:
        parts.append("Limited direct evidence collected")

    observation_count = sum(
        1 for r in reasoning_chain if "Observation" in r
    )
    if observation_count > 0:
        parts.append(f"Observations gathered: {observation_count}")

    return ". ".join(parts) + "."
