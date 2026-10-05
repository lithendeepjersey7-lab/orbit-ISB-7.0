"""Run the full validation-to-report flow against offline agent fixtures.

Run from the repository root with:
    python backend/e2e_test_runner.py

This checks integration and response contracts only. It does not evaluate live
search results or the quality of Gemini-generated analysis.
"""

import importlib
import json
import threading
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch


IDEAS = [
    ("SaaS", "AI-powered inventory management for small retailers"),
    ("Consumer", "Smart meal planning app for busy families"),
    ("Hardware", "Low-cost smart water monitoring device for homes"),
    ("Marketplace", "Marketplace connecting local photographers with customers"),
    ("EdTech", "Adaptive learning platform for engineering students"),
]

REPORT_HEADINGS = (
    b"1. Startup Idea / Executive Summary",
    b"2. Market Analysis",
    b"3. Competitor Analysis",
    b"4. SWOT & Risks",
    b"5. MVP Recommendations",
    b"6. Go-To-Market Strategy",
    b"7. Validation Score & Verdict",
    b"8. Roadmap",
    b"9. Sources",
)


def _load_application():
    """Import app modules without constructing real external API clients."""
    with patch("langchain_google_genai.ChatGoogleGenerativeAI"), patch(
        "tavily.TavilyClient"
    ):
        app_module = importlib.import_module("main")
        pipeline_module = importlib.import_module("agents.pipeline")
    return app_module, pipeline_module


def _is_valid_result(name, value):
    required = {
        "search": ("queries", "categories", "counts", "results", "stats"),
        "market": ("market_summary", "market_size", "growth_and_demand", "segments", "evidence_gaps"),
        "competitors": ("landscape_summary", "competitors", "market_gaps"),
        "swot": ("strengths", "weaknesses", "opportunities", "threats", "risks"),
        "mvp": ("target_audience", "product_summary", "must_have_features", "should_have_features", "nice_to_have_features", "build_phases", "prioritization_rationale"),
        "gtm": ("positioning", "early_target_customers", "customer_acquisition_channels", "first_100_users", "monetization", "first_90_days"),
    }
    if not isinstance(value, dict) or not all(key in value for key in required[name]):
        return False
    list_fields = {
        "search": ("queries", "categories", "results"),
        "market": ("segments",),
        "competitors": ("competitors",),
        "swot": ("strengths", "weaknesses", "opportunities", "threats", "risks"),
        "mvp": ("must_have_features", "should_have_features", "nice_to_have_features", "build_phases"),
        "gtm": ("early_target_customers", "customer_acquisition_channels"),
    }
    if any(not isinstance(value.get(key), list) for key in list_fields.get(name, ())):
        return False
    if name == "search" and not isinstance(value.get("stats"), dict):
        return False
    if name == "gtm" and not isinstance(value.get("positioning"), dict):
        return False
    if name == "gtm" and not isinstance(value.get("first_90_days"), dict):
        return False
    if name == "swot" and any(
        not all(key in risk for key in ("category", "risk", "likelihood", "impact", "mitigation"))
        for risk in value["risks"]
    ):
        return False
    if name == "mvp" and any(
        not all(key in phase for key in ("phase", "features", "exit_criteria"))
        for phase in value["build_phases"]
    ):
        return False
    if name == "gtm" and (
        not value["first_100_users"].get("plan")
        or not value["monetization"].get("pricing_hypothesis")
    ):
        return False
    return True


