from google_auth_oauthlib.flow import Flow
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from app.config import settings
from app.models.schemas import UserProfile
import httpx
import json
import asyncio

SCOPES = [
    "https://www.googleapis.com/auth/calendar",
    "https://www.googleapis.com/auth/tasks",
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/gmail.modify",
    "https://www.googleapis.com/auth/contacts",
    "openid",
    "https://www.googleapis.com/auth/userinfo.email",
    "https://www.googleapis.com/auth/userinfo.profile",
]

# In-memory credential store (falls back if Redis unavailable)
_creds_store: dict = {}

async def _get_redis():
    try:
        import redis.asyncio as redis
        r = redis.from_url(
            settings.redis_connection_url,
            decode_responses=True,
            socket_connect_timeout=2,
        )
        await r.ping()
        return r
    except Exception:
        return None


def get_auth_url() -> str:
    flow = Flow.from_client_config(
        {
            "web": {
                "client_id": settings.GOOGLE_CLIENT_ID,
                "client_secret": settings.GOOGLE_CLIENT_SECRET,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": [settings.GOOGLE_REDIRECT_URI],
            }
        },
        scopes=SCOPES,
    )
    flow.redirect_uri = settings.GOOGLE_REDIRECT_URI
    auth_url, _ = flow.authorization_url(
        access_type="offline",
        include_granted_scopes="true",
        prompt="consent",
    )
    return auth_url


async def handle_callback(code: str) -> dict:
    flow = Flow.from_client_config(
        {
            "web": {
                "client_id": settings.GOOGLE_CLIENT_ID,
                "client_secret": settings.GOOGLE_CLIENT_SECRET,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": [settings.GOOGLE_REDIRECT_URI],
            }
        },
        scopes=SCOPES,
    )
    flow.redirect_uri = settings.GOOGLE_REDIRECT_URI
    flow.fetch_token(code=code)

    credentials = flow.credentials
    user_info = await _get_user_info(credentials.token)

    user_id = user_info["id"]
    user_email = user_info["email"]
    user_name = user_info["name"]
    user_picture = user_info.get("picture")

    creds_data = {
        "token": credentials.token,
        "refresh_token": credentials.refresh_token,
        "client_id": settings.GOOGLE_CLIENT_ID,
        "client_secret": settings.GOOGLE_CLIENT_SECRET,
        "scopes": list(credentials.scopes),
    }

    await _store_credentials(user_id, creds_data)

    from app.auth.jwt_handler import create_access_token
    token = create_access_token(
        data={
            "sub": user_id,
            "email": user_email,
            "name": user_name,
        }
    )

    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "id": user_id,
            "email": user_email,
            "name": user_name,
            "picture": user_picture,
        },
        "credentials": creds_data,
    }


async def refresh_credentials(credentials: dict) -> dict:
    creds = Credentials(
        token=credentials["token"],
        refresh_token=credentials.get("refresh_token"),
        token_uri="https://oauth2.googleapis.com/token",
        client_id=credentials["client_id"],
        client_secret=credentials["client_secret"],
        scopes=credentials["scopes"],
    )
    request = Request()
    creds.refresh(request)
    return {
        **credentials,
        "token": creds.token,
    }


async def _get_user_info(access_token: str) -> dict:
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            "https://www.googleapis.com/oauth2/v2/userinfo",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        resp.raise_for_status()
        return resp.json()


async def _store_credentials(user_id: str, creds: dict):
    r = await _get_redis()
    if r:
        await r.set(f"creds:{user_id}", json.dumps(creds), ex=86400)
    else:
        _creds_store[user_id] = creds


async def _load_credentials(user_id: str) -> dict:
    r = await _get_redis()
    if r:
        data = await r.get(f"creds:{user_id}")
        if data:
            return json.loads(data)
    return _creds_store.get(user_id, {})


async def get_current_user(authorization: str) -> UserProfile:
    from app.auth.jwt_handler import decode_access_token
    payload = decode_access_token(authorization.replace("Bearer ", ""))
    user_id = payload["sub"]
    credentials = await _load_credentials(user_id)

    if credentials and credentials.get("token"):
        try:
            credentials = await refresh_credentials(credentials)
            await _store_credentials(user_id, credentials)
        except Exception:
            pass

    return UserProfile(
        id=user_id,
        email=payload["email"],
        name=payload["name"],
        picture=payload.get("picture"),
        credentials=credentials,
    )
