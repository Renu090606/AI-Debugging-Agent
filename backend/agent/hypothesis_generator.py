"""Hypothesis generator — calls LLM to produce ranked root cause hypotheses."""

import asyncio
import json
import os
import re
from typing import List, Union

from dotenv import load_dotenv
from groq import AsyncGroq
import google.generativeai as genai

from parsers.models import ErrorContext, Hypothesis
from agent.llm_client import call_llm_with_retry

load_dotenv()

# System prompt for hypothesis generation
SYSTEM_PROMPT = """You are an expert Python debugger. Given an error context, generate 3-5 hypotheses about the root cause. Each hypothesis must have:
- id: string (h1, h2, ...)
- description: clear, specific root cause description
- probability: float between 0.0 and 1.0 (must sum to 1.0)
- evidence_needed: list of strings describing what would confirm this

Return ONLY a valid JSON array. No explanation text outside the JSON. No markdown fences."""


async def generate_hypotheses(
    error_context: ErrorContext,
) -> Union[List[Hypothesis], dict]:
    """Generate 3-5 root cause hypotheses from an error context using LLM.

    Calls Groq (primary) with retry logic, falls back to Gemini if Groq fails.
    Never crashes — returns a structured error dict if all calls fail.

    Args:
        error_context: Parsed error from Phase 1's parse_error().

    Returns:
        List[Hypothesis] on success, or {"error": "..."} on total failure.
    """
    user_prompt = _build_user_prompt(error_context)
    response_text = await call_llm_with_retry(SYSTEM_PROMPT, user_prompt)

    # If all LLM calls failed, response_text is an error dict
    if isinstance(response_text, dict):
        return response_text

    # Parse LLM response into Hypothesis objects
    hypotheses = _parse_hypotheses_response(response_text)
    if hypotheses is None:
        # JSON parsing failed — try one more time with stricter prompt
        strict_prompt = user_prompt + "\n\nRETURN ONLY RAW JSON ARRAY. NO OTHER TEXT."
        response_text = await call_llm_with_retry(SYSTEM_PROMPT, strict_prompt)
        if isinstance(response_text, dict):
            return response_text
        hypotheses = _parse_hypotheses_response(response_text)
        if hypotheses is None:
            return {"error": "LLM returned invalid format. Please try again."}

    return hypotheses


def _build_user_prompt(error_context: ErrorContext) -> str:
    """Construct the user prompt from an ErrorContext."""
    code_section = (
        "\n".join(error_context.code_lines)
        if error_context.code_lines
        else "(no code provided)"
    )

    return f"""Error Type: {error_context.error_type}
Error Message: {error_context.error_message}
Line Number: {error_context.line_number}
File: {error_context.file_name}

Code Context (lines around error):
{code_section}"""


def _parse_hypotheses_response(response_text: str) -> Union[List[Hypothesis], None]:
    """Parse LLM response text into a list of Hypothesis objects.

    Handles: raw JSON, markdown-fenced JSON, extra text around JSON.
    Returns None if parsing fails completely.
    """
    if not response_text:
        return None

    # Strip markdown code fences if present
    cleaned = _strip_markdown_fences(response_text)

    # Try to find JSON array in the response
    json_str = _extract_json_array(cleaned)
    if json_str is None:
        return None

    try:
        raw_list = json.loads(json_str)
    except json.JSONDecodeError:
        return None

    if not isinstance(raw_list, list) or len(raw_list) == 0:
        return None

    # Convert raw dicts to Hypothesis objects
    hypotheses = []
    for i, item in enumerate(raw_list):
        if not isinstance(item, dict):
            continue
        try:
            h = Hypothesis(
                id=item.get("id", f"h{i + 1}"),
                description=item.get("description", "Unknown cause"),
                probability=float(item.get("probability", 0.0)),
                evidence_needed=item.get("evidence_needed", []),
                evidence_collected=[],
                status="untested",
            )
            hypotheses.append(h)
        except (ValueError, TypeError):
            continue

    if not hypotheses:
        return None

    # Cap at 5 hypotheses (take top by probability)
    if len(hypotheses) > 5:
        hypotheses.sort(key=lambda h: h.probability, reverse=True)
        hypotheses = hypotheses[:5]

    # Normalize probabilities to sum to 1.0
    hypotheses = normalize_probabilities(hypotheses)

    return hypotheses


def _strip_markdown_fences(text: str) -> str:
    """Remove markdown code fences (```json ... ```) from LLM output."""
    text = re.sub(r"^```(?:json)?\s*\n?", "", text.strip())
    text = re.sub(r"\n?```\s*$", "", text.strip())
    return text.strip()


def _extract_json_array(text: str) -> Union[str, None]:
    """Find and extract a JSON array from text that may contain extra content."""
    text = text.strip()
    if text.startswith("["):
        return text

    # Look for a JSON array within the text
    start = text.find("[")
    if start == -1:
        return None

    # Find the matching closing bracket
    depth = 0
    for i in range(start, len(text)):
        if text[i] == "[":
            depth += 1
        elif text[i] == "]":
            depth -= 1
            if depth == 0:
                return text[start : i + 1]

    return None


def normalize_probabilities(hypotheses: List[Hypothesis]) -> List[Hypothesis]:
    """Normalize hypothesis probabilities to sum to 1.0."""
    total = sum(h.probability for h in hypotheses)
    if total <= 0:
        equal_prob = 1.0 / len(hypotheses)
        for h in hypotheses:
            h.probability = equal_prob
    else:
        for h in hypotheses:
            h.probability = round(h.probability / total, 4)
    return hypotheses
