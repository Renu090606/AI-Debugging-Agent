"""ReAct Agent Orchestrator — the core reasoning loop.

Implements the Reason → Act → Observe cycle that drives autonomous debugging.
Generates hypotheses, then iteratively tests them through tool use, user questions,
and belief updates until a termination condition is met.
"""

import uuid
from typing import List, Optional, Union

from parsers.models import (
    ErrorContext,
    Hypothesis,
    ToolResult,
    AgentAction,
    DebugResult,
)
from agent.hypothesis_generator import generate_hypotheses
from agent.belief_updater import update_beliefs
from agent.self_critique import self_critique, calculate_confidence
from agent.conclusion_generator import generate_conclusion
from agent.llm_client import call_llm_with_retry

# Loop configuration
MAX_ITERATIONS = 10
MAX_QUESTIONS = 3
CONFIDENCE_THRESHOLD = 0.80
STALE_THRESHOLD = 0.05
STALE_LIMIT = 2
LOW_CONFIDENCE_THRESHOLD = 0.15  # If ALL hypotheses below this, ask user


# --- Session State ---

class SessionState:
    """Holds the mutable state of a debug session across loop iterations."""

    def __init__(
        self,
        session_id: str,
        error_context: ErrorContext,
        code_snippet: str,
        hypotheses: List[Hypothesis],
    ):
        self.session_id = session_id
        self.error_context = error_context
        self.code_snippet = code_snippet
        self.hypotheses = hypotheses
        self.reasoning_chain: List[str] = []
        self.iteration: int = 0
        self.stale_counter: int = 0
        self.questions_asked: int = 0
        self.tools_used: List[str] = []
        self.pending_question: Optional[str] = None
        self.asked_questions: List[str] = []
        self.skip_ask_user: bool = False
        self.previous_qa: List[dict] = []  # [{question, answer}]


# In-memory session store (replaced by DB in production)
_sessions: dict = {}


def get_session(session_id: str) -> Optional[SessionState]:
    """Retrieve a session by ID."""
    return _sessions.get(session_id)


# --- Main Entry Points ---

async def run_debug_session(
    error_context: ErrorContext, code_snippet: str
) -> Union[DebugResult, dict]:
    """Start a new debugging session and run the ReAct loop.

    Args:
        error_context: Parsed error from Phase 1.
        code_snippet: Raw user code for tool analysis.

    Returns:
        DebugResult on completion, or dict with pending question / error.
    """
    session_id = str(uuid.uuid4())

    # Generate initial hypotheses
    hypotheses = await generate_hypotheses(error_context)

    # If hypothesis generation failed, return error
    if isinstance(hypotheses, dict):
        return hypotheses

    # Create session state
    state = SessionState(session_id, error_context, code_snippet, hypotheses)
    state.reasoning_chain.append(
        f"[Init] Generated {len(hypotheses)} hypotheses: "
        + ", ".join(f"{h.id}={h.probability:.2f}" for h in hypotheses)
    )
    _sessions[session_id] = state

    # Run the loop
    return await _run_loop(state)


async def resume_session(session_id: str, answer: str) -> Union[DebugResult, dict]:
    """Resume a paused session after user answers a question.

    Args:
        session_id: The session to resume.
        answer: User's answer to the pending question.

    Returns:
        DebugResult on completion, or dict with next pending question / error.
    """
    state = get_session(session_id)
    if state is None:
        return {"error": f"Session {session_id} not found."}

    if state.pending_question is None:
        return {"error": "No pending question for this session."}

    # Record the answer as observation
    state.reasoning_chain.append(
        f"[Iteration {state.iteration}] User answer: {answer}"
    )

    # Track Q&A for dedup injection into future prompts
    state.previous_qa.append({
        "question": state.pending_question,
        "answer": answer,
    })

    # Check if user signals no more info to give
    if _user_signals_complete(answer):
        state.skip_ask_user = True

    # Update beliefs with user answer
    old_probs = [h.probability for h in state.hypotheses]
    state.hypotheses = await update_beliefs(state.hypotheses, answer)
    new_probs = [h.probability for h in state.hypotheses]

    # Stale check
    _check_stale(state, old_probs, new_probs)

    # Clear pending question
    state.pending_question = None

    # Check termination after answer
    if state.stale_counter >= STALE_LIMIT:
        return await _force_conclude(state, confidence_level="low")

    if max(h.probability for h in state.hypotheses) >= CONFIDENCE_THRESHOLD:
        critique_result = await self_critique(
            state.hypotheses, state.reasoning_chain
        )
        if critique_result["recommendation"] == "CONCLUDE":
            return await _conclude(state, critique_result["adjusted_confidence"])

    # Continue loop
    return await _run_loop(state)


