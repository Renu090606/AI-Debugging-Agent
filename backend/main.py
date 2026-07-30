"""FastAPI backend for the AI Debugging Agent.

Exposes the debugging agent as an HTTP API with endpoints for:
- POST /debug — start a new debugging session
- POST /answer — answer agent's clarifying question
- GET /sessions — list active sessions
- GET /health — health check

Run: uvicorn main:app --reload --port 8000
"""

import os
from datetime import datetime, timezone
from typing import Optional

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from parsers.error_parser import parse_error
from agent.orchestrator import run_debug_session, resume_session, get_session, _sessions

load_dotenv()

# --- App Setup ---

app = FastAPI(
    title="AI Debugging Agent",
    description="A ReAct-based agentic AI system for automated Python code debugging",
    version="1.0.0",
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=[os.getenv("FRONTEND_URL", "http://localhost:5173")],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --- Request/Response Models ---

class DebugRequest(BaseModel):
    """Request body for POST /debug."""
    code: str = Field(..., min_length=1, max_length=50000, description="Python source code to debug")
    traceback: str = Field(..., min_length=1, max_length=20000, description="Python traceback string")


class AnswerRequest(BaseModel):
    """Request body for POST /answer."""
    session_id: str = Field(..., min_length=1, description="Session ID from /debug response")
    answer: str = Field(..., min_length=1, max_length=2000, description="User's answer to agent question")


# --- Endpoints ---

@app.post("/debug")
async def debug_code(request: DebugRequest):
    """Start a new debugging session.

    Parses the traceback, generates hypotheses, and runs the ReAct loop.
    Returns either a completed DebugResult or a pending question.
    """
    # Parse the error
    error_context = parse_error(request.traceback, request.code)

    # Run the debug session
    result = await run_debug_session(error_context, request.code)

    # If result is a DebugResult (Pydantic model), serialize it
    if hasattr(result, "model_dump"):
        return result.model_dump()

    # If result is a dict (pending question or error), return as-is
    return result


@app.post("/answer")
async def answer_question(request: AnswerRequest):
    """Answer the agent's clarifying question and resume the session.

    Returns either a completed DebugResult, another pending question, or error.
    """
    # Check session exists
    session = get_session(request.session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")

    # Check there's a pending question
    if session.pending_question is None:
        raise HTTPException(status_code=409, detail="No pending question for this session")

    # Resume the session with the answer
    result = await resume_session(request.session_id, request.answer)

    # Serialize
    if hasattr(result, "model_dump"):
        return result.model_dump()

    return result


@app.get("/sessions")
async def list_sessions():
    """List all active debug sessions."""
    sessions = []
    for session_id, state in _sessions.items():
        sessions.append({
            "session_id": session_id,
            "error_type": state.error_context.error_type,
            "status": "pending_question" if state.pending_question else "in_progress",
            "iteration": state.iteration,
        })

    return {"sessions": sessions}


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "ok",
        "version": "1.0.0",
        "model_primary": "llama-3.3-70b-versatile",
        "model_fallback": "gemini-2.0-flash",
    }