def _fixtures(domain, idea):
    marker = "OFFLINE TEST STUB [{}]: ".format(domain)
    return {
        "search": {
            "idea": idea,
            "queries": [marker + "search query"],
            "categories": ["Test evidence"],
            "counts": {"Test evidence": 1},
            "summary": marker + "search summary",
            "results": [{
                "title": marker + "test result",
                "url": "https://example.invalid/stub",
                "snippet": marker + "fixture only",
                "score": 1.0,
                "category": "Test evidence",
            }],
            "stats": {
                "searches_run": 1,
                "searches_succeeded": 1,
                "raw_results": 1,
                "duplicates_removed": 0,
                "shown": 1,
                "distinct_sites": 1,
                "elapsed_seconds": 0.0,
            },
            "elapsed_seconds": 0.0,
        },
        "market": {
            "market_summary": marker + "market summary",
            "market_size": marker + "not assessed offline",
            "growth_and_demand": marker + "not assessed offline",
            "segments": [{
                "name": marker + "customer segment",
                "side": "buyer",
                "who_they_are": marker + "not assessed offline",
                "pain_points": marker + "not assessed offline",
                "buying_behaviour": marker + "not assessed offline",
            }],
            "evidence_gaps": marker + "live evidence not assessed",
        },
        "competitors": {
            "landscape_summary": marker + "competitor summary",
            "competitors": [{
                "name": marker + "competitor",
                "type": "direct",
                "why_this_type": marker + "fixture classification",
                "offering": marker + "fixture offering",
                "positioning": marker + "fixture positioning",
                "target_customer": marker + "fixture customer",
                "weak_spots": marker + "not assessed offline",
            }],
            "market_gaps": marker + "not assessed offline",
        },
        "swot": {
            "strengths": [marker + "fixture strength"],
            "weaknesses": [marker + "not assessed offline"],
            "opportunities": [marker + "not assessed offline"],
            "threats": [marker + "not assessed offline"],
            "risks": [{
                "category": "market",
                "risk": marker + "not assessed offline",
                "likelihood": "medium",
                "impact": "medium",
                "mitigation": marker + "validate with customers",
            }],
        },
        "mvp": {
            "target_audience": marker + "not assessed offline",
            "product_summary": marker + "not assessed offline",
            "must_have_features": [{
                "feature": marker + "fixture feature",
                "why_important": marker + "not assessed offline",
            }],
            "should_have_features": [],
            "nice_to_have_features": [],
            "build_phases": [{
                "phase": "Prototype",
                "features": [marker + "fixture feature"],
                "exit_criteria": marker + "fixture criterion",
            }],
            "prioritization_rationale": marker + "fixture rationale",
        },
        "gtm": {
            "positioning": {
                "statement": marker + "not assessed offline",
                "differentiation": marker + "not assessed offline",
                "evidence_basis": marker + "fixture only",
            },
            "early_target_customers": [{
                "segment": marker + "fixture segment",
                "why_start_here": marker + "not assessed offline",
                "validation_signal": marker + "not assessed offline",
            }],
            "customer_acquisition_channels": [{
                "channel": marker + "fixture channel",
                "rationale": marker + "not assessed offline",
                "low_cost_test": marker + "not assessed offline",
            }],
            "first_100_users": {
                "plan": [marker + "fixture outreach"],
                "success_signal": marker + "fixture signal",
            },
            "monetization": {
                "model": marker + "fixture model",
                "pricing_hypothesis": marker + "fixture pricing hypothesis",
                "validation_test": marker + "fixture pricing test",
            },
            "first_90_days": {
                "days_1_30": [marker + "fixture step"],
                "days_31_60": [marker + "fixture step"],
                "days_61_90": [marker + "fixture step"],
            },
        },
    }