# --- Core Loop ---

async def _run_loop(state: SessionState) -> Union[DebugResult, dict]:
    """Execute the ReAct loop until a termination condition is met."""
    while state.iteration < MAX_ITERATIONS:
        state.iteration += 1

        # REASON: Assess current state
        thought = await _reason(state)
        state.reasoning_chain.append(
            f"[Iteration {state.iteration}] Thought: {thought}"
        )

        # Check: ALL hypotheses below LOW_CONFIDENCE_THRESHOLD
        if _all_hypotheses_low(state.hypotheses):
            if state.questions_asked < MAX_QUESTIONS:
                # Ask user for more context
                question = await _generate_low_confidence_question(state)
                return _pause_for_question(state, question)
            else:
                # No questions left — force conclude
                return await _force_conclude(state, confidence_level="low")

        # DECIDE: Choose action
        action = await _decide_action(state)
        state.reasoning_chain.append(
            f"[Iteration {state.iteration}] Action: {action.action_type}"
            + (f" ({action.tool_name})" if action.tool_name else "")
        )

        # CONCLUDE immediately if decided
        if action.action_type == "CONCLUDE":
            critique_result = await self_critique(
                state.hypotheses, state.reasoning_chain
            )
            return await _conclude(state, critique_result["adjusted_confidence"])

        # ASK_USER
        if action.action_type == "ASK_USER":
            # Dedup check: skip if flagged or question is too similar to a previous one
            if state.skip_ask_user or _is_duplicate_question(action.question, state.asked_questions):
                # Override to RUN_TOOL or CONCLUDE
                action = AgentAction(
                    action_type="RUN_TOOL",
                    tool_name="ast_analyzer",
                    question=None,
                    reasoning="Skipping duplicate/blocked question — running tool instead",
                )
                state.reasoning_chain.append(
                    f"[Iteration {state.iteration}] Skipped duplicate question, running tool"
                )
            else:
                state.questions_asked += 1
                state.asked_questions.append(action.question)
                return _pause_for_question(state, action.question)

        # RUN_TOOL
        if action.action_type == "RUN_TOOL":
            observation = await _execute_tool(
                action.tool_name, state.code_snippet, state.error_context
            )
            state.reasoning_chain.append(
                f"[Iteration {state.iteration}] Observation ({action.tool_name}): "
                + _summarize_observation(observation)
            )
            state.tools_used.append(action.tool_name)

            # UPDATE beliefs
            old_probs = [h.probability for h in state.hypotheses]
            state.hypotheses = await update_beliefs(state.hypotheses, observation)
            new_probs = [h.probability for h in state.hypotheses]

            # STALE CHECK
            _check_stale(state, old_probs, new_probs)

            if state.stale_counter >= STALE_LIMIT:
                return await _force_conclude(state, confidence_level="low")

            # CONFIDENCE CHECK
            if max(new_probs) >= CONFIDENCE_THRESHOLD:
                critique_result = await self_critique(
                    state.hypotheses, state.reasoning_chain
                )
                if critique_result["recommendation"] == "CONCLUDE":
                    return await _conclude(
                        state, critique_result["adjusted_confidence"]
                    )
                else:
                    state.reasoning_chain.append(
                        f"[Iteration {state.iteration}] Self-critique: CONTINUE"
                    )

    # MAX ITERATIONS reached
    return await _force_conclude(state, confidence_level="medium")


# --- Reasoning (LLM-based) ---

REASON_PROMPT = """You are a debugging agent analyzing Python errors.
Given the current hypotheses and reasoning so far, produce a brief thought
about what to investigate next. Focus on which hypothesis needs more evidence
and what kind of evidence would help.

Keep your thought to 1-2 sentences."""


