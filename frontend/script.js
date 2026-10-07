// Localhost previews use the hosted API by default so a static demo works
// without requiring a separate local backend. Opt into localhost:8000 with
// ?api=local when intentionally developing against a local backend.
let latestValidation = null;

const API_URL = new URLSearchParams(location.search).get("api") === "local"
  ? "http://127.0.0.1:8000"
  : "https://orbit-isb-7-0-staging.onrender.com";

const ideaBox = document.getElementById("idea");
const submitButton = document.getElementById("submit");
const statusLine = document.getElementById("status");
const resultsBox = document.getElementById("results");
const ideaForm = document.getElementById("idea-form");
const advisorDock = document.getElementById("advisor-dock");
const advisorToggle = document.getElementById("advisor-toggle");

advisorToggle.addEventListener("click", function () {
  const isOpen = document.body.classList.toggle("advisor-dock-open");
  advisorToggle.setAttribute("aria-expanded", String(isOpen));
  advisorToggle.textContent = isOpen ? "Close advisor" : "Ask Litmus";
  if (isOpen) {
    const input = advisorDock.querySelector("textarea");
    if (input) input.focus();
  }
});

ideaForm.addEventListener("submit", function (event) {
  event.preventDefault();
  validateIdea();
});

document.querySelectorAll(".example-chip").forEach(function (button) {
  button.addEventListener("click", function () {
    ideaBox.value = button.dataset.idea;
    ideaBox.focus();
  });
});

async function validateIdea() {
  const idea = ideaBox.value.trim();

  if (idea.length < 10) {
    statusLine.textContent = "Please write a bit more about your idea.";
    statusLine.className = "error";
    ideaBox.focus();
    return;
  }

  statusLine.className = "";
  resultsBox.innerHTML = "";
  submitButton.disabled = true;
  submitButton.querySelector("span:first-child").textContent = "Validating…";

  // A full run takes about a minute on Render's free tier, which gives the
  // backend a tenth of a CPU. Without these updates the page looks frozen,
  // so say which agent is working rather than showing one static message.
  const stages = [
    [0, "Searching the web…"],
    [4, "Reading the results. Market and competitor analysis is running…"],
    [25, "Running SWOT, MVP, and go-to-market analysis…"],
    [75, "This is taking longer than usual; the pipeline is still running…"],
  ];
  const startedAt = Date.now();
  statusLine.textContent = stages[0][1];
  const ticker = setInterval(function () {
    const seconds = (Date.now() - startedAt) / 1000;
    for (const [after, message] of stages) {
      if (seconds >= after) statusLine.textContent = message;
    }
  }, 1000);

  // The try only wraps the network call. If it wrapped the rendering too, a
  // bug in showResults would be reported as "could not reach the API", which
  // sends you looking in the wrong place.
  let data;
  try {
    const response = await fetch(API_URL + "/validate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ idea: idea }),
    });
    try {
      data = await response.json();
    } catch (parseError) {
      throw new Error("The validation service returned an unreadable response. Please try again.");
    }
    if (!response.ok) {
      throw new Error(
        typeof data.detail === "string"
          ? data.detail
          : "Validation failed with status " + response.status
      );
    }
  } catch (error) {
    clearInterval(ticker);
    showApiError(error, "validation");
    submitButton.disabled = false;
    submitButton.querySelector("span:first-child").textContent = "Validate This Idea";
    return;
  }

  clearInterval(ticker);
  try {
    if (showResults(data)) {
      const coverage = getAnalysisCoverage(data);
      statusLine.textContent =
        "Validation ready · " + (Array.isArray(data.results) ? data.results.length : 0) +
        " sources · " + coverage.score + "% analysis coverage";
      resultsBox.scrollIntoView({
        behavior: window.matchMedia("(prefers-reduced-motion: reduce)").matches ? "auto" : "smooth",
        block: "start"
      });
    }
  } catch (error) {
    statusLine.textContent = "The validation completed, but its results could not be displayed.";
    statusLine.className = "error";
    console.error("Could not render validation results:", error);
  } finally {
    submitButton.disabled = false;
    submitButton.querySelector("span:first-child").textContent = "Validate This Idea";
  }
}

