Files:

- `app.py`: FastAPI server exposing endpoints `/summary` and `/stream`
- `poller.py`: polls the GitHub events endpoint and pushes anomalies to the queue
- `analyzer.py`: reads from the message queue and runs an LLM analysis on each anomaly
- `common.py`: common variables used between the poller, analyzer, and server
- `cleanup.py`: removes stale records from the events table

Database:

- hosted on supabase
- schema:
  - events
    - id
    - JSON payload of the event
    - created_at
  - warnings
    - id
    - root_cause (array of strings)
    - impact (array of strings)
    - next_steps (array of strings)
    - has_been_analyzed (boolean indicating whether we've run an LLM analysis on this warning yet)
    - created_at
  - events_warnings
    - id
    - event_id
    - warning_id
- some of the checks for anomalies can involve multiple commits (e.g. a single user making an unreasonable number of commits to a repo), so we store all events which could be tied to future warnings in the database. additionally, a single commit could theoretically be used in multiple warnings, therefore we establish a many-to-many relation between the events and the warnings
- to avoid unnecessarily storing commits that will never be involved in flags, we periodically remove records which are x hours old and unrelated to any warnings

Main pipeline:

- in `poller.py`, we periodically poll GitHub for new events, maintaining a "cursor" by storing the ID of the last-processed event in Redis and processing all events until we hit that one (the API doesn't provide a parameter to only get the events since a particular time)
- for each event we see, we pass it through `event_flagger()` which checks for common things to look out for (e.g. a forced push to main) and if the event trips any of the checks it is marked; these checks are currently hard-coded because I didn't want to run an LLM on every single event out of both cost and time considerations, but a more complex flagging process is a natural extension of the project if I were to continue workin on it
- whether an event is flagged or not, we write it to the database in case it can be used in a future analysis, but if the event does end up getting flagged, we push it to our message queue and create entries in the `warnings` and `events_warnings` tables corresponding to this warning
- in `app.py` we use `sse_stream()` to read from this message queue without popping from it, using it in our `/stream` endpoint to create a stream which the frontend can read from
- in `analyzer.py`, we read from the same message queue, except this time we pop from the queue as we process new messages. each message in the message queue will correspond to exactly warning. from the message, we extract the warning id, which we use to extract the relevant commits from the database and pass them to an LLM which will generate the `root_cause`, `impact`, and `next_steps` fields, then we mark the `has_been_analyzed` field as true
  - note that, in the time between an event being streamed to the frontend and the LLM analysis, the fields on the card will be unpopulated, so it will just saying something like "working on LLM summary..."