async def _reason(state: SessionState) -> str:
    """Generate a reasoning thought about the current state."""
    hyp_summary = "\n".join(
        f"- {h.id}: {h.description} (p={h.probability:.2f}, status={h.status})"
        for h in state.hypotheses
        if h.status != "eliminated"
    )
    recent_chain = "\n".join(state.reasoning_chain[-3:]) if state.reasoning_chain else "(start)"

    user_prompt = f"""Current hypotheses:
{hyp_summary}

Recent reasoning:
{recent_chain}

Error: {state.error_context.error_type}: {state.error_context.error_message}
{_build_qa_context(state)}
What should we investigate next?"""

    result = await call_llm_with_retry(REASON_PROMPT, user_prompt)
    if isinstance(result, dict):
        return "Unable to reason — proceeding with tool analysis."
    return result.strip()[:200]  # Cap length


# --- Action Decision (LLM-based) ---

DECIDE_PROMPT = """You are a debugging agent deciding your next action.

Available actions:
1. RUN_TOOL: Run a static analysis tool. Available tools:
   - ast_analyzer: Finds undefined names, unused variables, function calls, imports
   - linter: Finds style/logic issues (E-codes and W-codes)
   - variable_tracker: Tracks variable assignments and usage, finds undefined usages
2. ASK_USER: Ask the user a clarifying question (you have {questions_remaining} questions remaining)
3. CONCLUDE: End debugging with your current best hypothesis

Decision rules:
- If top hypothesis probability >= 0.80, choose CONCLUDE
- If evidence gaps exist and a tool can help, choose RUN_TOOL
- If you need information only the user can provide, choose ASK_USER
- If no useful actions remain, choose CONCLUDE

Return ONLY a JSON object:
{{"action_type": "RUN_TOOL|ASK_USER|CONCLUDE", "tool_name": "ast_analyzer|linter|variable_tracker|null", "question": "your question|null", "reasoning": "why this action"}}

No markdown fences. No extra text."""


async def _decide_action(state: SessionState) -> AgentAction:
    """Use LLM to decide the next action."""
    questions_remaining = MAX_QUESTIONS - state.questions_asked

    hyp_summary = "\n".join(
        f"- {h.id}: {h.description} (p={h.probability:.2f}, evidence_needed={h.evidence_needed})"
        for h in state.hypotheses
        if h.status != "eliminated"
    )
    tools_used = ", ".join(state.tools_used) if state.tools_used else "none yet"

    user_prompt = f"""Current hypotheses:
{hyp_summary}

Tools already used: {tools_used}
Questions asked: {state.questions_asked}/{MAX_QUESTIONS}
Current iteration: {state.iteration}/{MAX_ITERATIONS}

Error: {state.error_context.error_type}: {state.error_context.error_message}

Choose your next action."""

    system = DECIDE_PROMPT.format(questions_remaining=questions_remaining)
    result = await call_llm_with_retry(system, user_prompt)

    if isinstance(result, dict):
        # LLM failed — default to running ast_analyzer
        return AgentAction(
            action_type="RUN_TOOL",
            tool_name="ast_analyzer",
            question=None,
            reasoning="LLM unavailable — defaulting to AST analysis",
        )

    return _parse_action_response(result, questions_remaining)


def _parse_action_response(response_text: str, questions_remaining: int) -> AgentAction:
    """Parse LLM action decision response."""
    import json
    import re

    # Strip markdown fences
    cleaned = re.sub(r"^```(?:json)?\s*\n?", "", response_text.strip())
    cleaned = re.sub(r"\n?```\s*$", "", cleaned.strip())

    try:
        # Try to extract JSON object
        start = cleaned.find("{")
        end = cleaned.rfind("}") + 1
        if start >= 0 and end > start:
            data = json.loads(cleaned[start:end])
        else:
            raise ValueError("No JSON object found")

        action_type = data.get("action_type", "RUN_TOOL")
        tool_name = data.get("tool_name")
        question = data.get("question")
        reasoning = data.get("reasoning", "")

        # Validate action type
        if action_type not in ("RUN_TOOL", "ASK_USER", "CONCLUDE"):
            action_type = "RUN_TOOL"

        # Validate tool name
        if action_type == "RUN_TOOL" and tool_name not in (
            "ast_analyzer", "linter", "variable_tracker"
        ):
            tool_name = "ast_analyzer"

        # Can't ask if no questions remaining
        if action_type == "ASK_USER" and questions_remaining <= 0:
            action_type = "RUN_TOOL"
            tool_name = "ast_analyzer"
            reasoning += " (no questions remaining, switching to tool)"

        return AgentAction(
            action_type=action_type,
            tool_name=tool_name if action_type == "RUN_TOOL" else None,
            question=question if action_type == "ASK_USER" else None,
            reasoning=reasoning,
        )
    except (json.JSONDecodeError, ValueError, KeyError):
        # Default fallback
        return AgentAction(
            action_type="RUN_TOOL",
            tool_name="ast_analyzer",
            question=None,
            reasoning="Could not parse LLM decision — defaulting to AST analysis",
        )