function showApiError(error, operation) {
  statusLine.replaceChildren();
  statusLine.className = "error api-error";
  const message = document.createElement("span");
  const networkFailure = error instanceof TypeError ||
    (error && /failed to fetch|networkerror|load failed/i.test(error.message || ""));
  if (networkFailure) {
    message.textContent =
      "Couldn’t connect to the " + (operation || "validation") +
      " API at " + API_URL + ". Check your internet connection or the backend status.";
  } else {
    message.textContent = error.message || "The " + (operation || "validation") + " request failed.";
  }
  statusLine.appendChild(message);

  if (networkFailure) {
    const healthLink = document.createElement("a");
    healthLink.href = API_URL + "/";
    healthLink.target = "_blank";
    healthLink.rel = "noopener noreferrer";
    healthLink.textContent = " Check API status";
    statusLine.appendChild(healthLink);
    if (new URLSearchParams(location.search).get("api") !== "local") {
      const localHint = document.createElement("span");
      localHint.textContent = " · For a running local backend, add ?api=local to this page’s URL.";
      statusLine.appendChild(localHint);
    }
  }
}

function showResults(data) {
  if (!data || typeof data !== "object") {
    statusLine.textContent = "The validation service returned an invalid response.";
    statusLine.className = "error";
    return false;
  }
  resultsBox.appendChild(buildValidationOverview(data));
  resultsBox.appendChild(buildSectionNav(data));

  if (data.errors && data.errors.length) {
    resultsBox.appendChild(buildErrors(data.errors));
  }

  latestValidation = data;

  // The analysis comes before the raw sources. A founder wants the conclusion
  // first and the evidence underneath it, not the other way round.
  if (data.market) resultsBox.appendChild(buildMarket(data.market));
  if (data.competitors) resultsBox.appendChild(buildCompetitors(data.competitors));
  if (data.swot) resultsBox.appendChild(buildSwot(data.swot));
  if (data.mvp) resultsBox.appendChild(buildMvp(data.mvp));
  if (data.gtm) resultsBox.appendChild(buildGtm(data.gtm));
  advisorDock.replaceChildren(buildAdvisor(data));
  advisorDock.hidden = false;
  advisorToggle.hidden = false;
  if (window.matchMedia("(min-width: 1800px)").matches) {
    document.body.classList.add("advisor-dock-open");
    advisorToggle.setAttribute("aria-expanded", "true");
    advisorToggle.textContent = "Close advisor";
  }

  const evidence = document.createElement("details");
  evidence.className = "source-evidence";
  evidence.id = "sources";
  const evidenceHeading = document.createElement("summary");
  evidenceHeading.textContent = "Search evidence & sources";
  const evidenceCount = document.createElement("span");
  evidenceCount.className = "source-evidence__count";
  const resultCount = Array.isArray(data.results) ? data.results.length : 0;
  evidenceCount.textContent = resultCount + (resultCount === 1 ? " source" : " sources");
  evidenceHeading.appendChild(evidenceCount);
  evidence.appendChild(evidenceHeading);

  const queries = document.createElement("div");
  queries.className = "queries";

  const heading = document.createElement("h3");
  heading.textContent = "Searches the agent ran:";
  queries.appendChild(heading);

  const list = document.createElement("ol");
  for (const query of data.queries || []) {
    const item = document.createElement("li");
    item.textContent = query;
    list.appendChild(item);
  }
  queries.appendChild(list);
  if ((data.queries || []).length) evidence.appendChild(queries);

  // Show the sources grouped under the angle that found them
  const categoryNames = Array.isArray(data.categories) ? data.categories.slice() : [];
  for (const result of Array.isArray(data.results) ? data.results : []) {
    const category = result.category || "Other sources";
    if (!categoryNames.includes(category)) categoryNames.push(category);
  }
  for (const category of categoryNames) {
    const group = (Array.isArray(data.results) ? data.results : []).filter((r) => (r.category || "Other sources") === category);
    if (group.length === 0) continue;

    const label = document.createElement("h2");
    label.className = "category";
    label.textContent = category;

    const count = document.createElement("span");
    count.textContent = group.length + (group.length === 1 ? " source" : " sources");
    label.appendChild(count);

    evidence.appendChild(label);

    for (const result of group) {
      evidence.appendChild(buildCard(result));
    }
  }
  if (!resultCount && !(data.queries || []).length) {
    const empty = document.createElement("p");
    empty.className = "source-evidence__empty";
    empty.textContent = "No web sources were returned in this validation run.";
    evidence.appendChild(empty);
  }
  resultsBox.appendChild(evidence);
  return true;
}

