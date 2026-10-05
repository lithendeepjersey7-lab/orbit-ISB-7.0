// Opened from disk or localhost, talk to the local backend. Served from
// Vercel, talk to Render. This means the file is never edited back and forth
// before a push, which is the usual way a deploy ends up pointing at
// localhost.
const LOCAL = ["localhost", "127.0.0.1", ""].includes(location.hostname);
let latestValidation = null;

const API_URL = LOCAL
  ? "http://127.0.0.1:8000"
  : "https://orbit-isb-7-0-staging.onrender.com";

const ideaBox = document.getElementById("idea");
const submitButton = document.getElementById("submit");
const statusLine = document.getElementById("status");
const resultsBox = document.getElementById("results");

submitButton.addEventListener("click", validateIdea);

async function validateIdea() {
  const idea = ideaBox.value.trim();

  if (idea.length < 10) {
    statusLine.textContent = "Please write a bit more about your idea.";
    statusLine.className = "error";
    return;
  }

  statusLine.className = "";
  resultsBox.innerHTML = "";
  submitButton.disabled = true;

  // A full run takes about a minute on Render's free tier, which gives the
  // backend a tenth of a CPU. Without these updates the page looks frozen,
  // so say which agent is working rather than showing one static message.
  const stages = [
    [0, "Searching the web..."],
    [4, "Reading the results. The market and competitor agents are running..."],
    [25, "Running SWOT, MVP, and go-to-market analyses..."],
    [75, "The analysis is taking longer than usual; the pipeline is still running..."],
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
    data = await response.json();
    if (!response.ok) {
      throw new Error(
        typeof data.detail === "string"
          ? data.detail
          : "Validation failed with status " + response.status
      );
    }
  } catch (error) {
    clearInterval(ticker);
    statusLine.textContent =
      error.message || "Could not reach the API. Is the backend running?";
    statusLine.className = "error";
    submitButton.disabled = false;
    return;
  }

  clearInterval(ticker);
  showResults(data);
  statusLine.textContent =
    data.results.length + " sources found in " + data.elapsed_seconds + "s";
  submitButton.disabled = false;
}

function showResults(data) {
  if (!data || typeof data !== "object") {
    statusLine.textContent = "The validation service returned an invalid response.";
    statusLine.className = "error";
    submitButton.disabled = false;
    return;
  }
  if (data.summary) {
    const summary = document.createElement("div");
    summary.className = "summary";
    summary.textContent = data.summary;
    resultsBox.appendChild(summary);
  }

  if (data.errors && data.errors.length) {
    resultsBox.appendChild(buildErrors(data.errors));
  }

  latestValidation = data;

  const reportButton = document.createElement("button");
  reportButton.type = "button";
  reportButton.className = "download-report";
  reportButton.textContent = "Download PDF validation report";
  reportButton.addEventListener("click", () => downloadReport(data, reportButton));
  resultsBox.appendChild(reportButton);

  resultsBox.appendChild(buildAgentRun(data));

  // The analysis comes before the raw sources. A founder wants the conclusion
  // first and the evidence underneath it, not the other way round.
  if (data.market) resultsBox.appendChild(buildMarket(data.market));
  if (data.competitors) resultsBox.appendChild(buildCompetitors(data.competitors));
  if (data.swot) resultsBox.appendChild(buildSwot(data.swot));
  if (data.mvp) resultsBox.appendChild(buildMvp(data.mvp));
  if (data.gtm) resultsBox.appendChild(buildGtm(data.gtm));
  resultsBox.appendChild(buildAdvisor(data));

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
  resultsBox.appendChild(queries);

  // Show the sources grouped under the angle that found them
  for (const category of data.categories || []) {
    const group = (data.results || []).filter((r) => r.category === category);
    if (group.length === 0) continue;

    const label = document.createElement("h2");
    label.className = "category";
    label.textContent = category;

    const count = document.createElement("span");
    count.textContent = group.length + (group.length === 1 ? " source" : " sources");
    label.appendChild(count);

    resultsBox.appendChild(label);

    for (const result of group) {
      resultsBox.appendChild(buildCard(result));
    }
  }
}

function buildAgentRun(data) {
  const stats = data.stats || {};
  const panel = document.createElement("div");
  panel.className = "agentrun";

  const heading = document.createElement("h3");
  heading.textContent = "Agent run";
  panel.appendChild(heading);

  const row = document.createElement("div");
  row.className = "stats";

  const tiles = [
    [5, "Analysis agents"],
    [stats.searches_run, "Searches, in parallel"],
    [stats.duplicates_removed, "Duplicates removed"],
    [stats.distinct_sites, "Distinct sites"],
  ];

  for (const [value, label] of tiles) {
    const tile = document.createElement("div");
    tile.className = "stat";

    const v = document.createElement("span");
    v.className = "stat__value";
    v.textContent = value;

    const l = document.createElement("span");
    l.className = "stat__label";
    l.textContent = label;

    tile.appendChild(v);
    tile.appendChild(l);
    row.appendChild(tile);
  }

  panel.appendChild(row);

  const foot = document.createElement("p");
  foot.className = "agentrun__foot";
  foot.textContent =
    (stats.shown || 0) + " sources gathered and analysed across the validation pipeline in " +
    data.elapsed_seconds + "s total";
  panel.appendChild(foot);

  return panel;
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

  addAskButton(box, "Market analysis");
  return box;
}