# --- Low Confidence Question ---

LOW_CONFIDENCE_PROMPT = """You are a debugging agent. All your hypotheses have very low probability,
meaning you're uncertain about the root cause. Generate ONE clarifying question for the user
that would help narrow down the problem. The question should be specific and actionable.

Return ONLY the question text. No JSON. No explanation."""


async def _generate_low_confidence_question(state: SessionState) -> str:
    """Generate a question when all hypotheses are below threshold."""
    hyp_summary = "\n".join(
        f"- {h.description} (p={h.probability:.2f})"
        for h in state.hypotheses
    )
    user_prompt = f"""Error: {state.error_context.error_type}: {state.error_context.error_message}
Hypotheses (all low confidence):
{hyp_summary}

What should I ask the user to clarify?"""

    result = await call_llm_with_retry(LOW_CONFIDENCE_PROMPT, user_prompt)
    if isinstance(result, dict):
        return "Could you provide more context about what this code is supposed to do?"
    return result.strip()[:300]


# --- Tool Execution ---

async def _execute_tool(
    tool_name: str, code_snippet: str, error_context: ErrorContext
) -> ToolResult:
    """Execute a static analysis tool and return its result.

    Currently uses stub implementations. Phase 4 will provide real tools.
    """
    try:
        if tool_name == "ast_analyzer":
            from tools.ast_analyzer import analyze_ast
            output = analyze_ast(code_snippet)
        elif tool_name == "linter":
            from tools.linter import run_linter
            output = run_linter(code_snippet)
        elif tool_name == "variable_tracker":
            from tools.variable_tracker import track_variables
            output = track_variables(code_snippet)
        else:
            output = {"error": f"Unknown tool: {tool_name}"}
    except Exception as e:
        output = {"error": f"Tool execution failed: {str(e)}"}

    return ToolResult(
        tool_name=tool_name,
        output=output,
        relevant_to=[],
    )


# --- Helper Functions ---

def _all_hypotheses_low(hypotheses: List[Hypothesis]) -> bool:
    """Check if ALL hypotheses are below the low confidence threshold."""
    active = [h for h in hypotheses if h.status != "eliminated"]
    if not active:
        return True
    return all(h.probability < LOW_CONFIDENCE_THRESHOLD for h in active)


def _check_stale(state: SessionState, old_probs: List[float], new_probs: List[float]):
    """Update stale counter based on probability changes."""
    if not old_probs or not new_probs:
        return
    max_change = max(abs(n - o) for n, o in zip(new_probs, old_probs))
    if max_change < STALE_THRESHOLD:
        state.stale_counter += 1
    else:
        state.stale_counter = 0


def _pause_for_question(state: SessionState, question: str) -> dict:
    """Pause the loop and return the question to the frontend."""
    state.pending_question = question
    return {
        "status": "pending_question",
        "session_id": state.session_id,
        "question": question,
        "question_id": f"q{state.questions_asked}",
        "hypotheses": [h.model_dump() for h in state.hypotheses],
        "reasoning_chain": state.reasoning_chain,
        "iteration": state.iteration,
    }


async def _conclude(state: SessionState, adjusted_confidence: float) -> DebugResult:
    """Normal conclusion — high confidence, with LLM-generated fix."""
    top = _get_top_hypothesis(state.hypotheses)
    confidence = min(adjusted_confidence, 0.95)  # Hard cap
    confidence_level = "high" if confidence >= 0.75 else "medium"

    # Generate rich conclusion via LLM
    conclusion_data = await generate_conclusion(
        top_hypothesis=top,
        error_context=state.error_context,
        reasoning_chain=state.reasoning_chain,
        tools_used=state.tools_used,
        confidence_level=confidence_level,
    )

    result = DebugResult(
        session_id=state.session_id,
        hypotheses=state.hypotheses,
        reasoning_chain=state.reasoning_chain,
        conclusion=conclusion_data["conclusion"],
        confidence=confidence,
        confidence_level=confidence_level,
        suggested_fix=conclusion_data["suggested_fix"],
    )

    # Clean up session
    _sessions.pop(state.session_id, None)
    return result