function getAnalysisCoverage(data) {
  const unavailableModes = new Set([
    "analysis_unavailable",
    "evidence_summary",
    "conservative_fallback",
    "advisor_unavailable"
  ]);
  const dimensions = ["market", "competitors", "swot", "mvp", "gtm"];
  const completed = dimensions.filter(function (key) {
    const section = data && data[key];
    return Boolean(section) && !unavailableModes.has(section.analysis_mode);
  }).length;
  return { completed: completed, total: dimensions.length, score: Math.round(100 * completed / dimensions.length) };
}

function buildValidationOverview(data) {
  const coverage = getAnalysisCoverage(data);
  const results = Array.isArray(data.results) ? data.results : [];
  const stats = data.stats || {};
  const card = document.createElement("section");
  card.className = "validation-overview";
  card.setAttribute("aria-labelledby", "validation-title");

  const intro = document.createElement("div");
  intro.className = "validation-overview__intro";
  const eyebrow = document.createElement("p");
  eyebrow.className = "step-label";
  eyebrow.textContent = coverage.completed === coverage.total ? "VALIDATION COMPLETE" : "VALIDATION SNAPSHOT";
  intro.appendChild(eyebrow);

  const title = document.createElement("h2");
  title.id = "validation-title";
  title.tabIndex = -1;
  title.textContent = data.idea || "Your startup idea";
  intro.appendChild(title);

  const summary = document.createElement("p");
  summary.className = "validation-overview__summary";
  summary.textContent = data.summary || "Your research and analysis are ready to review.";
  intro.appendChild(summary);

  const actions = document.createElement("div");
  actions.className = "validation-overview__actions";
  const reportButton = document.createElement("button");
  reportButton.type = "button";
  reportButton.className = "download-report";
  reportButton.textContent = "Download PDF report";
  reportButton.addEventListener("click", function () {
    downloadReport(data, reportButton);
  });
  actions.appendChild(reportButton);

  const advisorLink = document.createElement("a");
  advisorLink.className = "overview-link";
  advisorLink.href = "#advisor";
  advisorLink.textContent = "Ask the advisor";
  advisorLink.addEventListener("click", function () {
    openAdvisorDock();
  });
  actions.appendChild(advisorLink);
  intro.appendChild(actions);
  card.appendChild(intro);

  const metrics = document.createElement("div");
  metrics.className = "overview-metrics";
  const metricRows = [
    {
      value: coverage.score + "%",
      label: "AI analysis coverage",
      detail: coverage.completed + " of " + coverage.total + " analysis sections completed",
      progress: coverage.score
    },
    {
      value: String(results.length),
      label: "Search sources",
      detail: (stats.distinct_sites || 0) + " distinct sites"
    },
    {
      value: typeof stats.searches_run === "number" ? String(stats.searches_run) : "—",
      label: "Search queries",
      detail: "Run for this idea"
    },
    {
      value: typeof data.elapsed_seconds === "number" ? data.elapsed_seconds + "s" : "—",
      label: "Run time",
      detail: "Across the validation pipeline"
    }
  ];
  for (const metric of metricRows) {
    const tile = document.createElement("div");
    tile.className = "overview-metric";
    const value = document.createElement("strong");
    value.className = "overview-metric__value";
    value.textContent = metric.value;
    tile.appendChild(value);
    const label = document.createElement("span");
    label.className = "overview-metric__label";
    label.textContent = metric.label;
    tile.appendChild(label);
    const detail = document.createElement("span");
    detail.className = "overview-metric__detail";
    detail.textContent = metric.detail;
    tile.appendChild(detail);
    if (typeof metric.progress === "number") {
      const progress = document.createElement("progress");
      progress.className = "coverage-progress";
      progress.max = 100;
      progress.value = metric.progress;
      progress.setAttribute("aria-label", "AI analysis coverage");
      tile.appendChild(progress);
    }
    metrics.appendChild(tile);
  }
  card.appendChild(metrics);

  const note = document.createElement("p");
  note.className = "coverage-note";
  note.textContent = "Coverage describes completed AI analyses, not the likelihood that the startup will succeed.";
  card.appendChild(note);
  return card;
}

