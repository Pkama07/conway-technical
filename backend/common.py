import os
from typing import Optional
from supabase import create_client, Client
from redis import asyncio as aioredis
from fastapi import HTTPException, status

# redis key for the warning queue
WARNING_QUEUE = "warning_queue"

# supabase singleton
_supabase_client: Optional[Client] = None


def get_supabase() -> Client:
    global _supabase_client

    if _supabase_client is None:
        url = os.environ.get("SUPABASE_URL")
        key = os.environ.get("SUPABASE_SERVICE_KEY")

        if not url or not key:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Supabase credentials not configured",
            )

        _supabase_client = create_client(url, key)

    return _supabase_client


# redis singleton
_redis_client: Optional[aioredis.Redis] = None


async def get_redis() -> aioredis.Redis:
    global _redis_client

    if _redis_client is None:
        redis_url = os.environ.get("REDIS_URL", "redis://localhost:6379")
        _redis_client = await aioredis.Redis.from_url(redis_url)

    return _redis_client
