# AI Personal Assistant — Codebase Documentation

## 1. Architecture Overview

```
User (Browser)
    │
    ├─ Web Speech API (Voice Input)
    │
    ▼
┌──────────────────────────────────────────────────────────────┐
│  Frontend (Vue 3 + Vite)   localhost:5173                    │
│  ┌─────────────┐ ┌────────────┐ ┌──────────────────┐       │
│  │ ChatInterface│ │ VoiceInput │ │ AuthButton       │       │
│  │ (WebSocket)  │ │ (SpeechRec)│ │ (Google OAuth)   │       │
│  └─────────────┘ └────────────┘ └──────────────────┘       │
└──────────────────────────┬───────────────────────────────────┘
                           │ HTTP / WebSocket
                           ▼
┌──────────────────────────────────────────────────────────────┐
│  Backend (FastAPI + Uvicorn)   localhost:8000                │
│                                                              │
│  ┌──────────┐  ┌───────────┐  ┌─────────────────────────┐  │
│  │ Auth     │  │ LLMEngine │  │ ConversationManager     │  │
│  │ (JWT +   │  │ (Groq/    │  │ (Redis / in-memory)     │  │
│  │  OAuth2) │  │  OpenAI)  │  │                         │  │
│  └──────────┘  └─────┬─────┘  └─────────────────────────┘  │
│                      │                                       │
│         ┌────────────┼────────────┐                          │
│         ▼            ▼            ▼                          │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐                    │
│  │ Calendar │ │ Tasks    │ │ Gmail    │                    │
│  │ Tool     │ │ Tool     │ │ Tool     │                    │
│  └──────────┘ └──────────┘ └──────────┘                    │
│  ┌──────────┐                                                │
│  │ Contacts │                                                │
│  │ Tool     │                                                │
│  └──────────┘                                                │
└──────────────────────────────────────────────────────────────┘
                           │
                           ▼
                  Google APIs (REST)
                  Calendar / Tasks / Gmail / People
```

## 2. Request Lifecycle

### 2a. Text Command via WebSocket (Primary Path)

```
1. User types message in ChatInterface.vue
2. sendMessage() → ws.send(JSON.stringify({message}))
3. Backend WebSocket handler receives message
4. conversation_manager.get_context(user_id) → loads last 10 messages from Redis
5. llm_engine.process_command(message, context, user, tools) →
   a. If LLM provider (Groq/OpenAI) configured:
      - Calls LLM with tools/functions schema
      - If LLM returns tool_calls → executes them via _handle_tool_calls()
      - If LLM doesn't call tools → falls back to offline intent router
   b. If no LLM provider (offline mode):
      - IntentRouter classifies intent (e.g. "calendar_list_events")
      - Executes the corresponding tool function
      - Formats response
6. conversation_manager.update_context() → saves to Redis
7. Response sent back via WebSocket
8. ChatInterface.vue renders the response
```

### 2b. Voice Input

```
1. User clicks Voice button
2. VoiceInput.vue → new SpeechRecognition()
3. Browser captures audio and transcribes via Google's Web Speech API
4. onresult emits transcribed text
5. ChatInterface receives text → sends as regular message (same as 2a)
6. No backend transcription needed (client-side only)
```

### 2c. OAuth Authentication Flow

```
1. User clicks "Sign in with Google"
2. AuthButton.vue → fetch GET /auth/google
3. Backend returns Google OAuth consent URL
4. Browser redirects to Google consent screen
5. User authorizes Calendar + Tasks + Gmail + Contacts scopes
6. Google redirects to http://localhost:8000/auth/callback?code=...
7. Backend exchanges code for tokens (access_token + refresh_token)
8. Backend stores Google credentials in Redis (key: "creds:{user_id}")
9. Backend creates JWT with user info (sub, email, name)
10. Backend redirects browser to http://localhost:5173?token=JWT&user=...
11. Frontend stores JWT + user in localStorage
12. WebSocket connects using JWT as token parameter
```

## 3. File-by-File Breakdown

### Backend (`backend/app/`)