function buildSectionNav(data) {
  const sections = [
    ["market", "Market", data.market],
    ["competitors", "Competitors", data.competitors],
    ["swot", "SWOT & risks", data.swot],
    ["mvp", "MVP", data.mvp],
    ["gtm", "Go-to-market", data.gtm],
    ["advisor", "Advisor", true],
    ["sources", "Sources", true]
  ].filter(function (section) { return Boolean(section[2]); });
  const nav = document.createElement("nav");
  nav.className = "result-nav";
  nav.setAttribute("aria-label", "Jump to a validation section");
  const label = document.createElement("span");
  label.className = "result-nav__label";
  label.textContent = "IN THIS REPORT";
  nav.appendChild(label);
  for (const [id, title] of sections) {
    const link = document.createElement("a");
    link.href = "#" + id;
    link.textContent = title;
    nav.appendChild(link);
  }
  return nav;
}

function buildCard(result) {
  const card = document.createElement("div");
  card.className = "result";

  const link = document.createElement("a");
  link.href = result.url;
  link.target = "_blank";
  link.textContent = result.title;

  const host = document.createElement("p");
  host.className = "host";
  host.textContent = result.url;

  const snippet = document.createElement("p");
  snippet.textContent = result.snippet;

  card.appendChild(link);
  card.appendChild(host);
  card.appendChild(snippet);
  return card;
}

// ---------------------------------------------------------------------------
// Milestone 2 rendering
// ---------------------------------------------------------------------------

function withEstimateMarks(text) {
  // Rule 2 of both agent prompts: anything the sources did not support is
  // prefixed "Estimate (not from sources):". Mark it visually so a founder can
  // tell evidence from inference at a glance.
  const marker = "Estimate (not from sources):";
  const p = document.createElement("p");
  if (!text) return p;

  const at = text.indexOf(marker);
  if (at === -1) {
    p.textContent = text;
    return p;
  }

  p.appendChild(document.createTextNode(text.slice(0, at)));
  const estimate = document.createElement("span");
  estimate.className = "estimate";
  estimate.textContent = text.slice(at);
  p.appendChild(estimate);
  return p;
}

function labelled(label, value) {
  const p = document.createElement("p");
  const b = document.createElement("b");
  b.textContent = label + " ";
  p.appendChild(b);
  p.appendChild(document.createTextNode(value));
  return p;
}

function buildMarket(market) {
  const box = document.createElement("section");
  box.className = "analysis";
  box.id = "market";

  const title = document.createElement("h2");
  title.textContent = "Market opportunity";
  box.appendChild(title);

  const fields = [
    ["Summary", market.market_summary],
    ["Market size", market.market_size],
    ["Growth and demand", market.growth_and_demand],
  ];
  for (const [label, value] of fields) {
    if (!value) continue;
    const h = document.createElement("h3");
    h.textContent = label;
    box.appendChild(h);
    box.appendChild(withEstimateMarks(value));
  }

  const segments = market.segments || [];
  if (segments.length) {
    const h = document.createElement("h3");
    h.textContent = "Customer segments";
    box.appendChild(h);

    const grid = document.createElement("div");
    grid.className = "segments";

    for (const segment of segments) {
      const card = document.createElement("div");
      card.className = "segment";

      const name = document.createElement("h4");
      name.textContent = segment.name;
      if (segment.side && segment.side !== "n/a") {
        const tag = document.createElement("span");
        tag.className = "tag";
        tag.textContent = segment.side;
        name.appendChild(tag);
      }
      card.appendChild(name);

      const rows = [
        ["Who they are", segment.who_they_are],
        ["Pain points", segment.pain_points],
        ["Buying behaviour", segment.buying_behaviour],
      ];
      for (const [label, value] of rows) {
        if (value) card.appendChild(labelled(label, value));
      }
      grid.appendChild(card);
    }
    box.appendChild(grid);
  }

  if (market.evidence_gaps) {
    const h = document.createElement("h3");
    h.textContent = "What the sources did not answer";
    box.appendChild(h);
    box.appendChild(withEstimateMarks(market.evidence_gaps));
  }

  appendResearchLeads(box, "Live market search leads (not verified findings)", market.source_findings);
  addAskButton(box, "Market analysis");
  return box;
}

