import html
import re


def _label(value):
    return " ".join(part.capitalize() for part in value.replace("_", " ").split())


def _render_value(value):
    if isinstance(value, dict):
        rows = []
        for key, item in value.items():
            if item is None or item == "" or item == [] or item == {}:
                continue
            rows.append(
                "<div class=\"report-field\"><dt>"
                + html.escape(_label(str(key)))
                + "</dt><dd>"
                + _render_value(item)
                + "</dd></div>"
            )
        return "<dl>" + "".join(rows) + "</dl>" if rows else ""

    if isinstance(value, list):
        items = [item for item in value if item is not None and item != ""]
        if not items:
            return ""
        if all(not isinstance(item, (dict, list)) for item in items):
            return "<ul>" + "".join(
                "<li>" + html.escape(str(item)) + "</li>" for item in items
            ) + "</ul>"
        return "<div class=\"report-items\">" + "".join(
            "<div class=\"report-item\">" + _render_value(item) + "</div>"
            for item in items
        ) + "</div>"

    if isinstance(value, bool):
        return "Yes" if value else "No"
    if value is None or value == "":
        return ""
    return html.escape(str(value)).replace("\n", "<br>")


def _section(title, data):
    rendered = _render_value(data)
    if not rendered:
        rendered = '<p class="unavailable">Not available in this validation run.</p>'
    return (
        "<section><h2>" + html.escape(title) + "</h2>"
        + rendered + "</section>"
    )


def build_validation_report(validation_result):
    """Build a self-contained HTML report from the pipeline's result object."""
    result = validation_result if isinstance(validation_result, dict) else {}
    executive_summary = {
        "startup_idea": result.get("idea"),
        "summary": result.get("summary"),
    }
    sections = [
        _section("1. Startup Idea / Executive Summary", executive_summary),
        _section("2. Market Analysis", result.get("market")),
        _section("3. Competitor Analysis", result.get("competitors")),
        _section("4. SWOT & Risks", result.get("swot")),
        _section("5. MVP Recommendations", result.get("mvp")),
        _section("6. Go-To-Market Strategy", result.get("gtm")),
    ]
    title = html.escape(str(result.get("idea") or "Startup Validation Report"))
    return """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Startup Validation Report</title>
  <style>
    :root { color-scheme: light; --ink: #202a33; --muted: #5e6b75; --line: #d9e0e5; --accent: #245f65; }
    * { box-sizing: border-box; }
    body { margin: 0; background: #eef2f3; color: var(--ink); font: 16px/1.6 Georgia, "Times New Roman", serif; }
    main { max-width: 900px; margin: 36px auto; padding: 52px 64px; background: #fff; box-shadow: 0 8px 32px #15252a18; }
    header { padding-bottom: 24px; border-bottom: 2px solid var(--accent); }
    .eyebrow { margin: 0 0 8px; color: var(--accent); font: 700 12px/1.4 Arial, sans-serif; letter-spacing: .1em; text-transform: uppercase; }
    h1 { margin: 0; font-size: 34px; line-height: 1.2; }
    .idea { margin: 10px 0 0; color: var(--muted); font-size: 18px; }
    section { padding: 22px 0; border-bottom: 1px solid var(--line); break-inside: avoid; }
    h2 { margin: 0 0 14px; color: var(--accent); font: 700 19px/1.35 Arial, sans-serif; }
    dl { margin: 0; }
    .report-field { margin: 0 0 12px; }
    dt { color: var(--muted); font: 700 12px/1.4 Arial, sans-serif; letter-spacing: .04em; text-transform: uppercase; }
    dd { margin: 3px 0 0; }
    ul { margin: 4px 0 12px; padding-left: 22px; }
    .report-items { display: grid; gap: 10px; }
    .report-item { padding: 12px 14px; border-left: 3px solid var(--line); background: #f7f9f9; }
    .report-item dl .report-field:last-child { margin-bottom: 0; }
    .unavailable { margin: 0; color: var(--muted); font-style: italic; }
    @media (max-width: 700px) { main { margin: 0; padding: 28px 22px; } h1 { font-size: 28px; } }
    @media print { body { background: #fff; } main { max-width: none; margin: 0; padding: 0; box-shadow: none; } }
  </style>
</head>
<body>
  <main>
    <header>
      <p class="eyebrow">Litmus · Startup Validation</p>
      <h1>Startup Validation Report</h1>
      <p class="idea">""" + title + "</p>\n    </header>\n    """ + "\n    ".join(sections) + """
  </main>
</body>
</html>"""


def report_filename(idea):
    """Return a filesystem-safe report filename derived from the idea."""
    slug = re.sub(r"[^a-z0-9]+", "-", str(idea).lower()).strip("-")[:48]
    return (slug or "startup-validation") + "-report.html"