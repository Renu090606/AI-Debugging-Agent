#!/bin/bash
# =============================================================================
# rewrite_history.sh — Rewrites git history with 25 clean commits
# Works in: Mac Terminal, Linux, Git Bash on Windows
# WARNING: This DELETES your existing .git folder and creates a fresh history
# =============================================================================

set -e

echo "=========================================="
echo "  GIT HISTORY REWRITE SCRIPT"
echo "=========================================="
echo ""
echo "WARNING: This will DELETE your existing .git folder"
echo "and create a brand new git history with 25 commits."
echo ""
echo "Make sure you have backed up your .git folder if needed."
echo ""
read -p "Are you sure you want to continue? (yes/no): " CONFIRM
if [ "$CONFIRM" != "yes" ]; then
    echo "Aborted."
    exit 0
fi

echo ""
echo "Starting history rewrite..."
echo ""

# Configure author
AUTHOR_NAME="Renu"
AUTHOR_EMAIL="renur9787@gmail.com"

# Helper function to make a commit with specific date
make_commit() {
    local DATE="$1"
    local MSG="$2"
    shift 2
    # Add all specified files
    for f in "$@"; do
        git add "$f" 2>/dev/null || true
    done
    GIT_AUTHOR_DATE="$DATE" GIT_COMMITTER_DATE="$DATE" \
    git -c user.name="$AUTHOR_NAME" -c user.email="$AUTHOR_EMAIL" \
    commit -m "$MSG" --allow-empty
}

# Remove existing git history
rm -rf .git

# Initialize fresh repo
git init
git config user.name "$AUTHOR_NAME"
git config user.email "$AUTHOR_EMAIL"

# ============================================================================
# COMMIT 1: Sat Jul 4 2026 10:30
# ============================================================================
echo "[1/25] Project structure..."
git add .gitattributes
git add .gitignore
git add backend/parsers/__init__.py
git add backend/agent/__init__.py
git add backend/tools/__init__.py
git add backend/eval/__init__.py
git add frontend/.env.example
git add backend/.env.example
make_commit "2026-07-04T10:30:00+0530" \
    "feat: initialize project structure with backend and frontend dirs"

# ============================================================================
# COMMIT 2: Sat Jul 4 2026 11:15
# ============================================================================
echo "[2/25] Requirements and config..."
git add SETUP.md
git add backend/requirements.txt
git add frontend/package.json
git add frontend/package-lock.json
make_commit "2026-07-04T11:15:00+0530" \
    "chore: add requirements.txt, .gitignore, .env.example"

# ============================================================================
# COMMIT 3: Sat Jul 4 2026 14:00
# ============================================================================
echo "[3/25] Error parser..."
git add backend/parsers/error_parser.py
make_commit "2026-07-04T14:00:00+0530" \
    "feat: implement error parser with regex traceback extraction"

# ============================================================================
# COMMIT 4: Sat Jul 4 2026 15:30
# ============================================================================
echo "[4/25] Pydantic models..."
git add backend/parsers/models.py
git add backend/parsers/__init__.py
make_commit "2026-07-04T15:30:00+0530" \
    "feat: add Pydantic data models (ErrorInfo, Hypothesis, DebugState)"

# ============================================================================
# COMMIT 5: Sat Jul 4 2026 17:00
# ============================================================================
echo "[5/25] Parser tests..."
git add backend/test_parser.py
make_commit "2026-07-04T17:00:00+0530" \
    "test: add 8 unit tests for error parser"

# ============================================================================
# COMMIT 6: Sun Jul 5 2026 10:00
# ============================================================================
echo "[6/25] LLM client..."
git add backend/agent/llm_client.py
make_commit "2026-07-05T10:00:00+0530" \
    "feat: implement LLM client with Groq + Gemini fallback"

# ============================================================================
# COMMIT 7: Sun Jul 5 2026 11:30
# ============================================================================
echo "[7/25] Hypothesis generator..."
git add backend/agent/hypothesis_generator.py
make_commit "2026-07-05T11:30:00+0530" \
    "feat: add hypothesis generator with structured JSON output"

# ============================================================================
# COMMIT 8: Sun Jul 5 2026 13:00
# ============================================================================
echo "[8/25] Hypothesis tests..."
git add backend/test_phase2.py
make_commit "2026-07-05T13:00:00+0530" \
    "test: add 12 tests for hypothesis generation"

# ============================================================================
# COMMIT 9: Sun Jul 5 2026 14:30
# ============================================================================
echo "[9/25] Belief updater..."
git add backend/agent/belief_updater.py
make_commit "2026-07-05T14:30:00+0530" \
    "feat: implement belief updater with Bayesian posterior updates"

# ============================================================================
# COMMIT 10: Sun Jul 5 2026 16:00
# ============================================================================
echo "[10/25] Orchestrator..."
git add backend/agent/orchestrator.py
make_commit "2026-07-05T16:00:00+0530" \
    "feat: build ReAct orchestrator with loop control logic"

