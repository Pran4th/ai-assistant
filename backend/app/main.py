from fastapi import FastAPI, Depends, HTTPException, WebSocket, WebSocketDisconnect, Header
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import json
from typing import Optional

from app.config import settings
from app.auth.google_oauth import get_current_user, get_auth_url, handle_callback
from app.core.llm_engine import LLMEngine
from app.core.conversation import ConversationManager
from app.tools.calendar import CalendarTool
from app.tools.tasks import TasksTool
from app.tools.gmail import GmailTool
from app.tools.contacts import ContactsTool
from app.models.schemas import (
    ChatRequest, ChatResponse, VoiceRequest, UserProfile, AuthResponse,
)

calendar_tool = CalendarTool()
tasks_tool = TasksTool()
gmail_tool = GmailTool()
contacts_tool = ContactsTool()
conversation_manager = ConversationManager()
llm_engine = LLMEngine()


@asynccontextmanager
async def lifespan(app: FastAPI):
    await llm_engine.initialize()
    yield
    await llm_engine.shutdown()


app = FastAPI(
    title="AI Personal Assistant",
    description="AI-powered assistant for Google Workspace",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/auth/google")
async def google_auth():
    return {"auth_url": get_auth_url()}


@app.get("/auth/callback")
async def auth_callback(code: str):
    tokens = await handle_callback(code)
    from fastapi.responses import RedirectResponse
    import urllib.parse
    frontend_url = settings.FRONTEND_URL
    params = urllib.parse.urlencode({
        "token": tokens["access_token"],
        "user": urllib.parse.quote(json.dumps(tokens["user"])),
    })
    return RedirectResponse(url=f"{frontend_url}?{params}")


@app.post("/api/chat", response_model=ChatResponse)
async def chat_endpoint(
    request: ChatRequest,
    authorization: str = Header(None),
):
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing authorization header")
    user = await get_current_user(authorization)

    try:
        context = await conversation_manager.get_context(user.id)
        result = await llm_engine.process_command(
            message=request.message,
            context=context,
            user=user,
            tools=[calendar_tool, tasks_tool, gmail_tool, contacts_tool],
        )
        await conversation_manager.update_context(
            user_id=user.id,
            message=request.message,
            response=result.response,
        )

        return ChatResponse(
            response=result.response,
            action_taken=result.action,
            data=result.data,
            follow_up_needed=result.follow_up_needed,
            suggested_questions=result.suggestions,
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Processing error: {str(e)}")


@app.post("/api/voice")
async def voice_endpoint(
    request: VoiceRequest,
    authorization: str = Header(None),
):
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing authorization header")
    user = await get_current_user(authorization)

    if request.audio_data:
        transcription = await llm_engine.transcribe_audio(request.audio_data)
        text_input = transcription
    else:
        text_input = request.text

    chat_request = ChatRequest(message=text_input)
    return await chat_endpoint(chat_request, authorization)


@app.websocket("/ws/chat")
async def websocket_chat(
    websocket: WebSocket,
    token: str,
):
    await websocket.accept()

    try:
        user = await get_current_user(f"Bearer {token}")

        while True:
            message = await websocket.receive_text()
            data = json.loads(message)

            result = await llm_engine.process_command(
                message=data["message"],
                context=await conversation_manager.get_context(user.id),
                user=user,
                tools=[calendar_tool, tasks_tool, gmail_tool, contacts_tool],
            )

            await conversation_manager.update_context(
                user_id=user.id,
                message=data["message"],
                response=result.response,
            )

            await websocket.send_json({
                "type": "response",
                "content": result.response,
                "action": result.action,
                "data": result.data,
            })

            if result.follow_up_needed:
                await websocket.send_json({
                    "type": "clarification",
                    "question": result.clarification_question,
                })

    except WebSocketDisconnect:
        pass
    except Exception as e:
        try:
            await websocket.send_json({"type": "error", "message": str(e)})
        except Exception:
            pass


@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "services": {
            "llm": llm_engine.is_ready(),
            "calendar": calendar_tool.is_ready(),
            "tasks": tasks_tool.is_ready(),
            "gmail": gmail_tool.is_ready(),
            "contacts": contacts_tool.is_ready(),
        },
    }
