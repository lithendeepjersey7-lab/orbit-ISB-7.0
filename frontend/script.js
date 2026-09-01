const API_URL = "https://orbit-isb-7-0-staging.onrender.com";

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

  statusLine.textContent = "Searching the web...";
  statusLine.className = "";
  resultsBox.innerHTML = "";
  submitButton.disabled = true;

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
    statusLine.textContent = "Could not reach the API. Is the backend running?";
    statusLine.className = "error";
    submitButton.disabled = false;
    return;
  }

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

  resultsBox.appendChild(buildAgentRun(data.stats));

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

function buildAgentRun(stats) {
  const panel = document.createElement("div");
  panel.className = "agentrun";

  const heading = document.createElement("h3");
  heading.textContent = "Agent run";
  panel.appendChild(heading);

  const row = document.createElement("div");
  row.className = "stats";

  const tiles = [
    [stats.searches_run, "Searches, in parallel"],
    [stats.raw_results, "Results retrieved"],
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
  foot.textContent = stats.shown + " sources shown in " + stats.elapsed_seconds + "s";
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