| File | Purpose | Key Components |
|------|---------|----------------|
| `main.py` | FastAPI entry point | REST endpoints, WebSocket handler, health check, lifespan |
| `config.py` | Environment config | Settings from `.env` via pydantic-settings |
| `auth/google_oauth.py` | Google OAuth2 + credential store | `get_auth_url()`, `handle_callback()`, `get_current_user()`, `refresh_credentials()`, Redis/in-memory credential store |
| `auth/jwt_handler.py` | JWT operations | `create_access_token()`, `decode_access_token()` |
| `core/llm_engine.py` | LLM orchestration + offline fallback | `LLMEngine` class: 14 function schemas, `_process_with_llm()`, `_process_offline()`, `_handle_tool_calls()`, response formatters |
| `core/intent_router.py` | Rule-based intent classification | `IntentRouter.classify()`: detects calendar/tasks/gmail/contacts intents, date/time/entity extraction, context awareness |
| `core/conversation.py` | Conversation history | Redis-backed context storage, 10-message history, 24hr expiry |
| `tools/calendar.py` | Google Calendar CRUD | `create_event()`, `list_events()`, `update_event()`, `delete_event()`, RFC 3339 date handling |
| `tools/tasks.py` | Google Tasks CRUD | `create_task()`, `list_tasks()`, `update_task()`, `delete_task()` |
| `tools/gmail.py` | Gmail operations | `list_inbox()`, `send_email()`, `search_emails()`, `get_email()`, `delete_email()` |
| `tools/contacts.py` | Google Contacts operations | `list_contacts()`, `search_contacts()`, `create_contact()` |
| `tools/base.py` | Abstract base class | `BaseTool` ABC |
| `models/schemas.py` | Pydantic models | `ChatRequest`, `ChatResponse`, `VoiceRequest`, `UserProfile`, `AuthResponse` |
| `utils/helpers.py` | Utility functions | `parse_relative_date()`, `parse_time()`, `sanitize_input()` |

### Frontend (`frontend/src/`)

| File | Purpose | Key Components |
|------|---------|----------------|
| `components/ChatInterface.vue` | Main chat UI | WebSocket connection, message rendering, suggestion buttons, confirmation dialogs, typing indicator |
| `components/VoiceInput.vue` | Voice button | Web Speech API, error handling (not-allowed, no-speech, network), recording animation |
| `components/AuthButton.vue` | Auth UI | Google sign-in, user avatar, logout, URL token extraction |
| `stores/auth.js` | Auth state | Reactive store with localStorage persistence |
| `services/api.js` | REST client | Auto-inject JWT, error handling |
| `App.vue` | Root component | Auth-gated view switching |

## 4. Tool Architecture

### Tool Index Mapping
```
tools[0] = CalendarTool    (indices 0-3 in schemas)
tools[1] = TasksTool       (indices 4-7 in schemas)
tools[2] = GmailTool       (indices 8-10 in schemas)
tools[3] = ContactsTool    (indices 11-13 in schemas)
```

### How Tools Execute
```
1. IntentRouter.classify() → returns IntentResult { intent, entities, confidence, requires_clarification }
2. _process_offline() maps intent → (function, formatter) pair
3. Tool function called with: {**entities, credentials: user.credentials}
4. Response formatter converts raw API response to readable text
```

## 5. LLM Providers

| Provider | Model | Key Required | Notes |
|----------|-------|-------------|-------|
| OpenAI | gpt-4-turbo-preview | `OPENAI_API_KEY` | Full function calling, best reliability |
| Groq | llama-3.3-70b-versatile | `GROQ_API_KEY` | Free, fast inference, sometimes doesn't call tools |
| Offline | IntentRouter only | None | Rule-based, works for all CRUD operations |

### Provider Selection Logic (`llm_engine.py:22-41`)
```
if OPENAI_API_KEY is set → use OpenAI
elif GROQ_API_KEY is set → use Groq
else → offline mode (IntentRouter only)
```

### Fallback Chain (`process_command`)
```
1. Try LLM (Groq/OpenAI) with function calling
2. If LLM returns tool_calls → execute tools, send results back to LLM for response generation
3. If LLM doesn't call tools → fall back to IntentRouter (_process_offline)
```

## 6. Credential Management

### Storage
- After OAuth: credentials stored in Redis (`creds:{user_id}`) with 24hr expiry
- Fallback: in-memory dict `_creds_store` if Redis unavailable

### Auto-Refresh
- Every request calls `get_current_user()` → `_load_credentials()` → `refresh_credentials()`
- If access token expired, uses refresh_token to get new one
- Updated credentials saved back to store

## 7. Intent Router Details

### Supported Intents (14 total)

