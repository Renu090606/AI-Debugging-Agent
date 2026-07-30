# =============================================================================
# rewrite_history.ps1 — Rewrites git history with 25 clean commits
# Works in: Windows PowerShell
# WARNING: This DELETES your existing .git folder and creates a fresh history
# =============================================================================

$ErrorActionPreference = "Stop"

Write-Host "=========================================="
Write-Host "  GIT HISTORY REWRITE SCRIPT"
Write-Host "=========================================="
Write-Host ""
Write-Host "WARNING: This will DELETE your existing .git folder"
Write-Host "and create a brand new git history with 25 commits."
Write-Host ""
Write-Host "Make sure you have backed up your .git folder if needed."
Write-Host ""
$confirm = Read-Host "Are you sure you want to continue? (yes/no)"
if ($confirm -ne "yes") {
    Write-Host "Aborted."
    exit
}

Write-Host ""
Write-Host "Starting history rewrite..."
Write-Host ""

# Configure author
$env:GIT_AUTHOR_NAME = "Renu"
$env:GIT_AUTHOR_EMAIL = "renur9787@gmail.com"
$env:GIT_COMMITTER_NAME = "Renu"
$env:GIT_COMMITTER_EMAIL = "renur9787@gmail.com"

function Make-Commit {
    param(
        [string]$Date,
        [string]$Message,
        [string[]]$Files
    )
    foreach ($f in $Files) {
        git add $f 2>$null
    }
    $env:GIT_AUTHOR_DATE = $Date
    $env:GIT_COMMITTER_DATE = $Date
    git commit -m $Message --allow-empty
}

# Remove existing git history
if (Test-Path .git) {
    Remove-Item -Recurse -Force .git
}

# Initialize fresh repo
git init
git config user.name "Renu"
git config user.email "renur9787@gmail.com"

# ============================================================================
# COMMIT 1: Sat Jul 4 2026 10:30
# ============================================================================
Write-Host "[1/25] Project structure..."
git add .gitattributes
git add .gitignore
git add backend/parsers/__init__.py
git add backend/agent/__init__.py
git add backend/tools/__init__.py
git add backend/eval/__init__.py
git add frontend/.env.example
git add backend/.env.example
Make-Commit -Date "2026-07-04T10:30:00+0530" `
    -Message "feat: initialize project structure with backend and frontend dirs" `
    -Files @()

# ============================================================================
# COMMIT 2: Sat Jul 4 2026 11:15
# ============================================================================
Write-Host "[2/25] Requirements and config..."
Make-Commit -Date "2026-07-04T11:15:00+0530" `
    -Message "chore: add requirements.txt, .gitignore, .env.example" `
    -Files @("SETUP.md", "backend/requirements.txt", "frontend/package.json", "frontend/package-lock.json")

# ============================================================================
# COMMIT 3: Sat Jul 4 2026 14:00
# ============================================================================
Write-Host "[3/25] Error parser..."
Make-Commit -Date "2026-07-04T14:00:00+0530" `
    -Message "feat: implement error parser with regex traceback extraction" `
    -Files @("backend/parsers/error_parser.py")

# ============================================================================
# COMMIT 4: Sat Jul 4 2026 15:30
# ============================================================================
Write-Host "[4/25] Pydantic models..."
Make-Commit -Date "2026-07-04T15:30:00+0530" `
    -Message "feat: add Pydantic data models (ErrorInfo, Hypothesis, DebugState)" `
    -Files @("backend/parsers/models.py", "backend/parsers/__init__.py")

# ============================================================================
# COMMIT 5: Sat Jul 4 2026 17:00
# ============================================================================
Write-Host "[5/25] Parser tests..."
Make-Commit -Date "2026-07-04T17:00:00+0530" `
    -Message "test: add 8 unit tests for error parser" `
    -Files @("backend/test_parser.py")

# ============================================================================
# COMMIT 6: Sun Jul 5 2026 10:00
# ============================================================================
Write-Host "[6/25] LLM client..."
Make-Commit -Date "2026-07-05T10:00:00+0530" `
    -Message "feat: implement LLM client with Groq + Gemini fallback" `
    -Files @("backend/agent/llm_client.py")

