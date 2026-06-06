"""
AI Service — Meeting summaries, task extraction, daily to-do using OpenAI.
"""

from openai import AsyncOpenAI
from app.core.config import settings
from app.core.config import settings
from datetime import date

client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)


async def generate_meeting_summary(transcript_or_notes: str) -> dict:
    """Generate structured meeting summary from notes or transcript."""

    if not settings.OPENAI_API_KEY:
        return {
            "summary": "AI not configured. Please add OPENAI_API_KEY in .env",
            "decisions": [],
            "action_items": [],
            "pending_approvals": [],
        }

    prompt = f"""
Analyze the following meeting notes/transcript. Create a professional meeting summary.

Extract:
1. Key Discussion Points (bullet list)
2. Decisions Taken (numbered list)
3. Action Items — each with: task_title, owner_name, deadline (if mentioned), priority
4. Pending Approvals (if any)
5. Next Follow-up Points

Meeting Content:
{transcript_or_notes}

Respond in JSON format:
{{
  "summary": "2-3 line executive summary",
  "key_points": ["point 1", "point 2"],
  "decisions": ["decision 1", "decision 2"],
  "action_items": [
    {{"title": "task", "owner": "name", "deadline": "date or Needs Confirmation", "priority": "high/medium/low"}}
  ],
  "pending_approvals": ["approval 1"],
  "next_followup": "suggested date or topic"
}}
"""

    response = await client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_object"},
        temperature=0.3,
    )

    import json
    return json.loads(response.choices[0].message.content)


async def extract_tasks_from_text(text: str) -> list:
    """Extract actionable tasks from any text input."""

    if not settings.OPENAI_API_KEY:
        return []

    prompt = f"""
From the following text, identify all actionable tasks.

For each task provide:
- title
- description
- responsible_person (name if mentioned, else 'Needs Confirmation')
- deadline (if mentioned, else 'Needs Confirmation')
- priority (high/medium/low)
- dependency (if any)

Text:
{text}

Respond as JSON array:
[
  {{
    "title": "task title",
    "description": "details",
    "responsible_person": "name",
    "deadline": "date or Needs Confirmation",
    "priority": "high",
    "dependency": "none"
  }}
]
"""

    response = await client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_object"},
        temperature=0.3,
    )

    import json
    result = json.loads(response.choices[0].message.content)
    # handle both {"tasks": [...]} and plain [...]
    if isinstance(result, list):
        return result
    return result.get("tasks", result.get("action_items", []))


async def generate_daily_todo(context: dict) -> str:
    """Generate morning priority to-do list for Prakhar Sir."""

    if not settings.OPENAI_API_KEY:
        return "AI not configured. Please add OPENAI_API_KEY."

    prompt = f"""
Generate a morning executive priority list for Prakhar Bagora.

Context:
- Overdue Tasks: {context.get('overdue_tasks', [])}
- Today's Deadlines: {context.get('todays_tasks', [])}
- Pending Decisions: {context.get('pending_decisions', [])}
- Today's Meetings: {context.get('meetings', [])}
- EOD Non-submitters from yesterday: {context.get('eod_non_submitters', [])}

Create a clear, action-oriented priority list. Format it as a WhatsApp message.
Start with: Good Morning Prakhar Sir,
Then list priorities in order of urgency.
Keep it concise and actionable.
"""

    response = await client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.4,
    )

    return response.choices[0].message.content
