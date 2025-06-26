import asyncio
import json
from typing import Dict, List, Tuple, Optional, Any
import time
import requests
from requests.models import Response
from common import get_redis, get_supabase, WARNING_QUEUE
from dotenv import load_dotenv
import os
import traceback
import logging

load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


GITHUB_ENDPOINT = "https://api.github.com/events?per_page=100&page=2"
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")
LAST_EVENT_ID_KEY = "last_processed_event_id"

DEFAULT_BRANCHES = {"refs/heads/main", "refs/heads/master"}
LARGE_PUSH_THRESHOLD = 100


def should_flag_event(event: Dict[str, Any]) -> Tuple[bool, str]:
    """
    Inspect a single GitHub Events API event object and return a list
    of text warnings describing potentially risky activity.

    Parameters
    ----------
    event : dict
        An event exactly as returned by GET /events, /orgs/:org/events, etc.

    Returns
    -------
    List[str]
        Zero or more warning strings.
    """
    etype = event.get("type")
    payload = event.get("payload", {})
    warning_type = ""

    # ---------- PushEvent checks ----------
    if etype == "PushEvent":  # push event :contentReference[oaicite:6]{index=6}
        ref = payload.get("ref")
        size = payload.get(
            "size", 0
        )  # size field :contentReference[oaicite:7]{index=7}
        if ref in DEFAULT_BRANCHES:
            warning_type = "Push to default branch"
        if isinstance(size, int) and size > LARGE_PUSH_THRESHOLD:
            warning_type = "Large push to default branch"

    # ---------- DeleteEvent checks ----------
    elif etype == "DeleteEvent":  # delete event :contentReference[oaicite:8]{index=8}
        if payload.get("ref_type") == "branch":
            if payload.get("ref") in {"main", "master"}:
                warning_type = "Default branch deleted"

    # ---------- PublicEvent checks ----------
    elif (
        etype == "PublicEvent"
    ):  # repo made public :contentReference[oaicite:9]{index=9}
        warning_type = "Repository visibility changed to public"

    # ---------- MemberEvent checks ----------
    elif (
        etype == "MemberEvent"
    ):  # collaborator changes :contentReference[oaicite:10]{index=10}
        if payload.get("action") == "added":
            warning_type = "New collaborator added"

    # to ensure a feed of events appears on the frontend, we add some dummy events
    if int(event.get("id", "0")) % 15 == 0:
        warning_type = "Dummy warning"

    logging.info(f"Warning type: {warning_type}")

    return warning_type != "", warning_type


def make_github_request(
    url: str, headers: Dict[str, str], backoff_time: float = 1.0
) -> Optional[Response]:
    """
    Make a request to the GitHub Events API with exponential backoff.

    Args:
        url: GitHub API endpoint URL
        headers: Request headers including auth token
        backoff_time: Current backoff time in seconds

    Returns:
        Response object if successful, None if 304 Not Modified
    """
    logger.info(f"Making GitHub API request to: {url}")

    while True:
        try:
            response = requests.get(url, headers=headers)

            if response.status_code == 304:
                logger.info("No new events (304 Not Modified)")
                return None

            if response.status_code in (403, 503):
                logger.warning(
                    f"Rate limited or service unavailable ({response.status_code}), backing off for {backoff_time}s"
                )
                time.sleep(backoff_time)
                backoff_time *= 2
                continue

            logger.info(f"Successfully fetched events (status: {response.status_code})")
            return response

        except requests.exceptions.RequestException as e:
            logger.error(f"Request failed: {e}, backing off for {backoff_time}s")
            time.sleep(backoff_time)
            backoff_time *= 2


def process_events(
    events: List[Dict], last_processed_id: str
) -> Tuple[List[Dict], bool]:
    """
    Process GitHub events and check for flagged events.

    Args:
        events: List of GitHub event objects
        last_processed_id: ID of last processed event from previous run

    Returns:
        Tuple containing:
            - List of flagged events
            - Boolean indicating if last_processed_id was found
    """
    logger.info(
        f"Processing {len(events)} events, looking for last_processed_id: {last_processed_id}"
    )

    flagged_events = []
    found_last_id = False

    for event in events:
        event_id = event.get("id")

        # Log event to file for debugging/monitoring
        with open("events.txt", "a") as f:
            f.write(f"{json.dumps(event)}\n")

        if event_id == last_processed_id:
            logger.info(f"Found last processed event ID: {event_id}")
            found_last_id = True
            break

        should_flag, warning_type = should_flag_event(event)
        if should_flag:
            logger.info(f"Flagged event {event_id} as: {warning_type}")
            flagged_events.append((event, warning_type))

    logger.info(f"Found {len(flagged_events)} flagged events")
    return flagged_events, found_last_id