def _run_response_validation_checks():
    fixture_set = _fixtures("schema-test", "sample startup")
    advisor_response = {
        "answer": "OFFLINE TEST STUB: answer",
        "has_sufficient_context": True,
        "missing_context": [],
        "citations": [],
    }
    cases = {
        "market": (
            importlib.import_module("agents.market_agent"),
            fixture_set["market"],
            lambda module: module.analyse_market("sample", fixture_set["search"]["results"]),
            lambda value: value["segments"][0].update(name=42),
            lambda value: value["segments"][0].update(side="invalid"),
        ),
        "competitors": (
            importlib.import_module("agents.competitor_agent"),
            fixture_set["competitors"],
            lambda module: module.analyse_competitors("sample", fixture_set["search"]["results"]),
            lambda value: value["competitors"][0].update(offering=None),
            lambda value: value["competitors"][0].update(type="invalid"),
        ),
        "swot": (
            importlib.import_module("agents.swot_agent"),
            fixture_set["swot"],
            lambda module: module.analyse_swot("sample", {}, {}),
            lambda value: value["strengths"].append(1),
            None,
        ),
        "mvp": (
            importlib.import_module("agents.mvp_agent"),
            fixture_set["mvp"],
            lambda module: module.recommend_mvp("sample", {}, {}),
            lambda value: value["must_have_features"][0].update(feature=42),
            lambda value: value.update(must_have_features=[]),
        ),
        "gtm": (
            importlib.import_module("agents.gtm_agent"),
            fixture_set["gtm"],
            lambda module: module.develop_gtm_strategy("sample", {}, {}, {}),
            lambda value: value["positioning"].update(statement=42),
            lambda value: value.update(customer_acquisition_channels=[]),
        ),
        "advisor": (
            importlib.import_module("agents.advisor_agent"),
            advisor_response,
            lambda module: module.answer_follow_up("question", "sample", {}, {}, {}, {}, {}),
            lambda value: value.update(has_sufficient_context="yes"),
            lambda value: value.update(
                has_sufficient_context=False,
                missing_context=[],
            ),
        ),
    }
    failures = []

    for name, (module, valid_payload, invoke_agent, make_wrong_type, make_semantically_invalid) in cases.items():
        valid_text = json.dumps(valid_payload)
        fenced_text = "```json\n" + valid_text + "\n```"
        if module.parse_json(valid_text) != valid_payload:
            failures.append(name + " parser rejected a valid-shaped response")
        if module.parse_json(fenced_text) != valid_payload:
            failures.append(name + " parser rejected a fenced JSON response")
        for invalid_text in ("not json", "{}", "[]", None):
            if module.parse_json(invalid_text) is not None:
                failures.append(name + " parser accepted malformed/incomplete response")
                break

        invalid_nested = json.loads(valid_text)
        make_wrong_type(invalid_nested)
        if module.parse_json(json.dumps(invalid_nested)) is not None:
            failures.append(name + " parser accepted a wrong nested type")

        with patch.object(module.llm, "invoke", return_value=None):
            empty_result = invoke_agent(module)
            expected_fallback = True
            if (empty_result is not None) != expected_fallback or (
                expected_fallback
                and not empty_result.get("analysis_mode")
            ):
                failures.append(name + " agent accepted a response without text")

        with patch.object(
            module.llm,
            "invoke",
            side_effect=[
                SimpleNamespace(text="Here is the result, but it is not JSON."),
                SimpleNamespace(text=valid_text),
            ],
        ) as invoke:
            repaired = invoke_agent(module)
            recovered = repaired == valid_payload
            fallback_used = (
                name in {"market", "competitors", "swot", "mvp", "gtm", "advisor"}
                and isinstance(repaired, dict)
                and repaired.get("analysis_mode")
            )
            if (not recovered and not fallback_used) or invoke.call_count != 2:
                failures.append(name + " agent did not recover from one malformed JSON response")

        with patch.object(
            module.llm,
            "invoke",
            side_effect=[
                SimpleNamespace(text="not JSON"),
                SimpleNamespace(text="still not JSON"),
            ],
        ) as invoke:
            unusable = invoke_agent(module)
            expected_fallback = True
            if (
                (unusable is not None) != expected_fallback
                or (expected_fallback and not unusable.get("analysis_mode"))
                or invoke.call_count != 2
            ):
                failures.append(name + " agent did not bound JSON repair to one attempt")

        if make_semantically_invalid is not None:
            semantic_invalid = json.loads(valid_text)
            make_semantically_invalid(semantic_invalid)
            with patch.object(
                module.llm,
                "invoke",
                return_value=SimpleNamespace(text=json.dumps(semantic_invalid)),
            ):
                invalid_result = invoke_agent(module)
                if not invalid_result or not invalid_result.get("analysis_mode"):
                    failures.append(name + " did not fall back from semantically invalid output")

    market_context = {
        "segments": [{"name": "independent grocery stores"}],
        "evidence_gaps": "Willingness to pay is not established.",
    }
    competitor_context = {
        "competitors": [{"name": "Existing inventory platform"}],
        "market_gaps": "Small-store demand forecasting is underserved.",
    }
    fallback_agents = (
        ("market", importlib.import_module("agents.market_agent"), lambda m: m.analyse_market("sample", fixture_set["search"]["results"]), fixture_set["market"]),
        ("competitors", importlib.import_module("agents.competitor_agent"), lambda m: m.analyse_competitors("sample", fixture_set["search"]["results"]), fixture_set["competitors"]),
        ("swot", importlib.import_module("agents.swot_agent"), lambda m: m.analyse_swot("sample", {}, {}), fixture_set["swot"]),
        ("mvp", importlib.import_module("agents.mvp_agent"), lambda m: m.recommend_mvp("sample", {}, {}), fixture_set["mvp"]),
        ("gtm", importlib.import_module("agents.gtm_agent"), lambda m: m.develop_gtm_strategy("sample", {}, {}, {}), fixture_set["gtm"]),
        ("advisor", importlib.import_module("agents.advisor_agent"), lambda m: m.answer_follow_up("question", "sample", {}, {}, {}, {}, {}), advisor_response),
    )
    for name, module, call, _ in fallback_agents:
        with patch.object(module, "invoke_with_json_repair", side_effect=RuntimeError("Gemini unavailable")):
            fallback = call(module)
        if not fallback or not fallback.get("analysis_mode"):
            failures.append(name + " agent did not return a labelled fallback on provider failure")

    for name, module, call in (
        (
            "swot",
            importlib.import_module("agents.swot_agent"),
            lambda module: module.analyse_swot(
                "AI inventory planning for small grocers",
                market_context,
                competitor_context,
            ),
        ),
        (
            "mvp",
            importlib.import_module("agents.mvp_agent"),
            lambda module: module.recommend_mvp(
                "AI inventory planning for small grocers",
                market_context,
                competitor_context,
            ),
        ),
    ):
        with patch.object(module, "invoke_with_json_repair", side_effect=RuntimeError("Gemini unavailable")):
            fallback = call(module)
        if not fallback or fallback.get("analysis_mode") != "conservative_fallback":
            failures.append(name + " agent did not return a clearly marked fallback on provider failure")
        elif not fallback.get("analysis_note"):
            failures.append(name + " fallback omitted its limitation notice")

    searchless = dict(fixture_set["search"])
    searchless["results"] = []
    pipeline_module = importlib.import_module("agents.pipeline")
    with patch.object(pipeline_module, "search_idea", return_value=searchless):
        response = pipeline_module.validate("sample startup")
    for name in ("market", "competitors", "swot", "mvp", "gtm"):
        if not response.get(name) or not response[name].get("analysis_mode"):
            failures.append(name + " stage disappeared when search returned no evidence")

    return failures