async def _force_conclude(state: SessionState, confidence_level: str) -> DebugResult:
    """Forced conclusion — stale loop or max iterations, with LLM-generated fix."""
    top = _get_top_hypothesis(state.hypotheses)
    confidence = top.probability * 0.8  # Discount for forced conclusion
    confidence = min(confidence, 0.95)

    reason = {
        "low": "Agent confidence remained low (stale loop detected)",
        "medium": "Maximum iterations reached",
    }.get(confidence_level, "Forced conclusion")

    state.reasoning_chain.append(f"[Conclude] {reason}. Best hypothesis: {top.id}")

    # Generate rich conclusion via LLM
    conclusion_data = await generate_conclusion(
        top_hypothesis=top,
        error_context=state.error_context,
        reasoning_chain=state.reasoning_chain,
        tools_used=state.tools_used,
        confidence_level=confidence_level,
    )

    result = DebugResult(
        session_id=state.session_id,
        hypotheses=state.hypotheses,
        reasoning_chain=state.reasoning_chain,
        conclusion=conclusion_data["conclusion"],
        confidence=confidence,
        confidence_level=confidence_level,
        suggested_fix=conclusion_data["suggested_fix"],
    )

    _sessions.pop(state.session_id, None)
    return result


def _get_top_hypothesis(hypotheses: List[Hypothesis]) -> Hypothesis:
    """Get the hypothesis with the highest probability."""
    active = [h for h in hypotheses if h.status != "eliminated"]
    if not active:
        active = hypotheses  # Fallback: use all if all eliminated
    return max(active, key=lambda h: h.probability)


def _summarize_observation(observation: ToolResult) -> str:
    """Create a brief summary of tool output for the reasoning chain."""
    output = observation.output
    if "error" in output:
        return f"Error: {output['error']}"

    # Summarize key findings
    findings = []
    if "undefined_names" in output and output["undefined_names"]:
        findings.append(f"undefined: {output['undefined_names']}")
    if "unused_variables" in output and output["unused_variables"]:
        findings.append(f"unused: {output['unused_variables']}")
    if "undefined_usages" in output and output["undefined_usages"]:
        findings.append(f"undefined usages: {output['undefined_usages']}")
    if "issues" in output and output["issues"]:
        findings.append(f"{len(output['issues'])} lint issues")

    return ", ".join(findings) if findings else "No notable findings"


# --- Duplicate Question Prevention ---

STOP_PHRASES = [
    "complete code", "full code", "entire code",
    "that's all", "that's it", "that's everything",
    "nothing else", "no more", "no other file",
]


def _user_signals_complete(answer: str) -> bool:
    """Check if user's answer signals they have no more info to provide."""
    answer_lower = answer.lower()
    return any(phrase in answer_lower for phrase in STOP_PHRASES)


def _is_duplicate_question(new_question: str, asked_questions: List[str]) -> bool:
    """Check if new question has 50%+ word overlap with any previously asked question."""
    if not asked_questions or not new_question:
        return False

    new_words = set(new_question.lower().split())
    if not new_words:
        return False

    for prev in asked_questions:
        prev_words = set(prev.lower().split())
        if not prev_words:
            continue
        overlap = len(new_words & prev_words)
        # 50% overlap relative to the smaller set
        min_size = min(len(new_words), len(prev_words))
        if min_size > 0 and overlap / min_size >= 0.5:
            return True

    return False


def _build_qa_context(state) -> str:
    """Build a context string of previous Q&A to inject into prompts."""
    if not state.previous_qa:
        return ""

    lines = ["\nPrevious questions and answers (DO NOT repeat these):"]
    for qa in state.previous_qa:
        lines.append(f"- You asked: \"{qa['question']}\"")
        lines.append(f"  User answered: \"{qa['answer']}\"")
    lines.append("Do NOT ask the same or similar question. Use tools or conclude.\n")
    return "\n".join(lines)
