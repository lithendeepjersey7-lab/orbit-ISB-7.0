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

  try {
    const response = await fetch(API_URL + "/validate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ idea: idea }),
    });

    const data = await response.json();
    showResults(data);
    statusLine.textContent =
      data.results.length + " sources found in " + data.elapsed_seconds + "s";
  } catch (error) {
    statusLine.textContent = "Could not reach the API. Is the backend running?";
    statusLine.className = "error";
  }

  submitButton.disabled = false;
}

function showResults(data) {
  if (data.summary) {
    const summary = document.createElement("div");
    summary.className = "summary";
    summary.textContent = data.summary;
    resultsBox.appendChild(summary);
  }

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