def _run_idea(app_module, pipeline_module, domain, idea):
    fixtures = _fixtures(domain, idea)
    events = []
    event_lock = threading.Lock()
    errors = []
    result = None
    report_generated = False
    report_downloadable = False

    def record(event):
        with event_lock:
            events.append(event)

    def search_stub(received_idea):
        record("search")
        if received_idea != idea:
            raise AssertionError("search received a different idea")
        return fixtures["search"]

    def market_stub(received_idea, results):
        record("market")
        if received_idea != idea or results != fixtures["search"]["results"]:
            raise AssertionError("market did not receive expected idea/search results")
        return fixtures["market"]

    def competitor_stub(received_idea, results):
        record("competitors")
        if received_idea != idea or results != fixtures["search"]["results"]:
            raise AssertionError("competitor did not receive expected idea/search results")
        return fixtures["competitors"]

    def swot_stub(received_idea, market, competitors):
        record("swot")
        if received_idea != idea or market != fixtures["market"] or competitors != fixtures["competitors"]:
            raise AssertionError("SWOT did not receive expected market/competitor context")
        return fixtures["swot"]

    def mvp_stub(received_idea, market, competitors, swot):
        record("mvp")
        if (
            received_idea != idea
            or market != fixtures["market"]
            or competitors != fixtures["competitors"]
            or swot != fixtures["swot"]
        ):
            raise AssertionError("MVP did not receive expected idea/analysis context")
        return fixtures["mvp"]

    def gtm_stub(received_idea, market, competitors, swot):
        record("gtm")
        if (
            received_idea != idea
            or market != fixtures["market"]
            or competitors != fixtures["competitors"]
            or swot != fixtures["swot"]
        ):
            raise AssertionError("GTM did not receive expected idea and analysis context")
        return fixtures["gtm"]

    with (
        patch.object(pipeline_module, "search_idea", side_effect=search_stub),
        patch.object(pipeline_module, "analyse_market", side_effect=market_stub),
        patch.object(pipeline_module, "analyse_competitors", side_effect=competitor_stub),
        patch.object(pipeline_module, "analyse_swot", side_effect=swot_stub),
        patch.object(pipeline_module, "recommend_mvp", side_effect=mvp_stub),
        patch.object(pipeline_module, "develop_gtm_strategy", side_effect=gtm_stub),
    ):
        try:
            result = app_module.run_pipeline(idea)
            events_snapshot = list(events)
            positions = {event: events_snapshot.index(event) for event in set(events_snapshot)}
            expected_order = (
                "search" in positions
                and "market" in positions
                and "competitors" in positions
                and "swot" in positions
                and "mvp" in positions
                and "gtm" in positions
                and positions["search"] < positions["market"]
                and positions["search"] < positions["competitors"]
                and positions["market"] < positions["swot"]
                and positions["competitors"] < positions["swot"]
                and positions["swot"] < positions["mvp"] < positions["gtm"]
            )
            if not expected_order:
                errors.append("Observed agent call order did not match pipeline dependencies")
        except Exception as error:
            errors.append("Pipeline exception: {}: {}".format(type(error).__name__, error))

    agent_results = {
        name: _is_valid_result(
            name,
            result if name == "search" else result.get(name),
        ) if isinstance(result, dict) else False
        for name in ("search", "market", "competitors", "swot", "mvp", "gtm")
    }
    if isinstance(result, dict):
        errors.extend(str(error) for error in result.get("errors", []))
        try:
            response = app_module.generate_report(result)
            body = response.body
            report_generated = all(heading in body for heading in REPORT_HEADINGS)
            report_downloadable = (
                response.media_type == "application/pdf"
                and body.startswith(b"%PDF")
                and "attachment; filename=" in response.headers.get("content-disposition", "")
            )
            if not report_generated:
                errors.append("Report missing one or more required section headings")
            if not report_downloadable:
                errors.append("Report response was not a downloadable PDF")
        except Exception as error:
            errors.append("Report exception: {}: {}".format(type(error).__name__, error))
    else:
        errors.append("Pipeline returned no validation result")

    completed = bool(result) and all(agent_results.values()) and not errors
    return {
        "domain": domain,
        "idea": idea,
        "completed": completed,
        "agents": agent_results,
        "swot": agent_results["swot"],
        "mvp": agent_results["mvp"],
        "gtm": agent_results["gtm"],
        "report": report_generated and report_downloadable,
        "errors": errors,
        "elapsed": result.get("elapsed_seconds") if isinstance(result, dict) else None,
    }


