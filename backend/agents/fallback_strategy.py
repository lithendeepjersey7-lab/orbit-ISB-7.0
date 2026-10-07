"""Idea-specific, explicitly unvalidated strategy drafts for provider outages."""

import re


_PROFILES = (
    {
        "keys": ("bicycle repair", "bike repair", "bike shop", "bicycle shop", "bike maintenance"),
        "audience": "Owners and managers of independent bicycle repair shops",
        "workflow": "accept repair appointment requests, organize workshop jobs, and keep customers updated",
        "must": [
            ("Repair appointment request with bicycle and service details", "Captures the information a shop needs to review an incoming repair request."),
            ("Workshop calendar and repair-job status board", "Lets staff see upcoming work and move a repair from intake through completion."),
            ("Customer-facing repair status updates", "Tests the idea's promise to keep customers informed during a repair."),
        ],
        "should": ("Booking confirmations and configurable reminders", "Reduces avoidable coordination after shops validate the booking workflow."),
        "later": ("Parts inventory, point-of-sale links, and automated SMS", "These add operational complexity or possible third-party costs; validate demand before building them."),
        "channels": ("Direct outreach to independent bicycle repair shops", "Shop owners and service managers can assess the workflow in context and recruit a small pilot."),
        "risk": ("Shop staff may keep using their existing booking and job-tracking process instead of adopting another tool.", "Observe repair intake at a small number of shops and run a side-by-side pilot before asking staff to change their workflow."),
        "market_segments": [
            {
                "name": "Independent bicycle repair shop owners and service managers",
                "side": "buyer",
                "who_they_are": "Likely purchasing decision-makers for a shop-facing scheduling and repair-status tool; inferred from the idea.",
                "pain_points": "The idea implies a need to coordinate repair appointments and keep customers updated; frequency and severity need interviews.",
                "buying_behaviour": "Not established by the available search leads; test with shop interviews and a guided pilot.",
            },
            {
                "name": "Customers booking bicycle repairs",
                "side": "n/a",
                "who_they_are": "Bicycle owners who request service and want to know the status of a repair.",
                "pain_points": "The idea explicitly targets repair scheduling and customer updates; current workarounds need validation.",
                "buying_behaviour": "Likely users rather than the primary buyer; validate whether shops or riders would pay.",
            },
        ],
        "pricing": {
            "model": "Shop subscription is a hypothesis to test, not a market finding.",
            "pricing_hypothesis": "Offer a no-cost guided pilot, then test willingness to pay for ongoing appointment and repair-status management; no price point is established.",
            "validation_test": "Ask shop decision-makers to choose between a continued free pilot and a clearly scoped paid trial, and record actual commitments.",
        },
    },
    {
        "keys": ("study group", "study-group"),
        "audience": "University students enrolled in challenging courses",
        "workflow": "find compatible study partners in their course",
        "must": [
            ("Course, topic, and availability preferences", "Defines matching criteria for students with the same immediate learning need."),
            ("Small-group match suggestions with session coordination", "Tests whether compatible students will meet and study together."),
        ],
        "should": ("Session scheduling and reminders", "Reduces coordination friction after a match."),
        "later": ("Course-level activity insights", "Wait until repeat participation is demonstrated."),
        "channels": ("Course communities and student clubs", "Reach students around a specific course without paid acquisition."),
        "risk": ("Students may not find a suitable group if each course has too few active participants.", "Run a manually recruited pilot in one course and track successful matches before adding courses."),
    },
    {
        "keys": ("adaptive learning", "tutoring", "learning platform", "education", "engineering student"),
        "audience": "Students in the specific subject or course named in the idea",
        "workflow": "complete a focused learning activity in the target subject and review progress",
        "must": [
            ("One subject-specific learning path", "Keeps the first release focused on the learner and subject named in the idea."),
            ("Practice activity with progress feedback", "Tests whether learners can complete and benefit from the core lesson."),
        ],
        "should": ("Educator or learner progress view", "Helps a small pilot review learning activity without building a full analytics suite."),
        "later": ("Additional subjects and advanced personalization", "Expand only after the first subject's learning loop is tested."),
        "channels": ("Course instructors and student learning communities", "Recruit a focused pilot cohort close to the learning context."),
        "risk": ("Learners may not improve or return if the activity does not fit their course needs.", "Pilot one topic with learners and an instructor; compare task completion and learner feedback."),
    },
    {
        "keys": ("inventory", "retailer", "stock management"),
        "audience": "Small retailers managing stock for the product category named in the idea",
        "workflow": "record stock changes and identify items that need replenishment",
        "must": [
            ("Simple product and stock register", "Provides the minimum data needed to test the inventory workflow."),
            ("Stock-change and low-stock alerts", "Tests whether timely visibility improves replenishment decisions."),
        ],
        "should": ("CSV import and export", "Reduces pilot setup and lets retailers retain access to their data."),
        "later": ("Point-of-sale integrations and demand forecasting", "Defer integrations and forecasts until pilot data and demand justify them."),
        "channels": ("Direct outreach to independent retailers", "Enables observation of real stock workflows before broader distribution."),
        "risk": ("Inaccurate or stale stock records may reduce trust in the tool.", "Test with a small product set and reconcile recorded counts against a physical count."),
    },
    {
        "keys": ("meal planning", "meal plan", "recipes", "busy families"),
        "audience": "Households with the meal-planning constraint named in the idea",
        "workflow": "turn household preferences and constraints into a practical weekly meal plan",
        "must": [
            ("Preference and dietary-constraint setup", "Makes the first plan relevant to the household using it."),
            ("Weekly plan with editable meals and shopping list", "Tests the end-to-end planning task before adding automation."),
        ],
        "should": ("Recipe substitutions and household sharing", "Improves collaboration and flexibility after the basic plan is useful."),
        "later": ("Grocery delivery integrations", "Depends on validated repeat use and integration demand."),
        "channels": ("Parent and household communities", "Reach people who already coordinate meals and can trial a weekly plan."),
        "risk": ("Plans may not fit household preferences, constraints, or available time.", "Test several plans with target households and record edits, skipped meals, and repeat use."),
    },
    {
        "keys": ("marketplace", "photographers"),
        "audience": "One narrowly defined buyer and provider group in the proposed marketplace",
        "workflow": "discover, compare, and contact a suitable provider",
        "must": [
            ("Focused provider profiles and service listings", "Creates enough trusted supply for buyers to evaluate the core offer."),
            ("Search, availability, and contact or booking request", "Tests whether the marketplace can create a useful buyer-provider match."),
        ],
        "should": ("Reviews and booking-status updates", "Add after real transactions establish what trust signals are needed."),
        "later": ("Automated payments and broad geographic expansion", "Defer until transactions and repeatable liquidity are demonstrated."),
        "channels": ("Recruit providers and buyers in one local niche", "Concentrating both sides makes early match quality measurable."),
        "risk": ("Buyers may see too little relevant supply, or providers too few qualified requests.", "Manually recruit both sides in one area and track qualified requests through completed matches."),
    },
    {
        "keys": ("water monitoring", "water monitor", "sensor", "hardware", "device"),
        "audience": "Households with the specific monitoring need described in the idea",
        "workflow": "measure a relevant water condition and communicate a clear status or alert",
        "must": [
            ("Reliable sensor reading for the target condition", "Validates that the device measures the problem the idea aims to address."),
            ("Clear status display and threshold alert", "Tests whether readings lead to an understandable, useful action."),
        ],
        "should": ("Measurement history and calibration flow", "Supports pilot troubleshooting and interpretation."),
        "later": ("Smart-home integrations and predictive features", "Wait until measurement reliability and alert usefulness are proven."),
        "channels": ("Small household pilot recruited through relevant local communities", "Allows installation, reliability, and usefulness to be observed directly."),
        "risk": ("Sensor readings may be unreliable or difficult for users to interpret.", "Bench-test against a reference measurement, then observe installation and alert interpretation in a small pilot."),
    },
)

