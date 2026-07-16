import logging
from io import BytesIO

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from src.summary.exceptions import PdfGenerationError
from src.summary.schemas import (
    LongAnswerSummary,
    MCSummary,
    MeetingSummary,
    QuestionSummary,
    RankedVotingSummary,
    RatingScaleSummary,
    YesNoSummary,
)

logger = logging.getLogger(__name__)


_FONT_SIZE_H1 = 18
_FONT_SIZE_H2 = 14
_FONT_SIZE_H3 = 12
_FONT_SIZE_BODY = 10


def _build_styles() -> dict[str, ParagraphStyle]:
    """Create the named paragraph styles used throughout the PDF report.

    Returns:
        A dict mapping style names ("h1", "h2", "body", etc.) to
        :class:`~reportlab.lib.styles.ParagraphStyle` instances.
    """
    base = getSampleStyleSheet()
    return {
        "h1": ParagraphStyle(
            "CM_H1",
            parent=base["Heading1"],
            fontSize=_FONT_SIZE_H1,
            spaceAfter=6 * mm,
            alignment=TA_LEFT,
            textColor=colors.HexColor("#1a1a1a"),
        ),
        "h2": ParagraphStyle(
            "CM_H2",
            parent=base["Heading2"],
            fontSize=_FONT_SIZE_H2,
            spaceBefore=8 * mm,
            spaceAfter=4 * mm,
            textColor=colors.HexColor("#333333"),
        ),
        "h3": ParagraphStyle(
            "CM_H3",
            parent=base["Heading3"],
            fontSize=_FONT_SIZE_H3,
            spaceBefore=6 * mm,
            spaceAfter=2 * mm,
            textColor=colors.HexColor("#555555"),
        ),
        "body": ParagraphStyle(
            "CM_Body",
            parent=base["Normal"],
            fontSize=_FONT_SIZE_BODY,
            leading=14,
            spaceAfter=3 * mm,
        ),
        "takeaway": ParagraphStyle(
            "CM_Takeaway",
            parent=base["Normal"],
            fontSize=_FONT_SIZE_BODY,
            leading=14,
            leftIndent=8 * mm,
            bulletIndent=4 * mm,
            spaceBefore=1 * mm,
            spaceAfter=1 * mm,
        ),
        "headline": ParagraphStyle(
            "CM_Headline",
            parent=base["Normal"],
            fontSize=_FONT_SIZE_BODY + 1,
            leading=16,
            textColor=colors.HexColor("#2c3e50"),
            spaceBefore=2 * mm,
            spaceAfter=2 * mm,
        ),
        "table_header": ParagraphStyle(
            "CM_TH",
            parent=base["Normal"],
            fontSize=_FONT_SIZE_BODY - 1,
            leading=12,
            textColor=colors.white,
            alignment=TA_LEFT,
        ),
        "table_cell": ParagraphStyle(
            "CM_TD",
            parent=base["Normal"],
            fontSize=_FONT_SIZE_BODY - 1,
            leading=12,
        ),
    }


def generate_pdf(summary: MeetingSummary, meeting_title: str) -> bytes:
    """Generate a PDF summary report from a MeetingSummary.

    Args:
        summary: Validated AI-generated meeting summary.
        meeting_title: Title of the meeting to use as the document title.

    Returns:
        The PDF file contents as bytes.

    Raises:
        PdfGenerationError: If PDF generation fails for any reason.
    """
    logger.debug("starting PDF generation for meeting %r", meeting_title)
    try:
        buf = BytesIO()
        doc = SimpleDocTemplate(
            buf,
            pagesize=A4,
            leftMargin=20 * mm,
            rightMargin=20 * mm,
            topMargin=20 * mm,
            bottomMargin=20 * mm,
            title=meeting_title,
            author="CraftMeet",
        )
        styles = _build_styles()
        story = _build_story(summary, meeting_title, styles)
        logger.debug("building PDF document from %d story elements", len(story))
        doc.build(story)
        pdf_bytes = buf.getvalue()
        logger.info(
            "successfully generated PDF for meeting %r (%d bytes)",
            meeting_title,
            len(pdf_bytes),
        )
        return pdf_bytes
    except Exception as e:
        logger.exception("failed to generate PDF: %s", e)
        raise PdfGenerationError from e