def _run_retry_and_advisor_checks(app_module, pipeline_module):
    """Offline checks for the Gemini retry rules, failure reporting and /advisor.

    Gemini is replaced by stubs that raise or return canned replies. This proves
    the retry/error handling logic only. It does not prove live Gemini behaviour.
    """
    gemini_retry = importlib.import_module("agents.gemini_retry")
    market_module = importlib.import_module("agents.market_agent")
    competitor_module = importlib.import_module("agents.competitor_agent")
    advisor_module = importlib.import_module("agents.advisor_agent")
    fixtures = _fixtures("RETRY", "retry test idea")
    failures = []

    class FakeApiError(Exception):
        def __init__(self, code, message):
            super().__init__("{} {}".format(code, message))
            self.code = code

    unavailable = FakeApiError(503, "UNAVAILABLE. This model is currently experiencing high demand.")
    internal = FakeApiError(500, "INTERNAL. Temporary internal service error.")

    # 1. A 503 followed by a good reply is retried once and succeeds.
    calls = []
    def flaky(prompt):
        calls.append(prompt)
        if len(calls) == 1:
            raise unavailable
        return "ok"
    with patch.object(gemini_retry.time, "sleep") as sleep:
        llm = SimpleNamespace(invoke=flaky)
        if gemini_retry.invoke_with_retry(llm, "p", "Test agent") != "ok" or len(calls) != 2 or sleep.call_count != 1:
            failures.append("retry: a single 503 was not retried exactly once")

    # 2. A persistent 503 stops after MAX_ATTEMPTS and re-raises the original error.
    calls.clear()
    def always_503(prompt):
        calls.append(prompt)
        raise unavailable
    with patch.object(gemini_retry.time, "sleep"):
        try:
            gemini_retry.invoke_with_retry(SimpleNamespace(invoke=always_503), "p", "Test agent")
            failures.append("retry: persistent 503 did not raise")
        except FakeApiError as error:
            if error is not unavailable or len(calls) != gemini_retry.MAX_ATTEMPTS:
                failures.append("retry: persistent 503 was not bounded to MAX_ATTEMPTS")
    if "503" not in (gemini_retry.take_failure() or ""):
        failures.append("retry: exhausted retries lost the original 503 detail")

    calls.clear()
    def intermittent_internal(prompt):
        calls.append(prompt)
        if len(calls) == 1:
            raise internal
        return "recovered after internal error"
    with patch.object(gemini_retry.time, "sleep"):
        if gemini_retry.invoke_with_retry(
            SimpleNamespace(invoke=intermittent_internal), "p", "Test agent"
        ) != "recovered after internal error" or len(calls) != 2:
            failures.append("retry: transient Gemini 500 INTERNAL was not retried once")

    # 2b. When the primary Gemini 3.7 model remains overloaded, a configured
    #     stable Flash fallback gets the same prompt and can recover the call.
    primary_calls = []
    fallback_calls = []
    primary_llm = SimpleNamespace(model="gemini-3.7-flash")

    def primary_503(prompt):
        primary_calls.append(prompt)
        raise unavailable

    def fallback_ok(prompt):
        fallback_calls.append(prompt)
        return "fallback reply"

    fallback_llm = SimpleNamespace(model="gemini-3.8-flash", invoke=fallback_ok)

    with patch.object(gemini_retry.time, "sleep"):
        recovered = gemini_retry.invoke_with_retry(
            SimpleNamespace(model=primary_llm.model, invoke=primary_503),
            "same prompt",
            "Test agent",
            max_attempts=2,
            fallback_factory=lambda primary: fallback_llm,
        )
    if (
        recovered != "fallback reply"
        or len(primary_calls) != 2
        or fallback_calls != ["same prompt"]
    ):
        failures.append("retry: overloaded primary did not fail over to the stable model")

    # A 429 quota response is not retried on that same model, but a single
    # call to an alternate model may have a separate per-model rate budget.
    quota_error = FakeApiError(429, "RESOURCE_EXHAUSTED model request quota")
    quota_primary_calls = []

    def primary_429(prompt):
        quota_primary_calls.append(prompt)
        raise quota_error

    fallback_calls.clear()
    with patch.object(gemini_retry.time, "sleep") as sleep:
        recovered = gemini_retry.invoke_with_retry(
            SimpleNamespace(model=primary_llm.model, invoke=primary_429),
            "quota prompt",
            "Test agent",
            max_attempts=2,
            fallback_factory=lambda primary: fallback_llm,
        )
    if (
        recovered != "fallback reply"
        or len(quota_primary_calls) != 1
        or fallback_calls != ["quota prompt"]
        or sleep.called
    ):
        failures.append("retry: quota-limited model was retried or alternate-model fallback failed")

    # The fallback is also bounded, and errors explain both failed models.
    fallback_calls.clear()

    def fallback_503(prompt):
        fallback_calls.append(prompt)
        raise unavailable

    with patch.object(gemini_retry.time, "sleep"):
        try:
            gemini_retry.invoke_with_retry(
                SimpleNamespace(model=primary_llm.model, invoke=primary_503),
                "same prompt",
                "Test agent",
                max_attempts=2,
                fallback_factory=lambda primary: SimpleNamespace(
                    model=fallback_llm.model, invoke=fallback_503
                ),
            )
            failures.append("retry: persistent primary and fallback outage did not raise")
        except FakeApiError:
            failure = gemini_retry.take_failure() or ""
            if "gemini-3.8-flash" not in failure or len(fallback_calls) != 2:
                failures.append("retry: dual-model failure was not reported or bounded")

    # 3. 429, auth, bad-request and unknown errors are never retried.
    for error in (FakeApiError(429, "RESOURCE_EXHAUSTED"), FakeApiError(403, "PERMISSION_DENIED"),
                  FakeApiError(400, "INVALID_ARGUMENT"), ValueError("boom")):
        calls.clear()
        def raises(prompt, error=error):
            calls.append(prompt)
            raise error
        with patch.object(gemini_retry.time, "sleep") as sleep:
            try:
                gemini_retry.invoke_with_retry(SimpleNamespace(invoke=raises), "p", "Test agent")
            except Exception:
                pass
            if len(calls) != 1 or sleep.call_count:
                failures.append("retry: non-transient error {!r} was retried".format(error))
    gemini_retry.take_failure()

    # 4. Error text is shortened and API keys are redacted.
    described = gemini_retry.describe_error(ValueError("bad url ?key=AIza" + "x" * 30 + " " + "y" * 500))
    if "AIza" in described or len(described) > 340:
        failures.append("describe_error leaked a key-like value or was not truncated")

    # 5. Pipeline: Market 503s (retries exhausted), Competitors succeed. The
    #    API must not crash, the real reason must be reported, nothing faked.
    # With the Gemini class mocked, every agent can share one llm object, so a
    # single stub tells the market and competitor prompts apart by their text.
    def make_llm_stub(market_behaviour):
        def stub(prompt):
            if "competitive analyst" in prompt:
                return SimpleNamespace(text=json.dumps(fixtures["competitors"]))
            if isinstance(market_behaviour, Exception):
                raise market_behaviour
            return SimpleNamespace(text=market_behaviour)
        return stub

    with (
        patch.object(gemini_retry.time, "sleep"),
        patch.object(pipeline_module, "search_idea", return_value=fixtures["search"]),
        patch.object(market_module.llm, "invoke", side_effect=make_llm_stub(unavailable)),
        patch.object(competitor_module.llm, "invoke", side_effect=make_llm_stub(unavailable)),
        patch.object(pipeline_module, "analyse_swot", return_value=fixtures["swot"]) as swot_call,
        patch.object(pipeline_module, "recommend_mvp", return_value=fixtures["mvp"]) as mvp_call,
        patch.object(pipeline_module, "develop_gtm_strategy", return_value=fixtures["gtm"]) as gtm_call,
    ):
        result = app_module.run_pipeline("retry test idea")
    errors = result.get("errors", [])
    if not result.get("market"):
        failures.append("pipeline: market fallback was not returned after provider failure")
    elif result["market"].get("analysis_mode") != "analysis_unavailable":
        failures.append("pipeline: unavailable market analysis was not labelled")
    if result.get("competitors") != fixtures["competitors"]:
        failures.append("pipeline: competitor fallback/result was not returned")
    if result.get("swot") is None or result.get("mvp") is None or result.get("gtm") is None:
        failures.append("pipeline: downstream agents did not use available competitor context")
    if result.get("market") is None and result.get("competitors"):
        if swot_call.call_args.args[1] != {} or mvp_call.call_args.args[1] != {}:
            failures.append("pipeline: unavailable market context was not represented as empty")
        if gtm_call.call_args.args[1] != {}:
            failures.append("pipeline: unavailable market context was not represented in GTM input")

    swot_module = importlib.import_module("agents.swot_agent")
    mvp_module = importlib.import_module("agents.mvp_agent")
    with (
        patch.object(pipeline_module, "search_idea", return_value=fixtures["search"]),
        patch.object(pipeline_module, "analyse_market", return_value=fixtures["market"]),
        patch.object(pipeline_module, "analyse_competitors", return_value=fixtures["competitors"]),
        patch.object(swot_module, "invoke_with_json_repair", side_effect=RuntimeError("Gemini unavailable")),
        patch.object(mvp_module, "invoke_with_json_repair", side_effect=RuntimeError("Gemini unavailable")),
        patch.object(pipeline_module, "develop_gtm_strategy", return_value=fixtures["gtm"]),
    ):
        result = app_module.run_pipeline("retry test idea")
    if not result.get("swot") or result["swot"].get("analysis_mode") != "conservative_fallback":
        failures.append("pipeline: SWOT provider failure did not return the labelled fallback")
    if not result.get("mvp") or result["mvp"].get("analysis_mode") != "conservative_fallback":
        failures.append("pipeline: MVP provider failure did not return the labelled fallback")
    if not any("SWOT agent used a conservative fallback" in error for error in result.get("errors", [])):
        failures.append("pipeline: SWOT fallback warning was not surfaced")
    if not any("MVP agent used a conservative fallback" in error for error in result.get("errors", [])):
        failures.append("pipeline: MVP fallback warning was not surfaced")

    search_without_results = dict(fixtures["search"])
    search_without_results["results"] = []
    with patch.object(pipeline_module, "search_idea", return_value=search_without_results):
        result = app_module.run_pipeline("retry test idea")
    if not result.get("swot") or not result["swot"].get("analysis_mode"):
        failures.append("pipeline: SWOT was skipped when market and competitor research were missing")
    if not result.get("mvp") or not result["mvp"].get("analysis_mode"):
        failures.append("pipeline: MVP was skipped when market and competitor research were missing")
    if not result.get("gtm") or result["gtm"].get("analysis_mode") != "conservative_fallback":
        failures.append("pipeline: GTM fallback was not returned without research")
    if not result.get("market") or result["market"].get("analysis_mode") != "analysis_unavailable":
        failures.append("pipeline: market did not disclose missing research")
    if not result.get("competitors") or result["competitors"].get("analysis_mode") != "analysis_unavailable":
        failures.append("pipeline: competitor analysis did not disclose missing research")

    # 6. Pipeline: a model reply that is not usable JSON keeps the old message.
    with (
        patch.object(pipeline_module, "search_idea", return_value=fixtures["search"]),
        patch.object(market_module.llm, "invoke", side_effect=make_llm_stub("not json")),
        patch.object(competitor_module.llm, "invoke", side_effect=make_llm_stub("not json")),
    ):
        result = app_module.run_pipeline("retry test idea")
    if not result.get("market") or result["market"].get("analysis_mode") != "analysis_unavailable":
        failures.append("pipeline: invalid market JSON did not return the labelled fallback")

    # 7. /advisor: success and labelled fallback on provider/output failure.
    good = {"answer": "Focus on the buyer segment.", "has_sufficient_context": True, "missing_context": [], "citations": []}
    request = app_module.AdvisorRequest(
        question="What is the biggest risk?", idea="retry test idea",
        market=fixtures["market"], competitors=None,
        results=fixtures["search"]["results"],
        conversation_history=[{"role": "user", "content": "prior detail"}],
    )
    with patch.object(advisor_module.llm, "invoke", return_value=SimpleNamespace(text=json.dumps(good))) as invoke:
        if {key: app_module.advise(request)[key] for key in good} != good:
            failures.append("advisor: valid answer was not returned")
        if "retry test idea" not in invoke.call_args.args[0] or "What is the biggest risk?" not in invoke.call_args.args[0]:
            failures.append("advisor: idea/question missing from the prompt")
    cited = {
        **good,
        "citations": [
            {"source_id": "report:market", "reason": "market context"},
            {"source_id": "live:1", "reason": "search evidence"},
            {"source_id": "live:999", "reason": "not supplied"},
        ],
    }
    with patch.object(advisor_module.llm, "invoke", return_value=SimpleNamespace(text=json.dumps(cited))) as invoke:
        answer = app_module.advise(request)
        if [item["label"] for item in answer["citations"]] != ["From report", "From live search"]:
            failures.append("advisor: source labels or untrusted citation filtering failed")
        if "prior detail" not in invoke.call_args.args[0]:
            failures.append("advisor: conversation history missing from the prompt")
    with patch.object(gemini_retry.time, "sleep"), patch.object(advisor_module.llm, "invoke", side_effect=unavailable):
        answer = app_module.advise(request)
        if answer.get("analysis_mode") != "advisor_unavailable" or answer.get("citations") != []:
            failures.append("advisor: provider failure did not return a labelled uncited response")
    with patch.object(advisor_module.llm, "invoke", return_value=SimpleNamespace(text="not json")):
        answer = app_module.advise(request)
        if answer.get("analysis_mode") != "advisor_unavailable" or answer.get("citations") != []:
            failures.append("advisor: invalid reply did not return a labelled uncited response")

    # 8. Real HTTP layer (skipped if the test client's dependency is missing).
    try:
        from fastapi.testclient import TestClient
    except Exception:
        return failures, "SKIPPED HTTP-level checks (fastapi TestClient/httpx not installed)"
    client = TestClient(app_module.app)
    body = {"question": "q", "idea": "i", "market": None, "competitors": None, "swot": None, "mvp": None, "gtm": None}
    with patch.object(advisor_module.llm, "invoke", return_value=SimpleNamespace(text=json.dumps(good))):
        response = client.post("/advisor", json=body)
        if response.status_code != 200 or any(response.json().get(key) != value for key, value in good.items()):
            failures.append("HTTP /advisor with null context: {} {}".format(response.status_code, response.text[:100]))
    with patch.object(gemini_retry.time, "sleep"), patch.object(advisor_module.llm, "invoke", side_effect=unavailable):
        response = client.post("/advisor", json=body)
        if response.status_code != 200 or response.json().get("analysis_mode") != "advisor_unavailable":
            failures.append("HTTP /advisor fallback case: {} {}".format(response.status_code, response.text[:100]))
    if client.post("/advisor", json={"idea": "i"}).status_code != 422:
        failures.append("HTTP /advisor must still reject a request missing question")
    frontend_script = (
        Path(__file__).resolve().parents[1] / "frontend" / "script.js"
    ).read_text(encoding="utf-8")
    if (
        frontend_script.count('className = "download-report"') != 1
        or "downloadReport(data, reportButton)" not in frontend_script
        or 'link.download = "litmus-validation-report.pdf"' not in frontend_script
        or "startup-validation-report.html" in frontend_script
    ):
        failures.append("Frontend does not expose exactly one working PDF download action")
    with patch.object(pipeline_module, "search_idea", return_value=fixtures["search"]), \
            patch.object(pipeline_module, "analyse_market", return_value=fixtures["market"]), \
            patch.object(pipeline_module, "analyse_competitors", return_value=fixtures["competitors"]), \
            patch.object(pipeline_module, "analyse_swot", return_value=fixtures["swot"]), \
            patch.object(pipeline_module, "recommend_mvp", return_value=fixtures["mvp"]), \
            patch.object(pipeline_module, "develop_gtm_strategy", return_value=fixtures["gtm"]):
        validated = client.post("/validate", json={"idea": "http idea"})
    if validated.status_code != 200 or validated.json().get("gtm") != fixtures["gtm"]:
        failures.append("HTTP /validate did not return the full pipeline result")
    else:
        report = client.post(
            "/report",
            json=validated.json(),
            headers={"Origin": "https://orbit-isb-7-0.vercel.app"},
        )
        if (
            report.status_code != 200
            or report.headers.get("content-type") != "application/pdf"
            or not report.content.startswith(b"%PDF")
            or "attachment; filename=" not in report.headers.get("content-disposition", "")
            or "content-disposition" not in report.headers.get("access-control-expose-headers", "").lower()
        ):
            failures.append("HTTP /report did not return a PDF attachment")
    return failures, None


