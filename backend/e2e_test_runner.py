"""Run the full validation-to-report flow against offline agent fixtures.

Run from the repository root with:
    python backend/e2e_test_runner.py

This checks integration and response contracts only. It does not evaluate live
search results or the quality of Gemini-generated analysis.
"""

import importlib
import json
import threading
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
    "1. Startup Idea / Executive Summary",
    "2. Market Analysis",
    "3. Competitor Analysis",
    "4. SWOT &amp; Risks",
    "5. MVP Recommendations",
    "6. Go-To-Market Strategy",
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
        "swot": ("strengths", "weaknesses", "opportunities", "threats", "execution_risks"),
        "mvp": ("target_audience", "product_summary", "must_have_features", "nice_to_have_features"),
        "gtm": ("positioning", "early_target_customers", "customer_acquisition_channels", "first_90_days"),
    }
    if not isinstance(value, dict) or not all(key in value for key in required[name]):
        return False
    list_fields = {
        "search": ("queries", "categories", "results"),
        "market": ("segments",),
        "competitors": ("competitors",),
        "swot": ("strengths", "weaknesses", "opportunities", "threats", "execution_risks"),
        "mvp": ("must_have_features", "nice_to_have_features"),
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
            "execution_risks": [marker + "not assessed offline"],
        },
        "mvp": {
            "target_audience": marker + "not assessed offline",
            "product_summary": marker + "not assessed offline",
            "must_have_features": [{
                "feature": marker + "fixture feature",
                "why_important": marker + "not assessed offline",
            }],
            "nice_to_have_features": [],
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
    }
    cases = {
        "market": (
            importlib.import_module("agents.market_agent"),
            fixture_set["market"],
            lambda module: module.analyse_market("sample", []),
            lambda value: value["segments"][0].update(name=42),
            lambda value: value["segments"][0].update(side="invalid"),
        ),
        "competitors": (
            importlib.import_module("agents.competitor_agent"),
            fixture_set["competitors"],
            lambda module: module.analyse_competitors("sample", []),
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
            if invoke_agent(module) is not None:
                failures.append(name + " agent accepted a response without text")

        if make_semantically_invalid is not None:
            semantic_invalid = json.loads(valid_text)
            make_semantically_invalid(semantic_invalid)
            with patch.object(
                module.llm,
                "invoke",
                return_value=SimpleNamespace(text=json.dumps(semantic_invalid)),
            ):
                if invoke_agent(module) is not None:
                    failures.append(name + " agent accepted an invalid domain-specific output")

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

    def mvp_stub(received_idea, market, competitors):
        record("mvp")
        if received_idea != idea or market != fixtures["market"] or competitors != fixtures["competitors"]:
            raise AssertionError("MVP did not receive expected market/competitor context")
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
            body = response.body.decode("utf-8")
            report_generated = all(heading in body for heading in REPORT_HEADINGS)
            report_downloadable = (
                response.media_type == "text/html"
                and "attachment; filename=" in response.headers.get("content-disposition", "")
            )
            if not report_generated:
                errors.append("Report missing one or more required section headings")
            if not report_downloadable:
                errors.append("Report response was not an HTML attachment")
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


def _status(value):
    return "PASS (stub)" if value else "FAIL"


def main():
    app_module, pipeline_module = _load_application()
    schema_failures = _run_response_validation_checks()
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
    print("- A schema-invalid response is rejected as a whole; consider a bounded repair attempt and safe validation diagnostics.")
    print("- Run a separate live or curated-output rubric before making claims about analysis quality.")

    return 0 if all(item["completed"] for item in results) and not schema_failures else 1


if __name__ == "__main__":
    raise SystemExit(main())