def _build_story(
    summary: MeetingSummary, meeting_title: str, styles: dict[str, ParagraphStyle]
) -> list:
    """Assemble the ordered list of Platypus flowables for the PDF.

    Args:
        summary: Validated meeting summary to render.
        meeting_title: Title used as the document's H1 heading.
        styles: Paragraph style dict from :func:`_build_styles`.

    Returns:
        A list of :class:`~reportlab.platypus.Flowable` objects ready for
        :meth:`~reportlab.platypus.SimpleDocTemplate.build`.
    """
    story: list = []

    # Title
    story.append(Paragraph(meeting_title, styles["h1"]))

    # Executive Summary
    story.append(Paragraph("Executive Summary", styles["h2"]))
    story.append(Paragraph(summary.executive_summary, styles["body"]))

    # Key Takeaways
    story.append(Paragraph("Key Takeaways", styles["h2"]))
    for i, takeaway in enumerate(summary.key_takeaways, start=1):
        story.append(Paragraph(f"{i}. {takeaway}", styles["takeaway"]))

    # Participation Insight
    story.append(Paragraph("Participation Insight", styles["h2"]))
    story.append(Paragraph(summary.participation_insight, styles["body"]))

    # Questions
    if summary.questions:
        story.append(Paragraph("Question Results", styles["h2"]))
        for question in summary.questions:
            story.extend(_build_question_section(question, styles))

    return story


def _build_question_section(
    question: QuestionSummary, styles: dict[str, ParagraphStyle]
) -> list:
    """Render a single question's summary into flowable elements.

    Produces the question header (position, prompt, type, response stats),
    headline, narrative, and a type-specific details table.

    Args:
        question: A single question summary from the AI response.
        styles: Paragraph style dict from :func:`_build_styles`.

    Returns:
        List of flowables for this question.
    """
    elements: list = []

    # Question header
    q_type = (
        question.type.value if hasattr(question.type, "value") else str(question.type)
    )
    elements.append(
        Paragraph(
            f"Q{question.position}: {question.prompt}",
            styles["h3"],
        )
    )
    elements.append(
        Paragraph(
            f"Type: {q_type}  |  Responses: {question.response_count}  "
            f"({question.response_rate:.0f}%)",
            styles["body"],
        )
    )

    # Headline
    if question.headline:
        elements.append(Paragraph(f"<b>{question.headline}</b>", styles["headline"]))

    # Narrative
    if question.narrative:
        elements.append(Paragraph(question.narrative, styles["body"]))

    # Type-specific details
    elements.extend(_build_details_table(question, styles))

    elements.append(Spacer(1, 4 * mm))
    return elements


def _build_details_table(
    question: QuestionSummary, styles: dict[str, ParagraphStyle]
) -> list:
    """Dispatch to the correct detail-table builder based on question type.

    Args:
        question: A single question summary whose ``details`` field
                  determines which builder is invoked.
        styles: Paragraph style dict from :func:`_build_styles`.

    Returns:
        List of flowables (table, paragraphs, or empty list if type is
        unrecognized).
    """
    details = question.details

    if isinstance(details, MCSummary):
        return _build_mc_table(details, styles)
    elif isinstance(details, YesNoSummary):
        return _build_yesno_table(details, styles)
    elif isinstance(details, RatingScaleSummary):
        return _build_rating_table(details, styles)
    elif isinstance(details, RankedVotingSummary):
        return _build_ranked_table(details, styles)
    elif isinstance(details, LongAnswerSummary):
        return _build_long_answer_section(details, styles)
    else:
        return []


