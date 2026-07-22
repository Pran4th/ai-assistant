# AI Personal Assistant

AI-powered personal assistant for Google Workspace with voice and text input.

## Features

- **Google Calendar**: Create, read, update, delete events
- **Google Tasks**: Create, read, update, delete tasks
- **Voice Input**: Web Speech API integration
- **Smart Clarification**: Asks follow-up questions for ambiguous requests
- **Real-time Chat**: WebSocket support for live conversations
- **OAuth2 Security**: Secure Google authentication

## Architecture

```
User -> Frontend (Vue3) -> FastAPI -> LLM Engine (GPT-4) -> Google APIs
                              |
                         Redis (Session)
```

## Local Setup Guide

### Prerequisites

Install these on your machine first:

| Tool | Version | Check Command |
|------|---------|---------------|
| Python | 3.11+ | `python --version` |
| Node.js | 18+ | `node --version` |
| npm | 9+ | `npm --version` |
| Redis | 7+ | `redis-server --version` |

### Step 1: Google Cloud Setup

You need Google OAuth credentials for Calendar and Tasks APIs:

1. Go to [Google Cloud Console](https://console.cloud.google.com)
2. Create a new project (or select existing)
3. Go to **APIs & Services > Library**
4. Enable these APIs:
   - **Google Calendar API**
   - **Google Tasks API**
5. Go to **APIs & Services > Credentials**
6. Click **Create Credentials > OAuth client ID**
   - Application type: **Web application**
   - Name: `AI Assistant Dev`
   - Authorized redirect URIs: `http://localhost:8000/auth/callback`
7. Click **Create** and copy the **Client ID** and **Client Secret**

### Step 2: Environment Configuration

```bash
# Clone / navigate to the project
cd ai-assistant

# Copy environment file
cp .env.example .env
```

Edit `.env` with your credentials. The `.env` file is pre-filled with your Google OAuth credentials and a generated secret key — just add an OpenAI key if you have one:

```env
SECRET_KEY=your-generated-secret-key
GOOGLE_CLIENT_ID=your-client-id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=your-client-secret
OPENAI_API_KEY=         # Leave empty to use Groq instead
GROQ_API_KEY=gsk_...    # Free LLM provider — get at https://console.groq.com/keys
```

> **No OpenAI key?** No problem! The `.env` already has a **Groq API key** configured — it's a free, fast LLM provider (Llama 3 70B). The app will use Groq automatically. If both are empty, it falls back to **offline mode** (built-in intent router).

> To generate a SECRET_KEY: `python -c "import secrets; print(secrets.token_hex(32))"`

### Step 3: Start Redis

**Option A — Local install:**

```bash
# Windows (using WSL)
wsl redis-server

# macOS
brew services start redis

# Linux
sudo systemctl start redis
```

**Option B — Docker (recommended for dev):**

```bash
docker run -d -p 6379:6379 --name redis-dev redis:7-alpine
```

Verify Redis is running:

```bash
redis-cli ping
# Should return: PONG
```

### Step 4: Start Backend (FastAPI)

```bash
cd backend

# Create virtual environment
python -m venv venv

# Activate it
# Windows:
venv\Scripts\activate
# macOS / Linux:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Start the server (reload enabled for development)
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

The API will be available at **http://localhost:8000**

- Interactive docs: http://localhost:8000/docs
- Health check: http://localhost:8000/health
- OpenAPI spec: http://localhost:8000/openapi.json

### Step 5: Start Frontend (Vue 3)

Open a **new terminal** (keep backend running):

```bash
cd frontend

# Install dependencies
npm install

# Start dev server
npm run dev
```

The frontend will be available at **http://localhost:5173**

The Vite dev server proxies `/api`, `/auth`, `/ws`, and `/health` to the backend automatically.

### Step 6: Verify Everything Works

1. Open **http://localhost:5173** in your browser
2. Click **"Sign in with Google"** — you'll be redirected to Google OAuth
3. After authorizing, you'll be redirected back to the chat interface
4. The connection status should show **"Connected"** (WebSocket)
5. Try commands like:
   - *"Show my events for today"*
   - *"Create a meeting tomorrow at 2pm"*
   - *"Add a task to buy groceries"*
   - *"What's on my calendar this week?"*

### Troubleshooting

| Problem | Fix |
|---------|-----|
| OAuth redirect error | Ensure `GOOGLE_REDIRECT_URI` in `.env` matches exactly what's in Google Cloud Console |
| Redis connection refused | Start Redis first — see Step 3 |
| OpenAI API errors | Verify `OPENAI_API_KEY` is set correctly in `.env` |
| Port already in use | Kill existing processes: `lsof -i :8000` (macOS/Linux) or `netstat -ano | findstr :8000` (Windows) |
| CORS errors | Check `CORS_ORIGINS` in `.env` includes `http://localhost:5173` |
| Module not found | Ensure virtual env is activated and `pip install -r requirements.txt` ran successfully |

### Alternative: Docker (Full Stack)

```bash
# From the project root
docker-compose up --build

# This starts all 3 services:
#   - Backend API on http://localhost:8000
#   - Frontend on http://localhost:80
#   - Redis on port 6379
```

To stop: `docker-compose down`

## Project Structure

```
ai-assistant/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI entry point
│   │   ├── config.py            # Configuration from .env
│   │   ├── auth/                # Google OAuth + JWT
│   │   ├── core/                # LLM engine, intent router, conversation
│   │   ├── tools/               # Calendar, Tasks, Gmail integrations
│   │   ├── models/              # Pydantic schemas
│   │   └── utils/               # Helpers
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── components/          # ChatInterface, VoiceInput, AuthButton
│   │   ├── stores/              # Auth state
│   │   └── services/            # API client
│   ├── Dockerfile
│   ├── nginx.conf
│   └── package.json
├── docker-compose.yml
├── .env / .env.example
└── README.md
```

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| /auth/google | GET | Initiate OAuth |
| /auth/callback | GET | OAuth callback |
| /api/chat | POST | Text command |
| /api/voice | POST | Voice command |
| /ws/chat | WS | Real-time chat |
| /health | GET | Health check |
