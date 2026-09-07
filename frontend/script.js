// Opened from disk or localhost, talk to the local backend. Served from
// Vercel, talk to Render. This means the file is never edited back and forth
// before a push, which is the usual way a deploy ends up pointing at
// localhost.
const LOCAL = ["localhost", "127.0.0.1", ""].includes(location.hostname);
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
    [25, "Still working. The free hosting tier is slow, but it is not stuck..."],
    [75, "Taking longer than usual. The backend may be waking from sleep..."],
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
  } catch (error) {
    clearInterval(ticker);
    statusLine.textContent = "Could not reach the API. Is the backend running?";
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
  if (data.summary) {
    const summary = document.createElement("div");
    summary.className = "summary";
    summary.textContent = data.summary;
    resultsBox.appendChild(summary);
  }

  if (data.errors && data.errors.length) {
    resultsBox.appendChild(buildErrors(data.errors));
  }

  resultsBox.appendChild(buildAgentRun(data));

  // The analysis comes before the raw sources. A founder wants the conclusion
  // first and the evidence underneath it, not the other way round.
  if (data.market) resultsBox.appendChild(buildMarket(data.market));
  if (data.competitors) resultsBox.appendChild(buildCompetitors(data.competitors));

  const queries = document.createElement("div");
  queries.className = "queries";

  const heading = document.createElement("h3");
  heading.textContent = "Searches the agent ran:";
  queries.appendChild(heading);

  const list = document.createElement("ol");
  for (const query of data.queries) {
    const item = document.createElement("li");
    item.textContent = query;
    list.appendChild(item);
  }
  queries.appendChild(list);
  resultsBox.appendChild(queries);

  // Show the sources grouped under the angle that found them
  for (const category of data.categories) {
    const group = data.results.filter((r) => r.category === category);
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
  const stats = data.stats;
  const panel = document.createElement("div");
  panel.className = "agentrun";

  const heading = document.createElement("h3");
  heading.textContent = "Agent run";
  panel.appendChild(heading);

  const row = document.createElement("div");
  row.className = "stats";

  const tiles = [
    [3, "Agents run"],
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
    stats.shown + " sources gathered, then analysed by two agents at the same time, in " +
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