| Intent | Trigger Words | Entities Extracted |
|--------|---------------|-------------------|
| `calendar_create_event` | create/add/new/schedule + meeting/event/appointment | start_time, end_time |
| `calendar_list_events` | list/show/what + event/meeting/calendar | start_date, end_date |
| `calendar_update_event` | update/change/modify + event/meeting | query |
| `calendar_delete_event` | delete/remove/cancel + event/meeting | query |
| `tasks_create` | add/create/new/make + task/todo | title |
| `tasks_list` | list/show/what + task/todo | none |
| `tasks_update` | update/change + task/todo | query |
| `tasks_delete` | delete/remove + task/todo | query |
| `gmail_list_inbox` | list/show/view + email/mail/inbox | query |
| `gmail_send_email` | send + email/mail | to, subject, body |
| `gmail_search_emails` | find/search + email/mail | query |
| `contacts_list` | list/show + contacts/people | none |
| `contacts_search` | find/search + contact/person | query |
| `contacts_create` | add/create + contact/person | name, email, phone |
| `greeting` | hi/hello/hey | none |
| `help` | help/what can you | none |

## 8. Error Handling Strategy

| Layer | Strategy | Example |
|-------|----------|---------|
| Google API auth | Auto-refresh tokens | `invalid_grant` → re-authenticate prompt |
| Google API calls | try/except with categorized errors | Rate limits → "Please wait", NotFound → "Not found" |
| LLM provider | Fallback to offline mode | Groq returns text instead of tool_calls → IntentRouter |
| Invalid operations | Entity validation before API call | Missing required params → clarification question |
| Frontend | Visible error messages | Voice: "Microphone denied", Chat: "Error: ..." |
| WebSocket disconnect | Auto-reconnect with 3s delay | Connection lost → retry with stored token |

## 9. OAuth Scopes Required

```
https://www.googleapis.com/auth/calendar        # Calendar CRUD
https://www.googleapis.com/auth/tasks            # Tasks CRUD
https://www.googleapis.com/auth/gmail.readonly   # Read emails
https://www.googleapis.com/auth/gmail.send       # Send emails
https://www.googleapis.com/auth/gmail.modify     # Delete emails
https://www.googleapis.com/auth/contacts         # Contacts CRUD
openid                                          # User identity
userinfo.email                                  # User email
userinfo.profile                                # User profile
```

## 10. Data Flow Diagrams

### Create Event Flow
```
User: "Schedule a meeting tomorrow at 3pm"
  → IntentRouter: calendar_create_event (confidence: 0.9)
  → Entities: { start_time: "2026-07-23T15:00:00", end_time: "2026-07-23T16:00:00" }
  → CalendarTool.create_event(summary="meeting", start_time=..., end_time=..., credentials=...)
  → Google Calendar API: POST /calendar/v3/calendars/primary/events
  → Response: { event_id: "...", summary: "meeting" }
  → Formatter: "Created event 'meeting' successfully!"
  → ConversationManager: save to Redis
  → WebSocket: send response to frontend
```

### Send Email Flow
```
User: "Send an email to John about the project"
  → IntentRouter: gmail_send_email (confidence: 0.85)
  → Entities: { to: "John", subject: "project" }
  → Requires clarification: "Who would you like to send the email to?"
  → User responds: "john@email.com"
  → Context: detects context_type=email_recipient
  → GmailTool.send_email(to="john@email.com", subject="project", body=...)
  → Google Gmail API: POST /gmail/v1/users/me/messages/send
  → Formatter: "Email sent to john@email.com"
```

## 11. Key Design Decisions

1. **Dual LLM + Rule Engine**: Using IntentRouter as fallback ensures reliability even when the LLM fails to call tools. The LLM handles complex/fuzzy requests, the rule engine handles precise CRUD.

2. **Client-side Speech Recognition**: Web Speech API runs in-browser, no server cost, works offline for transcription. Only needs internet for the speech service itself.

3. **Redis for State**: Conversation history + credentials in Redis with TTL. Falls back to in-memory dict for zero-dependency development.

4. **JWT for Auth, Redis for Credentials**: JWT stays small (just user info), Google tokens stored server-side for security and refresh capability.

5. **WebSocket Primary**: Real-time bidirectional communication. REST endpoints provided as fallback.

6. **Credential Store in google_oauth.py**: Co-located with OAuth logic for simplicity. Uses Redis with in-memory fallback.

## 12. Running Locally

```bash
# Terminal 1 - Redis (if using Docker)
docker run -d -p 6379:6379 redis:7-alpine

# Terminal 2 - Backend
cd backend
python -m venv venv
venv\Scripts\activate  # Windows
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000

# Terminal 3 - Frontend
cd frontend
npm install
npm run dev

# Open http://localhost:5173
```

### `.env` Configuration
```env
SECRET_KEY=your-jwt-secret
GOOGLE_CLIENT_ID=your-oauth-client-id
GOOGLE_CLIENT_SECRET=your-oauth-client-secret
OPENAI_API_KEY=         # Optional — set for OpenAI, leave blank for Groq
GROQ_API_KEY=gsk_...    # Optional — set for Groq, leave blank for offline
```
