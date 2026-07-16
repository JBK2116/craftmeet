import statistics
from collections import Counter

from src.models import (
    LongAnswerQuestion,
    Meeting,
    MultipleChoiceQuestion,
    Question,
    RankedVotingQuestion,
    RatingScaleQuestion,
    YesNoQuestion,
)
from src.types import QuestionType

SYSTEM_PROMPT = """\
You are an expert meeting analyst. Analyze the provided meeting data and produce a structured JSON summary report.

Guidelines:
- Be concise and data-driven. No filler or speculation.
- Flag outliers, split consensus, and notable patterns explicitly.
- When data is thin or ambiguous, acknowledge uncertainty instead of over-interpreting.
- Produce actionable takeaways, not just observations.
- Write all text in English regardless of the language of participant responses.

Return ONLY a valid JSON object. Do NOT wrap your response in markdown fences (```json) and do NOT include any text outside the JSON object.

JSON structure:
{
  "executive_summary": "<2-3 sentence overview of the entire meeting>",
  "key_takeaways": ["<takeaway>", ...],
  "participation_insight": "<note on overall engagement quality, notable patterns>",
  "questions": [
    {
      "position": <int>,
      "prompt": "<original prompt text>",
      "type": "multiple_choice|long_answer|ranked_voting|rating_scale|yes_no",
      "response_count": <int>,
      "response_rate": <float 0-100>,
      "headline": "<one-line finding summarizing this question's result>",
      "narrative": "<2-4 sentence analysis with context and interpretation>",
      "details": { ... }
    }
  ]
}

Per-type "details" shapes:
- multiple_choice: {"options": [{"label": "<text>", "votes": <int>, "pct": <float>}, ...], "allow_multiple": <bool>}
- yes_no: {"yes_count": <int>, "no_count": <int>, "yes_pct": <float>, "no_pct": <float>}
- rating_scale: {"min": <int>, "max": <int>, "average": <float>, "median": <float>, "distribution": {"<value>": <count>, ...}}
- ranked_voting: {"items": [{"label": "<text>", "average_rank": <float>, "first_place_count": <int>}, ...]}
- long_answer: {"themes": ["<theme>", ...], "sample_size": <int>}"""


def generate_summary_prompt(meeting: Meeting) -> dict[str, str]:
    """Build system and user prompts for AI meeting summarization.

    Args:
        meeting: Meeting with all relationships eagerly loaded
                 (stats, questions, and their subtype + response collections).

    Returns:
        Dict with ``system`` and ``user`` keys, ready for an OpenAI
        chat-completion call.
    """
    return {"system": SYSTEM_PROMPT, "user": _build_user_prompt(meeting)}


def _build_user_prompt(meeting: Meeting) -> str:
    lines: list[str] = []
    total_participants = meeting.stats.total_participants if meeting.stats else 0

    # Meeting header
    lines.append(f'MEETING: "{meeting.title}"')
    if meeting.description:
        lines.append(f"Description: {meeting.description}")

    duration_parts = [f"Max duration: {meeting.duration} min"]
    if meeting.stats and meeting.stats.duration_seconds is not None:
        duration_parts.append(f"Actual: {meeting.stats.duration_seconds // 60} min")
    lines.append(" | ".join(duration_parts))
    lines.append(f"Participants: {total_participants}")

    # Stats overview
    if meeting.stats:
        lines.append(
            f"Questions asked: {meeting.stats.total_questions_asked}  "
            f"Total responses: {meeting.stats.total_responses_received}  "
            f"Avg response rate: {meeting.stats.average_response_rate:.0%}"
        )

    lines.append("")

    # Per-question breakdown
    for question in meeting.questions:
        lines.append(_format_question(question, total_participants))
        lines.append("")

    # Final instruction
    lines.append(
        "Analyze the above meeting data and return the JSON summary as specified."
    )
    return "\n".join(lines)


def _format_question(question: Question, total_participants: int) -> str:
    """Route a question to its type-specific formatter and return the
    complete formatted block."""
    responses: list = _get_responses(question)
    response_count = len(responses)
    response_rate = (
        (response_count / total_participants * 100) if total_participants else 0.0
    )

    header = (
        f"Q{question.position} | {question.type.value} | "
        f"{response_count}/{total_participants} responses ({response_rate:.0f}%)"
    )
    parts = [header, f'Prompt: "{question.prompt}"']

    # Delegate to type-specific detail formatter
    match question.type:
        case QuestionType.MULTIPLE_CHOICE if question.multiple_choice:
            detail_lines = _format_multiple_choice(question.multiple_choice)
        case QuestionType.YES_NO if question.yes_no:
            detail_lines = _format_yes_no(question.yes_no)
        case QuestionType.RATING_SCALE if question.rating_scale:
            detail_lines = _format_rating_scale(question.rating_scale)
        case QuestionType.RANKED_VOTING if question.ranked_voting:
            detail_lines = _format_ranked_voting(question.ranked_voting)
        case QuestionType.LONG_ANSWER if question.long_answer:
            detail_lines = _format_long_answer(question.long_answer)
        case _:
            detail_lines = ["(No subtype data available)"]

    parts.extend(detail_lines)
    return "\n".join(parts)


