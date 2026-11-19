"""A saved report as a PDF. IOCs print verbatim; only typography outside Latin-1 is mapped."""
import html

import markdown
from fpdf import FPDF

from app.agent.investigation_models import InvestigationReport

_TYPOGRAPHY = str.maketrans({"—": "-", "–": "-", "‘": "'", "’": "'", "“": '"', "”": '"', "…": "...",
                             "→": "->", "←": "<-", "•": "-", "≥": ">=", "≤": "<=", "✓": "yes", "✗": "no"})


def serial(report_id: str) -> str:
    """Same serial the web app shows: R- and the first six hex digits."""
    return "R-" + report_id.replace("-", "")[:6].upper()


def _latin1(text: str) -> str:
    return text.translate(_TYPOGRAPHY).encode("latin-1", "replace").decode("latin-1")


def _body_html(report: InvestigationReport) -> str:
    # Markdown passes raw HTML through, and the PDF renderer would fetch an <img src> it met. The
    # report is model output, so no tag in it may reach the renderer: "<" is escaped first.
    body = markdown.markdown(report.final_report.replace("<", "&lt;"), extensions=["tables"])
    if report.sources:
        items = "".join(
            f"<li>{html.escape(s.source)}{f' ({html.escape(s.ref_id)})' if s.ref_id else ''}: {html.escape(s.text[:220])}</li>"
            for s in report.sources
        )
        body += f"<h2>Knowledge-base sources</h2><ol>{items}</ol>"
    return body


def build_pdf(report: InvestigationReport) -> bytes:
    pdf = FPDF()
    pdf.set_auto_page_break(True, margin=15)
    pdf.add_page()
    label = serial(report.report_id or "draft")
    pdf.set_title(_latin1(f"ThreatRAG {label}: {report.ioc}"))
    pdf.set_creator("ThreatRAG")
    meta = f"ThreatRAG {label}  |  {report.ioc_type.upper()} {report.ioc}  |  {(report.created_at or '')[:19]}"
    if report.parent_id:
        meta += f"  |  revision of {serial(report.parent_id)}"
    pdf.set_font("Helvetica", "B", 8)
    pdf.set_text_color(90)
    pdf.cell(0, 6, _latin1(meta), new_x="LMARGIN", new_y="NEXT")
    pdf.set_text_color(0)
    pdf.set_font("Helvetica", size=10)
    pdf.write_html(_latin1(_body_html(report)))
    return bytes(pdf.output())
