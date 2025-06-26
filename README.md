notes:

- fly.io automatically spins down a machine after 5 minutes because I'm still on the trial period
- this means that if you're on the application for a while, the feed might die, but you just need to refresh the website and it will spin up a new machine
- (because a new request will have been made)

components:

- database of events stored on supabase, used to power the search feature of the website
- backend hosted on fly.io
- frontend hosted with vercel

backend flow:

- `poller.py` is running an infinite loop which periodically requests the events API, paginates through the response, and flags events based on some hard-coded checks
- we batch write this set of flagged events to the database then push all of them into a redis stream
- in `app.py`, which hosts the main server of the backend, we read from this redis stream, passing each flagged event to the OpenAI API, get a structured response, and load the necessary fields into the database and stream the new event to the frontend

improvements that can be made:

- the most obvious shortcoming of the final product is the quality of warnings; almost all of them are just "pushes to the default branch", which isn't even something that someone would really care about unless it was a large, collaborative repo. the warning checks are currently hard-coded from the backend, ideally I would have been able to run an LLM on the payload for a smarter flagging process but doing this for every event would have gotten extremely expensive. I think if I had more time I'd look the GitHub events API more closely to find more flags to make and maybe even do some research into the ML space to find a cheaper but more sophisticated flagging method.
- considering multiple events in the analysis; oftentimes it's gonna be more than a single event that will provide signal of an anomaly, ideally we'd have some process that groups events based on their probability of being connected to some unwanted behavior and analyzes them together with an LLM. I didn't opt for this because it would require either (a) a ton of storage to hold all of the events I'm processing (which I wasn't trying to pay for) or (b) another process which is periodically cleaning the database of events which aren't tied to any warnings, but I didn't have the time to implement this
- doing parallel processing of the pages of the returned information from github in the polling process would result in faster processing of the results, although the main bottleneck of the UI updates was the LLM inference, not the loading of events into the redis stream

limitations:

- in every response, there's an X-Poll-Interval header that indicates the amount of time until I'm allowed to request the API again. In this time, there are countless events that are going unchecked; this is more of a limitation of the API but worth noting