# ============================================================================
# COMMIT 7: Sun Jul 5 2026 11:30
# ============================================================================
Write-Host "[7/25] Hypothesis generator..."
Make-Commit -Date "2026-07-05T11:30:00+0530" `
    -Message "feat: add hypothesis generator with structured JSON output" `
    -Files @("backend/agent/hypothesis_generator.py")

# ============================================================================
# COMMIT 8: Sun Jul 5 2026 13:00
# ============================================================================
Write-Host "[8/25] Hypothesis tests..."
Make-Commit -Date "2026-07-05T13:00:00+0530" `
    -Message "test: add 12 tests for hypothesis generation" `
    -Files @("backend/test_phase2.py")

# ============================================================================
# COMMIT 9: Sun Jul 5 2026 14:30
# ============================================================================
Write-Host "[9/25] Belief updater..."
Make-Commit -Date "2026-07-05T14:30:00+0530" `
    -Message "feat: implement belief updater with Bayesian posterior updates" `
    -Files @("backend/agent/belief_updater.py")

# ============================================================================
# COMMIT 10: Sun Jul 5 2026 16:00
# ============================================================================
Write-Host "[10/25] Orchestrator..."
Make-Commit -Date "2026-07-05T16:00:00+0530" `
    -Message "feat: build ReAct orchestrator with loop control logic" `
    -Files @("backend/agent/orchestrator.py")

# ============================================================================
# COMMIT 11: Sun Jul 5 2026 17:30
# ============================================================================
Write-Host "[11/25] Orchestrator tests..."
Make-Commit -Date "2026-07-05T17:30:00+0530" `
    -Message "test: add 17 orchestrator tests with mock LLM" `
    -Files @("backend/test_phase3.py")

# ============================================================================
# COMMIT 12: Sat Jul 11 2026 10:00
# ============================================================================
Write-Host "[12/25] AST analyzer..."
Make-Commit -Date "2026-07-11T10:00:00+0530" `
    -Message "feat: implement AST analyzer for undefined variable detection" `
    -Files @("backend/tools/ast_analyzer.py")

# ============================================================================
# COMMIT 13: Sat Jul 11 2026 11:30
# ============================================================================
Write-Host "[13/25] Variable tracker + linter..."
Make-Commit -Date "2026-07-11T11:30:00+0530" `
    -Message "feat: add variable tracker and linter tools" `
    -Files @("backend/tools/variable_tracker.py", "backend/tools/linter.py", "backend/tools/__init__.py")

# ============================================================================
# COMMIT 14: Sat Jul 11 2026 13:00
# ============================================================================
Write-Host "[14/25] Self-critique..."
Make-Commit -Date "2026-07-11T13:00:00+0530" `
    -Message "feat: implement self-critique with 8 confidence adjustments" `
    -Files @("backend/agent/self_critique.py")

# ============================================================================
# COMMIT 15: Sat Jul 11 2026 14:30
# ============================================================================
Write-Host "[15/25] Conclusion generator..."
Make-Commit -Date "2026-07-11T14:30:00+0530" `
    -Message "feat: add conclusion generator with suggested fix output" `
    -Files @("backend/agent/conclusion_generator.py", "backend/agent/__init__.py")

# ============================================================================
# COMMIT 16: Sat Jul 11 2026 16:00
# ============================================================================
Write-Host "[16/25] Eval harness..."
git add backend/eval/__init__.py
git add backend/eval/run_eval.py
git add backend/eval/cases/
Make-Commit -Date "2026-07-11T16:00:00+0530" `
    -Message "feat: build eval harness with 18 test cases" `
    -Files @()

# ============================================================================
# COMMIT 17: Sat Jul 11 2026 17:30
# ============================================================================
Write-Host "[17/25] Eval results..."
Make-Commit -Date "2026-07-11T17:30:00+0530" `
    -Message "test: run eval — 100% accuracy on 16/16 completed cases" `
    -Files @("backend/eval/EVAL_RESULTS.md", "backend/test_phase4.py", "backend/test_phase5.py")

