# AI Debugging Agent — Setup Guide

## Prerequisites

| Requirement | Version | Install Command |
|---|---|---|
| Python | 3.11+ | [python.org/downloads](https://www.python.org/downloads/) |
| Node.js | 18+ | [nodejs.org](https://nodejs.org/) (LTS recommended) |
| npm | 9+ | Comes with Node.js |
| Git | 2.x | [git-scm.com](https://git-scm.com/) |

## Accounts Needed (All Free Tier, No Credit Card)

### 1. Groq (Primary LLM)

- **URL**: https://console.groq.com
- **Sign up**: Google/GitHub login
- **Free tier**: 30 requests/minute, 14,400 requests/day (Llama 3.1-8B)
- **Credit card required?** NO
- **Get API key**: Console → API Keys → Create API Key

### 2. Google AI Studio / Gemini (Fallback LLM)

- **URL**: https://aistudio.google.com/apikey
- **Sign up**: Google account
- **Free tier**: 15 requests/minute, 1,500 requests/day (Gemini Flash)
- **Credit card required?** NO
- **Get API key**: AI Studio → Get API Key → Create API Key

### 3. Render (Backend Hosting)

- **URL**: https://render.com
- **Sign up**: GitHub login
- **Free tier**: 750 hrs/month, auto-sleeps after 15 min inactivity
- **Credit card required?** NO
- **Note**: Cold starts take ~30s after sleeping

### 4. Vercel (Frontend Hosting)

- **URL**: https://vercel.com
- **Sign up**: GitHub login
- **Free tier**: Unlimited static deployments, 100 GB bandwidth/month
- **Credit card required?** NO

### 5. GitHub (Code Repository)

- **URL**: https://github.com
- **Free tier**: Unlimited public repos
- **Credit card required?** NO

---

## Local Development Setup

### Step 1: Clone and Navigate

```bash
git clone https://github.com/YOUR_USERNAME/ai-debugging-agent.git
cd ai-debugging-agent
```

### Step 2: Backend Setup

```bash
cd backend

# Create virtual environment
python -m venv venv

# Activate virtual environment
# macOS / Linux:
source venv/bin/activate
# Windows:
venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### Step 3: Backend Environment Variables

```bash
# Copy the example env file
cp .env.example .env

# Edit .env and add your actual API keys:
# GROQ_API_KEY=gsk_your_key_here
# GEMINI_API_KEY=your_key_here
# FRONTEND_URL=http://localhost:5173
```

### Step 4: Frontend Setup

```bash
cd ../frontend

# Install dependencies
npm install
```

### Step 5: Frontend Environment Variables

```bash
# Copy the example env file
cp .env.example .env

# Edit .env:
# VITE_API_URL=http://localhost:8000
```

### Step 6: Run Locally

**Terminal 1 — Backend:**
```bash
cd backend
source venv/bin/activate
uvicorn main:app --reload --port 8000
```

**Terminal 2 — Frontend:**
```bash
cd frontend
npm run dev
```

Frontend runs at http://localhost:5173, backend at http://localhost:8000.

---

## Environment Variables Reference

### Backend (`backend/.env`)

| Variable | Description | Example |
|---|---|---|
| `GROQ_API_KEY` | Groq API key (primary LLM) | `gsk_abc123...` |
| `GEMINI_API_KEY` | Google Gemini API key (fallback) | `AIza...` |
| `FRONTEND_URL` | Allowed CORS origin | `http://localhost:5173` |

### Frontend (`frontend/.env`)

| Variable | Description | Example |
|---|---|---|
| `VITE_API_URL` | Backend API base URL | `http://localhost:8000` |

> **Important**: All frontend env vars MUST use the `VITE_` prefix. Vite only exposes variables with this prefix to browser code.

---

## Verifying Setup

### Test Groq API Key

```bash
curl -X POST "https://api.groq.com/openai/v1/chat/completions" \
  -H "Authorization: Bearer $GROQ_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"model": "llama-3.1-8b-instant", "messages": [{"role": "user", "content": "Say hello"}], "max_tokens": 10}'
```

Expected: JSON response with a greeting.

### Test Gemini API Key

```bash
curl "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key=$GEMINI_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"contents": [{"parts": [{"text": "Say hello"}]}]}'
```

Expected: JSON response with a greeting.

### Test Backend Health

```bash
# With backend running:
curl http://localhost:8000/health
```

Expected: `{"status": "ok"}`

---

## Line Endings

This project enforces LF line endings on all platforms via `.gitattributes`:

```
* text=auto eol=lf
```

If you're on Windows and see CRLF warnings, run:
```bash
git config core.autocrlf input
```

---

## Troubleshooting

| Problem | Solution |
|---|---|
| `ModuleNotFoundError` | Activate venv: `source venv/bin/activate` |
| CORS errors in browser | Check `FRONTEND_URL` in backend `.env` matches your frontend URL |
| Groq 429 (rate limit) | Wait 60s, or check daily quota at console.groq.com |
| `VITE_API_URL` undefined in browser | Restart `npm run dev` after changing `.env` |
| Monaco editor blank | Clear browser cache, check console for load errors |
| Render cold start slow | First request after 15min idle takes ~30s — this is normal on free tier |

---

## Cost Summary

| Service | Free Tier Limit | Credit Card? |
|---|---|---|
| Groq | 14,400 req/day | NO |
| Gemini Flash | 1,500 req/day | NO |
| Render | 750 hrs/month | NO |
| Vercel | 100 GB bandwidth | NO |
| GitHub | Unlimited public | NO |

**Total cost: $0.00** — No service in this stack requires a credit card.
