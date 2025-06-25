import asyncio
import json
from typing import Dict, List, Tuple, Optional, Any
import time
import requests
from requests.models import Response
from common import get_redis, get_supabase, WARNING_QUEUE
from dotenv import load_dotenv
import os

load_dotenv()


GITHUB_ENDPOINT = "https://api.github.com/events"
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")
LAST_EVENT_ID_KEY = "last_processed_event_id"


# we make a request every X-Poll-Interval seconds
# if we get a 304 not modified, the poll run ends
# if we get a 403 or 503, we employ exponential backoff
# in the response, we will receive an array of 100 events
# and in one of these events, we will hit the ID which corresponds to thte last event we processed on the previous
# iteration (if it's the first run, the last_id will be -1 or something, in which case we just terminate after the
# first 100)
# so a structure that makes sense is one function to make the request to github, receiving the entire response
# along with the link header, then passes the body of the response to a function which will parse through it and
# return the set of events which have been flagged
# this secondary function should accept the list of events and the last processed event ID, and should return the
# set of events which have been flagged along with a boolean indicating whether we hit the last processed event ID
# so prior to the running of the while loop, we make the request, mark the new "last_processed_id" (which will be
# the ID of the first event in our response), then assign the list of events to some variable. in the while loop,
# first we pass our list of events and old last processed id to the secondary function, append the flagged events to
# some overarching list, then we make a new request to teh link header of the response, process the response, and
# repopulate the list variable storing the events we need to process. if the return value of the secondary function
# indicates we have hit the last processed event ID, we terminate the while loop
def should_flag_event(event: Dict[str, Any]) -> bool:
    """
    Determine if an event should be flagged.
    """
    return True


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
    while True:
        try:
            response = requests.get(url, headers=headers)

            if response.status_code == 304:
                return None

            if response.status_code in (403, 503):
                time.sleep(backoff_time)
                backoff_time *= 2
                continue

            return response

        except requests.exceptions.RequestException:
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
    flagged_events = []
    found_last_id = False

    for event in events:
        event_id = event.get("id")

        if event_id == last_processed_id:
            found_last_id = True
            break

        if should_flag_event(event):
            flagged_events.append(event)

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
    all_flagged_events = []

    # Make initial request
    response = make_github_request(api_url, headers)
    if not response:
        return all_flagged_events

    # Extract poll interval from response headers
    poll_interval = int(response.headers.get("X-Poll-Interval", 60))

    events = response.json()
    if not events:
        return all_flagged_events

    # Update last_processed_id to newest event
    new_last_id = events[0].get("id")

    while True:
        # Process current page of events
        flagged_events, found_last_id = process_events(events, last_processed_id)
        all_flagged_events.extend(flagged_events)

        if found_last_id:
            break

        # Get next page URL from Link header
        next_url = response.links.get("next", {}).get("url", "")
        if not next_url:
            break

        # Request next page
        response = make_github_request(next_url, headers)
        if not response:
            break

        events = response.json()
        if not events:
            break

    return all_flagged_events, new_last_id, poll_interval


# in the wrapper around poll_github_events, we need to first fetch the last processed event ID from redis and call the function with it
# then, we take the list of flagged events, write them to the database and add them to the warning queue
# - flagged_events
# - id
# - JSON of the event
# - root_cause (array of strings)
# - impact (array of strings)
# - next_steps (array of strings)
# - has_been_processed (boolean, default false)
# - created_at
# above is the schema for the table
# use client returned by get_supabase() to write to the database
# use the redis client returned by get_redis() to write to the warning queue, fetch the last processed event ID, and also write the last processed event ID to redis
def serialize_event_for_queue(warning_id: int, event: Dict[str, Any]) -> str:
    """
    Serialize an event for the warning queue.
    """
    return json.dumps({"warning_id": warning_id, "event": event})


async def poll_and_process_events(api_url: str, headers: dict) -> int:
    """
    Wrapper around poll_github_events that handles Redis state and processes flagged events.

    Args:
        api_url: GitHub Events API URL
        headers: Request headers including auth token
    """
    # Get Redis and Supabase clients
    redis = await get_redis()
    supabase = get_supabase()

    # Get last processed ID from Redis
    last_id = await redis.get("last_processed_event_id")
    last_id = int(last_id) if last_id else -1

    # Poll GitHub events
    flagged_events, new_last_id, poll_interval = poll_github_events(
        api_url, headers, last_id
    )

    # Store new events and create warnings
    # Process events in batches of 1000
    batch_size = 1000
    for i in range(0, len(flagged_events), batch_size):
        batch = flagged_events[i : i + batch_size]

        # Create batch of warning records
        warning_data = []
        for event in batch:
            warning_data.append({"event": event})

        # Insert batch into database
        result = supabase.table("warnings").insert(warning_data).execute()

        # Process results and publish to Redis
        if result.data:
            for idx, warning in enumerate(result.data):
                warning_id = warning["id"]
                event = batch[idx]

                # Add to Redis warning queue and publish
                message = serialize_event_for_queue(warning_id, event)
                await redis.xadd(WARNING_QUEUE, {"message": message}, maxlen=10_000)

    # Update last processed ID in Redis
    if new_last_id:
        await redis.set("last_processed_event_id", str(new_last_id))

    return poll_interval


# finally, we need to write a function which will be called from main to run the polling and processing function in a loop, sleeping for some duration between each run
async def run_poller():
    """
    Run the GitHub event poller in a continuous loop.
    """
    headers = {"Authorization": f"token {GITHUB_TOKEN}"}

    while True:
        try:
            poll_interval = await poll_and_process_events(GITHUB_ENDPOINT, headers)
        except Exception as e:
            print(f"Error during poll run: {e}")

        await asyncio.sleep(poll_interval)


if __name__ == "__main__":
    asyncio.run(run_poller())
