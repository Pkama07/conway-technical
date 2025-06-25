import asyncio
import json
import os
from datetime import datetime
from typing import AsyncGenerator, List, Optional

from redis import asyncio as aioredis
from fastapi import Depends, FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from sse_starlette.sse import EventSourceResponse
from supabase import Client
from dotenv import load_dotenv
from backend.common import get_supabase, get_redis

load_dotenv()

# fastapi setup
app = FastAPI(title="GitHub Events Monitor", version="1.0.0")
origins = [os.environ.get("FRONTEND_ORIGINS")]
if origins == [None]:
    exit("FRONTEND_ORIGINS is not set")
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["GET"],
    allow_headers=["*"],
)


# endpoints
@app.get("/summary", response_model=dict)
async def list_summaries(
    since: Optional[int] = None, supabase: Client = Depends(get_supabase)
):
    """
    Get warnings from the database.

    Args:
        since: Unix timestamp to filter warnings created after this time
        supabase: Supabase client dependency

    Returns:
        List of warning records from the database
    """
    try:
        query = supabase.table("warnings").select("*")
        if since is not None:
            since_datetime = datetime.fromtimestamp(since).isoformat()
            query = query.gt("created_at", since_datetime)
        query = query.order("created_at", desc=True)

        response = query.execute()

        return {"data": response.data, "count": len(response.data)}

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch summaries: {str(e)}",
        )


async def redis_event_stream(
    request: Request, redis: aioredis.Redis
) -> AsyncGenerator[str, None]:
    """
    Yields JSON-serialized warnings each time the poller publishes one.
    Reads from Redis queue without popping (for streaming to frontend).
    """
    pubsub = redis.pubsub()
    await pubsub.subscribe("warning_channel")

    try:
        while True:
            if await request.is_disconnected():
                break

            message = await pubsub.get_message(
                ignore_subscribe_messages=True, timeout=1.0
            )

            if message and message["type"] == "message":
                try:
                    data = message["data"]
                    if isinstance(data, bytes):
                        data = data.decode("utf-8")
                    json.loads(data)  # ensure it's valid json
                    yield f"data: {data}\n\n"

                except (json.JSONDecodeError, UnicodeDecodeError) as e:
                    print(f"Error processing message: {e}")
                    continue

            await asyncio.sleep(0.01)  # yield

    finally:
        await pubsub.unsubscribe("warning_channel")
        await pubsub.close()


@app.get("/stream")
async def stream(request: Request, redis: aioredis.Redis = Depends(get_redis)):
    return EventSourceResponse(
        redis_event_stream(request, redis), media_type="text/event-stream"
    )


@app.get("/health")
async def health():
    """Simple health check endpoint."""
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}
