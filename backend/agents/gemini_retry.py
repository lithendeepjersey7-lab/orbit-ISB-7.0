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

MAX_ATTEMPTS = 2
FALLBACK_MODEL = "gemini-2.5-flash"
BASE_DELAY_SECONDS = 1.5  # fail over quickly enough to preserve the request budget

# The last agent-call failure seen by THIS thread. The pipeline runs each node
# in a worker thread and reads this straight after the agent returns, in the
# same thread, so concurrent requests and the parallel market/competitor
# nodes cannot see each other's failures.
_local = threading.local()
_fallback_lock = threading.Lock()
_fallback_llm = None


def is_transient(error):
    """True only for a temporary Gemini availability error (503 / UNAVAILABLE)."""
    for attribute in ("code", "status_code"):
        value = getattr(error, attribute, None)
        if isinstance(value, int):
            return value == 503
    text = str(error)
    return "503" in text and "UNAVAILABLE" in text.upper()


def is_model_quota_limited(error):
    """Detect Gemini 429 RESOURCE_EXHAUSTED without retrying that same model."""
    text = str(error).upper()
    return "RESOURCE_EXHAUSTED" in text and (
        getattr(error, "code", None) == 429
        or getattr(error, "status_code", None) == 429
        or "429" in text
    )


def describe_error(error):
    """One short, secret-free line describing an exception for logs and the API."""
    text = " ".join(str(error).split())
    text = re.sub(r"AIza[0-9A-Za-z_\-]{20,}", "[redacted]", text)
    text = re.sub(r"(?i)(key=)[^&\s'\"]+", r"\1[redacted]", text)
    if len(text) > 300:
        text = text[:300] + "..."
    return type(error).__name__ + ": " + text


def _invoke_model(llm, prompt, agent_name, max_attempts):
    """Invoke one model with bounded retries for transient 503 responses."""
    for attempt in range(1, max_attempts + 1):
        try:
            return llm.invoke(prompt)
        except Exception as error:
            transient = is_transient(error)
            if not transient or attempt == max_attempts:
                raise
            delay = BASE_DELAY_SECONDS * (2 ** (attempt - 1)) + random.uniform(0, 1)
            print(
                "%s: Gemini 503 UNAVAILABLE on attempt %d of %d, retrying in %.1fs"
                % (agent_name, attempt, max_attempts, delay)
            )
            time.sleep(delay)


def _create_fallback_model(primary):
    """Create/cache the stable Flash fallback only when primary is overloaded."""
    global _fallback_llm
    if getattr(primary, "model", None) != "gemini-3.7-flash":
        return None
    if _fallback_llm is None:
        with _fallback_lock:
            if _fallback_llm is None:
                from langchain_google_genai import ChatGoogleGenerativeAI

                _fallback_llm = ChatGoogleGenerativeAI(
                    model=FALLBACK_MODEL,
                    thinking_budget=512,
                    max_retries=0,
                )
    return _fallback_llm


def invoke_with_retry(
    llm,
    prompt,
    agent_name,
    max_attempts=MAX_ATTEMPTS,
    fallback_factory=_create_fallback_model,
):
    """Invoke Gemini with bounded retries and a stable-model overload fallback.

    Only 503 errors trigger retries/failover. After the primary model exhausts
    its retry budget, supported Gemini 3.7 Flash callers try Gemini 2.5 Flash
    with the same prompt. Other failures are re-raised without extra calls.
    """
    _local.failure = None
    try:
        return _invoke_model(llm, prompt, agent_name, max_attempts)
    except Exception as primary_error:
        last_primary_error = primary_error
        if not is_transient(primary_error) and not is_model_quota_limited(primary_error):
            _local.failure = "Gemini failed (%s)" % describe_error(primary_error)
            raise

    fallback = fallback_factory(llm)
    if fallback is None:
        suffix = " after %d attempts" % max_attempts
        _local.failure = "Gemini temporarily unavailable%s (%s)" % (
            suffix,
            describe_error(last_primary_error),
        )
        raise last_primary_error

    reason = "quota/rate limited" if is_model_quota_limited(last_primary_error) else "overloaded"
    print("%s: primary model %s; trying %s once" % (agent_name, reason, FALLBACK_MODEL))
    try:
        return _invoke_model(
            fallback,
            prompt,
            agent_name + " fallback (" + FALLBACK_MODEL + ")",
            max_attempts,
        )
    except Exception as fallback_error:
        _local.failure = (
            "Gemini primary model unavailable after %d attempts (%s); fallback %s "
            "failed after %d attempts (%s)"
            % (
                max_attempts,
                describe_error(last_primary_error),
                FALLBACK_MODEL,
                max_attempts,
                describe_error(fallback_error),
            )
        )
        raise


def take_failure():
    """Return and clear this thread's last model-call failure, or None.

    None means the last agent call did not fail at the model call, so a None
    result from the agent came from the reply itself (empty or invalid JSON).
    """
    failure = getattr(_local, "failure", None)
    _local.failure = None
    return failure
