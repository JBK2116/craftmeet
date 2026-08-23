import datetime
import uuid

from src.live.schemas import ChatMessage, Participant
from src.meeting.schemas import QuestionOut, ResponseIn
from src.models import Meeting
from src.types import QuestionType

SYSTEM_PROMPT = """\
You are an expert live meeting facilitator. Analyze the current, in-progress meeting and produce a real-time "pulse" snapshot that helps the host understand the room and what to do next.

Guidelines:
- Assess only what the data supports. Do not fabricate or over-interpret thin data; acknowledge uncertainty instead.
- Derive the mood from the tone of long-answer responses and chat, plus engagement signals (response rate, participation, disconnect activity).
- attention_flag must be a short, concrete, actionable note about what the host should look at right now (e.g. "3 of 5 participants have not answered", "Chat sentiment is turning negative"). If nothing needs attention, state that plainly.
- suggested_question_prompt must be a single, ready-to-ask question (one sentence, no answer options) that builds on the meeting topic and the discussion so far, and must not repeat a question that has already been asked.
- Write all text in English regardless of the language of participant responses.

Return ONLY a valid JSON object. Do NOT wrap the response in markdown fences (```json) and do NOT include any text outside the JSON object.

JSON structure:
{
  "mood": "<positive|neutral|negative|mixed|disengaged>",
  "attention_flag": "<short actionable note string>",
  "suggested_question_prompt": "<one ready-to-ask question string>"
}

Mood values:
- "positive": engaged, constructive, optimistic sentiment
- "neutral": balanced or low-signal, no strong sentiment either way
- "negative": frustration, disagreement, or declining sentiment
- "mixed": split opinions or competing strong sentiments
- "disengaged": low participation, little or no response activity
"""


def generate_snapshot_prompt(
    meeting: Meeting,
    asked_questions: list[QuestionOut],
    responses: dict[uuid.UUID, list[ResponseIn]],
    participants: list[Participant],
    chat: list[ChatMessage],
) -> dict[str, str]:
    """Build system and user prompts for the AI live meeting snapshot.

    Args:
        meeting: The lazily loaded meeting (title, description, duration,
            started_at, etc.).
        asked_questions: All questions asked so far, in order (current is last).
        responses: Sub-question ID → list of responses received for it.
        participants: Participants currently tracked in the room.
        chat: All chat messages received so far.

    Returns:
        Dict with ``system`` and ``user`` keys, ready for an OpenAI
        responses call.
    """
    current_question = asked_questions[-1] if asked_questions else None
    current_responses = (
        responses.get(current_question.sub_question.id, []) if current_question else []
    )
    past_questions = asked_questions[:-1]
    return {
        "system": SYSTEM_PROMPT,
        "user": _build_user_prompt(
            meeting=meeting,
            current_question=current_question,
            current_responses=current_responses,
            past_questions=past_questions,
            responses=responses,
            participants=participants,
            chat=chat,
        ),
    }


def _build_user_prompt(
    meeting: Meeting,
    current_question: QuestionOut | None,
    current_responses: list[ResponseIn],
    past_questions: list[QuestionOut],
    responses: dict[uuid.UUID, list[ResponseIn]],
    participants: list[Participant],
    chat: list[ChatMessage],
) -> str:
    lines: list[str] = []
    total_participants = len(participants)
    connected = sum(1 for p in participants if p.connected)

    # Meeting context
    lines.append(f'MEETING: "{meeting.title}"')
    if meeting.description:
        lines.append(f"Description: {meeting.description}")
    lines.append(f"Max duration: {meeting.duration} min")
    if meeting.started_at:
        elapsed = int(
            (
                datetime.datetime.now(tz=datetime.UTC) - meeting.started_at
            ).total_seconds()
        )
        lines.append(f"Elapsed: {elapsed // 60} min")
    lines.append(f"Participants: {total_participants} total, {connected} connected")
    lines.append("")

    # Progress — previously asked questions (brief, for redundancy avoidance)
    if past_questions:
        lines.append("Questions asked so far:")
        for q in past_questions:
            count = len(responses.get(q.sub_question.id, []))
            lines.append(
                f'  Q{q.position} ({q.type.value}): "{q.prompt}" — {count} response(s)'
            )
    else:
        lines.append("Questions asked so far: none.")
    lines.append("")

    # Current question and its live responses
    if current_question is not None:
        answered = sum(1 for p in participants if p.has_answered)
        lines.append(
            f'CURRENT QUESTION (Q{current_question.position}, {current_question.type.value}): "{current_question.prompt}"'
        )
        lines.append(
            f"Responses: {len(current_responses)}/{total_participants}  "
            f"Answered: {answered}/{total_participants}"
        )
        lines.extend(_format_responses(current_question, current_responses))
    else:
        lines.append("Current question: none (meeting has not started).")
    lines.append("")

    # Chat (recent messages only)
    if chat:
        recent = chat[-20:]
        lines.append(f"Chat (last {len(recent)} messages):")
        for m in recent:
            who = "host" if m.is_host else "participant"
            lines.append(f"  [{who}] {m.name}: {m.message}")
    else:
        lines.append("Chat: no messages yet.")
    lines.append("")

    lines.append(
        "Analyze the above live meeting state and return the JSON snapshot as specified."
    )
    return "\n".join(lines)