function appendResearchLeads(box, headingText, leads) {
  if (!Array.isArray(leads) || !leads.length) return;
  const heading = document.createElement("h3");
  heading.textContent = headingText;
  box.appendChild(heading);
  const list = document.createElement("ul");
  for (const lead of leads) {
    const item = document.createElement("li");
    const link = document.createElement("a");
    link.textContent = lead.title || "Search result";
    link.href = lead.url || "#";
    if (lead.url) {
      link.target = "_blank";
      link.rel = "noopener noreferrer";
    }
    item.appendChild(link);
    if (lead.category || lead.snippet) {
      const detail = document.createElement("p");
      detail.textContent = [lead.category, lead.snippet].filter(Boolean).join(" — ");
      item.appendChild(detail);
    }
    list.appendChild(item);
  }
  box.appendChild(list);
}

function buildCompetitors(data) {
  const box = document.createElement("section");
  box.className = "analysis";
  box.id = "competitors";

  const title = document.createElement("h2");
  title.textContent = "Competitor landscape";
  box.appendChild(title);

  if (data.landscape_summary) {
    box.appendChild(withEstimateMarks(data.landscape_summary));
  }

  const competitors = data.competitors || [];
  if (competitors.length) {
    const wrap = document.createElement("div");
    wrap.className = "tablewrap";

    const table = document.createElement("table");
    const head = document.createElement("tr");
    const columns = ["Competitor", "Type", "What they offer", "Target customer", "Weak spots"];
    for (const column of columns) {
      const th = document.createElement("th");
      th.textContent = column;
      head.appendChild(th);
    }
    table.appendChild(head);

    for (const competitor of competitors) {
      const row = document.createElement("tr");

      const name = document.createElement("td");
      name.className = "cname";
      name.textContent = competitor.name;
      row.appendChild(name);

      const type = document.createElement("td");
      const tag = document.createElement("span");
      tag.className = "tag tag--" + (competitor.type || "unknown");
      tag.textContent = competitor.type || "";
      // The agent explains its own classification; show it on hover.
      if (competitor.why_this_type) tag.title = competitor.why_this_type;
      type.appendChild(tag);
      row.appendChild(type);

      for (const key of ["offering", "target_customer", "weak_spots"]) {
        const cell = document.createElement("td");
        cell.textContent = competitor[key] || "";
        row.appendChild(cell);
      }
      table.appendChild(row);
    }
    wrap.appendChild(table);
    box.appendChild(wrap);
  }

  if (data.market_gaps) {
    const h = document.createElement("h3");
    h.textContent = "Gaps nobody is serving";
    box.appendChild(h);
    box.appendChild(withEstimateMarks(data.market_gaps));
  }

  appendResearchLeads(box, "Competitor search leads (not confirmed competitors)", data.research_leads);
  addAskButton(box, "Competitor analysis");
  return box;
}

