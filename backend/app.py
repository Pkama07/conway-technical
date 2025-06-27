import asyncio
import json
import logging
import os
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel

from fastapi import Depends, FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from sse_starlette.sse import EventSourceResponse
from supabase import Client
from dotenv import load_dotenv
from common import get_supabase, get_redis
from common import WARNING_QUEUE
from openai import OpenAI

load_dotenv()

# Singleton pattern for OpenAI client using global variable
_openai_client = None


def get_openai_client() -> OpenAI:
    global _openai_client
    if _openai_client is None:
        _openai_client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
    return _openai_client


# fastapi setup
app = FastAPI(title="GitHub Events Monitor", version="1.0.0")
origins = [os.environ.get("FRONTEND_ORIGINS")]
if origins == [None]:
    origins = ["*"]
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
        query = supabase.table("flagged_events").select("*")
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


class Analysis(BaseModel):
    root_cause: List[str]
    impact: List[str]
    next_steps: List[str]


async def analyze_warning(warning_type: str, payload: dict, warning_id: int) -> dict:
    """
    Analyze a warning and return analysis results using OpenAI.

    Args:
        warning_type: Type of warning
        payload: Warning payload data
        warning_id: ID of the warning

    Returns:
        Dict containing original payload and AI analysis
    """
    client = get_openai_client()

    # Construct the comprehensive prompt
    prompt = f"""You are a GitHub security and DevOps expert analyzing repository events that may pose risks. 

You will be given a warning type and the corresponding GitHub event payload. Analyze the event and provide your assessment in the structured format.

Warning Type: {warning_type}
Event Payload: {json.dumps(payload, indent=2)}

Analysis Guidelines:

For "Push to default branch":
- Focus on code quality, security implications, and deployment risks
- Consider commit frequency, author patterns, and file changes
- Assess potential for breaking changes or security vulnerabilities

For "Large push to default branch":
- Emphasize the risks of large code changes
- Consider review process gaps and testing coverage
- Focus on coordination and change management issues

For "Default branch deleted":
- This is a critical security incident
- Focus on data loss, malicious activity, and recovery procedures
- Emphasize immediate containment and investigation needs

For "Repository visibility changed to public":
- Critical security concern about exposed sensitive data
- Focus on intellectual property, credentials, and compliance risks
- Emphasize immediate assessment and remediation

For "New collaborator added":
- Focus on access control and insider threat risks
- Consider vetting processes and principle of least privilege
- Assess potential for unauthorized access or data exfiltration

For "Dummy warning":
- Generate realistic but varied security/DevOps concerns
- Create plausible scenarios that could affect any development team
- Focus on common issues like dependency vulnerabilities, configuration drift, or process gaps

Instructions:
- In your descriptions, include payload specific information; use the names of the actor, repo, and branch where applicable
- Provide 2-4 specific, actionable root causes
- List 2-4 concrete impacts that could affect the organization
- Suggest 3-5 specific, prioritized next steps
- Be concise but informative
- Focus on practical, real-world concerns
- Avoid generic responses - tailor to the specific event type and payload details when available"""

    try:
        response = client.responses.parse(
            model="gpt-4o-mini",
            input=[{"role": "user", "content": prompt}],
            text_format=Analysis,
        )

        analysis: Analysis = response.output_parsed

        return {
            "payload": payload,
            "analysis": {
                "root_cause": analysis.root_cause,
                "impact": analysis.impact,
                "next_steps": analysis.next_steps,
            },
            "warning_id": warning_id,
            "warning_type": warning_type,
            "is_ping": False,
        }

    except Exception as e:
        print(e)
        # Fallback to mock data if OpenAI fails
        mock_analysis = {
            "root_cause": ["Analysis service temporarily unavailable"],
            "impact": ["Unable to assess risk level"],
            "next_steps": ["Retry analysis", "Manual review recommended"],
        }

        return {
            "payload": payload,
            "analysis": mock_analysis,
            "warning_id": warning_id,
            "warning_type": warning_type,
            "is_ping": False,
        }


async def stream_reader(request: Request):
    """
    Yield new messages forever without popping from the queueu.
    """
    redis = await get_redis()
    supabase = get_supabase()
    last_id = "0-0"

    while True:

        if await request.is_disconnected():
            break

        results = await redis.xread(
            {WARNING_QUEUE: last_id},
            count=1,
            block=500,
        )

        try:
            if results:
                ((_, entries),) = results
                last_id, fields = entries[0]
                data = json.loads(fields[b"message"].decode())
                analysis = await analyze_warning(
                    data["type"], data["event_payload"], data["warning_id"]
                )
                supabase.table("flagged_events").update(
                    {
                        "root_cause": analysis["analysis"]["root_cause"],
                        "impact": analysis["analysis"]["impact"],
                        "next_steps": analysis["analysis"]["next_steps"],
                        "has_been_processed": True,
                    }
                ).eq("id", data["warning_id"]).execute()
                response = json.dumps(analysis)
                yield f"{response}"
            else:
                response = {"is_ping": True}
                yield f"{json.dumps(response)}"
        except Exception as e:
            logging.error(e)
            yield f"error: {str(e)}"


@app.get("/stream")
async def stream(request: Request):
    return EventSourceResponse(stream_reader(request), media_type="text/event-stream")


@app.get("/health")
async def health():
    """Simple health check endpoint."""
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}