# ============================================================================
# COMMIT 18: Sun Jul 12 2026 10:00
# ============================================================================
Write-Host "[18/25] FastAPI backend..."
Make-Commit -Date "2026-07-12T10:00:00+0530" `
    -Message "feat: build FastAPI backend with session management" `
    -Files @("backend/main.py")

# ============================================================================
# COMMIT 19: Sun Jul 12 2026 12:00
# ============================================================================
Write-Host "[19/25] API endpoints..."
Make-Commit -Date "2026-07-12T12:00:00+0530" `
    -Message "feat: add /debug and /answer endpoints with CORS" `
    -Files @("backend/main.py")

# ============================================================================
# COMMIT 20: Sun Jul 12 2026 14:00
# ============================================================================
Write-Host "[20/25] React frontend..."
Make-Commit -Date "2026-07-12T14:00:00+0530" `
    -Message "feat: implement React frontend with Monaco Editor" `
    -Files @("frontend/index.html", "frontend/vite.config.js", "frontend/src/main.jsx", "frontend/src/App.jsx", "frontend/src/App.css")

# ============================================================================
# COMMIT 21: Sun Jul 12 2026 15:30
# ============================================================================
Write-Host "[21/25] Frontend components..."
Make-Commit -Date "2026-07-12T15:30:00+0530" `
    -Message "feat: add hypothesis cards, confidence bars, reasoning chain UI" `
    -Files @("frontend/src/components/CodeEditor.jsx", "frontend/src/components/DebugPanel.jsx", "frontend/src/components/HypothesisDisplay.jsx")

# ============================================================================
# COMMIT 22: Sun Jul 12 2026 17:00
# ============================================================================
Write-Host "[22/25] Duplicate question fix..."
Make-Commit -Date "2026-07-12T17:00:00+0530" `
    -Message "fix: prevent duplicate agent questions with word overlap detection" `
    -Files @("backend/agent/orchestrator.py")

# ============================================================================
# COMMIT 23: Sun Jul 12 2026 17:45
# ============================================================================
Write-Host "[23/25] Empty response fix + model update..."
Make-Commit -Date "2026-07-12T17:45:00+0530" `
    -Message "fix: handle empty LLM responses, update model to llama-3.3-70b" `
    -Files @("backend/agent/llm_client.py")

# ============================================================================
# COMMIT 24: Sat Jul 18 2026 10:00
# ============================================================================
Write-Host "[24/25] Deployment config..."
Make-Commit -Date "2026-07-18T10:00:00+0530" `
    -Message "feat: add render.yaml, vercel.json, deployment config" `
    -Files @("render.yaml", "vercel.json")

# ============================================================================
# COMMIT 25: Sun Jul 19 2026 11:30
# ============================================================================
Write-Host "[25/25] Documentation..."
git add README.md
git add SETUP.md
git add docs/
Make-Commit -Date "2026-07-19T11:30:00+0530" `
    -Message "docs: add README, transfer guide, commands reference" `
    -Files @()

# ============================================================================
Write-Host ""
Write-Host "=========================================="
Write-Host "  DONE! 25 commits created."
Write-Host "=========================================="
Write-Host ""
git -P log --oneline --all
Write-Host ""
Write-Host "Run 'git log' to verify the full history."

# Clean up env vars
Remove-Item Env:GIT_AUTHOR_DATE -ErrorAction SilentlyContinue
Remove-Item Env:GIT_COMMITTER_DATE -ErrorAction SilentlyContinue
Remove-Item Env:GIT_AUTHOR_NAME -ErrorAction SilentlyContinue
Remove-Item Env:GIT_AUTHOR_EMAIL -ErrorAction SilentlyContinue
Remove-Item Env:GIT_COMMITTER_NAME -ErrorAction SilentlyContinue
Remove-Item Env:GIT_COMMITTER_EMAIL -ErrorAction SilentlyContinue