def _format_responses(question: QuestionOut, responses: list[ResponseIn]) -> list[str]:
    """Route the current question's responses to a type-specific formatter."""
    match question.type:
        case QuestionType.MULTIPLE_CHOICE:
            return _format_multiple_choice(question.sub_question, responses)
        case QuestionType.YES_NO:
            return _format_yes_no(responses)
        case QuestionType.RATING_SCALE:
            return _format_rating_scale(question.sub_question, responses)
        case QuestionType.RANKED_VOTING:
            return _format_ranked_voting(question.sub_question, responses)
        case QuestionType.LONG_ANSWER:
            return _format_long_answer(responses)


def _format_multiple_choice(sub_question, responses: list) -> list[str]:
    options: dict[int, dict] = {}
    for i, opt in enumerate(
        [
            sub_question.option_1,
            sub_question.option_2,
            sub_question.option_3,
            sub_question.option_4,
        ],
        start=1,
    ):
        if opt is not None:
            options[i] = {"label": opt, "count": 0}
    for r in responses:
        for sel in r.selected_options:
            if sel in options:
                options[sel]["count"] += 1
    lines: list[str] = []
    if sub_question.allow_multiple:
        lines.append("(Multi-select allowed)")
    for idx, data in options.items():
        lines.append(f"  {idx}) {data['label']}: {data['count']} vote(s)")
    return lines


def _format_yes_no(responses: list) -> list[str]:
    yes = sum(1 for r in responses if r.value)
    no = len(responses) - yes
    return [f"Yes = {yes}, No = {no}"]


def _format_rating_scale(sub_question, responses: list) -> list[str]:
    values = [r.value for r in responses]
    if not values:
        return ["No responses yet."]
    return [f"Scale {sub_question.min}–{sub_question.max}: {sorted(values)}"]


def _format_ranked_voting(sub_question, responses: list) -> list[str]:
    items: dict[int, dict] = {}
    for i, item in enumerate(
        [
            sub_question.item_1,
            sub_question.item_2,
            sub_question.item_3,
            sub_question.item_4,
        ],
        start=1,
    ):
        if item is not None:
            items[i] = {"label": item, "first": 0}
    for r in responses:
        if r.rank_1 in items:
            items[r.rank_1]["first"] += 1
    lines = ["First-place votes:"]
    for idx, data in items.items():
        lines.append(f"  {idx}) {data['label']}: {data['first']}")
    return lines


def _format_long_answer(
    responses: list, max_entries: int = 20, max_chars: int = 200
) -> list[str]:
    if not responses:
        return ["No responses yet."]
    lines = [f"Responses ({len(responses)}):"]
    for i, r in enumerate(responses[:max_entries]):
        content = r.content[:max_chars]
        if len(r.content) > max_chars:
            content += "…"
        lines.append(f"  [{i + 1}] {content}")
    if len(responses) > max_entries:
        lines.append(f"  … (+{len(responses) - max_entries} more responses)")
    return lines