def _make_table(data: list[list], col_widths: list[int | float] | None = None) -> Table:
    """Create a table with the shared CraftMeet report style.

    Applies a dark header row, alternating body-row backgrounds, grid
    lines, and consistent padding to the given data.

    Args:
        data: Row-oriented table data. The first row is treated as the
              header.
        col_widths: Optional explicit column widths. If ``None``,
                    reportlab auto-sizes columns.

    Returns:
        A styled :class:`~reportlab.platypus.Table` ready for the story.
    """
    t = Table(data, colWidths=col_widths, hAlign="LEFT")
    t.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2c3e50")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTSIZE", (0, 0), (-1, 0), _FONT_SIZE_BODY - 1),
                ("FONTSIZE", (0, 1), (-1, -1), _FONT_SIZE_BODY - 1),
                ("ALIGN", (0, 0), (-1, 0), "LEFT"),
                ("ALIGN", (1, 1), (-1, -1), "CENTER"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cccccc")),
                (
                    "ROWBACKGROUNDS",
                    (0, 1),
                    (-1, -1),
                    [colors.white, colors.HexColor("#f5f6fa")],
                ),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    return t


def _build_mc_table(details: MCSummary, styles: dict[str, ParagraphStyle]) -> list:
    """Build a multiple-choice results table with option labels, vote counts,
    and percentages.

    Args:
        details: Multiple-choice summary from the AI response.
        styles: Paragraph style dict from :func:`_build_styles`.

    Returns:
        List containing an optional multi-select note paragraph followed by
        the results table.
    """
    if not details.options:
        return []
    header = [
        Paragraph("Option", styles["table_header"]),
        Paragraph("Votes", styles["table_header"]),
        Paragraph("%", styles["table_header"]),
    ]
    rows = [header]
    for opt in details.options:
        rows.append(
            [
                Paragraph(opt.label, styles["table_cell"]),
                str(opt.votes),
                f"{opt.pct:.0f}%",
            ]
        )
    if details.allow_multiple:
        return [
            Paragraph("<i>(Multi-select allowed)</i>", styles["body"]),
            _make_table(rows, col_widths=[80 * mm, 30 * mm, 30 * mm]),
        ]
    return [_make_table(rows, col_widths=[80 * mm, 30 * mm, 30 * mm])]


def _build_yesno_table(
    details: YesNoSummary, styles: dict[str, ParagraphStyle]
) -> list:
    """Build a yes/no results table.

    Args:
        details: Yes/no summary from the AI response.
        styles: Paragraph style dict from :func:`_build_styles`.

    Returns:
        List containing the yes/no results table.
    """
    header = [
        Paragraph("Response", styles["table_header"]),
        Paragraph("Count", styles["table_header"]),
        Paragraph("%", styles["table_header"]),
    ]
    rows = [
        header,
        ["Yes", str(details.yes_count), f"{details.yes_pct:.0f}%"],
        ["No", str(details.no_count), f"{details.no_pct:.0f}%"],
    ]
    return [_make_table(rows, col_widths=[80 * mm, 30 * mm, 30 * mm])]


def _build_rating_table(
    details: RatingScaleSummary, styles: dict[str, ParagraphStyle]
) -> list:
    """Build a rating-scale summary with stats line and distribution table.

    Args:
        details: Rating-scale summary from the AI response.
        styles: Paragraph style dict from :func:`_build_styles`.

    Returns:
        List containing a summary-stats paragraph and the distribution table.
    """
    elements: list = []

    # Summary stats
    elements.append(
        Paragraph(
            f"Scale: {details.min}–{details.max}  |  "
            f"Average: {details.average:.1f}  |  Median: {details.median:.0f}",
            styles["body"],
        )
    )

    # Distribution table
    if details.distribution:
        header = [
            Paragraph("Rating", styles["table_header"]),
            Paragraph("Count", styles["table_header"]),
        ]
        rows = [header]
        for val, count in sorted(details.distribution.items(), key=lambda x: int(x[0])):
            rows.append([val, str(count)])
        elements.append(_make_table(rows, col_widths=[70 * mm, 70 * mm]))

    return elements


def _build_ranked_table(
    details: RankedVotingSummary, styles: dict[str, ParagraphStyle]
) -> list:
    """Build a ranked-voting results table.

    Args:
        details: Ranked-voting summary from the AI response.
        styles: Paragraph style dict from :func:`_build_styles`.

    Returns:
        List containing the ranked-voting results table, or an empty list
        when there are no items.
    """
    if not details.items:
        return []
    header = [
        Paragraph("Item", styles["table_header"]),
        Paragraph("Avg Rank", styles["table_header"]),
        Paragraph("1st Place", styles["table_header"]),
    ]
    rows = [header]
    for item in details.items:
        avg_str = (
            f"{item.average_rank:.1f}" if item.average_rank != float("inf") else "N/A"
        )
        rows.append(
            [
                Paragraph(item.label, styles["table_cell"]),
                avg_str,
                str(item.first_place_count),
            ]
        )
    return [_make_table(rows, col_widths=[80 * mm, 30 * mm, 30 * mm])]


def _build_long_answer_section(
    details: LongAnswerSummary, styles: dict[str, ParagraphStyle]
) -> list:
    """Build a long-answer summary with identified themes and sample size.

    Args:
        details: Long-answer summary from the AI response.
        styles: Paragraph style dict from :func:`_build_styles`.

    Returns:
        List containing a themes paragraph and a sample-size note.
    """
    elements: list = []
    if details.themes:
        elements.append(
            Paragraph(
                f"<b>Themes:</b> {', '.join(details.themes)}",
                styles["body"],
            )
        )
    elements.append(Paragraph(f"Sample size: {details.sample_size}", styles["body"]))
    return elements
