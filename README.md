# AI Debugging Agent

A ReAct-based agentic AI system that autonomously debugs Python errors through hypothesis-elimination — like a doctor diagnosing a patient.

Paste your buggy Python code and traceback, and the agent generates hypotheses, runs static analysis tools (AST analyzer, linter, variable tracker), updates beliefs based on evidence, self-critiques its reasoning, and produces a root cause diagnosis with a concrete fix suggestion.

## Live Demo

> Coming soon — [https://ai-debug.vercel.app](https://ai-debug.vercel.app)

## Screenshots

| Dark Mode | Light Mode |
|---|---|
| ![Dark Mode](docs/screenshots/dark.png) | ![Light Mode](docs/screenshots/light.png) |

*Add screenshots after running the app locally*

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | React 18, Vite 6, Monaco Editor |
| Backend | FastAPI, Python 3.12, Uvicorn |
| Primary LLM | Groq (llama-3.3-70b-versatile) |
| Fallback LLM | Google Gemini (gemini-2.0-flash) |
| Static Analysis | Python ast module, flake8, custom variable tracker |
| Deployment | Render (backend), Vercel (frontend) |

## Architecture

```
Frontend (React + Monaco)
    │
    ├── POST /debug   → sends code + traceback
    ├── POST /answer  → sends user answer to agent question
    ├── GET /health   → status check
    │
    ▼
Backend (FastAPI)
    │
    ├── Error Parser        → regex-based traceback extraction
    ├── Hypothesis Generator → LLM generates 3-5 root cause candidates
    ├── ReAct Orchestrator  → Reason → Act → Observe → Update loop
    │   ├── AST Analyzer    → undefined names, unused vars, imports
    │   ├── Linter (flake8) → style/logic issues
    │   └── Variable Tracker → assignment/usage with line numbers
    ├── Belief Updater      → Bayesian probability adjustments
    ├── Self-Critique       → metacognition before concluding
    └── Conclusion Generator → LLM-powered fix suggestion
```

## Key Features

- **Autonomous debugging** — no human prompts needed between steps
- **Hypothesis-elimination** — 3-5 candidates ranked by probability, systematically tested
- **Tool-grounded reasoning** — runs real static analysis, not just LLM guessing
- **Bayesian belief updates** — probabilities adjusted based on tool evidence
- **Self-critique** — agent reviews its own reasoning before concluding
- **Confidence calibration** — honest about uncertainty (never claims 100%)
- **Graceful degradation** — template fallback if LLM unavailable
- **Dark/Light theme** — toggle persists across reloads

## Run Locally

### Prerequisites

- Python 3.11+ ([python.org](https://www.python.org/downloads/))
- Node.js 18+ ([nodejs.org](https://nodejs.org/))
- API keys: [Groq](https://console.groq.com) + [Google AI Studio](https://aistudio.google.com/apikey) (both free, no credit card)

### Mac / Linux

```bash
# Backend
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # Edit with your API keys
uvicorn main:app --reload --port 8000

# Frontend (new terminal)
cd frontend
npm install
npm run dev
```

### Windows (PowerShell)

```powershell
# Backend
cd backend
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
cp .env.example .env   # Edit with your API keys
uvicorn main:app --reload --port 8000

# Frontend (new terminal)
cd frontend
npm install
npm run dev
```

Open http://localhost:5173

## Deploy

### Backend → Render (free tier)

1. Push to GitHub
2. Render → New Web Service → connect repo
3. Root Directory: `backend`
4. Build: `pip install -r requirements.txt`
5. Start: `uvicorn main:app --host 0.0.0.0 --port $PORT`
6. Add env vars: `GROQ_API_KEY`, `GEMINI_API_KEY`, `FRONTEND_URL`

### Frontend → Vercel (free tier)

1. Vercel → Import repo
2. Framework: Vite, Root: `frontend`
3. Add env var: `VITE_API_URL` = your Render backend URL
4. Deploy

## Eval Results

| Metric | Value |
|---|---|
| Accuracy | 100% (16/16 completed) |
| Avg Iterations | 2.5 |
| Avg Confidence | 0.47 (conservative by design) |
| Error Types | NameError, TypeError, IndexError, AttributeError, Logic Bugs |

Run the eval yourself:
```bash
cd backend
source venv/bin/activate
python -m eval.run_eval --dry-run   # Validate cases
python -m eval.run_eval             # Full run (needs API keys)
```

## Project Structure

```
├── backend/
│   ├── main.py              # FastAPI app (4 endpoints)
│   ├── agent/               # ReAct orchestrator, LLM client, hypothesis gen, belief updater, self-critique, conclusion gen
│   ├── parsers/             # Error parser + Pydantic models
│   ├── tools/               # AST analyzer, linter, variable tracker
│   └── eval/                # 18 curated test cases + eval runner
├── frontend/
│   └── src/
│       ├── App.jsx          # State + API integration
│       └── components/      # CodeEditor, DebugPanel, HypothesisDisplay
├── docs/                    # Study guides, interview Q&A, comparisons
├── render.yaml              # Render deployment config
├── vercel.json              # Vercel deployment config
└── SETUP.md                 # Full setup guide
```

## Credits

Built by **Renu** as a portfolio project demonstrating:
- Agentic AI architecture (ReAct pattern)
- LLM integration with retry/fallback
- Static analysis tooling
- Full-stack development (FastAPI + React)
- Systematic evaluation methodology

## License

MIT