def poll_github_events(
    api_url: str, headers: Dict[str, str], last_processed_id: str
) -> Tuple[List[Dict], str]:
    """
    Poll GitHub Events API and collect flagged events.

    Args:
        api_url: GitHub Events API URL
        headers: Request headers including auth token
        last_processed_id: ID of last processed event from previous run

    Returns:
        List of flagged events
    """
    logger.info(f"Starting GitHub events poll, last_processed_id: {last_processed_id}")
    all_flagged_events = []

    # Make initial request
    response = make_github_request(api_url, headers)
    if not response:
        logger.info("No response from GitHub API, ending poll")
        return all_flagged_events

    # Extract poll interval from response headers
    poll_interval = int(response.headers.get("X-Poll-Interval", 60))
    logger.info(f"GitHub API poll interval: {poll_interval}s")

    events = response.json()
    if not events:
        logger.info("No events returned from GitHub API")
        return all_flagged_events

    # Update last_processed_id to newest event
    new_last_id = events[0].get("id")
    logger.info(f"New last_processed_id will be: {new_last_id}")

    page_count = 1
    while True:
        logger.info(f"Processing page {page_count}")

        # Process current page of events
        flagged_events, found_last_id = process_events(events, last_processed_id)
        all_flagged_events.extend(flagged_events)

        if found_last_id:
            logger.info("Found last processed ID, stopping pagination")
            break

        with open("events.txt", "a") as f:
            f.write(f"NEW PAGE\n")

        # Get next page URL from Link header
        next_url = response.links.get("next", {}).get("url", "")
        if not next_url:
            logger.info("No more pages available")
            break

        # Request next page
        response = make_github_request(next_url, headers)
        if not response:
            break

        events = response.json()
        if not events:
            break

        page_count += 1

    # Remove duplicate events by tracking seen IDs
    seen_ids = set()
    unique_flagged_events = []

    for event in all_flagged_events:
        event_id = event[0].get("id")
        if event_id not in seen_ids:
            seen_ids.add(event_id)
            unique_flagged_events.append(event)

    logger.info(
        f"After deduplication: {len(unique_flagged_events)} unique flagged events"
    )
    return unique_flagged_events, new_last_id, poll_interval


def serialize_event_for_queue(
    warning_id: int, event: Dict[str, Any], warning_type: str
) -> str:
    """
    Serialize an event for the warning queue.
    """
    return json.dumps(
        {"warning_id": warning_id, "event_payload": event, "type": warning_type}
    )


async def poll_and_process_events(api_url: str, headers: dict) -> int:
    """
    Wrapper around poll_github_events that handles Redis state and processes flagged events.

    Args:
        api_url: GitHub Events API URL
        headers: Request headers including auth token
    """
    logger.info("Starting poll and process cycle")

    # Get Redis and Supabase clients
    redis = await get_redis()
    supabase = get_supabase()

    # Get last processed ID from Redis
    last_id = await redis.get("last_processed_event_id")
    last_id = int(last_id) if last_id else -1
    logger.info(f"Retrieved last_processed_id from Redis: {last_id}")

    # Poll GitHub events
    flagged_events, new_last_id, poll_interval = poll_github_events(
        api_url, headers, last_id
    )

    if not flagged_events:
        logger.info("No flagged events to process")
        return poll_interval

    logger.info(f"Processing {len(flagged_events)} flagged events in database")

    # Store new events and create warnings
    # Process events in batches of 1000
    batch_size = 1000
    for i in range(0, len(flagged_events), batch_size):
        batch = flagged_events[i : i + batch_size]
        logger.info(f"Processing batch {i//batch_size + 1} with {len(batch)} events")

        # Create batch of warning records
        warning_data = []
        for event in batch:
            warning_data.append(
                {
                    "event_payload": event[0],
                    "type": event[1],
                    "id": event[0].get("id"),
                    "actor_username": event[0].get("actor", {}).get("login", ""),
                    "repo_name": event[0].get("repo", {}).get("name", ""),
                    "org_name": event[0].get("org", {}).get("login", ""),
                }
            )

        # Insert batch into database
        result = (
            supabase.table("flagged_events")
            .upsert(warning_data, on_conflict="id", ignore_duplicates=True)
            .execute()
        )

        logger.info(
            f"Inserted {len(result.data) if result.data else 0} records into database"
        )

        # Process results and publish to Redis
        if result.data:
            for event in flagged_events:
                event_payload = event[0]
                warning_id = event_payload.get("id")
                message = serialize_event_for_queue(
                    warning_id,
                    event_payload,
                    event[1],
                )
                await redis.xadd(WARNING_QUEUE, {"message": message}, maxlen=10_000)

            logger.info(f"Added {len(flagged_events)} messages to Redis queue")

    # Update last processed ID in Redis
    if new_last_id:
        await redis.set("last_processed_event_id", str(new_last_id))
        logger.info(f"Updated last_processed_id in Redis to: {new_last_id}")

    logger.info(f"Poll cycle complete, next poll in {poll_interval}s")
    return poll_interval


# finally, we need to write a function which will be called from main to run the polling and processing function in a loop, sleeping for some duration between each run
async def run_poller():
    """
    Run the GitHub event poller in a continuous loop.
    """
    logger.info("Starting GitHub event poller")
    headers = {"Authorization": f"Bearer {GITHUB_TOKEN}"}

    while True:
        try:
            poll_interval = await poll_and_process_events(GITHUB_ENDPOINT, headers)
        except Exception as e:
            logger.error(f"Error during poll run: {e}")
            logger.error(traceback.format_exc())
            poll_interval = 60  # Default fallback interval

        logger.info(f"Sleeping for {poll_interval} seconds before next poll")
        await asyncio.sleep(poll_interval)


if __name__ == "__main__":
    asyncio.run(run_poller())
