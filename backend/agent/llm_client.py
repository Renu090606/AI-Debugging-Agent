"""Shared LLM client with retry and fallback logic.

Used by both hypothesis_generator.py and belief_updater.py to ensure
consistent retry behavior across the project.
"""

import asyncio
import os
from typing import Union

from dotenv import load_dotenv
from groq import AsyncGroq
import google.generativeai as genai

load_dotenv()

# LLM Configuration
GROQ_MODEL = "llama-3.3-70b-versatile"
GEMINI_MODEL = "gemini-2.0-flash"
TEMPERATURE = 0.3
MAX_TOKENS = 1024
MAX_RETRIES = 2
BASE_DELAY = 2  # seconds


async def call_llm_with_retry(
    system_prompt: str, user_prompt: str
) -> Union[str, dict]:
    """Call Groq with retries, fallback to Gemini. Returns text or error dict.

    Retry logic:
    - Up to MAX_RETRIES retries on Groq (3 total attempts)
    - Exponential backoff: 2s, 4s
    - If Groq exhausted, single Gemini attempt
    - Returns error dict if everything fails
    """
    # Try Groq with retries
    for attempt in range(MAX_RETRIES + 1):
        try:
            result = await _call_groq(system_prompt, user_prompt)
            return result
        except Exception:
            if attempt < MAX_RETRIES:
                delay = BASE_DELAY * (2**attempt)
                await asyncio.sleep(delay)

    # Groq failed — try Gemini fallback
    try:
        result = await _call_gemini(system_prompt, user_prompt)
        return result
    except Exception:
        return {
            "error": "LLM temporarily unavailable. Please try again in 30 seconds."
        }


async def _call_groq(system_prompt: str, user_prompt: str) -> str:
    """Call Groq API and return the response text."""
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise ValueError("GROQ_API_KEY not set in environment")

    client = AsyncGroq(api_key=api_key)
    response = await client.chat.completions.create(
        model=GROQ_MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=TEMPERATURE,
        max_tokens=MAX_TOKENS,
    )
    content = response.choices[0].message.content
    if not content or not content.strip():
        raise ValueError("Groq returned empty response")
    return content


async def _call_gemini(system_prompt: str, user_prompt: str) -> str:
    """Call Gemini API and return the response text."""
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY not set in environment")

    genai.configure(api_key=api_key)
    model = genai.GenerativeModel(
        GEMINI_MODEL,
        system_instruction=system_prompt,
    )

    # Gemini's generate_content is synchronous — run in executor
    loop = asyncio.get_event_loop()
    response = await loop.run_in_executor(
        None, lambda: model.generate_content(user_prompt)
    )
    return response.text