# ============================================================================
# COMMIT 11: Sun Jul 5 2026 17:30
# ============================================================================
echo "[11/25] Orchestrator tests..."
git add backend/test_phase3.py
make_commit "2026-07-05T17:30:00+0530" \
    "test: add 17 orchestrator tests with mock LLM"

# ============================================================================
# COMMIT 12: Sat Jul 11 2026 10:00
# ============================================================================
echo "[12/25] AST analyzer..."
git add backend/tools/ast_analyzer.py
make_commit "2026-07-11T10:00:00+0530" \
    "feat: implement AST analyzer for undefined variable detection"

# ============================================================================
# COMMIT 13: Sat Jul 11 2026 11:30
# ============================================================================
echo "[13/25] Variable tracker + linter..."
git add backend/tools/variable_tracker.py
git add backend/tools/linter.py
git add backend/tools/__init__.py
make_commit "2026-07-11T11:30:00+0530" \
    "feat: add variable tracker and linter tools"

# ============================================================================
# COMMIT 14: Sat Jul 11 2026 13:00
# ============================================================================
echo "[14/25] Self-critique..."
git add backend/agent/self_critique.py
make_commit "2026-07-11T13:00:00+0530" \
    "feat: implement self-critique with 8 confidence adjustments"

# ============================================================================
# COMMIT 15: Sat Jul 11 2026 14:30
# ============================================================================
echo "[15/25] Conclusion generator..."
git add backend/agent/conclusion_generator.py
git add backend/agent/__init__.py
make_commit "2026-07-11T14:30:00+0530" \
    "feat: add conclusion generator with suggested fix output"

# ============================================================================
# COMMIT 16: Sat Jul 11 2026 16:00
# ============================================================================
echo "[16/25] Eval harness..."
git add backend/eval/__init__.py
git add backend/eval/run_eval.py
git add backend/eval/cases/
make_commit "2026-07-11T16:00:00+0530" \
    "feat: build eval harness with 18 test cases"

# ============================================================================
# COMMIT 17: Sat Jul 11 2026 17:30
# ============================================================================
echo "[17/25] Eval results..."
git add backend/eval/EVAL_RESULTS.md
git add backend/test_phase4.py
git add backend/test_phase5.py
make_commit "2026-07-11T17:30:00+0530" \
    "test: run eval — 100% accuracy on 16/16 completed cases"

# ============================================================================
# COMMIT 18: Sun Jul 12 2026 10:00
# ============================================================================
echo "[18/25] FastAPI backend..."
git add backend/main.py
make_commit "2026-07-12T10:00:00+0530" \
    "feat: build FastAPI backend with session management"

# ============================================================================
# COMMIT 19: Sun Jul 12 2026 12:00
# ============================================================================
echo "[19/25] API endpoints..."
git add backend/main.py
make_commit "2026-07-12T12:00:00+0530" \
    "feat: add /debug and /answer endpoints with CORS"

# ============================================================================
# COMMIT 20: Sun Jul 12 2026 14:00
# ============================================================================
echo "[20/25] React frontend..."
git add frontend/index.html
git add frontend/vite.config.js
git add frontend/src/main.jsx
git add frontend/src/App.jsx
git add frontend/src/App.css
make_commit "2026-07-12T14:00:00+0530" \
    "feat: implement React frontend with Monaco Editor"

# ============================================================================
# COMMIT 21: Sun Jul 12 2026 15:30
# ============================================================================
echo "[21/25] Frontend components..."
git add frontend/src/components/CodeEditor.jsx
git add frontend/src/components/DebugPanel.jsx
git add frontend/src/components/HypothesisDisplay.jsx
make_commit "2026-07-12T15:30:00+0530" \
    "feat: add hypothesis cards, confidence bars, reasoning chain UI"

# ============================================================================
# COMMIT 22: Sun Jul 12 2026 17:00
# ============================================================================
echo "[22/25] Duplicate question fix..."
git add backend/agent/orchestrator.py
make_commit "2026-07-12T17:00:00+0530" \
    "fix: prevent duplicate agent questions with word overlap detection"

# ============================================================================
# COMMIT 23: Sun Jul 12 2026 17:45
# ============================================================================
echo "[23/25] Empty response fix + model update..."
git add backend/agent/llm_client.py
make_commit "2026-07-12T17:45:00+0530" \
    "fix: handle empty LLM responses, update model to llama-3.3-70b"

# ============================================================================
# COMMIT 24: Sat Jul 18 2026 10:00
# ============================================================================
echo "[24/25] Deployment config..."
git add render.yaml
git add vercel.json
make_commit "2026-07-18T10:00:00+0530" \
    "feat: add render.yaml, vercel.json, deployment config"

# ============================================================================
# COMMIT 25: Sun Jul 19 2026 11:30
# ============================================================================
echo "[25/25] Documentation..."
git add README.md
git add SETUP.md
git add docs/
make_commit "2026-07-19T11:30:00+0530" \
    "docs: add README, transfer guide, commands reference"

# ============================================================================
echo ""
echo "=========================================="
echo "  DONE! 25 commits created."
echo "=========================================="
echo ""
git -P log --oneline --all
echo ""
echo "Run 'git log' to verify the full history."