def _get_responses(question: Question) -> list:
    """Return the response list for a question regardless of its type."""
    match question.type:
        case QuestionType.MULTIPLE_CHOICE if question.multiple_choice:
            return question.multiple_choice.responses
        case QuestionType.LONG_ANSWER if question.long_answer:
            return question.long_answer.responses
        case QuestionType.RANKED_VOTING if question.ranked_voting:
            return question.ranked_voting.responses
        case QuestionType.RATING_SCALE if question.rating_scale:
            return question.rating_scale.responses
        case QuestionType.YES_NO if question.yes_no:
            return question.yes_no.responses
        case _:
            return []


def _format_multiple_choice(mcq: MultipleChoiceQuestion) -> list[str]:
    """Format multiple-choice options with vote tallies."""
    lines: list[str] = []
    options: dict[int, dict] = {}
    for i, opt in enumerate(
        [mcq.option_1, mcq.option_2, mcq.option_3, mcq.option_4], start=1
    ):
        if opt is not None:
            options[i] = {"label": opt, "count": 0}

    total_selections = 0
    for r in mcq.responses:
        for sel in r.selected_options:
            if sel in options:
                options[sel]["count"] += 1
                total_selections += 1

    if mcq.allow_multiple:
        lines.append("(Multi-select allowed)")

    lines.append("Votes:")
    for idx, data in options.items():
        pct = (data["count"] / total_selections * 100) if total_selections else 0.0
        lines.append(f"  {idx}) {data['label']}: {data['count']} ({pct:.0f}%)")

    return lines


def _format_yes_no(ynq: YesNoQuestion) -> list[str]:
    """Format yes/no tallies."""
    yes_count = sum(1 for r in ynq.responses if r.value)
    total = len(ynq.responses)
    no_count = total - yes_count
    yes_pct = (yes_count / total * 100) if total else 0.0
    no_pct = (no_count / total * 100) if total else 0.0
    return [
        f"Results: Yes = {yes_count} ({yes_pct:.0f}%)  No = {no_count} ({no_pct:.0f}%)"
    ]


def _format_rating_scale(rsq: RatingScaleQuestion) -> list[str]:
    """Format rating-scale distribution with summary statistics."""
    values = [r.value for r in rsq.responses]
    if not values:
        return ["No responses."]

    avg = statistics.mean(values)
    med = statistics.median(values)
    dist = Counter(values)

    lines = [
        f"Scale: {rsq.min}–{rsq.max}",
        f"Average: {avg:.1f}  Median: {med:.0f}  "
        f"Min: {min(values)}  Max: {max(values)}",
        "Distribution:",
    ]
    for val in sorted(dist):
        lines.append(f"  {val}: {dist[val]} response(s)")

    return lines


def _format_ranked_voting(rvq: RankedVotingQuestion) -> list[str]:
    """Format ranked-voting items with average rank and first-place counts."""
    lines: list[str] = []
    items: dict[int, dict] = {}
    for i, item in enumerate([rvq.item_1, rvq.item_2, rvq.item_3, rvq.item_4], start=1):
        if item is not None:
            items[i] = {"label": item, "ranks": [], "first_place": 0}

    for r in rvq.responses:
        for rank_num, item_num in [
            (1, r.rank_1),
            (2, r.rank_2),
            (3, r.rank_3),
            (4, r.rank_4),
        ]:
            if item_num is not None and item_num in items:
                items[item_num]["ranks"].append(rank_num)
                if rank_num == 1:
                    items[item_num]["first_place"] += 1

    lines.append("Items (rank 1 = highest priority):")
    for idx, data in items.items():
        avg_rank = statistics.mean(data["ranks"]) if data["ranks"] else float("inf")
        rank_str = f"{avg_rank:.1f}" if avg_rank != float("inf") else "N/A"
        lines.append(
            f"  {idx}) {data['label']}: avg rank {rank_str}  "
            f"{data['first_place']} first-place vote(s)"
        )

    return lines


def _format_long_answer(laq: LongAnswerQuestion) -> list[str]:
    """Format long-answer responses, capped for token budget."""
    if not laq.responses:
        return ["No responses."]

    max_entries = 20
    max_chars = 200

    lines = [f"Responses ({len(laq.responses)}):"]
    for i, r in enumerate(laq.responses[:max_entries]):
        content = r.content[:max_chars]
        if len(r.content) > max_chars:
            content += "…"
        lines.append(f"  [{i + 1}] {content}")

    if len(laq.responses) > max_entries:
        lines.append(f"  … (+{len(laq.responses) - max_entries} more responses)")

    return lines