function buildErrors(errors) {
  const box = document.createElement("section");
  box.className = "run-notice";
  box.setAttribute("aria-label", "Validation limitations");

  const hasQuotaError = errors.some(function (error) {
    return /429|RESOURCE_EXHAUSTED|quota|rate.?limit/i.test(error);
  });
  const failedAgents = [];
  for (const agent of ["Market", "Competitor", "SWOT", "MVP", "GTM"]) {
    if (errors.some((error) => error.startsWith(agent + " agent"))) {
      failedAgents.push(agent);
    }
  }

  const heading = document.createElement("h3");
  heading.textContent = hasQuotaError
    ? "AI provider quota reached — partial results are available"
    : "Some analysis could not be completed";
  box.appendChild(heading);

  const explanation = document.createElement("p");
  if (hasQuotaError) {
    explanation.textContent =
      "Gemini’s free request quota is exhausted. You do not need to pay to keep using Litmus: search, the advisor, PDF reports, and clearly labelled strategy drafts remain available. Market and competitor sections may show search leads rather than verified analysis. Full Gemini analysis can resume when free quota is available again.";
  } else {
    explanation.textContent =
      "The pipeline returned the sections it could complete. Any unavailable sections are identified below; available research and the PDF report remain usable.";
  }
  box.appendChild(explanation);

  if (failedAgents.length) {
    const affected = document.createElement("p");
    affected.className = "run-notice__affected";
    affected.textContent = "Affected agents: " + failedAgents.join(", ") + ".";
    box.appendChild(affected);
  }

  const technical = document.createElement("details");
  technical.className = "run-notice__details";
  const summary = document.createElement("summary");
  summary.textContent = "Technical details";
  technical.appendChild(summary);
  const list = document.createElement("ul");
  for (const error of errors) {
    const item = document.createElement("li");
    item.textContent = error;
    list.appendChild(item);
  }
  technical.appendChild(list);
  box.appendChild(technical);
  return box;
}

function addAskButton(box, title) {
  const ask = document.createElement("button");
  ask.type = "button";
  ask.className = "ask-about";
  ask.textContent = "Ask about this";
  ask.addEventListener("click", function () {
    openAdvisorDock();
    const advisor = document.querySelector(".advisor textarea");
    if (!advisor) return;
    advisor.value = "Explain the " + title.toLowerCase() + " findings and their implications.";
    advisor.focus();
    advisor.scrollIntoView({
      behavior: window.matchMedia("(prefers-reduced-motion: reduce)").matches ? "auto" : "smooth",
      block: "center"
    });
    document.querySelector(".advisor__form").requestSubmit();
  });
  box.appendChild(ask);
}

function buildSection(title, data) {
  const box = buildGenericAnalysis(title, data);
  box.id = title === "SWOT and execution risks" ? "swot" :
    title === "MVP recommendations" ? "mvp" : "gtm";
  addAskButton(box, title);
  return box;
}

function buildSwot(data) {
  return buildSection("SWOT and execution risks", data);
}

function buildMvp(data) {
  return buildSection("MVP recommendations", data);
}

function buildGtm(data) {
  return buildSection("Go-to-market strategy", data);
}

function buildGenericAnalysis(title, data) {
  const box = document.createElement("section");
  box.className = "analysis";

  const heading = document.createElement("h2");
  heading.textContent = title;
  box.appendChild(heading);

  if (data && typeof data === "object" && data.analysis_mode === "fallback") {
    const notice = document.createElement("p");
    notice.className = "analysis-status";
    notice.textContent = data.analysis_note || "Conservative fallback; model-generated analysis was unavailable.";
    box.appendChild(notice);
  }

  box.appendChild(renderAnalysisValue(data));

  return box;
}


function renderAnalysisValue(value) {
  const container = document.createElement("div");

  if (value === null || value === undefined || value === "") {
    container.textContent = "Not available in this validation run.";
    return container;
  }

  if (Array.isArray(value)) {
    const list = document.createElement("ul");

    for (const item of value) {
      const li = document.createElement("li");
      li.appendChild(renderAnalysisValue(item));
      list.appendChild(li);
    }

    container.appendChild(list);
    return container;
  }

  if (typeof value === "object") {
    for (const [key, item] of Object.entries(value)) {
      if (key === "analysis_mode" || key === "analysis_note") continue;
      if (item === null || item === undefined || item === "") continue;

      const heading = document.createElement("h3");
      heading.textContent = key.replaceAll("_", " ");
      container.appendChild(heading);

      container.appendChild(renderAnalysisValue(item));
    }

    return container;
  }

  container.textContent = String(value);
  return container;
}