def _status(value):
    return "PASS (stub)" if value else "FAIL"


def main():
    app_module, pipeline_module = _load_application()
    schema_failures = _run_response_validation_checks()
    retry_failures, retry_note = _run_retry_and_advisor_checks(app_module, pipeline_module)
    results = [
        _run_idea(app_module, pipeline_module, domain, idea)
        for domain, idea in IDEAS
    ]

    print("Offline end-to-end validation and report contract test")
    print("All external agent calls return clearly marked synthetic fixtures. No live APIs were called.\n")
    print(
        "Agent schema/error-path checks: {}\n".format(
            "FAIL: " + "; ".join(schema_failures)
            if schema_failures
            else "PASS for all Gemini-backed agents (valid, fenced, malformed, incomplete, wrong-type, and missing-text cases)."
        )
    )
    print(
        "Retry / failure-reporting / advisor checks (stubbed Gemini): {}\n".format(
            "FAIL: " + "; ".join(retry_failures)
            if retry_failures
            else "PASS" + (" - " + retry_note if retry_note else "")
        )
    )
    print("| Domain | Startup idea | Pipeline | Search | Market | Competitor | SWOT | MVP | GTM | Report | Elapsed | Errors |")
    print("|---|---|---|---|---|---|---|---|---|---|---:|---|")
    for item in results:
        agent_statuses = item["agents"]
        errors = "; ".join(item["errors"]) or "None"
        elapsed = (
            "{:.1f}s".format(item["elapsed"])
            if isinstance(item["elapsed"], (int, float))
            else "Unavailable"
        )
        print(
            "| {} | {} | {} | {} | {} | {} | {} | {} | {} | {} | {} | {} |".format(
                item["domain"],
                item["idea"],
                _status(item["completed"]),
                _status(agent_statuses["search"]),
                _status(agent_statuses["market"]),
                _status(agent_statuses["competitors"]),
                _status(item["swot"]),
                _status(item["mvp"]),
                _status(item["gtm"]),
                _status(item["report"]),
                elapsed,
                errors.replace("|", "\\|"),
            )
        )

    error_counts = {}
    for item in results:
        for error in item["errors"]:
            error_counts[error] = error_counts.get(error, 0) + 1

    print("\nRecurring failures")
    repeated = [
        "{} ({} ideas)".format(error, count)
        for error, count in error_counts.items()
        if count > 1
    ]
    print("- " + ("; ".join(repeated) if repeated else "None observed in this offline stub run."))

    missing = [
        "{}: {}".format(item["domain"], ", ".join(
            name for name, valid in item["agents"].items() if not valid
        ))
        for item in results
        if not all(item["agents"].values())
    ]
    print("\nWeak or missing outputs")
    print("- " + ("; ".join(missing) if missing else "No missing/invalid fixture outputs; this does not assess live output quality."))

    print("\nPrompt/agent issues for the next M4 step")
    print("- This stubbed run cannot assess grounding, usefulness, domain fit, or prompt consistency.")
    print("- Schema-invalid responses are rejected instead of being silently repaired into potentially fabricated analysis.")
    print("- Run a separate live or curated-output rubric before making claims about analysis quality.")

    return 0 if all(item["completed"] for item in results) and not schema_failures and not retry_failures else 1


if __name__ == "__main__":
    raise SystemExit(main())