import json
from typing import List, Dict
import redis.asyncio as redis
from app.config import settings


class ConversationManager:
    def __init__(self):
        self.redis = redis.Redis(
            host=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
            decode_responses=True,
        )
        self.max_history = 10

    async def get_context(self, user_id: str) -> List[Dict]:
        key = f"conv:{user_id}"
        history = await self.redis.lrange(key, 0, -1)
        return [json.loads(h) for h in history] if history else []

    async def update_context(self, user_id: str, message: str, response: str):
        key = f"conv:{user_id}"
        await self.redis.rpush(
            key,
            json.dumps({"role": "user", "content": message}),
            json.dumps({"role": "assistant", "content": response}),
        )
        await self.redis.ltrim(key, -self.max_history * 2, -1)
        await self.redis.expire(key, 86400)

    async def clear_context(self, user_id: str):
        key = f"conv:{user_id}"
        await self.redis.delete(key)