function buildAdvisor(data) {
  const box = document.createElement("section");
  box.className = "analysis advisor";
  box.id = "advisor";

  const header = document.createElement("div");
  header.className = "advisor__header";
  const heading = document.createElement("h2");
  heading.textContent = "Talk through your next move";
  header.appendChild(heading);
  const sourceHint = document.createElement("span");
  sourceHint.className = "source-label source-label--report";
  sourceHint.textContent = "Grounded in this report";
  header.appendChild(sourceHint);
  const closeButton = document.createElement("button");
  closeButton.type = "button";
  closeButton.className = "advisor-close";
  closeButton.setAttribute("aria-label", "Close advisor panel");
  closeButton.textContent = "×";
  closeButton.addEventListener("click", closeAdvisorDock);
  header.appendChild(closeButton);
  box.appendChild(header);

  const description = document.createElement("p");
  description.className = "advisor__description";
  description.textContent =
    "Ask a follow-up. The advisor uses this report and cites live search when relevant.";
  box.appendChild(description);

  const history = [];
  const transcript = document.createElement("div");
  transcript.className = "advisor-transcript";
  transcript.setAttribute("aria-label", "Advisor conversation");
  transcript.setAttribute("aria-live", "polite");
  transcript.setAttribute("aria-relevant", "additions");
  const welcomeText =
    "I can help interpret these findings, compare priorities, or turn them into a concrete next step. Try a question below.";
  transcript.appendChild(buildAdvisorMessage("assistant", welcomeText));
  box.appendChild(transcript);

  const suggested = document.createElement("div");
  suggested.className = "suggested-questions";
  const suggestedHeading = document.createElement("p");
  suggestedHeading.textContent = "Good questions to start with";
  suggested.appendChild(suggestedHeading);
  for (const question of [
    "What is the highest-priority risk and how should we mitigate it?",
    "Which MVP feature should we build first?",
    "How can we find our first 100 users?",
  ]) {
    const suggestion = document.createElement("button");
    suggestion.type = "button";
    suggestion.className = "suggested-question";
    suggestion.textContent = question;
    suggestion.addEventListener("click", function () {
      input.value = question;
      form.requestSubmit();
    });
    suggested.appendChild(suggestion);
  }
  box.appendChild(suggested);

  const form = document.createElement("form");
  form.className = "advisor__form";
  const input = document.createElement("textarea");
  input.id = "advisor-question";
  input.name = "question";
  input.rows = 2;
  input.autocomplete = "off";
  input.placeholder = "Ask about a risk, feature, customer, or next step…";
  input.setAttribute("aria-label", "Ask the startup advisor a question");
  form.appendChild(input);
  const button = document.createElement("button");
  button.type = "submit";
  button.textContent = "Send question";
  form.appendChild(button);
  box.appendChild(form);

  input.addEventListener("keydown", function (event) {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      form.requestSubmit();
    }
  });

  form.addEventListener("submit", async function (event) {
    event.preventDefault();
    if (button.disabled) return;
    const question = input.value.trim();
    if (!question) {
      input.focus();
      return;
    }

    button.disabled = true;
    const typing = document.createElement("p");
    typing.className = "advisor-typing";
    typing.setAttribute("role", "status");
    typing.textContent = "Advisor is thinking…";
    transcript.appendChild(typing);

    try {
      const response = await fetch(API_URL + "/advisor", {
        method: "POST",
        headers: {
          "Content-Type": "application/json"
        },
        body: JSON.stringify({
          question: question,
          idea: data.idea,
          market: data.market,
          competitors: data.competitors,
          swot: data.swot,
          mvp: data.mvp,
          gtm: data.gtm,
          results: data.results || [],
          conversation_history: history
        })
      });

      let result;
      try {
        result = await response.json();
      } catch (parseError) {
        throw new Error("The advisor returned an unreadable response. Please try again.");
      }
      if (!response.ok) {
        const detail = result && result.detail;
        const message = typeof detail === "string"
          ? detail
          : Array.isArray(detail)
            ? detail.map((item) => item.msg || item.type || "").filter(Boolean).join("; ")
            : "Advisor request failed (" + response.status + ").";
        throw new Error(message);
      }

      const userMessage = buildAdvisorMessage("user", question);
      const assistantMessage = buildAdvisorMessage("assistant", result.answer || "The advisor could not provide an answer.", result);
      transcript.removeChild(typing);
      transcript.appendChild(userMessage);
      transcript.appendChild(assistantMessage);
      history.push({ role: "user", content: question });
      history.push({ role: "assistant", content: result.answer || "" });
      input.value = "";
    } catch (error) {
      if (typing.parentNode === transcript) transcript.removeChild(typing);
      const networkFailure = error instanceof TypeError ||
        (error && /failed to fetch|networkerror|load failed/i.test(error.message || ""));
      transcript.appendChild(buildAdvisorError(
        networkFailure
          ? "Couldn’t connect to the advisor API at " + API_URL + ". Check API status or try again."
          : error.message || "The advisor request failed. Please try again."
      ));
    } finally {
      button.disabled = false;
    }
  });

  return box;
}