_ACTION_WORDS = (
    "schedule", "book", "manage", "track", "find", "connect", "monitor",
    "reduce", "improve", "plan", "learn", "organize", "organise", "update",
    "automate", "deliver", "analyze", "analyse", "sell", "share",
    "create", "match", "predict", "repair", "remind", "measure",
)


def fallback_profile(idea, market=None):
    """Return a practical idea archetype without asserting market validation."""
    idea_text = " ".join(str(idea or "").split())
    lowered = idea_text.casefold()
    profile = next(
        (
            item
            for item in _PROFILES
            if any(key in lowered for key in item["keys"])
        ),
        None,
    )
    if profile is None:
        profile = {
            "audience": "The narrowest customer segment named in the idea",
            "workflow": "complete the core task described in the submitted idea",
            "must": [
                ("A minimal end-to-end core workflow", "Tests whether the proposed product can solve the specific problem in the idea."),
                ("A simple way to observe task completion and collect feedback", "Provides a low-cost signal before expanding product scope."),
            ],
            "should": ("Basic onboarding for a small pilot", "Helps initial users reach the core task without building broad automation."),
            "later": ("Integrations or automation requested repeatedly by pilot users", "Defer until observed use shows which extensions matter."),
            "channels": ("Direct outreach to people matching the proposed customer segment", "Enables discovery and a manually supported pilot before acquisition spend."),
            "risk": ("The core workflow may not solve a frequent or urgent customer problem.", "Observe target users attempting the core task and ask for a concrete pilot commitment."),
        }
    else:
        profile = dict(profile)

    if not profile.get("market_segments"):
        profile["market_segments"] = [{
            "name": profile["audience"],
            "side": "buyer",
            "who_they_are": "Candidate initial customer inferred from the submitted idea; confirm through interviews.",
            "pain_points": "The idea describes the task to improve, but its frequency and severity need customer validation.",
            "buying_behaviour": "Not established by available evidence; test with a pilot offer rather than assuming willingness to pay.",
        }]
    if not profile.get("pricing"):
        profile["pricing"] = {
            "model": "Not selected; validate who receives value and who pays.",
            "pricing_hypothesis": "No price point is supported by this run; test willingness to pay with a clearly scoped pilot.",
            "validation_test": "Compare stated interest with concrete pilot commitments; do not treat stated intent as proof.",
        }

    if profile.get("workflow") == "complete the core task described in the submitted idea":
        lowered_idea = idea_text.casefold()
        audience_match = re.search(
            r"\bhelps?\s+(.+?)\s+(?:to\s+)?(?:schedule|book|manage|track|find|connect|monitor|reduce|improve|plan|learn|organize|organise|update|automate|deliver|analy[sz]e|sell|share|create|match|predict|repair|remind|measure)\b",
            idea_text,
            flags=re.IGNORECASE,
        )
        if audience_match:
            profile["audience"] = audience_match.group(1).strip(" ,.")
            profile["market_segments"][0]["name"] = profile["audience"]
            profile["market_segments"][0]["who_they_are"] = (
                "Candidate customer segment named in the idea; confirm the buyer and user through interviews."
            )
        action_match = next(
            (word for word in _ACTION_WORDS if word in lowered),
            None,
        )
        if action_match:
            action_index = lowered.find(action_match)
            phrase = idea_text[action_index:].strip(" .,:;")
            profile["workflow"] = phrase[:180]

    segments = (market or {}).get("segments") or []
    segment_name = next(
        (
            item.get("name", "").strip()
            for item in segments
            if isinstance(item, dict) and item.get("name", "").strip()
        ),
        "",
    )
    audience = segment_name or profile["audience"]
    profile["audience"] = audience
    profile["idea"] = idea_text
    profile["workflow_text"] = profile["workflow"]
    return profile