function buildCompetitors(data) {
  const box = document.createElement("section");
  box.className = "analysis";

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

  addAskButton(box, "Competitor analysis");
  return box;
}

function buildErrors(errors) {
  // The pipeline returns whatever worked plus a list of what did not, so the
  // page shows partial results instead of a blank screen.
  const box = document.createElement("div");
  box.className = "agenterrors";

  const h = document.createElement("h3");
  h.textContent = "Part of this run did not complete";
  box.appendChild(h);

  const list = document.createElement("ul");
  for (const error of errors) {
    const item = document.createElement("li");
    item.textContent = error;
    list.appendChild(item);
  }

  box.appendChild(list);
  return box;
}

function addAskButton(box, title) {
  const ask = document.createElement("button");
  ask.type = "button";
  ask.className = "ask-about";
  ask.textContent = "Ask about this";
  ask.addEventListener("click", function () {
    const advisor = document.querySelector(".advisor textarea");
    if (!advisor) return;
    advisor.value = "Explain the " + title.toLowerCase() + " findings and their implications.";
    advisor.focus();
    advisor.scrollIntoView({ behavior: "smooth", block: "center" });
    document.querySelector(".advisor > button").click();
  });
  box.appendChild(ask);
}

function buildSection(title, data) {
  const box = buildGenericAnalysis(title, data);
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

  const heading = document.createElement("h2");
  heading.textContent = "Conversational Startup Advisor";
  box.appendChild(heading);

  const description = document.createElement("p");
  description.textContent =
    "Ask a follow-up question about this startup validation.";
  box.appendChild(description);

  const input = document.createElement("textarea");
  input.rows = 3;
  input.placeholder =
    "Example: What is the biggest risk for this startup?";
  box.appendChild(input);

  const button = document.createElement("button");
  button.type = "button";
  button.textContent = "Ask Advisor";
  box.appendChild(button);

  const answer = document.createElement("div");
  answer.className = "advisor-answer";
  box.appendChild(answer);
  const history = [];
  const suggested = document.createElement("div");
  suggested.className = "suggested-questions";
  const suggestedHeading = document.createElement("p");
  suggestedHeading.textContent = "Suggested questions";
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
      button.click();
    });
    suggested.appendChild(suggestion);
  }
  box.insertBefore(suggested, input);

  button.addEventListener("click", async function () {
    const question = input.value.trim();

    if (!question) {
      answer.textContent = "Please enter a question.";
      return;
    }

    button.disabled = true;
    answer.textContent = "Advisor is thinking...";
    let serverMessage = "";

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

      if (!response.ok) {
        // The backend explains why (for example Gemini unavailable). Show that
        // instead of claiming the server could not be reached.
        try {
          const body = await response.json();
          if (typeof body.detail === "string") serverMessage = body.detail;
        } catch (parseError) {}
        throw new Error("Advisor request failed");
      }

      const result = await response.json();

      answer.textContent =
        result.answer || "The advisor could not provide an answer.";
      if (result.has_sufficient_context === false && result.missing_context.length) {
        const missing = document.createElement("p");
        missing.className = "advisor-missing";
        missing.textContent = "Needs validation: " + result.missing_context.join(", ");
        answer.appendChild(missing);
      }
      if (result.citations && result.citations.length) {
        const citationList = document.createElement("ul");
        citationList.className = "citations";
        for (const citation of result.citations) {
          const item = document.createElement("li");
          const label = citation.label || "From report";
          if (citation.url) {
            const link = document.createElement("a");
            link.href = citation.url;
            link.target = "_blank";
            link.rel = "noopener noreferrer";
            link.textContent = label + ": " + citation.title;
            item.appendChild(link);
          } else {
            item.textContent = label + ": " + citation.title;
          }
          citationList.appendChild(item);
        }
        answer.appendChild(citationList);
      }
      history.push({ role: "user", content: question });
      history.push({ role: "assistant", content: result.answer || "" });
      input.value = "";
    } catch (error) {
      answer.textContent =
        serverMessage || "Could not reach the advisor. Please try again.";
    } finally {
      button.disabled = false;
    }

  });

  return box;
}

async function downloadReport(data, button) {
  button.disabled = true;
  const original = button.textContent;
  button.textContent = "Preparing PDF...";
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
    link.click();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  } catch (error) {
    statusLine.textContent = error.message || "Could not generate the PDF report.";
    statusLine.className = "error";
  } finally {
    button.textContent = original;
    button.disabled = false;
  }
}