function openAdvisorDock() {
  if (advisorDock.hidden) return;
  document.body.classList.add("advisor-dock-open");
  advisorToggle.setAttribute("aria-expanded", "true");
  advisorToggle.textContent = "Close advisor";
}

function closeAdvisorDock() {
  document.body.classList.remove("advisor-dock-open");
  advisorToggle.setAttribute("aria-expanded", "false");
  advisorToggle.textContent = "Ask Litmus";
  advisorToggle.focus();
}

function buildAdvisorMessage(role, text, result) {
  const article = document.createElement("article");
  article.className = "advisor-message advisor-message--" + role;
  const label = document.createElement("span");
  label.className = "advisor-message__label";
  label.textContent = role === "user" ? "You" : "Litmus advisor";
  article.appendChild(label);

  const content = document.createElement("p");
  content.className = "advisor-message__content";
  content.textContent = text;
  article.appendChild(content);

  if (result && result.analysis_mode === "conservative_fallback") {
    const note = document.createElement("p");
    note.className = "advisor-fallback-note";
    note.textContent = "Report-based fallback · Gemini is temporarily unavailable";
    article.appendChild(note);
  }

  if (result && result.has_sufficient_context === false && Array.isArray(result.missing_context) && result.missing_context.length) {
    const missing = document.createElement("p");
    missing.className = "advisor-missing";
    missing.textContent = "Needs more validation: " + result.missing_context.join(", ");
    article.appendChild(missing);
  }

  if (result && Array.isArray(result.citations) && result.citations.length) {
    const citationList = document.createElement("ul");
    citationList.className = "citations";
    for (const citation of result.citations) {
      if (!citation || typeof citation !== "object") continue;
      const item = document.createElement("li");
      item.className = "citation-item";
      const labelText = citation.label || (citation.url ? "From live search" : "From report");
      const titleText = citation.title || "Supporting source";
      if (citation.url) {
        const link = document.createElement("a");
        link.href = citation.url;
        link.target = "_blank";
        link.rel = "noopener noreferrer";
        link.textContent = labelText + ": " + titleText;
        item.appendChild(link);
      } else {
        item.textContent = labelText + ": " + titleText;
      }
      citationList.appendChild(item);
    }
    article.appendChild(citationList);
  }
  return article;
}

function buildAdvisorError(message) {
  const article = document.createElement("article");
  article.className = "advisor-message advisor-message--error";
  article.setAttribute("role", "alert");
  const label = document.createElement("span");
  label.className = "advisor-message__label";
  label.textContent = "Advisor unavailable";
  const content = document.createElement("p");
  content.className = "advisor-message__content";
  content.textContent = message;
  article.appendChild(label);
  article.appendChild(content);
  return article;
}
async function downloadReport(data, button) {
  button.disabled = true;
  const original = button.textContent;
  button.textContent = "Preparing PDF…";
  try {
    const response = await fetch(API_URL + "/report", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(data),
    });
    if (!response.ok) throw new Error("Report request failed (" + response.status + ")");
    const blob = await response.blob();
    if (blob.type !== "application/pdf") throw new Error("The server did not return a PDF.");
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = "litmus-validation-report.pdf";
    document.body.appendChild(link);
    link.click();
    link.remove();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
    statusLine.textContent = "Validation PDF downloaded.";
    statusLine.className = "";
  } catch (error) {
    showApiError(error, "PDF report");
  } finally {
    button.textContent = original;
    button.disabled = false;
  }
}
