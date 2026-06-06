from app.core.config import settings   # ← Yeh missing tha
from datetime import date


try:
    from openai import AsyncOpenAI
    client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
except Exception:
    client = None


async def generate_daily_todo(context: dict) -> str:
    """Generate morning priority to-do list for Prakhar Sir."""

    if not settings.OPENAI_API_KEY:
        return _generate_simple_todo(context)

    if client is None:
        return _generate_simple_todo(context)

    try:
        prompt = f"""
You are an AI Personal Secretary for Prakhar Bagora.
Generate a clear, professional, action-oriented morning priority list.

Today's Date: {context.get('today')}

Data:
- Overdue Tasks: {context.get('overdue_tasks')}
- Today's Tasks: {context.get('todays_tasks')}
- Today's Meetings: {context.get('meetings')}
- Pending Decisions: {context.get('pending_decisions')}
- Delayed Tasks: {context.get('delayed_tasks')}
- EOD Non-Submitters: {context.get('eod_non_submitters')}
- High Priority Pending: {context.get('high_priority_tasks')}

Format EXACTLY like this:

Good Morning Prakhar Sir! 🌅

📅 Aaj ka Date: [date]

🔴 HIGH PRIORITY DECISIONS
1. [item]

⚠️ OVERDUE WORK
1. [item]

📋 TODAY'S TASKS
1. [item]

📅 TODAY'S MEETINGS
1. [item]

👥 TEAM FOLLOW-UPS
1. [item]

🔴 DELAYED TASKS
1. [item]

📝 EOD NOT SUBMITTED (Yesterday)
1. [name]

– AI-PS System
"""
        response = await client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.4,
            max_tokens=1000,
        )
        return response.choices[0].message.content

    except Exception as e:
        # OpenAI fail ho jaye to simple format use karo
        return _generate_simple_todo(context)


def _generate_simple_todo(context: dict) -> str:
    """OpenAI ke bina simple format mein to-do generate karo."""
    today = context.get('today', str(date.today()))
    lines = [f"Good Morning Prakhar Sir! 🌅\n"]
    lines.append(f"📅 Aaj ka Date: {today}\n")

    if context.get('pending_decisions'):
        lines.append("🔴 HIGH PRIORITY DECISIONS")
        for i, t in enumerate(context['pending_decisions'], 1):
            title = t['title'] if isinstance(t, dict) else t
            lines.append(f"  {i}. {title}")
        lines.append("")

    if context.get('overdue_tasks'):
        lines.append("⚠️ OVERDUE WORK")
        for i, t in enumerate(context['overdue_tasks'], 1):
            title = t['title'] if isinstance(t, dict) else t
            lines.append(f"  {i}. {title}")
        lines.append("")

    if context.get('todays_tasks'):
        lines.append("📋 TODAY'S TASKS")
        for i, t in enumerate(context['todays_tasks'], 1):
            title = t['title'] if isinstance(t, dict) else t
            lines.append(f"  {i}. {title}")
        lines.append("")

    if context.get('todays_meetings'):
        lines.append("📅 TODAY'S MEETINGS")
        for i, m in enumerate(context['todays_meetings'], 1):
            title = m['title'] if isinstance(m, dict) else m
            lines.append(f"  {i}. {title}")
        lines.append("")

    if context.get('delayed_tasks'):
        lines.append("🔴 DELAYED TASKS")
        for i, t in enumerate(context['delayed_tasks'], 1):
            title = t['title'] if isinstance(t, dict) else t
            lines.append(f"  {i}. {title}")
        lines.append("")

    if context.get('eod_non_submitters'):
        lines.append("📝 EOD NOT SUBMITTED")
        for i, name in enumerate(context['eod_non_submitters'], 1):
            lines.append(f"  {i}. {name}")
        lines.append("")

    if context.get('high_priority_tasks'):
        lines.append("🔥 HIGH PRIORITY TASKS")
        for i, t in enumerate(context['high_priority_tasks'], 1):
            title = t['title'] if isinstance(t, dict) else t
            lines.append(f"  {i}. {title}")
        lines.append("")

    lines.append("— AI-PS System")
    return "\n".join(lines)


async def generate_meeting_summary(transcript_or_notes: str) -> dict:
    """Generate structured meeting summary from notes or transcript."""

    if not settings.OPENAI_API_KEY or client is None:
        return {
            "summary":          "AI not configured. Add OPENAI_API_KEY in .env",
            "decisions":        [],
            "action_items":     [],
            "pending_approvals": [],
        }

    try:
        import json
        prompt = f"""
Analyze the following meeting notes/transcript.

Extract:
1. Summary (2-3 lines)
2. Key Discussion Points
3. Decisions Taken
4. Action Items — task_title, owner_name, deadline, priority
5. Pending Approvals

Meeting Content:
{transcript_or_notes}

Respond in JSON:
{{
  "summary": "...",
  "key_points": ["..."],
  "decisions": ["..."],
  "action_items": [
    {{"title": "...", "owner": "...", "deadline": "...", "priority": "high/medium/low"}}
  ],
  "pending_approvals": ["..."],
  "next_followup": "..."
}}
"""
        response = await client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
            temperature=0.3,
        )
        return json.loads(response.choices[0].message.content)

    except Exception as e:
        return {
            "summary":          f"Error generating summary: {str(e)}",
            "decisions":        [],
            "action_items":     [],
            "pending_approvals": [],
        }


async def extract_tasks_from_text(text: str) -> list:
    """Extract actionable tasks from any text input."""

    if not settings.OPENAI_API_KEY or client is None:
        return []

    try:
        import json
        prompt = f"""
From the following text, identify all actionable tasks.

For each task:
- title
- description
- responsible_person
- deadline
- priority (high/medium/low)
- dependency

Text:
{text}

Respond as JSON:
{{
  "tasks": [
    {{
      "title": "...",
      "description": "...",
      "responsible_person": "...",
      "deadline": "...",
      "priority": "...",
      "dependency": "..."
    }}
  ]
}}
"""
        response = await client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
            temperature=0.3,
        )
        result = json.loads(response.choices[0].message.content)
        return result.get("tasks", [])

    except Exception as e:
        return []