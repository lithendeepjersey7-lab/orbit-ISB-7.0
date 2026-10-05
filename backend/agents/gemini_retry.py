"""Small, bounded retry for temporary Gemini outages (503 UNAVAILABLE).

Every Gemini-backed agent calls the model through invoke_with_retry() instead
of llm.invoke() directly, so the retry rules live in exactly one place.

Why this exists: Gemini sometimes answers 503 "This model is currently
experiencing high demand." That is a temporary availability problem, not a bug
in the agent, and one more attempt a few seconds later often works.

Rules:
- Only 503 / UNAVAILABLE is retried. Auth, bad request, not found and
  unknown errors are NOT retried: repeating them cannot help.
- 429 is NOT retried. It can mean the quota is exhausted, and hammering a
  quota limit only wastes time.
- At most MAX_ATTEMPTS attempts in total, with exponential backoff.
- The langchain Gemini client also retries on its own by default (6 attempts,
  including 429). The agents turn that off with max_retries=0 so this helper
  is the only retry layer, and the only retrying is the bounded, logged
  retrying done here.
- Retrying does not guarantee success. When attempts run out the original
  exception is re-raised and the agent returns None as it always did.
"""

import random
import re
import threading
import time

MAX_ATTEMPTS = 4
BASE_DELAY_SECONDS = 4.0  # waits ~4s, 8s, then 16s (plus up to 1s jitter)

# The last agent-call failure seen by THIS thread. The pipeline runs each node
# in a worker thread and reads this straight after the agent returns, in the
# same thread, so concurrent requests and the parallel market/competitor
# nodes cannot see each other's failures.
_local = threading.local()


def is_transient(error):
    """True only for a temporary Gemini availability error (503 / UNAVAILABLE)."""
    for attribute in ("code", "status_code"):
        value = getattr(error, attribute, None)
        if isinstance(value, int):
            return value == 503
    text = str(error)
    return "503" in text and "UNAVAILABLE" in text.upper()


def describe_error(error):
    """One short, secret-free line describing an exception for logs and the API."""
    text = " ".join(str(error).split())
    text = re.sub(r"AIza[0-9A-Za-z_\-]{20,}", "[redacted]", text)
    text = re.sub(r"(?i)(key=)[^&\s'\"]+", r"\1[redacted]", text)
    if len(text) > 300:
        text = text[:300] + "..."
    return type(error).__name__ + ": " + text


def invoke_with_retry(llm, prompt, agent_name, max_attempts=MAX_ATTEMPTS):
    """Call llm.invoke(prompt), retrying only temporary 503 errors.

    Returns the model reply. Re-raises the original exception if the error is
    not transient or the attempts are used up, after remembering a short
    description of it for take_failure().
    """
    _local.failure = None
    for attempt in range(1, max_attempts + 1):
        try:
            return llm.invoke(prompt)
        except Exception as error:
            transient = is_transient(error)
            if not transient or attempt == max_attempts:
                suffix = " after %d attempts" % attempt if attempt > 1 else ""
                kind = "temporarily unavailable" if transient else "failed"
                _local.failure = "Gemini %s%s (%s)" % (kind, suffix, describe_error(error))
                raise
            delay = BASE_DELAY_SECONDS * (2 ** (attempt - 1)) + random.uniform(0, 1)
            print(
                "%s: Gemini 503 UNAVAILABLE on attempt %d of %d, retrying in %.1fs"
                % (agent_name, attempt, max_attempts, delay)
            )
            time.sleep(delay)


def take_failure():
    """Return and clear this thread's last model-call failure, or None.

    None means the last agent call did not fail at the model call, so a None
    result from the agent came from the reply itself (empty or invalid JSON).
    """
    failure = getattr(_local, "failure", None)
    _local.failure = None
    return failure
