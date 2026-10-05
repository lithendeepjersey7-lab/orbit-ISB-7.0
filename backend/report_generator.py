"""Generate a downloadable, evidence-conscious PDF validation report."""

import re
from io import BytesIO

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import (
    HRFlowable,
    KeepTogether,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)
from xml.sax.saxutils import escape


SECTIONS = (
    ("1. Startup Idea / Executive Summary", "executive"),
    ("2. Market Analysis", "market"),
    ("3. Competitor Analysis", "competitors"),
    ("4. SWOT & Risks", "swot"),
    ("5. MVP Recommendations", "mvp"),
    ("6. Go-To-Market Strategy", "gtm"),
    ("7. Validation Score & Verdict", "score"),
    ("8. Roadmap", "roadmap"),
    ("9. Sources", "sources"),
)


def report_filename(idea):
    slug = re.sub(r"[^A-Za-z0-9]+", "-", str(idea)).strip("-").lower()[:48]
    return "litmus-validation-{}.pdf".format(slug or "report")


def _text(value):
    if isinstance(value, (str, int, float, bool)):
        return str(value)
    return ""


def _paragraph(text, style):
    safe = escape(_text(text)).replace("\n", "<br/>")
    return Paragraph(safe or "Not available in this validation run.", style)


def _add_value(story, label, value, styles):
    if value is None or value == "" or value == []:
        return
    story.append(Paragraph(escape(label), styles["Heading3"]))
    if isinstance(value, dict):
        for key, child in value.items():
            _add_value(story, key.replace("_", " ").title(), child, styles)
    elif isinstance(value, list):
        for item in value:
            if isinstance(item, dict):
                lines = [
                    "<b>{}</b>: {}".format(
                        escape(str(key).replace("_", " ").title()),
                        escape(_text(child)),
                    )
                    for key, child in item.items()
                    if not isinstance(child, (dict, list)) and child not in ("", None)
                ]
                nested = [
                    child for child in item.values() if isinstance(child, (dict, list))
                ]
                story.append(Paragraph(" • ".join(lines), styles["BodyText"]))
                for child in nested:
                    _add_value(story, "Details", child, styles)
            else:
                story.append(Paragraph("• " + escape(_text(item)), styles["BodyText"]))
            story.append(Spacer(1, 4))
    else:
        story.append(_paragraph(value, styles["BodyText"]))


def build_validation_report(data):
    """Return a PDF byte string for a completed or partial validation."""
    output = BytesIO()
    doc = SimpleDocTemplate(
        output,
        pagesize=letter,
        rightMargin=0.68 * inch,
        leftMargin=0.68 * inch,
        topMargin=0.65 * inch,
        bottomMargin=0.65 * inch,
        title="Litmus Startup Validation Report",
        author="Litmus",
        pageCompression=0,
    )
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(
        name="ReportTitle",
        parent=styles["Title"],
        alignment=TA_CENTER,
        textColor=colors.HexColor("#203458"),
        spaceAfter=10,
    ))
    styles["Heading2"].textColor = colors.HexColor("#2f5bea")
    styles["Heading3"].textColor = colors.HexColor("#35465e")

    story = [
        Paragraph("Litmus Startup Validation Report", styles["ReportTitle"]),
        Paragraph("Evidence-informed analysis. AI-generated recommendations require independent validation.", styles["Italic"]),
        Spacer(1, 12),
        HRFlowable(width="100%", color=colors.HexColor("#dce3ee")),
    ]

    market = data.get("market") or {}
    competitors = data.get("competitors") or {}
    swot = data.get("swot") or {}
    mvp = data.get("mvp") or {}
    gtm = data.get("gtm") or {}
    sources = data.get("results") or []
    unavailable_modes = {"analysis_unavailable", "evidence_summary", "conservative_fallback", "advisor_unavailable"}

    for title, key in SECTIONS:
        story.append(Paragraph(escape(title), styles["Heading2"]))
        story.append(Spacer(1, 4))
        if key == "executive":
            _add_value(story, "Startup idea", data.get("idea", ""), styles)
            _add_value(story, "Summary", data.get("summary"), styles)
            _add_value(story, "Run status", data.get("errors") or "All available stages completed.", styles)
        elif key == "market":
            _add_value(story, "Market analysis", market, styles)
        elif key == "competitors":
            _add_value(story, "Competitive landscape", competitors, styles)
        elif key == "swot":
            _add_value(story, "SWOT and execution risks", swot, styles)
        elif key == "mvp":
            _add_value(story, "MVP scope and phased build", mvp, styles)
        elif key == "gtm":
            _add_value(story, "Positioning, acquisition and monetization", gtm, styles)
        elif key == "score":
            dimensions = {
                "Market synthesis": bool(market) and market.get("analysis_mode") not in unavailable_modes,
                "Competitor verification": bool(competitors) and competitors.get("analysis_mode") not in unavailable_modes,
                "SWOT analysis": bool(swot) and swot.get("analysis_mode") not in unavailable_modes,
                "MVP recommendation": bool(mvp) and mvp.get("analysis_mode") not in unavailable_modes,
                "GTM strategy": bool(gtm) and gtm.get("analysis_mode") not in unavailable_modes,
            }
            score = round(100 * sum(dimensions.values()) / len(dimensions))
            verdict = (
                "All report analyses completed" if score == 100
                else "Partial AI analysis; consult section limitations" if score >= 40
                else "AI analyses unavailable; review source leads and fallback plans"
            )
            story.append(Paragraph(
                "<b>Evidence coverage score: {}/100</b> — {}".format(score, verdict),
                styles["BodyText"],
            ))
            story.append(Paragraph(
                "This score counts completed model-generated analyses only. Search leads and "
                "conservative fallback drafts are excluded; it is not a startup viability score.",
                styles["Italic"],
            ))
            table = Table(
                [[name, "Available" if present else "Unavailable"] for name, present in dimensions.items()],
                colWidths=[3.8 * inch, 2.0 * inch],
            )
            table.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f4f6fa")),
                ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#dce3ee")),
                ("PADDING", (0, 0), (-1, -1), 6),
            ]))
            story.append(table)
        elif key == "roadmap":
            phases = mvp.get("build_phases") or []
            if phases:
                _add_value(story, "Build phases", phases, styles)
            _add_value(story, "First 90 days", gtm.get("first_90_days"), styles)
        elif key == "sources":
            if sources:
                rows = [["#", "Source", "URL", "Search category"]]
                for index, source in enumerate(sources, 1):
                    rows.append([
                        str(index),
                        _text(source.get("title", "Untitled source"))[:120],
                        _text(source.get("url", ""))[:160],
                        _text(source.get("category", "")),
                    ])
                table = Table(rows, repeatRows=1, colWidths=[0.3 * inch, 2.0 * inch, 3.2 * inch, 1.3 * inch])
                table.setStyle(TableStyle([
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e8eef9")),
                    ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#dce3ee")),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("FONTSIZE", (0, 0), (-1, -1), 7.5),
                    ("WORDWRAP", (0, 0), (-1, -1), "CJK"),
                    ("PADDING", (0, 0), (-1, -1), 5),
                ]))
                story.append(table)
            else:
                story.append(Paragraph("No live sources were available for this run.", styles["BodyText"]))
        story.append(Spacer(1, 10))

    if data.get("errors"):
        story.append(PageBreak())
        story.append(Paragraph("Pipeline Errors and Limitations", styles["Heading2"]))
        _add_value(story, "Unavailable stages", data["errors"], styles)
    doc.build(story)
    return output.getvalue()
