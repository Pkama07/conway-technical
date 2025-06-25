import asyncio
import json
import os
from datetime import datetime
from typing import Optional

from fastapi import Depends, FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from sse_starlette.sse import EventSourceResponse
from supabase import Client
from dotenv import load_dotenv
from common import get_supabase, get_redis
from common import WARNING_QUEUE

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


async def stream_reader(request: Request):
    """
    Yield new messages forever without popping from the queueu.
    """
    redis = await get_redis()
    last_id = "0-0"

    while True:

        if await request.is_disconnected():
            break

        results = await redis.xread(
            {WARNING_QUEUE: last_id},
            count=1,
            block=500,
        )
        if results:
            ((_, entries),) = results
            last_id, fields = entries[0]
            data = fields[b"data"].decode()
            yield f"data: {data}\n\n"
        else:
            yield ": ping\n\n"


@app.get("/stream")
async def stream(request: Request):
    return EventSourceResponse(stream_reader(request), media_type="text/event-stream")


@app.get("/health")
async def health():
    """Simple health check endpoint."""
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}
